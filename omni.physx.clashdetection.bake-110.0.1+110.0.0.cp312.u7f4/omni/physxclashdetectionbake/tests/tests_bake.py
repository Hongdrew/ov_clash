# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb.tokens
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry
from pxr import Usd, Sdf, UsdGeom
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_info import ClashInfo
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_data_serializer_sqlite import ClashDataSerializerSqlite
from omni.physxclashdetectioncore.utils import OptimizedProgressUpdate, file_exists, safe_delete_file
from omni.kit.test import get_test_output_path

import carb
import carb.settings
import os.path
import omni.client
import omni.usd
import omni.timeline
import os
import tempfile
import stat
import shutil
import warp as wp
from omni.kit import ui_test
from typing import Awaitable, Callable

from omni.physxtestsvisual.utils import TestCase
import omni.ui as ui
from typing import Optional

TEST_WIREFRAME_THICKNESS = 1.0
TEST_OUTLINE_WIDTH_SIZE = 1.0
TEST_OUTLINE_WIDTH_SCALE = 5.0
class ClashBakeTest(TestCase):
    def __init__(self, tests=()):
        super().__init__(tests)
        self._test_data_dir = carb.tokens.get_tokens_interface().resolve(
            "${omni.physx.clashdetection.testdata}/data/USD/Bake"
        )
        self._goldens_data_dir = carb.tokens.get_tokens_interface().resolve(
            "${omni.physx.clashdetection.testdata}/data/Goldens/Bake"
        )
        self._clash_telemetry_logging_orig_val = ClashTelemetry.debug_logging
        self._ignore_save_load_events = None
        self._show_prompts_bak = None
        self._img_prefix = "test_clash_bake"
        self._viewport_settings["/app/window/hideUi"] = (True, False)
        self._viewport_settings["/app/transform/operation"] = ("select", "move")

        self._render_settings["/ngx/enabled"] = (False, True)
        self._render_settings["/rtx/indirectDiffuse/enabled"] = (False, True)
        self._render_settings["/rtx/sceneDb/ambientLightIntensity"] = (0.0, 0.0)
        self._render_settings["/rtx/directLighting/sampledLighting/enabled"] = (False, False)
        self._render_settings["/rtx/directLighting/sampledLighting/autoEnable"] = (False, True)
        self._render_settings["/rtx/newDenoiser/enabled"] = (False, True)

    async def setUp(self):
        await super().setUp()
        self._old_quiet = wp.config.quiet
        wp.config.quiet = True
        self._temp_dir = tempfile.mkdtemp(dir=get_test_output_path())
        shutil.copytree(self._test_data_dir, self._temp_dir, dirs_exist_ok=True)
        os.chmod(self._temp_dir, os.stat(self._temp_dir).st_mode | stat.S_IWRITE)
        self._curve_stage_path = os.path.join(self._temp_dir, "ClashBakingCurve.usd")
        os.chmod(self._curve_stage_path, os.stat(self._curve_stage_path).st_mode | stat.S_IWRITE)
        self._time_sampled_stage_path = os.path.join(self._temp_dir, "ClashBakingTimeSampled.usd")
        os.chmod(self._time_sampled_stage_path, os.stat(self._time_sampled_stage_path).st_mode | stat.S_IWRITE)
        self._clash_data = ClashData(ClashDataSerializerSqlite())
        self._clash_detect = ClashDetection()
        ClashTelemetry.debug_logging = True
        try:
            # disable the .ui module so stage events, so it is not interfering with the test
            from omni.physxclashdetectionui.settings import ExtensionSettings

            self._ignore_save_load_events = ExtensionSettings.ignore_save_load_events
            ExtensionSettings.ignore_save_load_events = True
            self._show_prompts_bak = ExtensionSettings.show_prompts
            ExtensionSettings.show_prompts = False
        except Exception:
            pass  # import not available, we don't need to care

    async def tearDown(self):
        wp.config.quiet = self._old_quiet
        ClashTelemetry.debug_logging = self._clash_telemetry_logging_orig_val
        try:
            from omni.physxclashdetectionui.settings import ExtensionSettings

            if self._ignore_save_load_events is not None:
                ExtensionSettings.ignore_save_load_events = self._ignore_save_load_events
            if self._show_prompts_bak is not None:
                ExtensionSettings.show_prompts = self._show_prompts_bak
        except Exception:
            pass  # import not available, we don't need to care

        # This fails on CI, so we just leave it there
        # shutil.rmtree(self._temp_dir)
        del self._temp_dir
        del self._curve_stage_path
        del self._time_sampled_stage_path
        await super().tearDown()

    async def screenshot_test(self, name: str):
        return await self.do_visual_test(
            img_name="",
            img_suffix=name,
            use_distant_light=True,
            skip_assert=True,
            threshold=0.0025,
            use_renderer_capture=True,
            setup_and_restore=False,
            img_golden_path=self._goldens_data_dir,
        )

    def _stage_cleanup(self) -> None:

        # Clear also clash layers and temp data files
        for k, v in self._clash_data._loaded_layers.items():
            if file_exists(k):
                safe_delete_file(k)
            if file_exists(v):
                safe_delete_file(v)
        self._clash_data._loaded_layers.clear()

    def _fetch_overlaps(self, stage: Usd.Stage, clash_query: ClashQuery) -> list[ClashInfo]:
        existing_clash_info_items = dict()
        new_clash_info_items = []
        setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0)
        setting_depth_epsilon = clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0)
        count = self._clash_detect.get_nb_overlaps()

        print(f"Fetching {count} overlaps")

        index = 0
        for idx in range(count):
            clash_info = self._clash_detect.process_overlap(
                stage, idx, existing_clash_info_items, clash_query.identifier, setting_tolerance, setting_depth_epsilon
            )
            if clash_info and clash_info.identifier == -1:  # identifier -1 means new clash, otherwise existing
                new_clash_info_items.append(clash_info)
            clash_info._identifier = index
            index = index + 1
        return new_clash_info_items

    def _record_curve_anims(self, stage: Usd.Stage, clash_query: Optional[ClashQuery]) -> None:
        """
        Records curve animations for the given stage and clash query.

        This function creates an AnimRecorder and gets time codes per second from the stage.
        It checks for a clash query, retrieving object paths if provided, or using the root path ("/") otherwise.
        Start and end times are determined from the clash query settings if available, or from the stage.
        Progress and memory usage are tracked during recording using the provided CodeTimer.

        Args:
            stage (Usd.Stage): The USD stage to record animations from
            clash_query (Optional[ClashQuery]): Optional clash query containing paths and settings

        Returns:
            None
        """
        anim_recorder = None
        try:
            from omni.physxclashdetectionanim.scripts.anim_recorder import AnimRecorder

            if not anim_recorder:
                anim_recorder = AnimRecorder()
        except Exception as e:
            anim_recorder = None
            print(
                "For curve anim support please enable physx.clashdetection.anim extension.\n"
                f"Import FAILED with exception: {e}"
            )
            return

        fps = stage.GetTimeCodesPerSecond()
        self.assertTrue(fps is not None and fps > 0, "Invalid stage FPS value")

        def is_xform(prim: Usd.Prim) -> bool:
            return prim.IsA(UsdGeom.Xformable)

        if clash_query and (clash_query.object_a_path or clash_query.object_b_path):
            _, int_paths_a = ClashDetection.get_list_of_prims_int_paths(
                stage, clash_query.object_a_path, True, is_xform
            )
            _, int_paths_b = ClashDetection.get_list_of_prims_int_paths(
                stage, clash_query.object_b_path, True, is_xform
            )
        else:
            # A special case - obj A and obj B paths empty means processing of the whole stage
            _, int_paths_a = ClashDetection.get_list_of_prims_int_paths(stage, "/", True, is_xform)
            int_paths_b = []

        self.assertTrue(stage.GetStartTimeCode() is not None, "Invalid stage start time")
        self.assertTrue(stage.GetEndTimeCode() is not None, "Invalid stage end time")

        start_time = float(stage.GetStartTimeCode() / fps)
        end_time = float(stage.GetEndTimeCode() / fps)

        self.assertTrue(start_time >= 0.0, "Invalid stage start time")
        self.assertTrue(end_time >= 0.0, "Invalid stage end time")

        if clash_query:
            setting_start_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_START_TIME.name)
            if setting_start_time is not None and setting_start_time > start_time:
                start_time = setting_start_time
            setting_end_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_END_TIME.name)
            if setting_end_time is not None and setting_end_time != 0.0 and setting_end_time < end_time:
                end_time = setting_end_time

        time_length = abs(end_time - start_time)
        if time_length <= 0.0:
            print("No time range to record. Skipping animation recording...")
            return

        if anim_recorder is None:
            print("Animation recorder not available. Skipping animation recording...")
            return

        for current_timecode in anim_recorder.run(stage, int_paths_a + int_paths_b, start_time, end_time, fps):
            if current_timecode < start_time:  # this can happen as user specified time might not match timeline
                start_time = current_timecode
                time_length = abs(end_time - start_time)
        recording_session_layer_name = anim_recorder.get_recording_session_layer_name()
        self.assertTrue(recording_session_layer_name is not None and recording_session_layer_name != "")

    def _execute_clash_on(self, stage: Usd.Stage) -> list[ClashInfo]:

        carb.log_info("Creating new query...")
        clash_detect_settings = {
            SettingId.SETTING_TIGHT_BOUNDS.name: True,
            SettingId.SETTING_DYNAMIC.name: True,
            SettingId.SETTING_DYNAMIC_START_TIME.name: 0.0,
            SettingId.SETTING_DYNAMIC_END_TIME.name: 5.0,
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_NEW_TASK_MANAGER.name: True,
            SettingId.SETTING_NB_TASKS.name: 128,
        }
        my_query = ClashQuery(
            query_name="My Test Query",
            object_a_path="",
            object_b_path="",
            clash_detect_settings=clash_detect_settings,
            comment="My comment",
        )
        self._clash_data.insert_query(my_query, True, True)

        carb.log_info("Setting up clash detection engine...")
        self.assertTrue(self._clash_detect.set_scope(stage, my_query.object_a_path, my_query.object_b_path))
        self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

        carb.log_info("Running curve animation recording...")
        self._record_curve_anims(stage, my_query)

        carb.log_info("Running clash detection engine...")
        progress_update = OptimizedProgressUpdate()
        num_steps = self._clash_detect.create_pipeline()
        for i in range(num_steps):
            step_data = self._clash_detect.get_pipeline_step_data(i)
            self._clash_detect.run_pipeline_step(i)
            if progress_update.update(step_data.progress):
                carb.log_info(f"\r{progress_update.progress_value}%")
        carb.log_info("\rDone!")

        clash_infos = self._fetch_overlaps(stage, my_query)
        return clash_infos

    async def load_test_stage(self, path_str) -> Usd.Stage:
        usd_context = omni.usd.get_context()
        print(f"Loading test stage '{path_str}'...")
        await usd_context.open_stage_async(path_str)  # type: ignore
        return usd_context.get_stage()  # type: ignore

    async def parametric_stage_test(self, stage_path_name: str, screenshot_name: str, options):
        from omni.physxclashdetectionbake import ClashDetectionBake

        """Executes a basic clash baking"""
        await self.new_stage()
        self._stage = await self.load_test_stage(stage_path_name)
        await self.apply_test_configuration()
        await self.wait(10)
        all_tests_passed = True
        stage = self._stage
        self.assertIsNotNone(stage)

        clash_infos = self._execute_clash_on(stage)
        EXPECTED_NUM_CLASHES = 5
        self.assertEqual(len(clash_infos), EXPECTED_NUM_CLASHES)

        # Collect all a/b paths
        paths = [(str(ci.object_a_path), str(ci.object_b_path)) for ci in clash_infos]

        # Prepare bake infos
        bake_infos = ClashDetectionBake.prepare_clash_bake_infos(stage=stage, clash_infos=clash_infos, options=options)
        self.assertEqual(len(bake_infos), EXPECTED_NUM_CLASHES)
        # Open or create two dedicates layers for clash baking, one for materials and one for meshes
        root_layer = stage.GetRootLayer()
        base_path, _ = os.path.splitext(root_layer.identifier)
        extension = "usd"
        layer_meshes_path = base_path + f"_CLASH_MESHES.{extension}"
        layer_materials_path = base_path + f"_CLASH_MATERIALS.{extension}"
        try:
            layer_meshes: Sdf.Layer = Sdf.Layer.CreateNew(layer_meshes_path)  # type: ignore
            layer_materials: Sdf.Layer = Sdf.Layer.CreateNew(layer_materials_path)  # type: ignore
        except Exception:
            layer_meshes: Sdf.Layer = Sdf.Layer.FindOrOpen(layer_meshes_path)  # type: ignore
            layer_materials: Sdf.Layer = Sdf.Layer.FindOrOpen(layer_materials_path)  # type: ignore
            layer_meshes.Clear()
            layer_materials.Clear()

        # NOTE: The layers must have same time codes per second as the original stage
        layer_meshes.timeCodesPerSecond = root_layer.timeCodesPerSecond  # type: ignore
        layer_materials.timeCodesPerSecond = root_layer.timeCodesPerSecond  # type: ignore

        # Insert layers into stage
        session_layer = stage.GetSessionLayer()
        if layer_meshes.identifier not in session_layer.subLayerPaths:
            session_layer.subLayerPaths.append(layer_meshes.identifier)
        if layer_materials.identifier not in session_layer.subLayerPaths:
            session_layer.subLayerPaths.append(layer_materials.identifier)

        # Copy Support files (material shaders mainly) to same folder where layers live
        support_paths = ClashDetectionBake.get_support_files_paths(options=options)
        dest_folder = os.path.dirname(str(layer_materials.identifier))
        for src in support_paths:
            dest = os.path.join(dest_folder, os.path.basename(src))
            await omni.client.copy_async(src, dest, omni.client.CopyBehavior.OVERWRITE)

        old_edit_target = stage.GetEditTarget()
        # Generate materials before they're referenced by meshes.
        # Generating them on a separate layer is not mandatory.
        stage.SetEditTarget(layer_materials)
        carb.log_info("Baking materials")
        materials = ClashDetectionBake.bake_clash_materials(stage=stage, options=options)

        # Bake clash meshes
        # This can be taking some time so if needed just split the bake_infos in batches to give some time to user
        # interfaces updates in order to display progress.
        # Generating them on a separate layer is not mandatory.
        stage.SetEditTarget(layer_meshes)

        carb.log_info("removing previously baked meshes")
        # Remove previously baked meshes (useful when opening an existing layer with pre-baked clash meshes)
        ClashDetectionBake.remove_baked_meshes(stage=stage, paths=paths, options=options)

        carb.log_info("Baking Meshes")
        ClashDetectionBake.bake_clash_meshes(stage=stage, bake_infos=bake_infos, materials=materials, options=options)

        # Finalize mesh baking (runs optimization / merge operations)
        # Also this operation can be taking some time so if needed split paths in batches and interleave with user
        # interface updates in order to display progress.
        carb.log_info("Finalizing Meshes")
        ClashDetectionBake.finalize_clash_meshes(stage=stage, paths=paths, options=options)
        # Make sure to restore original edit target in any case
        stage.SetEditTarget(old_edit_target)

        await self.wait(10)
        omni.timeline.get_timeline_interface().set_current_time(1)
        await self.wait(40)

        old_wireframe_thickness = carb.settings.get_settings().get_as_float("/rtx/wireframe/wireframeThickness")
        carb.settings.get_settings().set_float("/rtx/wireframe/wireframeThickness", TEST_WIREFRAME_THICKNESS)
        all_tests_passed &= await self.screenshot_test(f"{self._img_prefix}_{screenshot_name}")
        carb.settings.get_settings().set_float("/rtx/wireframe/wireframeThickness", old_wireframe_thickness)
        carb.log_info("Clash baking finished")

        # Save the layers
        layer_materials.Save()  # type: ignore
        layer_meshes.Save()  # type: ignore

        carb.log_info("Cleanup...")
        self._stage_cleanup()
        # These two cause problems with FSD
        # session_layer.subLayerPaths.remove(layer_meshes.identifier)
        # session_layer.subLayerPaths.remove(layer_materials.identifier)

        del layer_materials
        del layer_meshes
        del stage
        del session_layer

        await self.new_stage()
        self.assertTrue(all_tests_passed)

        carb.log_info("Deleting support files...")
        for src in support_paths:
            dest = os.path.join(dest_folder, os.path.basename(src))
            await omni.client.delete_async(dest)
        await omni.client.delete_async(layer_meshes_path)
        await omni.client.delete_async(layer_materials_path)

    async def apply_test_configuration(self):
        window = ui.Workspace.get_window("Viewport")
        test_window_width = 1000
        test_window_height = 800
        await self.setup_viewport_test(test_window_width, test_window_height)
        window.padding_x = 0  # type: ignore
        window.padding_y = 0  # type: ignore
        window.position_x = 0  # type: ignore
        window.position_y = 0  # type: ignore
        window.noTabBar = True  # type: ignore
        window.flags = (  # type: ignore
            ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_MOVE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        window.auto_resize = False  # type: ignore
        window.width = test_window_width
        window.height = test_window_height

    async def test_bake_curve_hole_indices_full(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._curve_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False # Wireframes offseting is not implemented for non layer mode
        options.generate_clash_polygons = True
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        # Private Options
        setattr(options, "_use_display_opacity", False)
        await self.parametric_stage_test(stage_path_name, "curve_hole_indices", options)

    async def test_bake_curve_hole_indices_outlines(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._curve_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False
        options.generate_clash_polygons = False
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        # Private Options
        setattr(options, "_use_display_opacity", False)
        await self.parametric_stage_test(stage_path_name, "curve_hole_indices_outlines", options)

    async def test_bake_curve_display_opacity_full(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._curve_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False # Wireframes offseting is not implemented for non layer mode
        options.generate_clash_polygons = True
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        await self.parametric_stage_test(stage_path_name, "curve_display_opacity", options)

    async def test_bake_curve_display_opacity_outlines(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._curve_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        options.generate_clash_polygons = False
        await self.parametric_stage_test(stage_path_name, "curve_display_opacity_outlines", options)

    async def parametric_layer_test(
        self,
        stage_path_name: str,
        screenshot_name: str,
        options,
        time: float = 1.0,
        custom_lambda: Callable[[], Awaitable[bool]] | None = None,
    ):
        from omni.physxclashdetectionbake import ClashBakeLayer

        """Executes a basic clash baking"""
        await self.new_stage()
        self._stage = await self.load_test_stage(stage_path_name)
        await self.apply_test_configuration()
        await self.wait(10)
        all_tests_passed = True
        stage = self._stage
        self.assertIsNotNone(stage)

        clash_infos = self._execute_clash_on(stage)
        EXPECTED_NUM_CLASHES = 5
        self.assertEqual(len(clash_infos), EXPECTED_NUM_CLASHES)

        # Collect all a/b paths
        paths = [(str(ci.object_a_path), str(ci.object_b_path)) for ci in clash_infos]

        # Open or create two dedicates layers for clash baking, one for materials and one for meshes
        root_layer = stage.GetRootLayer()
        base_path, _ = os.path.splitext(root_layer.identifier)
        extension = "usd"
        layer_meshes_path = base_path + f"_CLASH_MESHES.{extension}"
        layer_materials_path = base_path + f"_CLASH_MATERIALS.{extension}"
        try:
            layer_meshes: Sdf.Layer = Sdf.Layer.CreateNew(layer_meshes_path)  # type: ignore
            layer_materials: Sdf.Layer = Sdf.Layer.CreateNew(layer_materials_path)  # type: ignore
        except Exception:
            layer_meshes: Sdf.Layer = Sdf.Layer.FindOrOpen(layer_meshes_path)  # type: ignore
            layer_materials: Sdf.Layer = Sdf.Layer.FindOrOpen(layer_materials_path)  # type: ignore
            layer_meshes.Clear()
            layer_materials.Clear()

        # Remove previously baked meshes (useful when opening an existing layer with pre-baked clash meshes)
        ClashBakeLayer.remove_baked_meshes(stage=stage, layer=layer_meshes, paths=paths, options=options)

        # NOTE: The layers must have same time codes per second as the original stage
        layer_meshes.timeCodesPerSecond = root_layer.timeCodesPerSecond  # type: ignore
        layer_materials.timeCodesPerSecond = root_layer.timeCodesPerSecond  # type: ignore

        # Prepare bake infos
        bake_infos = ClashBakeLayer.prepare_clash_bake_infos(stage=stage, clash_infos=clash_infos, options=options)
        self.assertEqual(len(bake_infos), EXPECTED_NUM_CLASHES)

        # Copy Support files (material shaders mainly) to same folder where layers live
        support_paths = ClashBakeLayer.get_support_files_paths(options=options)
        dest_folder = os.path.dirname(str(layer_materials.identifier))
        for src in support_paths:
            dest = os.path.join(dest_folder, os.path.basename(src))
            await omni.client.copy_async(src, dest, omni.client.CopyBehavior.OVERWRITE)

        if not options.use_selection_groups:
            # Generate materials before they're referenced by meshes.
            # Generating them on a separate layer is not mandatory and not needed for selection groups anyway.
            carb.log_info("Baking materials")
            materials = ClashBakeLayer.bake_clash_materials(layer=layer_materials, options=options)
        else:
            materials = None

        # Bake clash meshes
        # This can be taking some time so if needed just split the bake_infos in batches to give some time to user
        # interfaces updates in order to display progress.
        # Generating them on a separate layer is not mandatory.
        carb.log_info("Baking Meshes")
        ClashBakeLayer.bake_clash_meshes(
            layer=layer_meshes, bake_infos=bake_infos, materials=materials, options=options
        )

        # Finalize mesh baking (runs optimization / merge operations)
        # Also this operation can be taking some time so if needed split paths in batches and interleave with user
        # interface updates in order to display progress.
        carb.log_info("Finalizing Meshes")
        ClashBakeLayer.finalize_clash_meshes(layer=layer_meshes, bake_infos=bake_infos, options=options)

        await self.wait(10)
        omni.timeline.get_timeline_interface().set_current_time(time)
        await self.wait(10)

        # Insert layers into stage to take the screenshot
        session_layer = stage.GetSessionLayer()
        if layer_meshes.identifier not in session_layer.subLayerPaths:
            session_layer.subLayerPaths.append(layer_meshes.identifier)
        if not options.use_selection_groups:
            if layer_materials.identifier not in session_layer.subLayerPaths:
                session_layer.subLayerPaths.append(layer_materials.identifier)
        old_wireframe_thickness = carb.settings.get_settings().get_as_float("/rtx/wireframe/wireframeThickness")
        carb.settings.get_settings().set_float("/rtx/wireframe/wireframeThickness", TEST_WIREFRAME_THICKNESS)
        await self.wait(40)

        all_tests_passed &= await self.screenshot_test(f"{self._img_prefix}_{screenshot_name}")
        carb.settings.get_settings().set_float("/rtx/wireframe/wireframeThickness", old_wireframe_thickness)

        if custom_lambda:
            all_tests_passed &= await custom_lambda()

        carb.log_info("Clash baking finished")

        # Save the layers
        layer_materials.Save()  # type: ignore
        layer_meshes.Save()  # type: ignore

        carb.log_info("Cleanup...")
        self._stage_cleanup()
        # These two cause problems with FSD
        # session_layer.subLayerPaths.remove(layer_meshes.identifier)
        # session_layer.subLayerPaths.remove(layer_materials.identifier)

        del layer_materials
        del layer_meshes
        del stage
        del session_layer

        await self.new_stage()
        self.assertTrue(all_tests_passed)

        carb.log_info("Deleting support files...")
        for src in support_paths:
            dest = os.path.join(dest_folder, os.path.basename(src))
            await omni.client.delete_async(dest)
        await omni.client.delete_async(layer_meshes_path)
        await omni.client.delete_async(layer_materials_path)

    async def test_bake_keyframe_layer(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._time_sampled_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False
        options.generate_clash_polygons = True
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        options.use_selection_groups = False
        await self.parametric_layer_test(stage_path_name, "keyframe_layer", options, time=0.45)
 
    async def test_bake_keyframe_layer_wireframe(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._time_sampled_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = True
        options.generate_clash_polygons = True
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        options.use_selection_groups = False
        await self.parametric_layer_test(stage_path_name, "keyframe_layer_wireframe", options)

    async def test_bake_selection_groups(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._time_sampled_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False
        options.generate_clash_polygons = False
        options.generate_outlines = True
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        screenshot_name = "selection_groups"

        async def select_deselect():
            # Test that the selection will "disable" the selection groups highlight and that deselecting will restore it
            # Selection from viewport clears the selection groups, but calling set_selected_prim_paths does not
            # Probably the extension handling the viewport clicks is responsible for clearing groups.
            # usd_context.get_selection().set_selected_prim_paths(prims_to_select, True)
            await self.apply_test_configuration()
            window = ui_test.find("Viewport")
            await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window.position.x + 550, window.position.y + 460))
            await self.wait(100)
            test_passed = True
            # Click on the Cylinder to select it, and that will clear the selection group
            test_passed &= await self.screenshot_test(f"{self._img_prefix}_{screenshot_name}_selected")
            await self.apply_test_configuration()
            # Click on the "void" to reset the selection
            await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window.position.x + 400, window.position.y + 80))
            await self.wait(100)
            test_passed &= await self.screenshot_test(f"{self._img_prefix}_{screenshot_name}_deselected")
            return test_passed

        await self.parametric_layer_test(stage_path_name, screenshot_name, options, custom_lambda=select_deselect)

    async def test_bake_selection_groups_outlines(self):
        from omni.physxclashdetectionbake import ClashBakeOptions

        stage_path_name = self._time_sampled_stage_path
        options = ClashBakeOptions()
        options.generate_wireframe = False
        options.generate_clash_polygons = False
        options.generate_outlines = True
        options.generate_clash_meshes = False
        options.outline_width_size = TEST_OUTLINE_WIDTH_SIZE
        options.outline_width_scale = TEST_OUTLINE_WIDTH_SCALE
        await self.parametric_layer_test(stage_path_name, "selection_groups_outlines", options)
