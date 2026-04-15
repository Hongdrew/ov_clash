# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pxr import Usd, Sdf, UsdUtils, UsdGeom
from typing import Callable, Awaitable, Any
import asyncio
import carb
import carb.settings
import os
import sys
import time
import traceback
import gc

from omni.physxclashdetectionbake import ClashBakeLayer, ClashDetectionBake, ClashBakeOptions


def get_used_mem() -> int:
    """
    Returns the amount of memory used by the current process in bytes.
    """
    import psutil

    return psutil.Process().memory_info().rss


# from omni.physxclashdetectioncore.clash_info import ClashInfo
# ClashInfoLike = ClashInfo
ClashInfoLike = Any
FAILED_PATHS_MAX_DISPLAY = 2  # Maximum number of paths to display in the error message


class ClashBakeAsyncUtils:

    @staticmethod
    def create_over_layer(stage: Usd.Stage, suffix: str, save_as_usd: bool) -> Sdf.Layer | None:
        root_layer: Sdf.Layer = stage.GetRootLayer()
        # CHECK IF LAYER IS ANONYMOUS / UNSAVED
        if root_layer.anonymous:
            return None

        if not root_layer.identifier:
            raise Exception("Invalid root layer identifier")

        base_path, _ = os.path.splitext(root_layer.identifier)

        if save_as_usd:
            extension = ".usd"
        else:
            extension = ".usda"
        _bake_layer_path = base_path + f"_{suffix}{extension}"
        _bake_layer = Sdf.Layer.FindOrOpen(_bake_layer_path)
        if not _bake_layer:
            _bake_layer: Sdf.Layer = Sdf.Layer.CreateNew(_bake_layer_path)  # type: ignore
        # _bake_layer.framesPerSecond = float(stage.GetFramesPerSecond())
        _bake_layer.timeCodesPerSecond = float(stage.GetTimeCodesPerSecond())  # type: ignore

        return _bake_layer

    @staticmethod
    def insert_as_sublayer(parent_layer: Sdf.Layer, layer: Sdf.Layer | None):
        if layer and layer.identifier not in parent_layer.subLayerPaths:  # type: ignore
            parent_layer.subLayerPaths.append(layer.identifier)  # type: ignore

    @staticmethod
    def remove_from_sublayers(parent_layer: Sdf.Layer, layer: Sdf.Layer | None):
        if layer and layer.identifier in parent_layer.subLayerPaths:  # type: ignore
            parent_layer.subLayerPaths.remove(layer.identifier)  # type: ignore

    @staticmethod
    def remove_all_prim_specs(layer: Sdf.Layer):

        def remove_prim_spec(prim_spec: Sdf.PrimSpec):
            """Removes prim spec from layer."""
            if prim_spec.nameParent:
                name_parent = prim_spec.nameParent
            else:
                name_parent = layer.pseudoRoot

            if not name_parent:
                return False

            name = prim_spec.name
            if name in name_parent.nameChildren:
                del name_parent.nameChildren[name]

        def on_prim_spec_path(prim_spec_path):
            if prim_spec_path.IsPropertyPath() or prim_spec_path == Sdf.Path.absoluteRootPath:
                return
            prim_spec = layer.GetPrimAtPath(prim_spec_path)
            if prim_spec:
                remove_prim_spec(prim_spec)

        layer.Traverse(Sdf.Path.absoluteRootPath, on_prim_spec_path)

    @staticmethod
    def format_exception(e):
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

        exception_str = "Traceback (most recent call last):\n"
        exception_str += "".join(exception_list)
        # Removing the last \n
        exception_str = exception_str[:-1]

        return exception_str


