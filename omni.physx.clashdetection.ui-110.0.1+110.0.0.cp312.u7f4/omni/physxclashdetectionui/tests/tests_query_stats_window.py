# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
import omni.kit.ui_test as ui_test
from .clash_detect_ui_test_case import ClashDetectUiTestCase
from ..settings import ExtensionSettings


class TestsQueryStatsWindow(ClashDetectUiTestCase):
    CLASH_QUERY_STATS_WND_NAME = "Clash Query Stats"
    CLASH_QUERY_MANAGEMENT_WND_NAME = "Clash Query Management"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._capture_wnd_name = self.CLASH_QUERY_STATS_WND_NAME
        self._capture_img_name = "clash_query_stats_wnd"
        self._capture_img_width = 800
        self._capture_img_height = 600
        self._clash_query_stats_window = None

    # Before running each test
    async def setUp(self):
        await super().setUp()
        # open the query stats window
        await self.open_query_stats_wnd()
        if self._clash_query_stats_window and self._clash_query_stats_window.window:
            await self._clash_query_stats_window.focus()
            self._clash_query_stats_window.window.position_x = 0
            self._clash_query_stats_window.window.position_y = 0
            self._clash_query_stats_window.window.width = self._capture_img_width
            self._clash_query_stats_window.window.height = self._capture_img_height
            await self.wait_render()
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await self.wait_render()

    async def tearDown(self):
        await super().tearDown()
        if self._clash_query_stats_window:
            self._clash_query_stats_window.visible = False
            self._clash_query_stats_window.window.destroy()
            self._clash_query_stats_window = None

    async def create_static_clash_queries(self):
        import omni.usd
        from omni.physxclashdetectioncore.clash_detect_settings import SettingId
        from omni.physxclashdetectioncore.clash_query import ClashQuery

        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        await omni.usd.get_context(ExtensionSettings.usd_context_name).open_stage_async(stage_path_name)
        stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        print("Creating new dynamic query...")
        my_query = ClashQuery(
            query_name="Static Query",
            object_a_path="",
            object_b_path="",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: False,
                SettingId.SETTING_TOLERANCE.name: 3.0,
                SettingId.SETTING_NEW_TASK_MANAGER.name: True,
                SettingId.SETTING_NB_TASKS.name: 128,
            },
            comment="UI test query"
        )
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)
        my_query.query_name = "Static Query X"
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 2)

    async def run_clash_detection(self, run_clash_detection_button):
        await run_clash_detection_button.click()  # run clash detection with the selected query
        await self.wait(100)
        while not run_clash_detection_button.widget.enabled:
            await self.wait(5)

    async def create_and_run_clash_query(self):
        # Get UI elements
        clash_query_combobox = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'")
        self.assertIsNotNone(clash_query_combobox)
        self.assertTrue(clash_query_combobox.widget.enabled)
        self.assertEqual(len(clash_query_combobox.widget.model.items), 0)
        self.assertEqual(clash_query_combobox.widget.model._current_index.as_int, -1)

        run_clash_detection_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Run Clash Detection'")
        self.assertIsNotNone(run_clash_detection_button)
        self.assertFalse(run_clash_detection_button.widget.enabled)

        # create a clash query and execute clash detection
        await self.create_static_clash_queries()
        self._settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        clash_query_combobox.widget.model.select_item_index(0)

        self.assertTrue(run_clash_detection_button.widget.enabled)
        await self.run_clash_detection(run_clash_detection_button)

    async def open_query_stats_wnd(self):
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        clash_window.window.width = 1900
        clash_window.window.visible = True
        await clash_window.focus()
        await self.wait_render()
        await self.create_and_run_clash_query()
        await self.wait_render()
        query_management_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Query Management'")
        self.assertIsNotNone(query_management_button)
        await query_management_button.click()
        await self.wait_render()
        self._clash_query_window = ui_test.find(self.CLASH_QUERY_MANAGEMENT_WND_NAME)
        self.assertIsNotNone(self._clash_query_window)
        stats_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Statistics'")
        self.assertIsNotNone(stats_button)
        self.assertTrue(stats_button.widget.enabled)
        await stats_button.click()
        await self.wait_render()
        self._clash_query_stats_window = ui_test.find(self.CLASH_QUERY_STATS_WND_NAME)
        self.assertIsNotNone(self._clash_query_stats_window)

    async def wait_for_data_loaded(self):
        # wait for the data to be loaded
        while self._clash_query_stats_window.window._loading_task is not None:
            await asyncio.sleep(0.25)
            await self.wait(1)
        await self.wait_render()

    async def test_query_stats_wnd_visual(self):
        await self.wait_render()  # wait for any possible tooltips to be hidden

        await self.wait_for_data_loaded()

        # Get UI elements
        refresh_button = ui_test.find(f"{self.CLASH_QUERY_STATS_WND_NAME}//Frame/**/Button[*].name=='refresh'")
        self.assertIsNotNone(refresh_button)
        search_field = ui_test.find(f"{self.CLASH_QUERY_STATS_WND_NAME}//Frame/**/StringField[0]")
        self.assertIsNotNone(search_field)
        stats_tree = ui_test.find(f"{self.CLASH_QUERY_STATS_WND_NAME}//Frame/**/TreeView[*].name=='stats'")
        self.assertIsNotNone(stats_tree)

        self.assertTrue(await self.run_visual_test("initial"))

        # check context menu
        label = stats_tree.find("**/Label[*].text=='Static Query'")
        self.assertIsNotNone(label)
        await label.right_click()
        self.check_menu_visibility("Context menu###ClashQueryStatsWindow", 1)

        # test filtering
        await search_field.input("x")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("filtered"))

        # refresh
        await refresh_button.click()
        await self.wait_for_data_loaded()
        self.assertTrue(await self.run_visual_test("after_refresh"))


