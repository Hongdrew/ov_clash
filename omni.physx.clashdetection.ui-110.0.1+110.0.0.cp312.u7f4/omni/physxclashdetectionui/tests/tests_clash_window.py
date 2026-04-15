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
import omni.usd
import omni.kit.ui_test as ui_test
import omni.kit.actions.core
from omni.usd.commands.usd_commands import DeletePrimsCommand
from .clash_detect_ui_test_case import ClashDetectUiTestCase
from ..settings import ExtensionSettings
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_query import ClashQuery


class TestsClashWindow(ClashDetectUiTestCase):
    def __init__(self, tests=()):
        super().__init__(tests)
        self._capture_wnd_name = self.CLASH_WND_NAME
        self._capture_img_name = "clash_wnd"
        self._capture_img_width = 1900
        self._capture_img_height = 360

    async def create_dyn_clash_query(self):
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        await omni.usd.get_context(ExtensionSettings.usd_context_name).open_stage_async(stage_path_name)
        stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        print("Creating new dynamic query...")
        my_query = ClashQuery(
            query_name="Dynamic Query",
            object_a_path="/Root/STATION_TIME_SAMPLED",
            object_b_path="/Root/Xform_Primitives",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: True,
                SettingId.SETTING_TOLERANCE.name: 3.0,
                SettingId.SETTING_SINGLE_THREADED.name: True,
            },
            comment="UI test query"
        )
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

    async def create_dyn_clash_query2(self, purge_permanent_static_overlaps: bool = False):
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        await omni.usd.get_context(ExtensionSettings.usd_context_name).open_stage_async(stage_path_name)
        stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        print("Creating new dynamic query...")
        my_query = ClashQuery(
            query_name="Dynamic Query",
            object_a_path="/Root/Utils.collection:StationCollection /Root/Xform_Primitives/Plane",
            object_b_path="/Root/Xform_Primitives /Root/STATION_TIME_SAMPLED/STATION/SKID/lnk/Mesh2",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: True,
                SettingId.SETTING_TOLERANCE.name: 3.0,
                SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS.name: purge_permanent_static_overlaps,
                SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name: True,
                SettingId.SETTING_DEPTH_EPSILON.name: 1.1,
                SettingId.SETTING_NEW_TASK_MANAGER.name: True,
                SettingId.SETTING_NB_TASKS.name: 128,
            },
            comment="UI test query"
        )
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

    async def create_dup_clash_query(self):
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        await omni.usd.get_context(ExtensionSettings.usd_context_name).open_stage_async(stage_path_name)

        print("Creating new static query with detection of duplicates...")
        omni.timeline.get_timeline_interface().set_current_time(1.0)  # detect in this timecode
        my_query = ClashQuery(
            query_name="Detect Dups Query",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: False,
                SettingId.SETTING_DUP_MESHES.name: True,
                SettingId.SETTING_NEW_TASK_MANAGER.name: True,
                SettingId.SETTING_NB_TASKS.name: 128,
            },
            comment="UI test query"
        )
        new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

    def get_widgets(self):
        # Get UI components and check their initial state
        # Note: Query Management button properly tested in Query Management wnd tests
        show_clash_viewport_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Show Clash Viewport'")
        self.assertIsNotNone(show_clash_viewport_button)
        self.assertTrue(show_clash_viewport_button.widget.enabled)
        clash_query_combobox = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'")
        self.assertIsNotNone(clash_query_combobox)
        self.assertTrue(clash_query_combobox.widget.enabled)
        self.assertEqual(len(clash_query_combobox.widget.model.items), 0)
        self.assertEqual(clash_query_combobox.widget.model._current_index.as_int, -1)
        run_clash_detection_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Run Clash Detection'")
        self.assertIsNotNone(run_clash_detection_button)
        self.assertFalse(run_clash_detection_button.widget.enabled)
        delete_selected_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Delete Selected'")
        self.assertIsNotNone(delete_selected_button)
        self.assertFalse(delete_selected_button.widget.enabled)
        export_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Export...'")
        self.assertIsNotNone(export_button)
        self.assertFalse(export_button.widget.enabled)
        refresh_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].name=='refresh'")
        self.assertIsNotNone(refresh_button)
        self.assertTrue(refresh_button.widget.enabled)
        progress_bar = ui_test.find(f"{self.PROGRESS_WND_NAME}//Frame/**/ProgressBar[*].name=='progress_bar'")
        self.assertIsNotNone(progress_bar)
        self.assertFalse(progress_bar.widget.visible)
        timeline_slider = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/FloatSlider[*].name=='timeline_slider'")
        self.assertIsNotNone(timeline_slider)
        self.assertFalse(timeline_slider.widget.visible)
        search_field = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/StringField[*].name=='search'")
        self.assertIsNotNone(search_field)
        self.assertTrue(search_field.widget.enabled)
        options_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].name=='options'")
        self.assertIsNotNone(options_button)
        self.assertTrue(options_button.widget.enabled)
        clash_results_tree = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/TreeView[*].name=='clash_results'")
        self.assertIsNotNone(clash_results_tree)
        self.assertTrue(clash_results_tree.widget.enabled)
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 0)
        self.assertEqual(len(clash_results_tree.widget.selection), 0)
        return (
            clash_query_combobox,
            run_clash_detection_button,
            delete_selected_button,
            export_button,
            refresh_button,
            progress_bar,
            timeline_slider,
            search_field,
            options_button,
            clash_results_tree,
            show_clash_viewport_button
        )

    async def run_clash_detection(self, run_clash_detection_button):
        await run_clash_detection_button.click()  # run clash detection with the selected query
        await self.wait(100)
        while not run_clash_detection_button.widget.enabled:
            await self.wait(5)

    async def test_clash_wnd_visual(self):
        # capture empty window
        self.assertTrue(await self.run_visual_test("empty"))

        # capture empty window with new query in the combo box
        (
            clash_query_combobox,
            run_clash_detection_button,
            delete_selected_button,
            export_button,
            refresh_button,
            progress_bar,
            timeline_slider,
            search_field,
            options_button,
            clash_results_tree,
            show_clash_viewport_button
        ) = self.get_widgets()

        # test duplicates query
        await self.create_dup_clash_query()
        self._settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        clash_query_combobox.widget.model.select_item_index(0)
        self.assertTrue(export_button.widget.enabled)  # export button should be enabled now
        # capture filled window with clash detection results
        await self.run_clash_detection(run_clash_detection_button)  # run clash detection with the selected query
        self.assertTrue(await self.run_visual_test("dup_query_results"))

        # test dynamic query features
        await self.create_dyn_clash_query2()

        self._settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        clash_query_combobox.widget.model.select_item_index(0)
        self.assertTrue(await self.run_visual_test("with_query"))

        # capture filled window with clash detection results
        await self.run_clash_detection(run_clash_detection_button)  # run clash detection with the selected query
        self.assertTrue(await self.run_visual_test("with_query_results"))

        # check with advanced filter active
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "set_custom_filter_expression", "[Triangles] > 100"
        )
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_advanced_filter"))
        # remove advanced filter
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "set_custom_filter_expression", ""
        )
        await self.wait_render()

        # capture window with timeline slider active
        treeview_item = clash_results_tree.find("**/Label[*].text=='6400'")  # find row number 1
        self.assertIsNotNone(treeview_item)
        await treeview_item.double_click()
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_timeline_slider"))

        # filter results to show only results with plane and compute penetration depths and max local depth for all
        await search_field.input("`plane`")
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        await self.wait_render()
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "select_all"
        )
        await self.wait_render()
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "run_full_penetration_depth_computation_on_selection"
        )
        await self.wait_render()
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "run_max_local_depth_computation_on_selection"
        )
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_plane_depths"))
        # remove search filter and selection
        search_field.widget.model.set_value('')
        search_field.widget.model._value_changed()
        await self.wait_render()
        omni.kit.actions.core.execute_action(
            "omni.physxclashdetectionui.clash_detect_window", "cancel_clash_detection_clear_selection"
        )
        await self.wait_render()

        # capture clash-no-longer-existing indicator
        deletePrimsCmd = DeletePrimsCommand(paths=["/Root/Xform_Primitives/Cube"])
        deletePrimsCmd.do()
        await self.wait_render()
        await self.run_clash_detection(run_clash_detection_button)  # run clash detection with the selected query
        self.assertTrue(await self.run_visual_test("with_clash_removed_indicator"))
        deletePrimsCmd.undo()
        await self.wait_render()

    async def test_clash_wnd_features(self):
        # undock the clash window and set its proper size
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        await self.wait_render()
        await clash_window.undock()
        clash_window.window.width = self._capture_img_width
        clash_window.window.height = self._capture_img_height
        clash_window.window.position_x = 0
        clash_window.window.position_y = 0
        clash_window.window.visible = True
        await clash_window.focus()
        await self.wait_render()

        # get window widgets
        (
            clash_query_combobox,
            run_clash_detection_button,
            delete_selected_button,
            export_button,
            refresh_button,
            progress_bar,
            timeline_slider,
            search_field,
            options_button,
            clash_results_tree,
            show_clash_viewport_button
        ) = self.get_widgets()

        # check settings menu
        await options_button.click()

        # create new clash query and refresh UI
        await self.create_dyn_clash_query()
        self._settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh

        # check the workflow - run clash detection
        self.assertEqual(len(clash_query_combobox.widget.model.items), 1)
        self.assertEqual(clash_query_combobox.widget.model._current_index.as_int, -1)
        clash_query_combobox.widget.model.select_item_index(0)
        self.assertEqual(clash_query_combobox.widget.model._current_index.as_int, 0)

        # check export menu
        await export_button.click()
        self.check_menu_visibility("Export menu###Clash", 9)

        self.assertTrue(run_clash_detection_button.widget.enabled)  # run clash detection button should now be enabled
        self.assertFalse(progress_bar.widget.visible)
        expected_num_clashes = 8
        await self.run_clash_detection(run_clash_detection_button)  # run clash detection with the selected query
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), expected_num_clashes)
        self.assertEqual(len(clash_results_tree.widget.selection), 0)

        # check sorting. assumption - sorted by max overlapping triangles
        # sort by number of records
        treeview_header_item = clash_results_tree.find("**/Label[*].text=='Records'")
        self.assertIsNotNone(treeview_header_item)
        await treeview_header_item.click()
        await self.wait_render()
        # set sorting back to max overlapping triangles ascending
        treeview_header_item = clash_results_tree.find("**/Label[*].text=='Triangles'")
        self.assertIsNotNone(treeview_header_item)
        await treeview_header_item.click()
        await self.wait_render()
        await treeview_header_item.click()
        await self.wait_render()

        # check search filter
        await search_field.input("nv_mesh1")
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 3)
        # remove search filter
        search_field.widget.model.set_value('')
        search_field.widget.model._value_changed()
        await self.wait_render()
        await search_field.input("nv_mesh12")
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 1)
        self.assertEqual(clash_results_tree.widget.model.filtered_children[0].row_num, 4)
        # remove search filter
        search_field.widget.model.set_value('')
        search_field.widget.model._value_changed()
        await self.wait_render()
        await search_field.input("`nv_mesh1`")
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 1)
        self.assertEqual(clash_results_tree.widget.model.filtered_children[0].row_num, 1)

        # check selection
        clash_results_tree.widget.selection = clash_results_tree.widget.model.filtered_children  # select all
        await self.wait_render()
        # delete selected button should now be enabled
        self.assertTrue(delete_selected_button.widget.enabled)

        # select first row
        first_row_num_str = clash_results_tree.widget.model.filtered_children[0].row_models[0].as_string
        treeview_item = clash_results_tree.find(f"**/Label[*].text=='{first_row_num_str}'")
        self.assertIsNotNone(treeview_item)
        # check context menu
        await treeview_item.right_click()
        await self.wait_render()
        self.check_menu_visibility("Context menu###Clash", 23)
        # double click on the treeview item to open the timeline slider
        await treeview_item.double_click()
        await self.wait_render()
        # should show the timeline slider
        self.assertTrue(timeline_slider.widget.visible)
        # check delete
        await delete_selected_button.click()
        await self.wait_render()
        # remove search filter
        search_field.widget.model.set_value('')
        search_field.widget.model._value_changed()
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        await self.wait_render()
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 7)
        # clear selection
        clash_results_tree.widget.selection = []
        self.assertFalse(delete_selected_button.widget.enabled)
        self.assertFalse(timeline_slider.widget.visible)

        # add filter and make a selection then test refresh button which should remove filter, refill and deselect everything
        await search_field.input(":05")
        await asyncio.sleep(ExtensionSettings.clash_results_typing_search_delay)
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 5)
        clash_results_tree.widget.selection = clash_results_tree.widget.model.filtered_children  # select all
        await self.wait_render()
        await refresh_button.click()
        await self.wait_render()
        self.assertEqual(len(clash_results_tree.widget.model.filtered_children), 7)
        self.assertEqual(len(clash_results_tree.widget.selection), 0)
