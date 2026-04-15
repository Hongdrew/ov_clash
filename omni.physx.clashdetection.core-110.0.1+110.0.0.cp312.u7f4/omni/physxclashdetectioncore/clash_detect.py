# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any, Dict, List, Callable, Optional, Generator, Tuple, Annotated, Iterator
import sys
import time
import warp as wp
import carb
from pxr import Usd, UsdUtils, Sdf, Gf
from omni.schemaclashdetection.bindings._usdUtils import sdfPathToInt
from omni.physxclashdetection import get_clash_detection_interface2
from omni.physxclashdetection.bindings._clashDetection import MaxLocalDepthMode, MeshIndex, OverlapReportFlag, OverlapData
from .clash_detect_settings import SettingId
from .clash_info import ClashInfo, ClashFrameInfo, OverlapType, ClashState
from .clash_query import ClashQuery
from .clash_data import ClashData
from .utils import make_int128, OptimizedProgressUpdate, get_available_system_memory, clamp_value
from .usd_utils import get_list_of_prim_paths, get_prim_matrix, list_to_matrix, matrix_to_list
from .config import ExtensionConfig
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry


class ClashDetection:
    """
    A class for handling clash detection operations within a USD stage.

    This class provides methods for initializing and managing clash detection pipelines,
    setting configurations, processing overlaps, and handling clash data. It interfaces
    with the underlying clash detection API to perform these operations effectively.
    """

    # Default settings for the clash detection engine.
    # IMPORTANT: make sure all existing settings have default values set!
    DEFAULT_SETTINGS: Dict[SettingId, Any] = {
        SettingId.SETTING_LOGGING: False,

        SettingId.SETTING_DYNAMIC: False,
        SettingId.SETTING_DYNAMIC_START_TIME: 0.0,
        SettingId.SETTING_DYNAMIC_END_TIME: 0.0,
        SettingId.SETTING_PURGE_PERMANENT_OVERLAPS: False,
        SettingId.SETTING_TOLERANCE: 0.0,
        SettingId.SETTING_STATIC_TIME: 0.0,
        SettingId.SETTING_DUP_MESHES: False,
        SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS: False,

        SettingId.SETTING_NEW_TASK_MANAGER: True,
        SettingId.SETTING_SINGLE_THREADED: False,
        SettingId.SETTING_NB_TASKS: 128,

        SettingId.SETTING_POSE_EPSILON: 1e-6,
        SettingId.SETTING_AREA_EPSILON: 1e-6,
        SettingId.SETTING_BOUNDS_EPSILON: 0.01,
        SettingId.SETTING_TIGHT_BOUNDS: True,
        SettingId.SETTING_COPLANAR: True,
        SettingId.SETTING_ANY_HIT: False,
        SettingId.SETTING_QUANTIZED: False,
        SettingId.SETTING_TRIS_PER_LEAF: 15,
        SettingId.SETTING_TRIANGLE_LIMIT: 0,
        SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS: True,
        SettingId.SETTING_USE_USDRT: True,
        SettingId.SETTING_IGNORE_INVISIBLE_PRIMS: True,

        SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH: False,
        SettingId.SETTING_DEPTH_EPSILON: -1.0,
        SettingId.SETTING_CONTACT_CUTOFF: -1.0,
        SettingId.SETTING_DISCARD_TOUCHING_CONTACTS: False,
        SettingId.SETTING_MAX_LOCAL_DEPTH_MODE: 1,

        SettingId.SETTING_OVERLAP_CODE: 3,
        SettingId.SETTING_FILTER_TEST: False,
    }

    def __init__(self) -> None:
        """Initializes the ClashDetection class.

        Creates a new clash detection context and initializes telemetry tracking.
        """
        super().__init__()
        self._clash_detect_api = get_clash_detection_interface2()
        self._context = self._clash_detect_api.create()
        # Telemetry-related data and interfaces to gather stats at runtime
        self._pipeline_started_at: float = 0
        self._available_mem_at_start: int = 0

    def _wp_array_from_sad(self, sz: int, count: int, ptr: int, dtype: Any, dtype_sz: int) -> wp.array:
        """Helper function to convert SAD arrays to Warp arrays."""
        if not self._clash_detect_api:
            return wp.empty(dtype=dtype)
        if ptr == 0 or count == 0 or sz != dtype_sz:
            return wp.empty(dtype=dtype)
        wp_arr = wp.array(
            ptr=ptr,
            dtype=dtype,
            shape=(count,),
            device="cpu",
            copy=wp.bool(False),
            deleter=lambda ptr, _: self._clash_detect_api.release_memory(ptr) if self._clash_detect_api else None
        )
        return wp_arr

    def destroy(self) -> None:
        """Releases resources held by the clash detection context and API.

        This method cleans up the clash detection API and context, freeing any allocated resources.
        After calling this method, the instance will no longer be usable for clash detection operations.
        """
        if self._clash_detect_api:
            self._clash_detect_api.release(self._context)
            self._clash_detect_api = None
        self._context = None

    def reset(self) -> None:
        """Resets the clash detection context to its initial state.

        This method clears any existing clash detection results and settings, returning the context
        to its default state while maintaining the API connection. Use this to start fresh without
        destroying the instance.
        """
        if self._clash_detect_api:
            self._clash_detect_api.reset(self._context)

    @property
    def clash_detect_api(self) -> Any:
        """Gets the low-level clash detection API interface.

        This property provides access to the underlying clash detection API implementation.
        The API can be used for direct low-level operations if needed.

        Returns:
            Any: The clash detection API interface instance, or None if not initialized.
        """
        return self._clash_detect_api

    @property
    def clash_detect_context(self) -> Any:
        """Gets the clash detection context handle.

        The context maintains the state and configuration for clash detection operations.
        This is typically used internally by the API methods.

        Returns:
            Any: The clash detection context handle, or None if not initialized.
        """
        return self._context

    @property
    def is_out_of_memory(self) -> bool:
        """Checks if the clash detection engine encountered memory exhaustion.

        This property indicates whether the last clash detection operation failed due to
        insufficient system memory. This can happen with very large or complex geometry.

        Returns:
            bool: True if the last operation ran out of memory, False otherwise.
        """
        if not self._clash_detect_api:
            return False
        return self._clash_detect_api.is_out_of_memory()

    def get_nb_overlaps(self) -> int:
        """Gets the total number of geometric overlaps detected.

        Counts all intersections between geometry pairs that were found during the last
        clash detection run. This includes both static and dynamic overlaps if dynamic
        detection was enabled.

        Returns:
            int: The total number of overlaps found, or 0 if no clashes detected or API not initialized.
        """
        if not self._clash_detect_api:
            return 0
        return self._clash_detect_api.get_nb_overlaps(self._context)

    def get_nb_duplicates(self) -> int:
        """Gets the number of duplicate meshes detected.

        Counts meshes that are exact geometric duplicates with identical transformations,
        resulting in complete overlap. This is useful for identifying redundant geometry
        that could be optimized.

        Returns:
            int: The number of duplicate meshes found, or 0 if none detected or API not initialized.
        """
        if not self._clash_detect_api:
            return 0
        return self._clash_detect_api.get_nb_duplicate_meshes(self._context)

    @classmethod
    def get_default_setting_value(cls, setting_id: SettingId) -> Any:
        """Returns the default (recommended default) value for a setting. If the setting is not found, returns None.

        Args:
            setting_id (SettingId): The setting ID.

        Returns:
            Any: The default value for the setting. Returns None if the setting is not found.
        """
        setting_value = cls.DEFAULT_SETTINGS.get(setting_id)
        if setting_value is None:
            carb.error(f"Setting {setting_id.name} not found in DEFAULT_SETTINGS!")  # type: ignore
            return None
        return setting_value

    def set_settings(self, settings: Dict[str, Any], stage: Optional[Usd.Stage] = None) -> bool:
        """Sets the settings for the clash detection.

        Settings which are not provided in the dictionary are left unchanged.

        Args:
            settings (Dict[str, Any]): The clash detection settings.
            stage (Usd.Stage): The USD stage.

        Returns:
            bool: True if settings were applied successfully, False otherwise.
        """
        def default_value(setting_id: SettingId) -> Any:
            return ClashDetection.get_default_setting_value(setting_id)

        if not self._clash_detect_api:
            return False
        api = self._clash_detect_api

        query_timeline_start_end_failed = False
        timeline_data = api.get_timeline_data()
        # get values from timeline, but we will use them only if stage is None or when codes_per_second is 0 - USD has priority
        start_time = max(0.0, timeline_data.startTime)
        end_time = max(0.0, timeline_data.endTime)
        codes_per_second = timeline_data.timeCodesPerSecond
        if stage:  # timeline data not available
            usd_codes_per_second = stage.GetTimeCodesPerSecond()
            if usd_codes_per_second:
                codes_per_second = usd_codes_per_second
                start_time = stage.GetStartTimeCode() / codes_per_second
                end_time = stage.GetEndTimeCode() / codes_per_second
            else:
                carb.warning("Cannot determine TimeCodesPerSecond from USD, will try to use timeline values...")  # type: ignore

        if codes_per_second == 0:
            carb.error("Failed to determine TimeCodesPerSecond from both USD and timeline!")  # type: ignore
            query_timeline_start_end_failed = True
            start_time = 0.0
            end_time = 0.0

        if (
            settings.get(SettingId.SETTING_DYNAMIC.name, default_value(SettingId.SETTING_DYNAMIC))
            and not settings.get(SettingId.SETTING_DUP_MESHES.name, default_value(SettingId.SETTING_DUP_MESHES))
        ):
            setting_start_time = settings.get(SettingId.SETTING_DYNAMIC_START_TIME.name, default_value(SettingId.SETTING_DYNAMIC_START_TIME))
            setting_end_time = settings.get(SettingId.SETTING_DYNAMIC_END_TIME.name, default_value(SettingId.SETTING_DYNAMIC_END_TIME))
            api.set_times(
                self._context,
                start_time if setting_start_time == 0.0 else setting_start_time,
                end_time if setting_end_time == 0.0 else setting_end_time,
                codes_per_second,
            )
        else:
            setting_static_time = settings.get(SettingId.SETTING_STATIC_TIME.name, default_value(SettingId.SETTING_STATIC_TIME))
            if query_timeline_start_end_failed:
                setting_static_time = 0.0
            else:
                setting_static_time = clamp_value(setting_static_time, start_time, end_time)
            api.set_times(self._context, setting_static_time, setting_static_time, codes_per_second)

        def safe_set(api_call: Callable[[Any, Any], None], setting_id: SettingId) -> None:
            """Calls the api to set the setting only when the value is not None."""
            val = settings.get(setting_id.name, default_value(setting_id))
            if val is not None:
                api_call(self._context, val)

        safe_set(api.set_log, SettingId.SETTING_LOGGING)
        safe_set(api.set_coplanar, SettingId.SETTING_COPLANAR)
        safe_set(api.set_any_hit, SettingId.SETTING_ANY_HIT)
        safe_set(api.set_quantized, SettingId.SETTING_QUANTIZED)
        safe_set(api.set_tight_bounds, SettingId.SETTING_TIGHT_BOUNDS)
        safe_set(api.set_subcomponent_filtering, SettingId.SETTING_FILTER_TEST)
        safe_set(api.set_single_threaded, SettingId.SETTING_SINGLE_THREADED)
        safe_set(api.set_new_task_manager, SettingId.SETTING_NEW_TASK_MANAGER)
        safe_set(api.set_purge_permanent_dynamic_overlaps, SettingId.SETTING_PURGE_PERMANENT_OVERLAPS)
        safe_set(api.set_purge_permanent_static_overlaps, SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS)
        safe_set(api.set_nb_tasks, SettingId.SETTING_NB_TASKS)
        safe_set(api.set_tris_per_leaf, SettingId.SETTING_TRIS_PER_LEAF)
        safe_set(api.set_overlap_code, SettingId.SETTING_OVERLAP_CODE)
        safe_set(api.set_pose_epsilon, SettingId.SETTING_POSE_EPSILON)
        safe_set(api.set_bounds_epsilon, SettingId.SETTING_BOUNDS_EPSILON)
        safe_set(api.set_area_epsilon, SettingId.SETTING_AREA_EPSILON)
        safe_set(api.set_tolerance, SettingId.SETTING_TOLERANCE)
        safe_set(api.set_only_find_duplicates, SettingId.SETTING_DUP_MESHES)
        safe_set(api.set_use_usdrt, SettingId.SETTING_USE_USDRT)
        safe_set(api.set_triangle_limit, SettingId.SETTING_TRIANGLE_LIMIT)
        safe_set(api.set_ignore_redundant_overlaps, SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS)
        safe_set(api.set_ignore_invisible_prims, SettingId.SETTING_IGNORE_INVISIBLE_PRIMS)

        if settings.get(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name, default_value(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH)):
            mode = settings.get(SettingId.SETTING_MAX_LOCAL_DEPTH_MODE.name, default_value(SettingId.SETTING_MAX_LOCAL_DEPTH_MODE))
            mode_map = {
                0: MaxLocalDepthMode.LEGACY,
                1: MaxLocalDepthMode.MEDIUM,
                2: MaxLocalDepthMode.HIGH,
            }
            api.set_compute_max_local_depth(self._context, mode_map.get(mode, MaxLocalDepthMode.MEDIUM))
        else:
            api.set_compute_max_local_depth(self._context, MaxLocalDepthMode.DISABLED)
        # Clash detection engine can ignore all possible contacts below the depth epsilon value
        # if SETTING_DISCARD_TOUCHING_CONTACTS setting is set and SETTING_DEPTH_EPSILON is set to a positive number.
        # Otherwise the classification is done on our side, nothing is being ignored.
        discard_contacts = settings.get(SettingId.SETTING_DISCARD_TOUCHING_CONTACTS.name, default_value(SettingId.SETTING_DISCARD_TOUCHING_CONTACTS))
        if discard_contacts:
            safe_set(api.set_contact_epsilon, SettingId.SETTING_DEPTH_EPSILON)
        else:
            api.set_contact_epsilon(self._context, default_value(SettingId.SETTING_DEPTH_EPSILON))

        safe_set(api.set_contact_cutoff, SettingId.SETTING_CONTACT_CUTOFF)

        return True

    @classmethod
    def get_list_of_prims_int_paths(
        cls,
        stage: Usd.Stage,
        prim_str_path: str,
        add_prim_children: bool = False,
        prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None
    ) -> Tuple[List[Sdf.Path], List[int]]:
        """
        Gets a list of prims in both Sdf.Path and integer path form.

        Note: The returned Sdf.Path objects must be kept alive while using the integer paths,
        as the integer paths are derived from them.

        Args:
            cls: The class instance.
            stage (Usd.Stage): The USD stage.
            prim_str_path (str): The path to the prim or collection. Can contain multiple paths separated by spaces.
            add_prim_children (bool): If True, includes paths of all child prims that match prim_accept_fn.
                If False, only returns the path of the specified prim. Defaults to False.
            prim_accept_fn (Optional[Callable[[Usd.Prim], bool]]): Optional predicate function that takes a Usd.Prim
                and returns True if the prim should be included. Only used when add_prim_children is True.
                If None, all active and visible prims are accepted. Defaults to None.

        Returns:
            Tuple[List[Sdf.Path], List[int]]: A tuple containing:
                - List of Sdf.Path objects for the matching prims
                - List of integer path representations of those prims

            For collection inputs, returns all prims in the collection regardless of add_prim_children.
            For prim inputs, returns either just the prim or all matching children based on add_prim_children.
        """
        prim_paths = []

        # Split and process obj_a paths
        if prim_str_path:
            for path in prim_str_path.split():
                stripped_path = path.strip()
                if stripped_path:
                    prim_paths.extend(get_list_of_prim_paths(stage, stripped_path, add_prim_children, prim_accept_fn))

        return prim_paths, [sdfPathToInt(path) for path in prim_paths if path]

    def set_scope(self, stage: Usd.Stage, obj_a: str, obj_b: str, merge_scopes: bool = False) -> bool:
        """Sets the scope for clash detection.

        If both `obj_a` and `obj_b` are empty -> process full scene.
        If only the `obj_a` list contains items -> limit processing only to `obj_a` items.
        If `obj_a` and `obj_b` lists contain items -> process obj_a against `obj_b`.

        obj_a and obj_b can both contain multiple paths separated by spaces.

        Args:
            stage (Usd.Stage): The USD stage.
            obj_a (str): Object A. Can contain multiple paths separated by space/tab/newline.
            obj_b (str): Object B. Can contain multiple paths separated by space/tab/newline.
            merge_scopes (bool): if True, then scopes are merged into one. Makes sense for detection of duplicates.

        Returns:
            bool: True if scope was set successfully, False otherwise.
        """
        if not self._clash_detect_api:
            return False

        if not stage:
            carb.error("Cannot set clash detection scope, stage is missing!")  # type: ignore
            return False

        prim_paths_a, int_paths_a = self.get_list_of_prims_int_paths(stage, obj_a)
        prim_paths_b, int_paths_b = self.get_list_of_prims_int_paths(stage, obj_b)

        stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()

        self._clash_detect_api.set_full_scene(
            self._context,
            True if len(int_paths_a) == 0 and len(int_paths_b) == 0 else False
        )

        if merge_scopes:
            self._clash_detect_api.set_scope(self._context, stage_id, int_paths_a + int_paths_b, [])
        else:
            self._clash_detect_api.set_scope(self._context, stage_id, int_paths_a, int_paths_b)

        return True

    def create_pipeline(self) -> int:
        """Creates and initializes the clash detection pipeline.

        This method sets up the pipeline for clash detection processing, records the start time,
        and captures initial memory state. The pipeline must be created before running any steps.

        Returns:
            int: The number of pipeline steps that need to be executed. Returns 0 if the clash detection API
                 is not initialized.
        """
        if not self._clash_detect_api:
            return 0
        self._pipeline_started_at = time.time()
        self._available_mem_at_start = get_available_system_memory()
        return self._clash_detect_api.create_pipeline(self._context)

    def get_pipeline_step_data(self, index: int) -> Any:
        """Gets metadata about a specific pipeline step.

        Retrieves information about a pipeline step including its progress percentage and description.
        Can be called before or after executing the step.

        Args:
            index (int): The index of the pipeline step to get data for.

        Returns:
            Any: A data object containing:
                - progress (float): Progress value between 0.0 and 1.0
                - name (str): Description of the pipeline step
                Returns None if clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return None
        return self._clash_detect_api.get_pipeline_step_data(self._context, index)

    def run_pipeline_step(self, index: int) -> None:
        """Executes a single step in the clash detection pipeline.

        This method processes one step of the clash detection algorithm. The pipeline must be created first
        by calling create_pipeline(). Steps must be executed sequentially starting from index 0.
        Progress and step information can be obtained by calling get_pipeline_step_data().

        The step execution is synchronous and will block until completed. For asynchronous execution,
        use run_async_pipeline() instead.

        Args:
            index (int): Zero-based index of the pipeline step to execute. Must be less than the number
                        of steps returned by create_pipeline().
        """
        if not self._clash_detect_api:
            return
        self._clash_detect_api.run_pipeline_step(self._context, index)

    def get_async_pipeline_step_data(self, cookie: Any) -> Any:
        """Gets data for the current step in an asynchronous clash detection pipeline.

        This method retrieves information about the current step being processed by the async pipeline,
        including progress percentage and step name. It can be called repeatedly while
        is_async_pipeline_running() returns True to monitor pipeline execution.

        Args:
            cookie (Any): Cookie obtained from run_async_pipeline() that identifies the pipeline instance.

        Returns:
            Any: A data object containing:
                - progress (float): Progress value between 0.0 and 1.0
                - name (str): Description of the current pipeline step
                Returns None if clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return None
        return self._clash_detect_api.get_pipeline_step_data_async(cookie)

    def run_async_pipeline(self) -> Any:
        """Starts asynchronous execution of the clash detection pipeline.

        Launches the clash detection process to run asynchronously in the background. The pipeline will
        execute all steps in separate threads without blocking the main thread. Progress can be monitored
        by calling get_async_pipeline_step_data() with the returned cookie.

        The pipeline must be properly cleaned up by calling finish_async_pipeline() after completion or
        cancel_async_pipeline() followed by finish_async_pipeline() if cancelled early.

        Returns:
            Any: A cookie identifying this async pipeline instance. The cookie is required for monitoring
                progress and cleanup. Returns None if the clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return None
        return self._clash_detect_api.run_pipeline_async(self._context)

    def is_async_pipeline_running(self, cookie: Any) -> bool:
        """Checks if an asynchronous clash detection pipeline is still executing.

        This method checks whether the pipeline identified by the cookie is still processing. While running,
        you can monitor progress by calling get_async_pipeline_step_data(). The pipeline must be cleaned up
        with finish_async_pipeline() after completion or cancellation.

        Args:
            cookie (Any): Cookie obtained from run_async_pipeline() that identifies the pipeline instance.

        Returns:
            bool: True if pipeline is still running, False if completed or API not initialized.
        """
        if not self._clash_detect_api:
            return False
        return self._clash_detect_api.is_pipeline_running(cookie)

    def finish_async_pipeline(self, cookie: Any) -> bool:
        """Cleans up resources used by an asynchronous clash detection pipeline.

        This is a blocking call that waits for the pipeline to finish before cleaning up resources.
        The cookie becomes invalid after this call and cannot be reused.
        Results like get_nb_overlaps() can only be accessed after this function returns.

        Args:
            cookie (Any): Cookie identifying the async pipeline instance to finish.

        Returns:
            bool: True if cleanup was successful, False if clash detection API is not
                initialized or cleanup failed.
        """
        if not self._clash_detect_api:
            return False
        return self._clash_detect_api.finish_pipeline(cookie)

    def cancel_async_pipeline(self, cookie: Any) -> None:
        """Cancels an asynchronous clash detection pipeline.

        Signals the pipeline to stop processing but does not clean up resources.
        finish_async_pipeline() must still be called after cancellation to properly
        clean up the pipeline.

        Args:
            cookie (Any): Cookie obtained from run_async_pipeline() that identifies
                the pipeline instance to cancel.
        """
        if not self._clash_detect_api:
            return
        self._clash_detect_api.cancel_pipeline(cookie)

    def compute_max_local_depth(
        self,
        mesh_path0: Sdf.Path,
        matrix0: Gf.Matrix4d,
        mesh_path1: Sdf.Path,
        matrix1: Gf.Matrix4d,
        clash_query: ClashQuery,
    ) -> float:
        """
        Computes the maximum local penetration depth between two meshes with given transforms.

        Args:
            mesh_path0 (Sdf.Path): USD path to the first mesh.
            matrix0 (Gf.Matrix4d): Transformation matrix for the first mesh.
            mesh_path1 (Sdf.Path): USD path to the second mesh.
            matrix1 (Gf.Matrix4d): Transformation matrix for the second mesh.
            clash_query (ClashQuery): ClashQuery object containing clash detection settings.

        Returns:
            float: The maximum local penetration depth. Returns 0.0 if the clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return 0.0

        # setup the clash detection engine with the settings from the clash query, force compute max local depth
        clash_detect_settings = clash_query.clash_detect_settings.copy()
        clash_detect_settings[SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name] = True
        self.set_settings(clash_detect_settings)

        depth_data = self._clash_detect_api.imm_compute_local_depth(
            self._context,
            sdfPathToInt(mesh_path0), matrix_to_list(matrix0),
            sdfPathToInt(mesh_path1), matrix_to_list(matrix1)
        )
        return depth_data.max_local_depth

    def compute_penetration_depth(
        self,
        mesh_path0: Sdf.Path,
        matrix0: Gf.Matrix4d,
        mesh_path1: Sdf.Path,
        matrix1: Gf.Matrix4d,
        clash_query: ClashQuery,
        dir: Tuple[float, float, float],
    ) -> Any:
        """
        Compute the penetration depth (amount and direction) necessary to resolve overlap between two meshes.

        This function calculates the penetration depth and the direction vector required to separate
        two mesh objects, using the provided transforms and clash detection settings. The method
        allows for specifying a custom penetration depth direction. The computation always enables max
        local depth calculation in the underlying engine for accurate depth results.

        Args:
            mesh_path0 (Sdf.Path): USD path of the first mesh.
            matrix0 (Gf.Matrix4d): Local-to-world transformation for the first mesh.
            mesh_path1 (Sdf.Path): USD path of the second mesh.
            matrix1 (Gf.Matrix4d): Local-to-world transformation for the second mesh.
            clash_query (ClashQuery): ClashQuery that provides the relevant clash detection settings.
            dir (Tuple[float, float, float]): The penetration depth direction vector (x, y, z).

        Returns:
            Any: An object containing at least:
                - depth (float): The penetration depth distance required to separate the meshes.
                - dir   (Tuple[float, float, float]): The penetration depth direction vector.
                Returns None if the clash detection API is not initialized or the direction is 0,0,0.
        """
        if not self._clash_detect_api or dir is None:
            return None

        # setup the clash detection engine with the settings from the clash query, force compute max local depth
        clash_detect_settings = clash_query.clash_detect_settings.copy()
        clash_detect_settings[SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name] = True
        self.set_settings(clash_detect_settings)

        data = self._clash_detect_api.imm_depenetrate_meshes(
            self._context,
            sdfPathToInt(mesh_path0), matrix_to_list(matrix0),
            sdfPathToInt(mesh_path1), matrix_to_list(matrix1),
            dir[0], dir[1], dir[2]
        )

        return data

    def get_overlap_data(self, overlap_index: int, frame_index: int) -> OverlapData:
        """Gets detailed data about a specific overlap at a given frame.

        Args:
            overlap_index (int): Index identifying the specific overlap to query
            frame_index (int): Frame number at which to get the overlap data

        Returns:
            OverlapData: Object containing detailed overlap information. Returns an empty
                OverlapData object if the clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return OverlapData()
        return self._clash_detect_api.get_overlap_data(self._context, overlap_index, frame_index)

    def get_overlap_report(
        self, overlap_index: int, frame_index: int, mesh_index: MeshIndex, flags: Annotated[int, "OverlapReportFlag"]
    ) -> Dict[str, Any]:
        """Generates a detailed report about a specific overlap's geometry.

        Creates a report containing geometric information about the overlap, including face indices
        and collision outlines. The report can be customized using flags to specify which data to include.

        Args:
            overlap_index (int): Index identifying the specific overlap to analyze
            frame_index (int): Frame number at which to analyze the overlap
            mesh_index (MeshIndex): Which mesh in the overlap pair to analyze
            flags (OverlapReportFlag): Bit flags controlling which data to include in the report

        Returns:
            Dict[str, Any]: Report containing geometric data about the overlap, including:
                - usd_faces: Warp array of face indices involved in the overlap
                - collision_outline: Warp array of outline vertices
                Returns empty dict if clash detection API is not initialized.
        """
        if not self._clash_detect_api:
            return {}

        # variant #1: get numpy arrays and convert them to warp arrays
        # d = self._clash_detect_api.get_overlap_report_np(self._context, overlap_index, frame_index, mesh_index, flags)
        # d["usd_faces"] = wp.from_numpy(d["usd_faces"], dtype=wp.uint32)
        # d["collision_outline"] = wp.from_numpy(d["collision_outline"], dtype=wp.float32)

        # variant #2: get simple array descs and convert them to warp arrays
        d = self._clash_detect_api.get_overlap_report_sad(self._context, overlap_index, frame_index, mesh_index, flags)
        sz, count, ptr = d["usd_faces"]
        d["usd_faces"] = self._wp_array_from_sad(sz, count, ptr, wp.uint32, 4)
        sz, count, ptr = d["collision_outline"]
        d["collision_outline"] = self._wp_array_from_sad(sz, count, ptr, wp.float32, 4)

        return d

    def get_overlap_report2(
        self, overlap_index: int, frame_index: int, flags: Annotated[int, "OverlapReportFlag"]
    ) -> Dict[str, Any]:
        """
        Generates a detailed report about a specific overlap's geometry for both meshes involved.

        This method queries the clash detection API for detailed information about an overlap at a given time/frame,
        returning the face indices for both meshes of the overlap, as well as the outline of the collision region.
        The results are converted into warp arrays for further processing.

        Args:
            overlap_index (int): Index identifying the specific overlap to analyze.
            frame_index (int): Frame number at which to analyze the overlap.
            flags (int): Bit flags (OverlapReportFlag) controlling which data to include in the report.

        Returns:
            Dict[str, Any]: Report containing:
                - 'usd_faces0': Warp array of face indices for the first mesh in the overlap.
                - 'usd_faces1': Warp array of face indices for the second mesh in the overlap.
                - 'collision_outline': Warp array of outline vertices for the collision region.
            Returns an empty dict if the clash detection API is not initialized.

        Difference between get_overlap_report and get_overlap_report2:
            - get_overlap_report only returns the face indices for a single mesh of the overlap (specified via the mesh_index argument)
              and the collision outline vertices.
            - get_overlap_report2 returns face indices for both meshes involved in the overlap (usd_faces0 and usd_faces1), as well as the
              collision outline, and does not require a mesh_index argument.
        """
        if not self._clash_detect_api:
            return {}

        d = self._clash_detect_api.get_overlap_report_sad2(self._context, overlap_index, frame_index, flags)
        sz, count, ptr0 = d["usd_faces0"]
        d["usd_faces0"] = self._wp_array_from_sad(sz, count, ptr0, wp.uint32, 4)
        sz, count, ptr1 = d["usd_faces1"]
        d["usd_faces1"] = self._wp_array_from_sad(sz, count, ptr1, wp.uint32, 4)
        sz, count, ptr = d["collision_outline"]
        d["collision_outline"] = self._wp_array_from_sad(sz, count, ptr, wp.float32, 4)

        return d

    def _get_existing_clash_info(
        self,
        existing_clash_info_items: Dict[str, ClashInfo],
        clash_hash: str,
        query_identifier: int
    ) -> Optional[ClashInfo]:
        """Retrieves a 'ClashInfo' object from existing_clash_info_items dictionary if present; otherwise, returns None."""
        existing_clash_info = existing_clash_info_items.get(clash_hash)
        if existing_clash_info:
            if existing_clash_info._present:
                carb.log_warn(f"ERROR! Overlap info with hash {clash_hash} retrieved multiple times!")
            if existing_clash_info._query_id != query_identifier:
                carb.log_warn(f"ERROR! Overlap info with hash {clash_hash} has query identifier mismatch! ({query_identifier} != {existing_clash_info._query_id})")
            return existing_clash_info
        return None

    def _update_or_create_clash_info(
        self,
        existing_clash_info: Optional[ClashInfo],
        clash_hash: str,
        query_identifier: int,
        overlap_type: OverlapType,
        min_distance: float,
        max_local_depth: float,
        setting_depth_epsilon: float,
        setting_tolerance: float,
        overlap_name_a: str,
        mesh_hash_a: str,
        overlap_name_b: str,
        mesh_hash_b: str,
        start_time: float,
        end_time: float,
        num_records: int,
        num_tris: int,
        existing_overlaps: Optional[List[ClashFrameInfo]]
    ) -> ClashInfo:  # returns updated ClashInfo
        """Updates provided existing_clash_info or, if not provided, creates a new instance of `ClashInfo` object."""
        if existing_clash_info:
            # update existing clash info
            existing_clash_info._overlap_type = overlap_type
            existing_clash_info._present = True
            existing_clash_info._min_distance = min_distance
            existing_clash_info._max_local_depth = max_local_depth
            existing_clash_info._depth_epsilon = setting_depth_epsilon
            existing_clash_info._tolerance = setting_tolerance
            existing_clash_info._object_a_path = overlap_name_a
            existing_clash_info._object_b_path = overlap_name_b
            existing_clash_info._object_a_mesh_crc = mesh_hash_a
            existing_clash_info._object_b_mesh_crc = mesh_hash_b
            existing_clash_info._overlap_tris = num_tris
            existing_clash_info._start_time = start_time
            existing_clash_info._end_time = end_time
            existing_clash_info._num_records = num_records
            existing_clash_info._clash_frame_info_items = existing_overlaps

            if ExtensionConfig.update_clash_states_after_detection:
                existing_clash_info._state = ClashState.ACTIVE

            existing_clash_info.update_last_modified_timestamp()
            return existing_clash_info
        else:
            new_clash_info = ClashInfo(
                -1,  # To be added by serializer
                query_identifier,
                clash_hash,
                overlap_type,
                True,
                min_distance,
                max_local_depth,
                setting_depth_epsilon,
                setting_tolerance,
                overlap_name_a,
                mesh_hash_a,
                overlap_name_b,
                mesh_hash_b,
                start_time,
                end_time,
                num_records,
                num_tris,
            )
            new_clash_info._clash_frame_info_items = existing_overlaps
            return new_clash_info

    def process_overlap_generator(
        self,
        idx: int,
        existing_overlaps: Dict[str, ClashInfo],
        query_identifier: int,
        setting_tolerance: float,
        setting_depth_epsilon: float,
        yield_progress_range: Tuple[float, float] = (0.0, 1.0)
    ) -> Generator[float, None, ClashInfo]:
        """Processes a detected overlap, updating or creating a `ClashInfo` object as necessary.
        Returns a generator that yields progress and finally returns ClashInfo (identifier -1 means new clash info otherwise it's an update).

        Args:
            stage (Usd.Stage): The USD stage containing the overlapping prims.
            idx (int): The index of the overlap to process.
            existing_overlaps (Dict[str, ClashInfo]): Dictionary of existing clash info objects, keyed by clash hash.
            query_identifier (int): Unique identifier for the clash detection query.
            setting_tolerance (float): Distance tolerance value for determining soft clashes.
            setting_depth_epsilon (float): Minimum collision depth to consider for clash detection.
            yield_progress_range (Tuple[float, float], optional): Range of progress values to yield, as (min, max). Defaults to None.

        Yields:
            float: Progress value between yield_progress_range[0] and yield_progress_range[1] for each processed frame.
                  If yield_progress_range is None, the method does not yield progress.

        Returns:
            ClashInfo: A ClashInfo object representing the processed overlap. If this is a new clash,
                      the identifier will be -1. If this updates an existing clash, the original
                      identifier is preserved.
        """
        progress_range_size = yield_progress_range[1] - yield_progress_range[0]

        clash_info = self.get_overlap_data(idx, 0)
        overlap_name_a = clash_info.name0
        overlap_name_b = clash_info.name1
        clash_hash = hex(make_int128(clash_info.clash_hash[0], clash_info.clash_hash[1]))
        mesh_hash_a = hex(make_int128(clash_info.mesh_hash0[0], clash_info.mesh_hash0[1]))
        mesh_hash_b = hex(make_int128(clash_info.mesh_hash1[0], clash_info.mesh_hash1[1]))
        num_records = clash_info.nb_records
        start_time = clash_info.time

        if ExtensionConfig.debug_logging:
            carb.log_info(f"{clash_hash}: {overlap_name_a}, {overlap_name_b}, records: {num_records}, num_tris: {clash_info.nb_tris}")

        # fetch clashing frame info, if there is more than 1 record
        # no need for sorting as frames are requested in ascending sequential order
        clash_frame_info_items: List[ClashFrameInfo] = []
        max_nb_tris = 0
        min_min_distance = sys.float_info.max  # minimal distance out of all minimal distances
        max_max_local_depth = -1.0  # maximal depth out of all maximal depths
        for frame_idx in range(num_records):
            frame_clash_info = self.get_overlap_data(idx, frame_idx)
            timecode = frame_clash_info.time

            flags: int = int(OverlapReportFlag.USD_FACES0) | int(OverlapReportFlag.USD_FACES1) | int(OverlapReportFlag.OUTLINE)
            report = self.get_overlap_report2(idx, frame_idx, flags)
            frame_overlap_faces0 = report["usd_faces0"]
            frame_overlap_faces1 = report["usd_faces1"]
            # In C++ we express outlines as Sequence of Segments, where each segment is a Point3D (3 floats)
            # In Python we keep it in a flat array of floats for efficiency when serializing and deserializing
            # [item.p0.x, item.p0.y, item.p0.z, item.p1.x, item.p1.y, item.p1.z... * num_of_items]
            frame_overlap_outline = report["collision_outline"]

            # get world matrices of the two overlapping prims at current timecode
            matrix0 = list_to_matrix(report["matrix0"])
            matrix1 = list_to_matrix(report["matrix1"])

            nb_tris = frame_clash_info.nb_tris
            if nb_tris > max_nb_tris:
                max_nb_tris = nb_tris

            min_distance = frame_clash_info.min_distance
            if min_distance < min_min_distance:
                min_min_distance = min_distance

            max_local_depth = frame_clash_info.max_local_depth
            if max_local_depth > max_max_local_depth:
                max_max_local_depth = max_local_depth

            if ExtensionConfig.debug_logging_detailed:
                carb.log_info(
                    f"  frame_idx {frame_idx}: num_tris: {nb_tris}, "
                    f"len(frame_overlap_faces0): {len(frame_overlap_faces0)}, "
                    f"len(frame_overlap_faces1): {len(frame_overlap_faces1)}, "
                    f"len(frame_overlap_outline): {len(frame_overlap_outline)}"
                )

            clash_frame_info_items.append(
                ClashFrameInfo(
                    timecode,
                    min_distance,
                    max_local_depth,
                    nb_tris,
                    frame_overlap_faces0,
                    frame_overlap_faces1,
                    frame_overlap_outline,
                    matrix0,
                    matrix1,
                )
            )

            # Yield progress for each processed frame
            yield yield_progress_range[0] + progress_range_size * (float(frame_idx + 1) / float(num_records))

        num_tris = max_nb_tris
        end_time = clash_frame_info_items[-1].timecode

        return self._update_or_create_clash_info(
            self._get_existing_clash_info(existing_overlaps, clash_hash, query_identifier),
            clash_hash,
            query_identifier,
            OverlapType.NORMAL,
            min_min_distance,
            max_max_local_depth,
            setting_depth_epsilon,
            setting_tolerance,
            overlap_name_a,
            mesh_hash_a,
            overlap_name_b,
            mesh_hash_b,
            start_time,
            end_time,
            num_records,
            num_tris,
            clash_frame_info_items
        )

    def process_overlap(
        self,
        stage: Usd.Stage,
        idx: int,
        existing_overlaps: Dict[str, ClashInfo],
        query_identifier: int,
        setting_tolerance: float,
        setting_depth_epsilon: float,
    ) -> ClashInfo:
        """Processes a detected overlap, updating or creating a `ClashInfo` object as necessary.

        Args:
            stage (Usd.Stage): The USD stage containing the overlapping prims.
            idx (int): The index of the overlap to process.
            existing_overlaps (Dict[str, ClashInfo]): Dictionary of existing clash info objects, keyed by clash hash.
            query_identifier (int): Unique identifier for the clash detection query.
            setting_tolerance (float): Distance tolerance value for determining soft clashes.
            setting_depth_epsilon (float): Minimum collision depth to consider for clash detection.

        Returns:
            ClashInfo: A ClashInfo object representing the processed overlap. If this is a new clash,
                       the identifier will be -1. If this updates an existing clash, the original
                       identifier is preserved.
        """
        gen = self.process_overlap_generator(
            idx, existing_overlaps, query_identifier, setting_tolerance, setting_depth_epsilon
        )
        try:
            while True:
                _ = next(gen)
        except StopIteration as e:
            return e.value

    def process_duplicate(
        self,
        stage: Usd.Stage,
        idx: int,
        existing_overlaps: Dict[str, ClashInfo],
        query_identifier: int,
    ) -> ClashInfo:  # returns ClashInfo (identifier -1 means new clash info otherwise it's an update)
        """Processes a detected duplicate overlap, updating or creating a `ClashInfo` object as necessary.

        Duplicate overlap is an overlap between identical meshes with identical transformations fully overlapping each other.
        This method processes a single duplicate overlap and either updates an existing ClashInfo object or creates a new one.

        Args:
            stage (Usd.Stage): The USD stage containing the overlapping meshes.
            idx (int): Index of the duplicate overlap to process.
            existing_overlaps (Dict[str, ClashInfo]): Dictionary of existing clash info objects, keyed by clash hash.
            query_identifier (int): Unique identifier for the current clash detection query.

        Returns:
            ClashInfo: Updated or newly created clash info object containing the duplicate overlap data.
        """
        if not self._clash_detect_api:
            return ClashInfo()
        dup_data = self._clash_detect_api.get_duplicated_meshes_data(self._context, idx)
        overlap_name_a = dup_data.name0
        overlap_name_b = dup_data.name1
        clash_hash = hex(make_int128(dup_data.clash_hash[0], dup_data.clash_hash[1]))
        mesh_hash_a = hex(make_int128(dup_data.mesh_hash0[0], dup_data.mesh_hash0[1]))
        mesh_hash_b = hex(make_int128(dup_data.mesh_hash1[0], dup_data.mesh_hash1[1]))
        num_tris = dup_data.nb_tris
        timecode = dup_data.time
        min_distance = dup_data.min_distance
        max_local_depth = dup_data.max_local_depth

        # get world matrices of the two overlapping prims
        matrix0 = get_prim_matrix(stage, overlap_name_a, timecode)
        matrix1 = get_prim_matrix(stage, overlap_name_b, timecode)

        if ExtensionConfig.debug_logging:
            carb.log_info(f"DUP {clash_hash}: {overlap_name_a}, {overlap_name_b}, num_tris: {num_tris}")

        # NOTE: we do not store collision outline for duplicates
        return self._update_or_create_clash_info(
            self._get_existing_clash_info(existing_overlaps, clash_hash, query_identifier),
            clash_hash,
            query_identifier,
            OverlapType.DUPLICATE,
            min_distance,
            max_local_depth,
            -1.0,
            0.0,
            overlap_name_a,
            mesh_hash_a,
            overlap_name_b,
            mesh_hash_b,
            timecode,
            timecode,
            1,
            num_tris,
            [ClashFrameInfo(timecode, min_distance, max_local_depth, num_tris, None, None, None, matrix0, matrix1)],
        )

    def fetch_and_save_overlaps(
        self,
        stage: Usd.Stage,
        clash_data: ClashData,
        clash_query: ClashQuery
    ) -> Iterator[float]:
        """Fetches and saves overlaps from clash detection, yielding progress updates.

        This method processes both normal overlaps and duplicate meshes (if enabled), updating
        the clash data with new clash information. Progress is reported via an iterator.

        Args:
            stage (Usd.Stage): The USD stage containing the meshes to check for clashes.
                Used to look up prim paths and extract transformation matrices.
            clash_data (ClashData): Container for storing and managing clash information.
                New clash records are added here and existing ones are updated.
            clash_query (ClashQuery): Query parameters and settings for clash detection.
                Controls behavior like duplicate mesh detection and clash tolerances.

        Returns:
            Iterator[float]: A generator yielding progress values between 0.0 and 1.0,
                where 1.0 indicates completion. Values are emitted after processing each overlapping frame
                to enable smooth progress bar updates.
                Note: returns -1 in case of an error (more info in the log).
        """
        abort_processing = False

        def _initialize_fetch(
            clash_query: ClashQuery,
            clash_data: ClashData
        ) -> Tuple[Dict[str, ClashInfo], int, int]:
            """Initialize clash detection parameters and get initial counts."""
            if not self._clash_detect_api:
                return {}, 0, 0
            existing_overlaps = clash_data.find_all_overlaps_by_query_id(clash_query.identifier, True)
            for ci in existing_overlaps.values():
                if ci.present:
                    ci._present = False
            count = self._clash_detect_api.get_nb_overlaps(self._context)
            setting_find_duplicates = clash_query.clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, False)
            # clash detection returns # of duplicates even when not specifically asking for looking for duplicates -> ignore.
            dups_count = self._clash_detect_api.get_nb_duplicate_meshes(self._context) if setting_find_duplicates else 0
            if ExtensionConfig.debug_logging:
                carb.log_info(f"Found {count} overlaps.")
                if dups_count:
                    carb.log_info(f"Found {dups_count} duplicates = fully overlapping identical meshes with identical transformation matrices.")
            return existing_overlaps, count, dups_count

        def _process_overlaps(
            stage: Usd.Stage,
            clash_data: ClashData,
            clash_query: ClashQuery,
            existing_overlaps: Dict[str, ClashInfo],
            count: int,
            total_count: int,
            progress_update: OptimizedProgressUpdate
        ) -> Generator[float, None, Tuple[int, int]]:
            """Process normal overlaps."""
            nonlocal abort_processing
            total_tris = total_soft = 0
            setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0)
            setting_depth_epsilon = clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0)
            for idx in range(count):
                prev_progress = float(idx + 1) / float(total_count)
                next_progress = float(idx + 2) / float(total_count)
                clash_info = yield from self.process_overlap_generator(
                    idx,
                    existing_overlaps,
                    clash_query.identifier,
                    setting_tolerance,
                    setting_depth_epsilon,
                    (prev_progress, next_progress)
                )
                if clash_info and clash_info.identifier == -1:
                    total_tris += clash_info.overlap_tris
                    if clash_info.min_distance > ClashInfo.EPSILON:
                        total_soft += 1
                    if not clash_data.insert_overlap(clash_info, True, True, False):
                        carb.log_error(
                            f"Failed to insert overlap info with hash {clash_info.overlap_id} into clash database."
                        )
                        yield -1.0
                        abort_processing = True
                        break
                if progress_update.update(next_progress):
                    yield next_progress
            return total_tris, total_soft

        def _process_existing_overlaps(
            existing_overlaps: Dict[str, ClashInfo],
            clash_data: ClashData,
            count: int,
            total_count: int,
            progress_update: OptimizedProgressUpdate,
        ) -> Generator[float, None, tuple[int, int]]:
            """Process existing overlaps."""
            nonlocal abort_processing
            total_tris = total_soft = 0
            for idx, ci in enumerate(existing_overlaps.values()):
                if ci._present:
                    total_tris += ci.overlap_tris
                if ci.min_distance > ClashInfo.EPSILON:
                    total_soft += 1
                if clash_data.update_overlap(ci, True, False) == 0:
                    carb.log_error(
                        f"Failed to update overlap info with hash {ci.overlap_id} in clash database."
                    )
                    yield -1.0
                    abort_processing = True
                    break
                progress_value = float(count + idx + 1) / float(total_count)
                if progress_update.update(progress_value):
                    yield progress_value
            return total_tris, total_soft

        def _process_duplicates(
            stage: Usd.Stage,
            dups_count: int,
            existing_overlaps: Dict[str, ClashInfo],
            clash_data: ClashData,
            clash_query: ClashQuery,
            count: int,
            total_count: int,
            progress_update: OptimizedProgressUpdate,
        ) -> Generator[float, None, int]:
            """Process duplicate overlaps."""
            nonlocal abort_processing
            total_overlapping_tris = 0
            for idx in range(dups_count):
                clash_info = self.process_duplicate(stage, idx, existing_overlaps, clash_query.identifier)
                if clash_info and clash_info.identifier == -1:  # identifier -1 means new clash, otherwise existing
                    total_overlapping_tris += clash_info.overlap_tris
                    new_id = clash_data.insert_overlap(clash_info, True, True, False)
                    if not new_id or new_id == 0:
                        carb.log_error(
                            f"Failed to insert overlap info with hash {clash_info.overlap_id} into clash database."
                        )
                        yield -1.0
                        abort_processing = True
                        break
                elif clash_info:
                    if clash_data.update_overlap(clash_info, True, False) == 0:
                        carb.log_error(
                            f"Failed to update overlap info with hash {clash_info.overlap_id} in clash database."
                        )
                        yield -1.0
                        abort_processing = True
                        break
                progress_value = float(count + idx + 1) / float(total_count)
                if progress_update.update(progress_value):
                    yield progress_value
            return total_overlapping_tris

        if not self._clash_detect_api:
            return

        start_time = time.time()
        total_tris = total_soft = 0

        # Initialize and get counts
        existing_items, count, dups_count = _initialize_fetch(clash_query, clash_data)
        total_count = count + len(existing_items) + dups_count
        progress_update = OptimizedProgressUpdate()

        # Process overlaps
        overlap_tris, overlap_soft = yield from _process_overlaps(
            stage, clash_data, clash_query, existing_items, count, total_count, progress_update
        )
        total_tris += overlap_tris
        total_soft += overlap_soft

        if abort_processing:
            return

        if ExtensionConfig.update_clash_states_after_detection:
            for ci in existing_items.values():
                if not ci.present:
                    ci._state = ClashState.RESOLVED

        if abort_processing:
            return

        # Process existing items
        existing_tris, existing_soft = yield from _process_existing_overlaps(
            existing_items, clash_data, count, total_count, progress_update
        )
        total_tris += existing_tris
        total_soft += existing_soft

        if abort_processing:
            return

        # Process duplicates if needed
        if dups_count:
            yield from _process_duplicates(
                stage, dups_count, existing_items, clash_data, clash_query,
                count + len(existing_items), total_count, progress_update
            )

        if abort_processing:
            return

        clash_data.commit()

        # Log relevant telemetry data
        dynamic_query = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC.name, False)
        setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0)
        self._log_telemetry_data(
            dynamic_query,
            setting_tolerance,
            count,
            total_tris,
            start_time,
            clash_data
        )

    def _log_telemetry_data(
        self,
        dynamic_query: bool,
        setting_tolerance: float,
        count: int,
        total_overlapping_tris: int,
        database_insert_started_at: float,
        clash_data: ClashData
    ) -> None:
        """Logs telemetry data for clash detection.

        Records various metrics about the clash detection process including query type,
        overlap counts, timing information, and resource usage. The data is logged using
        the ClashTelemetry interface for analytics and performance monitoring.

        Args:
            dynamic_query (bool): Whether the clash detection was performed on animated/time-varying geometry
            setting_tolerance (float): The tolerance value used for soft clash detection. Values > 0 indicate soft clash mode
            count (int): Total number of overlaps detected between geometries
            total_overlapping_tris (int): Total number of triangles involved in all detected overlaps
            database_insert_started_at (float): Unix timestamp when database insertion began
            clash_data (ClashData): Object containing clash detection results and serialization info
        """
        ClashTelemetry.log_dynamic_vs_static_query(dynamic_query)
        ClashTelemetry.log_soft_vs_hard_query(setting_tolerance > 0.0)
        ClashTelemetry.log_num_of_found_overlaps(count)
        ClashTelemetry.log_total_num_of_overlapping_tris(total_overlapping_tris)
        now_time = time.time()
        ClashTelemetry.log_elapsed_query_run(
            clash_processing_elapsed=now_time - self._pipeline_started_at,
            clash_serialization_elapsed=now_time - database_insert_started_at,
        )
        if clash_data._serializer:
            ClashTelemetry.log_clash_data_file_size(float(clash_data._serializer.get_file_size()) / (1024.0 * 1024.0))
        if self._clash_detect_api:
            stats = self._clash_detect_api.get_query_stats(self._context)
            ClashTelemetry.log_clash_data_meshes_stats(stats)