class ClashBakeAPI:
    """
    This class uses the layer API or the stage API to bake clash meshes.
    """

    def __init__(self, use_layer_api: bool = False):
        self.use_layer_api = use_layer_api

    def get_support_files_paths(self, options):
        paths1 = ClashBakeLayer.get_support_files_paths(options)
        paths2 = ClashDetectionBake.get_support_files_paths(options)
        combined_paths = [*paths1, *paths2]
        return list(set(combined_paths))

    def bake_clash_materials(self, stage: Usd.Stage, layer: Sdf.Layer, options):
        return ClashBakeLayer.bake_clash_materials(layer, options)

    def bake_clash_meshes(self, stage: Usd.Stage, layer: Sdf.Layer, bake_infos, materials, options):
        if self.use_layer_api:
            return ClashBakeLayer.bake_clash_meshes(layer, bake_infos, materials, options)
        else:
            return ClashDetectionBake.bake_clash_meshes(stage, bake_infos, materials, options)

    def remove_baked_meshes(self, stage: Usd.Stage, layer: Sdf.Layer, paths, options):
        if self.use_layer_api:
            return ClashBakeLayer.remove_baked_meshes(stage, layer, paths, options)
        else:
            return ClashDetectionBake.remove_baked_meshes(stage, paths, options)

    def prepare_clash_bake_infos(self, stage: Usd.Stage, clash_infos, options):
        if self.use_layer_api:
            return ClashBakeLayer.prepare_clash_bake_infos(stage, clash_infos, options)
        else:
            return ClashDetectionBake.prepare_clash_bake_infos(stage, clash_infos, options)

    def finalize_baked_meshes(self, stage: Usd.Stage, layer: Sdf.Layer, paths, bake_infos, options):
        with Sdf.ChangeBlock():
            if self.use_layer_api:
                ClashBakeLayer.finalize_clash_meshes(layer, bake_infos, options)
            else:
                ClashDetectionBake.finalize_clash_meshes(stage=stage, paths=paths, options=options)


class ClashBakeAsyncStatus:
    def __init__(self):
        """Status of the clash baking process.

        Attributes:
            progress (float): Progress of the clash baking process.
            infos_total (int): Total number of clash infos.
            infos_processed (int): Number of clash infos processed.
            info_message (str | None): Information message of the clash baking process.
            error_message (str | None): Error message of the clash baking process.
            memory_total (int): Total memory used by the clash baking process.
            memory_finalize (int): Memory used by the clash baking process at finalize time.
            memory_update_layer (int): Memory used by the clash baking process at update layer time.
            memory_remove_overs (int): Memory used by the clash baking process at remove overs time.
            memory_database_load (int): Memory used by the clash baking process at load database time.
            memory_kit_app_updates (int): Memory used by the clash baking process at kit app updates time.
            memory_prepare (int): Memory used by the clash baking process at prepare time.
            memory_bake (int): Memory used by the clash baking process at bake time.
            time_total (float): Total time of the clash baking process.
            time_database_load (float): Time taken to load data from the database.
            time_bake (float): Time taken to bake the clash meshes.
            time_remove_overs (float): Time taken to remove the baked meshes.
            time_prepare (float): Time taken to prepare the clash infos.
            time_finalize (float): Time taken to finalize the clash meshes.
            time_update_layer (float): Time taken to update the SDF specs.
        """
        self.reset()

    def reset(self):
        self.progress = 0.0
        self.infos_total = 0
        self.infos_processed = 0

        self.info_message: str | None = None
        self.error_message: str | None = None

        self.memory_total = 0
        self.memory_finalize = 0
        self.memory_update_layer = 0
        self.memory_remove_overs = 0
        self.memory_database_load = 0
        self.memory_prepare = 0
        self.memory_bake = 0
        self.memory_kit_app_updates = 0

        self.time_total = 0.0
        self.time_database_load = 0.0
        self.time_bake = 0.0
        self.time_remove_overs = 0.0
        self.time_prepare = 0.0
        self.time_finalize = 0.0
        self.time_update_layer = 0.0
        self.time_kit_app_updates = 0.0

    def finalize(
        self, detailed_message: bool, total_start_time: float, total_start_memory: int, cancelled: bool = False
    ):
        self.time_total = time.time() - total_start_time
        self.memory_total = get_used_mem() - total_start_memory
        self.time_kit_app_updates = self.time_total - (
            self.time_remove_overs
            + self.time_database_load
            + self.time_prepare
            + self.time_bake
            + self.time_finalize
            + self.time_update_layer
        )
        self.memory_kit_app_updates = self.memory_total - (
            self.memory_remove_overs
            + self.memory_database_load
            + self.memory_prepare
            + self.memory_bake
            + self.memory_finalize
            + self.memory_update_layer
        )
        message = f"Clash baking process {'completed' if not cancelled else 'cancelled'}.\n"
        message += f"{self.time_total:.2f} seconds for {self.infos_processed} of {self.infos_total} clashes"
        if detailed_message:
            message += f":\n"
            message += f"\n- {self.time_remove_overs:8.2f} seconds for removing baked meshes"
            message += f"\n- {self.time_database_load:8.2f} seconds for loading clash from db"
            message += f"\n- {self.time_prepare:8.2f} seconds for preparing clash infos"
            message += f"\n- {self.time_bake:8.2f} seconds for baking clash infos"
            message += f"\n- {self.time_finalize:8.2f} seconds for clashes finalization"
            if self.time_update_layer > 0:
                message += f"\n- {self.time_update_layer:8.2f} seconds for copying SDF specs"
            message += f"\n- {self.time_kit_app_updates:8.2f} seconds for kit app updates"
        self.info_message = message


