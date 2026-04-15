# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from pxr import Gf, Usd, UsdGeom

import omni.kit.ui_test as ui_test
import carb.tokens
import omni.ui as ui
import omni.usd
import omni.kit.commands
import carb.settings
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from omni.physxtests import utils
from omni.physxtests.utils.physicsBase import TestCategory
from omni.physxtestsvisual.utils import TestCase

from ..clash_viewport_settings import ClashViewportSettings
from .test_clash_detection_mock import TestClashDetectionMock
from ..clash_viewport_utility import get_context_stage, close_stage_async

TEST_WIREFRAME_THICKNESS = 1.0
class TestClashViewportVisualization(TestCase):
    category = TestCategory.Core

    SETTING_CLASH_DETECTION_WINDOW = "/physics/showClashDetectionWindow"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._goldens_data_dir = carb.tokens.get_tokens_interface().resolve(
            "${omni.physx.clashdetection.testdata}/data/Goldens/Viewport"
        )

        self._render_settings["/ngx/enabled"] = (False, True)
        self._render_settings["/rtx/indirectDiffuse/enabled"] = (False, True)
        self._render_settings["/rtx/sceneDb/ambientLightIntensity"] = (0.0, 0.0)
        self._render_settings["/rtx/directLighting/sampledLighting/enabled"] = (False, False)
        self._render_settings["/rtx/directLighting/sampledLighting/autoEnable"] = (False, True)
        self._render_settings["/rtx/newDenoiser/enabled"] = (False, True)

        self._ignore_save_load_events = None
        self._show_prompts_bak = None
        self._clash_interface = TestClashDetectionMock()

    async def setUp(self):
        await super().setUp()
        await self.new_stage()
        self._create_references = False
        self._reference_path = ""
        self._img_prefix = "test_clash_viewport"
        settings = carb.settings.get_settings()
        self._old_clash_detection_window = settings.get(TestClashViewportVisualization.SETTING_CLASH_DETECTION_WINDOW)
        self._old_clash_detection_viewport = settings.get(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
        # TODO: Add tests variation with enabled selection groups and disabled translucent materials
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, False)
        if not self._old_clash_detection_window:
            settings.set_bool(TestClashViewportVisualization.SETTING_CLASH_DETECTION_WINDOW, True)
        self._restore_clash_detection_viewport = False
        if not self._old_clash_detection_viewport:
            settings.get(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
        settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, True)
        settings.set_bool(ClashViewportSettings.LOG_PROFILE, False)
        # This is needed to avoid camera-recentering in tests
        settings.set_float(ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE, 0)
        settings.set_float(ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE, 0)
        settings.set_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE, 0.5)
        settings.set_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE, 5.0)

        self._clash_interface.find_controls()
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
        await super().tearDown()
        self._clash_interface.clear_controls()
        try:
            from omni.physxclashdetectionui.settings import ExtensionSettings

            if self._ignore_save_load_events is not None:
                ExtensionSettings.ignore_save_load_events = self._ignore_save_load_events
            if self._show_prompts_bak is not None:
                ExtensionSettings.show_prompts = self._show_prompts_bak
            await self.restore()
        except Exception:
            pass  # import not available, we don't need to care

    async def create_query(self, duplicate: bool, dynamic: bool, soft: bool):
        await self._clash_interface.create_new_query("My Query", duplicate, dynamic, soft)
        await self._clash_interface.select_clash_detection_query(0)

    def set_xform(self, prim, translation : Gf.Vec3f, rotation : Gf.Vec3f):
        xform: UsdGeom.Xform = UsdGeom.Xform(prim)
        # Clear all xform ops and set translation and rotation
        xform.ClearXformOpOrder()
        xform.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(translation)
        xform.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble).Set(rotation)

    def get_rotation(self, prim):
        xform: UsdGeom.Xform = UsdGeom.Xform(prim)
        xformops = xform.GetOrderedXformOps()
        return xformops[1]

    def get_translation(self, prim):
        xform: UsdGeom.Xform = UsdGeom.Xform(prim)
        xformops = xform.GetOrderedXformOps()
        return xformops[0]

    def create_torus(self, stage: Usd.Stage, translation: Gf.Vec3f, rotation: Gf.Vec3f) -> str:
        if self._create_references:
            if len(self._reference_path) == 0:
                self._reference_path = "/World/Prototype"
                omni.kit.commands.execute(
                    "CreatePrimWithDefaultXform", prim_path=self._reference_path, prim_type="Xform"
                )
                prototype = stage.GetPrimAtPath(self._reference_path)
                prototype.SetInstanceable(True)
                self.set_xform(prototype, Gf.Vec3f(0, 1000, 0), Gf.Vec3f(0, 0, 0))
                path_tuple = omni.kit.commands.execute(
                    "CreateMeshPrimWithDefaultXform", prim_path=self._reference_path + "/Torus", prim_type="Torus"
                )
            wanted_path = stage.GetPseudoRoot().GetPath().AppendPath("World").AppendPath("XForm")
            prim_path = omni.usd.get_stage_next_free_path(stage, str(wanted_path), False)
            omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_path=prim_path, prim_type="Xform")
            xform_prim = stage.GetPrimAtPath(prim_path)
            xform_prim.GetReferences().AddReference("", self._reference_path)
        else:
            path_tuple = omni.kit.commands.execute("CreateMeshPrimWithDefaultXform", prim_type="Torus")
            prim_path = path_tuple[1]
        self.set_xform(stage.GetPrimAtPath(prim_path), translation, rotation)
        assert prim_path
        return prim_path

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

    async def apply_test_configuration(self, width, height, window_name):
        window = ui.Workspace.get_window(window_name)
        await self.setup_viewport_test(width, height, window_name)
        window.padding_x = 0  # type: ignore
        window.padding_y = 0  # type: ignore
        window.position_x = 0
        window.position_y = 0
        window.visible = True
        window.auto_resize = False  # type: ignore
        window.width = width
        window.height = height
        # We set thickness here because opening clash viewport will load / restore main viewport settings
        carb.settings.get_settings().set_float("/rtx/wireframe/wireframeThickness", TEST_WIREFRAME_THICKNESS)
        await ui_test.find(window_name).focus()

    # Small helper function to run a test with a given viewport name
    async def _run_test(self, time):
        await self._clash_interface.unselect_clash_result()
        await self.wait(1)  # Wait for rendering
        await self._clash_interface.select_clash_result(0, time)
        await self.wait(30)  # Wait for rendering

    async def check_screenshots(self, test_name: str, time: float = 0) -> bool:
        settings = carb.settings.get_settings()

        main_viewport_file = f"{test_name}_main"
        clash_viewport_file = f"{test_name}_clash"

        all_passed = True
        usd_context = omni.usd.get_context()
        main_selection: omni.usd.Selection = usd_context.get_selection()
        main_selection.clear_selected_prim_paths()

        await self._clash_interface.run_clash_detection()
        await self.wait(5)  # Wait for Clash

        await utils.wait_for_stage_loading_status(usd_context, 5)

        # Setup camera for main viewport
        viewport = get_active_viewport("Viewport")
        viewport_camera_state = ViewportCameraState(viewport=viewport)
        viewport_camera_state.set_position_world(Gf.Vec3f(500.0, 50.0, 0.0), True)
        viewport_camera_state.set_target_world(Gf.Vec3f(0.0, 50.0, 0.0), True)

        await self.apply_test_configuration(500, 500, "Viewport")

        #############################################################################################################
        # Test 1: Main viewport with selection groups disabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, False)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, True)
        await self._run_test(time)
        all_passed = await self.screenshot_test(main_viewport_file) and all_passed

        #############################################################################################################
        # Test 2: Main viewport with selection groups enabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, True)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{main_viewport_file}_use_selection_groups") and all_passed

        #############################################################################################################
        # Test 3: Main viewport with selection groups enabled and clash meshes disabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, False)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, True)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{main_viewport_file}_no_show_clash_meshes") and all_passed

        #############################################################################################################
        # Test 4: Main viewport with selection groups enabled and clash outlines disabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, False)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{main_viewport_file}_no_show_clash_outlines") and all_passed

        #############################################################################################################
        # Test 5: Main viewport with selection groups enabled and clash meshes disabled
        #############################################################################################################
        # Disable main viewport visualization so that main context clash layer is unloaded
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, False)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, False)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{main_viewport_file}_unload_clash_layer") and all_passed

        #############################################################################################################
        # Clash viewport tests
        #############################################################################################################
        clash_viewport = get_active_viewport("Clash Detection Viewport")
        clash_viewport_camera_state = ViewportCameraState(viewport=clash_viewport)
        clash_viewport_camera_state.set_position_world(Gf.Vec3f(500.0, 50.0, 0.0), True)
        clash_viewport_camera_state.set_target_world(Gf.Vec3f(0.0, 50.0, 0.0), True)

        # Reset default settings
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, True)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS, True)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, True)

        await self.apply_test_configuration(500, 500, "Clash Detection Viewport")

        #############################################################################################################
        # Test 8: Clash viewport test with clashes disabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, False)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{clash_viewport_file}_no_show_clashes") and all_passed
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, True)

        #############################################################################################################
        # Test 6: Clash viewport test
        #############################################################################################################
        await self._run_test(time)
        all_passed = await self.screenshot_test(clash_viewport_file) and all_passed

        #############################################################################################################
        # Test 7: Clash viewport test with translucent materials disabled
        #############################################################################################################
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS, False)
        await self._run_test(time)
        all_passed = await self.screenshot_test(f"{clash_viewport_file}_no_translucent_materials") and all_passed

        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS, True)

        return all_passed

    async def change_options(self):
        await self._clash_interface.unselect_clash_result()
        settings = carb.settings.get_settings()
        settings.set_bool(ClashViewportSettings.USE_SOURCE_NORMALS, True)
        await self.wait(1)
        await self._clash_interface.select_clash_result(0, 0)
        settings.set_bool(ClashViewportSettings.USE_SOURCE_NORMALS, False)
        settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, False)
        await self.wait(1)
        settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, True)
        await self.wait(1)
        from ..extension import get_api_instance

        get_api_instance().hide_all_clash_meshes()
        await self.wait(1)

    async def test_static_clash(self):
        all_tests_passed = True

        await self.create_query(False, False, False)
        stage = get_context_stage(omni.usd.get_context())
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))
        await self.wait(10)  # This is needed for FSD to ensure that first torus is created before second torus
        prim_path2 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        all_tests_passed = await self.check_screenshots(f"{self._img_prefix}_static")

        self.set_xform(stage.GetPrimAtPath(prim_path1), Gf.Vec3f(0, 0, -30), Gf.Vec3f(0, 0, -20))
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_static_moved1") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path1), Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))

        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 160), Gf.Vec3f(0, 0, 80))
        await self.wait(10)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_static_moved2") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))
        await self.wait(10)

        stage.RemovePrim(prim_path1)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_static_removed1") and all_tests_passed

        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))
        stage.RemovePrim(prim_path2)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_static_removed2") and all_tests_passed

        stage.RemovePrim(prim_path1)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_static_removed3") and all_tests_passed

        # Coverage increase actions
        await self.change_options()
        stage = None
        self._clash_interface.clear_controls()
        await close_stage_async(omni.usd.get_context())

        self.assertTrue(all_tests_passed)

    async def test_duplicate_clash(self):
        all_tests_passed = True

        await self.create_query(True, False, False)
        stage = get_context_stage(omni.usd.get_context())
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))
        await self.wait(10)  # This is needed for FSD to ensure that first torus is created before second torus
        prim_path2 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        all_tests_passed = await self.check_screenshots(f"{self._img_prefix}_duplicate")

        self.set_xform(stage.GetPrimAtPath(prim_path1), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 70))
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_duplicate_moved1") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path1), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 70))
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_duplicate_moved2") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        stage.RemovePrim(prim_path1)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_duplicate_removed1") and all_tests_passed
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        stage.RemovePrim(prim_path2)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_duplicate_removed2") and all_tests_passed

        stage.RemovePrim(prim_path1)
        await self._run_test(0)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_duplicate_removed3") and all_tests_passed
        stage = None
        self._clash_interface.clear_controls()
        await close_stage_async(omni.usd.get_context())

        self.assertTrue(all_tests_passed)

    async def test_dynamic_clash(self):

        all_tests_passed = True

        await self.create_query(False, True, False)
        stage = get_context_stage(omni.usd.get_context())
        stage.SetTimeCodesPerSecond(60)
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))
        await self.wait(10)  # This is needed for FSD to ensure that first torus is created before second torus
        prim_path2 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        prim1 = stage.GetPrimAtPath(prim_path1)
        self.get_translation(prim1).Set(time=0, value=Gf.Vec3f(0, 0, -30))
        self.get_translation(prim1).Set(time=60, value=Gf.Vec3f(0, 0, 0))
        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, 20))

        all_tests_passed = await self.check_screenshots(f"{self._img_prefix}_dynamic", 0.5)
        end_time = 1.95

        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_end") and all_tests_passed

        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, 50))
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_moved1") and all_tests_passed

        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 200), Gf.Vec3f(0, 0, 80))
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_moved2") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        stage.RemovePrim(prim_path1)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_removed1") and all_tests_passed
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))
        prim1 = stage.GetPrimAtPath(prim_path1)
        self.get_translation(prim1).Set(time=0, value=Gf.Vec3f(0, 0, -30))
        self.get_translation(prim1).Set(time=60, value=Gf.Vec3f(0, 0, 0))
        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, 20))

        stage.RemovePrim(prim_path2)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_removed2") and all_tests_passed

        stage.RemovePrim(prim_path1)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_removed3") and all_tests_passed
        stage = None
        self._clash_interface.clear_controls()
        await close_stage_async(omni.usd.get_context())

        self.assertTrue(all_tests_passed)

    async def test_dynamic_soft_clash(self):

        all_tests_passed = True

        await self.create_query(False, True, True)
        stage = get_context_stage(omni.usd.get_context())
        stage.SetTimeCodesPerSecond(60)
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, -30), Gf.Vec3f(0, 0, -20))
        await self.wait(10)  # This is needed for FSD to ensure that first torus is created before second torus
        prim_path2 = self.create_torus(stage, Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        prim1 = stage.GetPrimAtPath(prim_path1)
        self.get_translation(prim1).Set(time=0, value=Gf.Vec3f(0, 0, -50))
        self.get_translation(prim1).Set(time=60, value=Gf.Vec3f(0, 0, -40))
        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, -30))

        end_time = 1.95
        all_tests_passed = await self.check_screenshots(f"{self._img_prefix}_dynamic_soft", end_time)

        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, -60))
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_soft_moved1") and all_tests_passed

        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, -30))
        await self.wait(1)
        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 200), Gf.Vec3f(0, 0, 80))
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_soft_moved2") and all_tests_passed
        self.set_xform(stage.GetPrimAtPath(prim_path2), Gf.Vec3f(0, 0, 130), Gf.Vec3f(0, 0, 80))

        stage.RemovePrim(prim_path1)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_soft_removed1") and all_tests_passed
        prim_path1 = self.create_torus(stage, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 0, -20))
        prim1 = stage.GetPrimAtPath(prim_path1)
        self.get_translation(prim1).Set(time=0, value=Gf.Vec3f(0, 0, -30))
        self.get_translation(prim1).Set(time=60, value=Gf.Vec3f(0, 0, 0))
        self.get_translation(prim1).Set(time=120, value=Gf.Vec3f(0, 0, 20))

        stage.RemovePrim(prim_path2)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_soft_removed2") and all_tests_passed

        stage.RemovePrim(prim_path1)
        await self._run_test(end_time)
        all_tests_passed = await self.screenshot_test(f"{self._img_prefix}_dynamic_soft_removed3") and all_tests_passed
        stage = None
        self._clash_interface.clear_controls()
        await close_stage_async(omni.usd.get_context())

        self.assertTrue(all_tests_passed)

    async def test_static_clash_instanced(self):
        self._create_references = True
        self._img_prefix = "test_clash_viewport_instanced"
        await self.test_static_clash()

    async def test_duplicate_clash_instanced(self):
        self._create_references = True
        self._img_prefix = "test_clash_viewport_instanced"
        await self.test_duplicate_clash()

    async def test_dynamic_clash_instanced(self):
        self._create_references = True
        self._img_prefix = "test_clash_viewport_instanced"
        await self.test_dynamic_clash()

    async def test_dynamic_soft_clash_instanced(self):
        self._create_references = True
        self._img_prefix = "test_clash_viewport_instanced"
        await self.test_dynamic_soft_clash()
