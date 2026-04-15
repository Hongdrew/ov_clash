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


class TestsGroupsWindow(ClashDetectUiTestCase):
    CLASH_GROUPS_WND_NAME = "Clash Groups"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._capture_wnd_name = self.CLASH_GROUPS_WND_NAME
        self._capture_img_name = "clash_groups_wnd"
        self._capture_img_width = 1900
        self._capture_img_height = 1160
        self._clash_groups_window = None

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._show_empty_groups_bak = self._settings.get_as_bool(ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS)
        self._settings.set_bool(ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, False)
        # open the groups window
        await self.open_groups_wnd()
        if self._clash_groups_window and self._clash_groups_window.window:
            await self._clash_groups_window.focus()
            self._clash_groups_window.window.position_x = 0
            self._clash_groups_window.window.position_y = 0
            self._clash_groups_window.window.width = self._capture_img_width
            self._clash_groups_window.window.height = self._capture_img_height
            await self.wait_render()
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await self.wait_render()

    async def tearDown(self):
        await super().tearDown()
        self._settings.set_bool(ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, self._show_empty_groups_bak)
        if self._clash_groups_window:
            self._clash_groups_window.visible = False
            self._clash_groups_window.window.destroy()
            self._clash_groups_window = None

    async def create_dyn_clash_query(self):
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
            query_name="Dynamic Query",
            object_a_path="",
            object_b_path="",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: True,
                SettingId.SETTING_TOLERANCE.name: 3.0,
            },
            comment="UI test query"
        )
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

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
        await self.create_dyn_clash_query()
        self._settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        clash_query_combobox.widget.model.select_item_index(0)

        self.assertTrue(run_clash_detection_button.widget.enabled)
        await self.run_clash_detection(run_clash_detection_button)

    async def open_groups_wnd(self):
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        clash_window.window.width = 1900
        clash_window.window.visible = True
        await clash_window.focus()
        await self.wait_render()
        await self.create_and_run_clash_query()
        await self.wait_render()
        # set sorting
        clash_results_tree = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/TreeView[*].name=='clash_results'")
        self.assertIsNotNone(clash_results_tree)
        treeview_header_item = clash_results_tree.find("**/Label[*].text=='#'")
        self.assertIsNotNone(treeview_header_item)
        await treeview_header_item.click()
        await self.wait_render()

        groups_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Grouped View'")
        self.assertIsNotNone(groups_button)
        self.assertTrue(groups_button.widget.enabled)
        await groups_button.click()
        await self.wait_render()
        self._clash_groups_window = ui_test.find(self.CLASH_GROUPS_WND_NAME)
        self.assertIsNotNone(self._clash_groups_window)


    async def wait_for_data_loaded(self):
        # wait for the data to be loaded
        while self._clash_groups_window.window._grouping_task is not None:
            await asyncio.sleep(0.25)
            await self.wait(1)
        await self.wait_render()

    async def test_groups_wnd_visual(self):
        await self.wait_render()  # wait for any possible tooltips to be hidden

        await self.wait_for_data_loaded()

        # Get UI elements
        refresh_button = ui_test.find(f"{self.CLASH_GROUPS_WND_NAME}//Frame/**/Button[*].name=='refresh'")
        self.assertIsNotNone(refresh_button)
        search_field = ui_test.find(f"{self.CLASH_GROUPS_WND_NAME}//Frame/**/StringField[0]")
        self.assertIsNotNone(search_field)
        options_button = ui_test.find(f"{self.CLASH_GROUPS_WND_NAME}//Frame/**/Button[*].name=='options'")
        self.assertIsNotNone(options_button)
        self.assertTrue(options_button.widget.enabled)
        groups_tree = ui_test.find(f"{self.CLASH_GROUPS_WND_NAME}//Frame/**/TreeView[*].name=='groups'")
        self.assertIsNotNone(groups_tree)

        self.assertTrue(await self.run_visual_test("initial"))

        # check settings menu
        await options_button.click()
        self.check_menu_visibility("Settings menu###GroupsWindow", 2)

        # select all groups
        self._clash_groups_window.window.select_all_groups()
        await self.wait_render()

        # check context menu
        label = groups_tree.find("**/Label[*].text=='Root'")
        self.assertIsNotNone(label)
        await label.right_click()
        self.check_menu_visibility("Context menu###GroupsWindow", 5)

        # expand all children
        self._clash_groups_window.window.expand_all_children()
        await self.wait_render()

        self.assertTrue(await self.run_visual_test("expanded_no_empty_groups"))

        # collapse all children
        self._clash_groups_window.window.collapse_all_children()
        await self.wait_render()

        self._settings.set_bool(ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, True)
        await self.wait_for_data_loaded()

        # select all groups
        self._clash_groups_window.window.select_all_groups()
        await self.wait_render()

        # expand all children
        self._clash_groups_window.window.expand_all_children()
        await self.wait_render()

        self.assertTrue(await self.run_visual_test("expanded_with_empty_groups"))

        # test filtering
        await search_field.input("1")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("filtered_with_empty_groups"))

        # refresh
        await refresh_button.click()
        await self.wait_for_data_loaded()
        self.assertTrue(await self.run_visual_test("after_refresh"))
