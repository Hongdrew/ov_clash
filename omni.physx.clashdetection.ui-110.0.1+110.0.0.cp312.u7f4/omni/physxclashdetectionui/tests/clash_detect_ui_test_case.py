# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import os
import gc
import carb
import carb.settings
import omni.kit.app
import omni.usd
import omni.ui as ui
import omni.kit.ui_test as ui_test
from omni.physxtestsvisual.utils import TestCase
from ..settings import ExtensionSettings
from omni.physxclashdetectioncore.config import ExtensionConfig


class ClashDetectUiTestCase(TestCase):
    CLASH_WND_NAME = "Clash Detection"
    PROGRESS_WND_NAME = "Clash Detection Progress"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._goldens_data_dir = carb.tokens.get_tokens_interface().resolve(
            "${omni.physx.clashdetection.testdata}/data/Goldens/UI"
        )
        self._settings = carb.settings.get_settings()
        test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
        self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'
        self._capture_wnd_name = self.CLASH_WND_NAME
        self._capture_img_name = "clash_detect_ui"
        self._capture_img_width = 1900
        self._capture_img_height = 1100
        self._clash_query_window = None
        # overridden settings
        self._clash_detect_wnd_bak = None
        self._show_full_clash_paths_bak = None
        self._show_prompts_bak = None
        self._ui_no_timestamps = None
        self._development_mode_bak = None
        self._core_debug_logging_bak = None

    # Before running each test
    async def setUp(self):
        await super().setUp()
        await self._setup_window(1920, 1100)

        self._clash_detect_wnd_bak = self._settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW)
        self._settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, True)

        self._show_full_clash_paths_bak = ExtensionSettings.show_full_clash_paths
        ExtensionSettings.show_full_clash_paths = False

        self._show_prompts_bak = ExtensionSettings.show_prompts
        ExtensionSettings.show_prompts = False

        self._ui_no_timestamps = ExtensionSettings.ui_no_timestamps
        ExtensionSettings.ui_no_timestamps = True

        self._ui_no_locale_formatting = ExtensionSettings.ui_no_locale_formatting
        ExtensionSettings.ui_no_locale_formatting = True

        self._development_mode_bak = ExtensionSettings.development_mode
        ExtensionSettings.development_mode = False

        self._core_debug_logging_bak = ExtensionConfig.debug_logging
        ExtensionConfig.debug_logging = True

        await self.wait(5)
        (result, err) = await omni.usd.get_context().new_stage_async()

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()

        if self._show_full_clash_paths_bak is not None:
            ExtensionSettings.show_full_clash_paths = self._show_full_clash_paths_bak
        if self._show_prompts_bak is not None:
            ExtensionSettings.show_prompts = self._show_prompts_bak
        if self._ui_no_timestamps is not None:
            ExtensionSettings.ui_no_timestamps = self._ui_no_timestamps
        if self._ui_no_locale_formatting is not None:
            ExtensionSettings.ui_no_locale_formatting = self._ui_no_locale_formatting
        if self._clash_detect_wnd_bak is not None:
            self._settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, self._clash_detect_wnd_bak)
        if self._development_mode_bak is not None:
            ExtensionSettings.development_mode = self._development_mode_bak
        if self._core_debug_logging_bak is not None:
            ExtensionConfig.debug_logging = self._core_debug_logging_bak

        await super().tearDown()
        gc.collect()

    async def wait(self, frames=1):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    async def wait_render(self, frames=5):
        await self.wait(frames)

    async def prepare_for_visual_test(self):
        await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
        await self.setup_docked_test(self._capture_wnd_name, None, self._capture_img_width, self._capture_img_height)
        await self.wait_render()

    async def run_visual_test(self, img_suffix, threshold=0.001) -> bool:
        await self.prepare_for_visual_test()
        return await self.do_visual_test(
            img_name=self._capture_img_name,
            img_suffix=f"_{img_suffix}",
            use_distant_light=True,
            threshold=threshold,
            use_renderer_capture=False,
            setup_and_restore=True,
            img_golden_path=self._goldens_data_dir,
        )

    def check_menu_visibility(self, menu_name: str, num_items: int):
        current_menu = ui.Menu.get_current()
        self.assertIsNotNone(current_menu)
        self.assertTrue(current_menu.visible)
        self.assertTrue(current_menu.shown)
        self.assertEqual(current_menu.text, menu_name)
        menu_items = ui.Inspector.get_children(current_menu)
        self.assertEqual(len(menu_items) - 2, num_items)  # -2 for surrounding frames