class ClashBakeAsync:
    def __init__(
        self,
        copy_support_files_fn: Callable[[str, str], Awaitable[None]],
        load_data_from_database_fn: Callable[[list[ClashInfoLike]], Awaitable[None]],
    ):
        """Async helper to bake batches of clash infos. This is currently a PRIVATE api, and its stability is not guaranteed.
        Args:
            copy_support_files_fn (Callable[[str, str], Awaitable[None]]): Function to copy support files (src, dest)
            load_data_from_database_fn (Callable[[list[ClashInfoLike]], Awaitable[None]]): Function to load data from the database
        """
        self._bake_layer = None
        self._copy_support_files_fn = copy_support_files_fn
        self._load_data_from_database_fn = load_data_from_database_fn
        self._finalize_when_cancelled = True
        self._clash_bake_materials = None
        self._clash_bake_options = ClashBakeOptions()
        self._keep_db_data_in_memory = True
        self._save_as_usd = True
        self._clash_bake_api = ClashBakeAPI(use_layer_api=True)
        self._stage = None
        self._stage_layer = None
        self._debug_logging = False
        self._status = ClashBakeAsyncStatus()
        self._meshes_suffix = ""
        self._materials_suffix = ""
        self._is_processing = False

    def destroy(self):
        self.detach_clash_bake()

    def is_bake_layer_enabled(self) -> bool:
        return self._bake_layer is not None

    def set_debug_logging(self, value: bool):
        self._debug_logging = value

    def get_debug_logging(self) -> bool:
        return self._debug_logging

    def get_status(self) -> ClashBakeAsyncStatus:
        return self._status

    def set_finalize_when_cancelled(self, value: bool):
        self._finalize_when_cancelled = value

    def get_finalize_when_cancelled(self) -> bool:
        return self._finalize_when_cancelled

    def set_use_display_opacity(self, value: bool):
        setattr(self._clash_bake_options, "_use_display_opacity", value)

    def get_use_display_opacity(self) -> bool:
        return getattr(self._clash_bake_options, "_use_display_opacity")

    def set_generate_wireframe(self, value: bool):
        self._clash_bake_options.generate_wireframe = value

    def get_generate_wireframe(self) -> bool:
        return self._clash_bake_options.generate_wireframe

    def set_generate_clash_meshes(self, value: bool):
        self._clash_bake_options.generate_clash_meshes = value

    def get_generate_clash_meshes(self) -> bool:
        return self._clash_bake_options.generate_clash_meshes

    def set_use_selection_groups(self, value: bool):
        self._clash_bake_options.use_selection_groups = value
        if not value and not self.can_generate_clash_mesh():
            # It's missing the material layer
            asyncio.ensure_future(self.attach_clash_bake(self._stage, self._stage_layer))

    def get_use_selection_groups(self) -> bool:
        return self._clash_bake_options.use_selection_groups

    def set_generate_clash_polygons(self, value: bool):
        self._clash_bake_options.generate_clash_polygons = value

    def get_generate_clash_polygons(self) -> bool:
        return self._clash_bake_options.generate_clash_polygons

    def set_generate_outlines(self, value: bool):
        self._clash_bake_options.generate_outlines = value

    def get_generate_outlines(self) -> bool:
        return self._clash_bake_options.generate_outlines

    def set_outline_width_size(self, value: float):
        self._clash_bake_options.outline_width_size = value

    def get_outline_width_size(self) -> float:
        return self._clash_bake_options.outline_width_size

    def set_outline_width_scale(self, value: float):
        self._clash_bake_options.outline_width_scale = value

    def get_outline_width_scale(self) -> float:
        return self._clash_bake_options.outline_width_scale

    def set_keep_db_data_in_memory(self, value: bool):
        self._keep_db_data_in_memory = value

    def get_keep_db_data_in_memory(self) -> bool:
        return self._keep_db_data_in_memory

    def set_use_layer_api(self, value: bool):
        asyncio.ensure_future(self.attach_clash_bake(self._stage, self._stage_layer))
        self._clash_bake_api = ClashBakeAPI(use_layer_api=value)

    def get_use_layer_api(self) -> bool:
        return self._clash_bake_api.use_layer_api

    def set_save_as_usd(self, value: bool):
        self._save_as_usd = value
        stage = self._stage
        stage_layer = self._stage_layer
        self.detach_clash_bake()
        asyncio.ensure_future(self.attach_clash_bake(stage, stage_layer))

    def get_save_as_usd(self) -> bool:
        return self._save_as_usd

    def can_generate_clash_mesh(self) -> bool:
        return self._bake_layer is not None and self._stage is not None and not self._is_processing

    async def attach_clash_bake(
        self, stage: Usd.Stage, stage_layer: Sdf.Layer, mesh_layer_suffix: str = "", material_layer_suffix: str = ""
    ):
        """
        Attach the clash bake layers to the stage.
        Args:
            stage (Usd.Stage): The stage to attach the clash bake layers to.
            stage_layer (Sdf.Layer): The stage layer to attach the clash bake layers to (for example the session layer).
            mesh_layer_suffix (str): The suffix for the mesh layer (for example "CLASH_QUERY_1234567890").
            material_layer_suffix (str): The suffix for the material layer (for example "CLASH_MATERIALS").
        """
        if stage_layer != self._stage_layer or self._stage != stage:
            self.detach_clash_bake()
        self._stage = stage
        self._stage_layer = stage_layer
        if mesh_layer_suffix != "":
            self._meshes_suffix = mesh_layer_suffix
        if material_layer_suffix != "":
            self._materials_suffix = material_layer_suffix

        if self._meshes_suffix == "":
            raise Exception("Layer suffix is empty")
        if self._materials_suffix == "":
            raise Exception("Materials suffix is empty")

        if self._bake_layer is None:
            dest_folder = os.path.dirname(stage.GetRootLayer().identifier)  # type: ignore
            paths = self._clash_bake_api.get_support_files_paths(options=self._clash_bake_options)
            # Copy support files to dest folder
            for src in paths:
                dest = os.path.join(dest_folder, os.path.basename(src))
                await self._copy_support_files_fn(src, dest)

            disk_materials = ClashBakeAsyncUtils.create_over_layer(stage, self._materials_suffix, self._save_as_usd)
            self.generate_clash_materials(stage=stage, dest_layer=disk_materials)

            # This is an attempt to avoid a full resync blocking for large amount of time.
            # Avoid inserting the layer directly as a sublayer of the given stage, this causes the full reasync.
            self._bake_layer = Sdf.Layer.CreateAnonymous("clash_bake_layer")
            self._bake_layer.timeCodesPerSecond = float(stage.GetTimeCodesPerSecond())  # type: ignore
            ClashBakeAsyncUtils.insert_as_sublayer(self._stage_layer, self._bake_layer)
            disk_meshes = ClashBakeAsyncUtils.create_over_layer(stage, self._meshes_suffix, self._save_as_usd)
            with Sdf.ChangeBlock():
                UsdUtils.StitchLayers(self._stage_layer, disk_materials)
                Sdf.CopySpec(disk_meshes, Sdf.Path("/"), self._bake_layer, Sdf.Path("/"))
            del disk_meshes
            del disk_materials

    def generate_clash_materials(self, stage: Usd.Stage, dest_layer: Sdf.Layer):
        if self._clash_bake_api.use_layer_api:
            old_edit_target = None
        else:
            old_edit_target = stage.GetEditTarget()
        try:
            if old_edit_target is not None:
                stage.SetEditTarget(dest_layer)
            # Materials must be generated first as they're referenced by meshes
            self._clash_bake_materials = self._clash_bake_api.bake_clash_materials(
                stage=stage, layer=dest_layer, options=self._clash_bake_options
            )
        finally:
            if old_edit_target is not None:
                stage.SetEditTarget(old_edit_target)

    def reattach_clash_bake(self, new_query_suffix: str = ""):
        if self._bake_layer and self._stage:
            self.clear_clash_bake()  # This makes the reattach a lot faster, as it avoids the full stage re-sync
            # Detach only the meshes layer, leaving material one to reduce chances of a resync
            ClashBakeAsyncUtils.remove_from_sublayers(self._stage_layer, layer=self._bake_layer)
            self._bake_layer = None
            asyncio.ensure_future(self.attach_clash_bake(self._stage, self._stage_layer, new_query_suffix))

    def clear_clash_bake(self):
        if self._bake_layer:
            # Removing prim specs one by one is significantly faster than clearing the layer self._bake_layer.Clear()
            with Sdf.ChangeBlock():
                ClashBakeAsyncUtils.remove_all_prim_specs(self._bake_layer)

    def clear_clash_materials(self):
        if self._stage_layer and self._stage:
            old_edit_target = self._stage.GetEditTarget()
            try:
                self._stage.SetEditTarget(self._stage_layer)
                self._stage.RemovePrim("/ClashMaterials")
            except Exception as e:
                carb.log_error(ClashBakeAsyncUtils.format_exception(e))
                raise e
            finally:
                if old_edit_target is not None:
                    self._stage.SetEditTarget(old_edit_target)

    def save_clash_bake(self):
        if self._bake_layer:
            bake_layer = ClashBakeAsyncUtils.create_over_layer(self._stage, self._meshes_suffix, self._save_as_usd)
            if bake_layer:
                Sdf.CopySpec(self._bake_layer, Sdf.Path("/"), bake_layer, Sdf.Path("/"))
                bake_layer.Save(True)
                del bake_layer
            materials_layer = ClashBakeAsyncUtils.create_over_layer(
                self._stage, self._materials_suffix, self._save_as_usd
            )
            if materials_layer:
                # Create a stage with materials layer and a Scope prim at /ClashMaterials
                materials_stage = Usd.Stage.Open(materials_layer)
                materials_stage.SetEditTarget(materials_layer)
                UsdGeom.Scope.Define(materials_stage, "/ClashMaterials")
                del materials_stage
                # Copy /ClashMaterials to the materials layer
                Sdf.CopySpec(
                    self._stage_layer, Sdf.Path("/ClashMaterials"), materials_layer, Sdf.Path("/ClashMaterials")
                )
                materials_layer.Save(True)
                del materials_layer

    def load_clash_bake(self):
        if self._bake_layer:
            disk_layer = ClashBakeAsyncUtils.create_over_layer(self._stage, self._meshes_suffix, self._save_as_usd)
            if disk_layer:
                disk_layer.Reload(True)
                Sdf.CopySpec(disk_layer, Sdf.Path("/"), self._bake_layer, Sdf.Path("/"))
                del disk_layer
            # Not loading materials layer

    def detach_clash_bake(self):
        if self._stage is None:
            return
        self.clear_clash_bake()  # This makes the detach a lot faster, as it avoids the full stage re-sync
        self.clear_clash_materials()
        ClashBakeAsyncUtils.remove_from_sublayers(self._stage_layer, self._bake_layer)
        self._bake_layer = None
        self._clash_bake_materials = None
        self._stage = None
        self._stage_layer = None

    async def async_bake(
        self, clash_infos: list[ClashInfoLike], batch_size: int, update_fn: Callable[[], Awaitable[None]]
    ):
        await self._generate_clash_meshes(clash_infos, False, batch_size, update_fn)

    async def async_clear(
        self, clash_infos: list[ClashInfoLike], batch_size: int, update_fn: Callable[[], Awaitable[None]]
    ):
        await self._generate_clash_meshes(clash_infos, True, batch_size, update_fn)

    async def _generate_clash_meshes(
        self,
        clash_infos: list[ClashInfoLike],
        just_clear: bool,
        batch_size: int,
        update_fn: Callable[[], Awaitable[None]],
    ):
        if not self.can_generate_clash_mesh() or not self._stage:
            return
        assert self._bake_layer is not None
        status = self._status
        status.reset()
        status.infos_processed = 0
        status.infos_total = len(clash_infos)

        stage = self._stage
        old_edit_target = None
        total_start_time = time.time()
        temp_layer = None

        all_bake_infos = []

        # Save current memory usage
        total_start_memory = get_used_mem()
        total_failed_prepare = 0
        # Collect paths
        paths: list[tuple[str, str]] = []
        for ci in clash_infos:
            paths.append((str(ci.object_a_path), str(ci.object_b_path)))
        try:
            self._is_processing = True
            if not self._clash_bake_api.use_layer_api:
                old_edit_target = stage.GetEditTarget()
                stage.SetEditTarget(self._bake_layer)

            await update_fn()
            start_memory = get_used_mem()
            start_time = time.time()
            with Sdf.ChangeBlock():
                failed_paths = self._clash_bake_api.remove_baked_meshes(
                    stage=stage, layer=self._bake_layer, paths=paths, options=self._clash_bake_options
                )
                if failed_paths:
                    if status.error_message is None:
                        status.error_message = ""
                    status.error_message += f"Failed to remove baked meshes for:"
                    for path in failed_paths[:FAILED_PATHS_MAX_DISPLAY]:
                        status.error_message += f"\n{path}"
                    if len(failed_paths) > FAILED_PATHS_MAX_DISPLAY:
                        status.error_message += f"\n\n... and {len(failed_paths) - FAILED_PATHS_MAX_DISPLAY} more (see console for details)."
                    status.error_message += f"\nCheck for the above prims still existing in the stage and try again.\n"
                    # Print all failed paths to the console
                    console_msg = "Failed to remove baked meshes for:"
                    for path in failed_paths:
                        console_msg += f"\n{path}"
                    carb.log_error(console_msg)
            end_time = time.time()
            status.time_remove_overs += end_time - start_time
            status.memory_remove_overs = get_used_mem() - start_memory

            if just_clear:
                status.time_total = time.time() - total_start_time
                status.info_message = f"Clash clear process completed.\n"
                status.info_message += f"{status.time_total:.2f} seconds for {status.infos_total} clashes.\n"
                return

            if self._clash_bake_api.use_layer_api:
                # Create a new SDF anonymous Layer to avoid needing SDF ChangeBlock
                temp_layer = Sdf.Layer.CreateAnonymous("clash_bake_layer")
                temp_layer.timeCodesPerSecond = float(stage.GetTimeCodesPerSecond())  # type: ignore
            else:
                temp_layer = self._bake_layer

            while status.infos_processed < status.infos_total:
                infos_slice = clash_infos[status.infos_processed : status.infos_processed + batch_size]

                # Compute how much time is taken for loading data from the database
                start_time = time.time()
                start_memory = get_used_mem()
                await self._load_data_from_database(infos_slice)
                end_time = time.time()
                status.time_database_load += end_time - start_time
                status.memory_database_load += get_used_mem() - start_memory

                # Compute how much time is taken for preparing bake infos
                start_time = time.time()
                start_memory = get_used_mem()
                bake_infos = self._clash_bake_api.prepare_clash_bake_infos(stage, infos_slice, self._clash_bake_options)
                end_time = time.time()
                if len(bake_infos) != len(infos_slice):
                    if status.error_message is None:
                        status.error_message = ""
                    if total_failed_prepare == 0:
                        status.error_message += f"Failed to prepare bake infos for some clashes."
                        status.error_message += f"\nCheck if prims below still exist in the stage and try again:\n"
                    for ci in infos_slice:
                        if ci not in bake_infos:
                            if total_failed_prepare < FAILED_PATHS_MAX_DISPLAY:
                                status.error_message += f"\t{ci.object_a_path} / {ci.object_b_path}\n"
                            elif total_failed_prepare == FAILED_PATHS_MAX_DISPLAY:
                                status.error_message += f"\n\n... and more (see console for details)."
                            carb.log_error(f"Failed to prepare bake infos for {ci.object_a_path} / {ci.object_b_path}")
                            total_failed_prepare += 1
                status.time_prepare += end_time - start_time
                status.memory_prepare += get_used_mem() - start_memory

                # Compute how much time is taken for baking meshes
                start_time = time.time()
                start_memory = get_used_mem()
                self._clash_bake_api.bake_clash_meshes(
                    stage=stage,
                    layer=temp_layer,
                    bake_infos=bake_infos,
                    materials=self._clash_bake_materials,
                    options=self._clash_bake_options,
                )
                status.memory_bake += get_used_mem() - start_memory
                end_time = time.time()
                status.time_bake += end_time - start_time
                all_bake_infos.extend(bake_infos)

                # Free memory if not being asked to keep the loaded data from db in memory
                if not self._keep_db_data_in_memory:
                    start_memory = get_used_mem()
                    for ci in infos_slice:
                        if getattr(ci, "_was_loaded", False):
                            ci.clash_frame_info_items = None
                            delattr(ci, "_was_loaded")
                    gc.collect()  # Force garbage collection to free memory
                    status.memory_database_load += get_used_mem() - start_memory  # This should get negative

                # Update progress bar
                status.infos_processed += batch_size
                if status.infos_processed >= status.infos_total:
                    status.infos_processed = status.infos_total
                status.progress = status.infos_processed / status.infos_total
                status.memory_total = get_used_mem() - total_start_memory
                await update_fn()

            # Finalization is always fast so we can do it after all the other operations in a single batch
            self._finalize(
                total_start_time, total_start_memory, status, stage, temp_layer, paths, all_bake_infos, False
            )
        except asyncio.CancelledError:
            if self._finalize_when_cancelled and temp_layer is not None:
                self._finalize(
                    total_start_time, total_start_memory, status, stage, temp_layer, paths, all_bake_infos, True
                )
        except Exception as e:
            status.finalize(self._debug_logging, total_start_time, total_start_memory, False)
            carb.log_error(ClashBakeAsyncUtils.format_exception(e))
            status.error_message = f"Clash baking process failed after {status.time_total:.2f} seconds.\n{e}\n"
            status.error_message += f"{status.infos_processed} of {status.infos_total} clashes processed."
        finally:
            self._is_processing = False
            if temp_layer:
                del temp_layer
            if old_edit_target is not None:
                stage.SetEditTarget(old_edit_target)

    def _finalize(
        self,
        total_start_time: float,
        total_start_memory: int,
        status: ClashBakeAsyncStatus,
        stage: Usd.Stage,
        temp_layer: Sdf.Layer,
        paths: list[tuple[str, str]],
        all_bake_infos,
        cancelled: bool,
    ):
        start_memory = get_used_mem()
        start_time = time.time()
        with Sdf.ChangeBlock():
            self._clash_bake_api.finalize_baked_meshes(
                stage=stage,
                layer=temp_layer,
                paths=paths,
                bake_infos=all_bake_infos,
                options=self._clash_bake_options,
            )
        end_time = time.time()
        status.time_finalize = end_time - start_time
        status.memory_finalize = get_used_mem() - start_memory

        if self._clash_bake_api.use_layer_api:
            assert self._bake_layer is not None
            start_memory = get_used_mem()
            # Copy specs to the main layer
            sdf_start_time = time.time()
            with Sdf.ChangeBlock():
                UsdUtils.StitchLayers(self._bake_layer, temp_layer)

                # These three lines below are needed to force FSD do a proper resync
                Sdf.CopySpec(self._bake_layer, Sdf.Path("/"), temp_layer, Sdf.Path("/"))
                ClashBakeAsyncUtils.remove_all_prim_specs(self._bake_layer)
                Sdf.CopySpec(temp_layer, Sdf.Path("/"), self._bake_layer, Sdf.Path("/"))
            end_time = time.time()
            status.time_update_layer = end_time - sdf_start_time
            status.memory_update_layer = get_used_mem() - start_memory

        status.finalize(self._debug_logging, total_start_time, total_start_memory, cancelled)

    async def _load_data_from_database(self, clash_infos: list[ClashInfoLike]):

        clash_infos_to_load = []
        for ci in clash_infos:
            setattr(ci, "_was_loaded", False)
            if self._clash_bake_options.generate_clash_polygons or self._clash_bake_options.generate_outlines:
                # needs frame data
                if ci.clash_frame_info_items is None or len(ci.clash_frame_info_items) < ci.num_records:
                    # frame data is not yet fully loaded
                    setattr(ci, "_was_loaded", True)
                    clash_infos_to_load.append(ci)

        await self._load_data_from_database_fn(clash_infos_to_load)
