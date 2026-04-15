# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.ui_test as ui_test
from .clash_detect_ui_test_case import ClashDetectUiTestCase


class TestsFilterWindow(ClashDetectUiTestCase):
    FILTER_WINDOW_NAME = "Custom Expression Filter###Clash"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._capture_wnd_name = self.FILTER_WINDOW_NAME
        self._capture_img_name = "filter_wnd"
        self._capture_img_width = 700
        self._capture_img_height = 400
        self._filter_window = None

    # Before running each test
    async def setUp(self):
        await super().setUp()
        # open the filter window
        await self.open_filter_window()
        if self._filter_window and self._filter_window.window:
            await self._filter_window.focus()
            self._filter_window.window.position_x = 0
            self._filter_window.window.position_y = 0
            self._filter_window.window.width = self._capture_img_width
            self._filter_window.window.height = self._capture_img_height
            await self.wait_render()
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await self.wait_render()

    async def tearDown(self):
        await super().tearDown()
        if self._filter_window:
            self._filter_window.visible = False
            self._filter_window.window.destroy()
            self._filter_window = None

    async def open_filter_window(self):
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        clash_window.window.width = 1900
        clash_window.window.visible = True
        await clash_window.focus()
        await self.wait_render()
        filter_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].name=='filter'")
        self.assertIsNotNone(filter_button)
        await filter_button.click()
        await self.wait_render()
        self._filter_window = ui_test.find(self.FILTER_WINDOW_NAME)
        self.assertIsNotNone(self._filter_window)

    async def test_filter_window_visual(self):
        await self.wait_render()  # wait for any possible tooltips to be hidden

        # Get UI elements
        help_frame = ui_test.find(f"{self.FILTER_WINDOW_NAME}//Frame/**/CollapsableFrame[*].name=='help_frame'")
        self.assertIsNotNone(help_frame)
        filter_expression_field = ui_test.find(f"{self.FILTER_WINDOW_NAME}//Frame/**/StringField[*].name=='filter_expression_field'")
        self.assertIsNotNone(filter_expression_field)

        self.assertTrue(await self.run_visual_test("initial"))

        # test help frame
        await help_frame.click()
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_help_frame"))

        # test filtering
        await filter_expression_field.input("[Triangles] > 100")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_filter_expr"))
