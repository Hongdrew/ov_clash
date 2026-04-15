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
import asyncio
import omni.kit.ui_test as ui_test
from .clash_detect_ui_test_case import ClashDetectUiTestCase
from ..settings import ExtensionSettings
from ..clash_detect_settings import ClashDetectionSettings
from .utils import compare_text_files
from omni.physxclashdetectioncore.utils import get_unique_temp_file_path_name


class TestsQueryWindow(ClashDetectUiTestCase):
    CLASH_QUERY_MANAGEMENT_WND_NAME = "Clash Query Management"

    def __init__(self, tests=()):
        super().__init__(tests)
        self._capture_wnd_name = self.CLASH_QUERY_MANAGEMENT_WND_NAME
        self._capture_img_name = "clash_query_wnd"
        self._capture_img_width = 1100
        self._capture_img_height = 1235
        self._clash_query_window = None

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._autosave_bak = self._settings.get_as_bool(ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE)
        self._settings.set_bool(ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE, True)
        # open clash query window
        await self.open_query_wnd()
        if self._clash_query_window and self._clash_query_window.window:
            await self._clash_query_window.focus()
            self._clash_query_window.window.position_x = 50
            self._clash_query_window.window.position_y = 50
            self._clash_query_window.window.width = self._capture_img_width
            self._clash_query_window.window.height = self._capture_img_height
            await self.wait_render()
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await self.wait_render()

    async def tearDown(self):
        await super().tearDown()
        self._settings.set_bool(ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE, self._autosave_bak)
        if self._clash_query_window:
            self._clash_query_window.visible = False
            self._clash_query_window.window.destroy()
            self._clash_query_window = None

    async def open_query_wnd(self):
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        clash_window.window.width = 1100
        clash_window.window.visible = True
        await clash_window.focus()
        await self.wait_render()
        query_management_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Query Management'")
        self.assertIsNotNone(query_management_button)
        await query_management_button.click()
        await self.wait_render()
        self._clash_query_window = ui_test.find(self.CLASH_QUERY_MANAGEMENT_WND_NAME)
        self.assertIsNotNone(self._clash_query_window)

    async def test_query_wnd_visual(self):
        await self.wait_render()  # wait for any possible tooltips to be hidden

        self.assertTrue(await self.run_visual_test("empty"))

        # test window with a query opened
        create_new_query_button = ui_test.find(f"{self._capture_wnd_name}//Frame/**/Button[*].text=='Create New Query'")
        self.assertIsNotNone(create_new_query_button)
        await create_new_query_button.click()
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_query"))

        # test dynamic clash detection setting
        settings_dynamic_cd = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[0]/CheckBox[0]")
        self.assertIsNotNone(settings_dynamic_cd)
        await self.wait_render()
        settings_dynamic_cd.widget.model.set_value(True)
        settings_dynamic_start_time = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[1]/FloatDrag[0]")
        self.assertIsNotNone(settings_dynamic_start_time)
        await settings_dynamic_start_time.input("0.5")
        settings_dynamic_end_time = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[2]/FloatDrag[0]")
        self.assertIsNotNone(settings_dynamic_end_time)
        await settings_dynamic_end_time.input("1.75")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_dyn_query"))

        # test editing in frames instead of time
        frames_setting_bak = self._settings.get_as_bool(ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES)
        self._settings.set_bool(ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES, True)
        settings_frame_debug = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[4]")
        self.assertIsNotNone(settings_frame_debug)
        settings_frame_debug.widget.collapsed = False
        self.assertTrue(await self.run_visual_test("with_dyn_query_frames"))
        self._settings.set_bool(ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES, frames_setting_bak)
        settings_frame_debug = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[4]")
        self.assertIsNotNone(settings_frame_debug)
        settings_frame_debug.widget.collapsed = False

        # test find duplicates
        settings_dynamic_cd.widget.model.set_value(False)
        settings_dup_meshes = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[6]/CheckBox[0]")
        self.assertIsNotNone(settings_dup_meshes)
        settings_dup_meshes.widget.model.set_value(True)
        await self.wait_render()
        self.assertEqual(settings_dup_meshes.widget.checked, True)
        self.assertEqual(settings_dup_meshes.widget.enabled, True)
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("with_dup_query"))

        # test filtering
        search_field = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[0]/ZStack[0]/HStack[0]/ZStack[0]/HStack[0]/VStack[0]/HStack[0]/StringField[0]")
        self.assertIsNotNone(search_field)
        await search_field.input("query")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("filtered"))
        await search_field.input("x")
        await self.wait_render()
        self.assertTrue(await self.run_visual_test("filtered_out"))

    def _modify_all_settings(self, clash_detection_settings: ClashDetectionSettings):
        # set all values to non-default values
        for settings_group in reversed(clash_detection_settings.all_settings):
            if settings_group:
                for setting in settings_group.values():
                    # Try to detect min/max/default from SettingDef
                    max_value = getattr(setting, "_max_value", None)
                    min_value = getattr(setting, "_min_value", None)
                    default_value = getattr(setting, "_default_value", None)

                    # Special case for ComboBoxSetting: set to first non-default option if possible
                    from omni.physxclashdetectionui.clash_detect_settings import ComboBoxSetting
                    if isinstance(setting, ComboBoxSetting):
                        combo_model = getattr(setting, "_combo_model", None)
                        default_value = getattr(setting, "_default_value", None)
                        if combo_model and hasattr(combo_model, "_combo_items"):
                            values = [item.model.value for item in combo_model._combo_items]
                            # Select the first non-default value if possible
                            try:
                                non_default = next(v for v in values if v != default_value)
                                setting.value = non_default
                            except StopIteration:
                                # fallback to next logic if all values are default
                                pass
                        else:
                            # fallback to next logic for malformed ComboBox
                            pass

                    elif max_value is not None:
                        # If max_value is same as default, use min instead
                        if default_value == max_value:
                            if min_value is not None:
                                setting.value = min_value
                            else:
                                setting.value = None  # fallback if min_value does not exist
                        else:
                            setting.value = max_value
                    elif min_value is not None:
                        # If only min_value exists (not usual), and it's not the default, use it
                        if default_value == min_value:
                            setting.value = None  # fallback
                        else:
                            setting.value = min_value
                    else:
                        # No min/max: "use not value as new value"
                        current_val = setting.value
                        try:
                            # Attempt to use logical not
                            setting.value = not current_val
                        except Exception:
                            # Fallback for non-bool/non-invertible
                            pass

    async def test_reset_settings_to_default(self):
        clash_detection_settings = ClashDetectionSettings()
        self._modify_all_settings(clash_detection_settings)
        clash_detection_settings.reset_settings_to_default()
        clash_detection_settings_default = ClashDetectionSettings()
        # Compare all settings between clash_detection_settings and clash_detection_settings_default
        # They both should have all_settings property containing tuples of OrderedDicts of SettingDefs
        for settings_group, default_group in zip(clash_detection_settings.all_settings, clash_detection_settings_default.all_settings):
            self.assertEqual(set(settings_group.keys()), set(default_group.keys()))
            for key in settings_group.keys():
                setting = settings_group[key]
                default_setting = default_group[key]
                # Compare each SettingDef's .value to default_setting.value
                self.assertEqual(
                    setting.value,
                    default_setting.value,
                    f"Setting '{setting.label}' does not match default value: {setting.value} != {default_setting.value}"
                )

    async def test_query_import_export(self):
        self.assertIsNotNone(self._clash_query_window)
        self.assertIsNotNone(self._clash_query_window.window)
        self.assertIsNotNone(ExtensionSettings.clash_data)
        # make sure there are no queries in the DB
        queries = ExtensionSettings.clash_data.fetch_all_queries()
        for query_id in queries.keys():
            ExtensionSettings.clash_data.remove_query_by_id(query_id, False)
        ExtensionSettings.clash_data.commit()
        fn = "exported_query_definitions.json"
        # import queries into the query mngmt window (they will get selected at when done)
        source_path_name = self._test_data_dir + fn
        result = self._clash_query_window.window.import_queries_from_json_file(source_path_name)
        self.assertTrue(result)
        self.assertTrue(len(self._clash_query_window.window._tree_view.selection) > 0)
        # export selected queries to a JSON file
        target_path_name = get_unique_temp_file_path_name("_" + fn)
        result = self._clash_query_window.window.save_queries_to_json_file(
            target_path_name,
            self._clash_query_window.window._tree_view.selection
        )
        self.assertTrue(result)
        # compare the exported file with the original
        differences = compare_text_files(source_path_name, target_path_name, True)
        self.assertEqual(len(differences), 0)

    async def test_query_mgmt_workflow(self):
        async def test_dynamic_settings():
            settings_dynamic_cd = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[0]/CheckBox[0]")
            self.assertIsNotNone(settings_dynamic_cd)
            settings_dynamic_start_time = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[1]/FloatDrag[0]")
            self.assertIsNotNone(settings_dynamic_start_time)
            settings_dynamic_end_time = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[2]/FloatDrag[0]")
            self.assertIsNotNone(settings_dynamic_end_time)
            settings_dynamic_purge = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[3]/CheckBox[0]")
            self.assertIsNotNone(settings_dynamic_purge)
            settings_tolerance = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[4]/FloatDrag[0]")
            self.assertIsNotNone(settings_tolerance)
            settings_static_time = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[5]/FloatDrag[0]")
            self.assertIsNotNone(settings_static_time)
            settings_dup_meshes = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[6]/CheckBox[0]")
            self.assertIsNotNone(settings_dup_meshes)

            async def check_dynamic(enabled: bool):
                settings_dynamic_cd.widget.model.set_value(enabled)
                await self.wait_render()
                self.assertEqual(settings_static_time.widget.enabled, not settings_dynamic_cd.widget.checked)
                self.assertEqual(settings_dup_meshes.widget.enabled, not settings_dynamic_cd.widget.checked)
                self.assertEqual(settings_dynamic_cd.widget.checked, enabled)
                self.assertEqual(settings_dynamic_start_time.widget.enabled, enabled)
                self.assertEqual(settings_dynamic_end_time.widget.enabled, enabled)
                self.assertEqual(settings_dynamic_purge.widget.enabled, enabled)
                self.assertEqual(settings_tolerance.widget.enabled, not settings_dup_meshes.widget.checked)

            await check_dynamic(True)
            await check_dynamic(False)

        async def test_threading_settings():
            settings_new_task_mgr = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[3]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[0]/CheckBox[0]")
            self.assertIsNotNone(settings_new_task_mgr)
            settings_single_threaded = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[3]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[1]/CheckBox[0]")
            self.assertIsNotNone(settings_single_threaded)
            settings_nb_of_tasks = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[3]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[2]/IntDrag[0]")
            self.assertIsNotNone(settings_nb_of_tasks)

            async def check_new_task_mgr(enabled: bool):
                settings_new_task_mgr.widget.model.set_value(enabled)
                await self.wait_render()
                self.assertEqual(settings_new_task_mgr.widget.checked, enabled)
                self.assertEqual(settings_nb_of_tasks.widget.enabled, not enabled)

            await check_new_task_mgr(True)
            await check_new_task_mgr(False)

            async def check_single_threaded(enabled: bool):
                settings_single_threaded.widget.model.set_value(enabled)
                await self.wait_render()
                self.assertEqual(settings_single_threaded.widget.checked, enabled)
                self.assertEqual(settings_new_task_mgr.widget.enabled, not enabled)
                self.assertEqual(settings_nb_of_tasks.widget.enabled, not enabled)

            await check_single_threaded(True)
            await check_single_threaded(False)

        async def test_depth_settings():
            settings_comp_depth = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[0]/CheckBox[0]")
            self.assertIsNotNone(settings_comp_depth)
            settings_depth_epsilon = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[1]/FloatDrag[0]")
            self.assertIsNotNone(settings_depth_epsilon)
            settings_contact_cutoff = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[2]/FloatDrag[0]")
            self.assertIsNotNone(settings_contact_cutoff)
            settings_discard_contacts = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[3]/CheckBox[0]")
            self.assertIsNotNone(settings_discard_contacts)
            settings_max_local_depth_mode = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[4]/ComboBox[0]")
            self.assertIsNotNone(settings_max_local_depth_mode)
            settings_any_hit = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[1]/Frame[0]/ZStack[0]/VStack[0]/Frame[0]/HStack[0]/VStack[0]/HStack[5]/CheckBox[0]")
            self.assertIsNotNone(settings_any_hit)

            async def check_depth_setting(enabled: bool):
                settings_comp_depth.widget.model.set_value(enabled)
                await self.wait_render()
                self.assertEqual(settings_comp_depth.widget.checked, enabled)
                self.assertEqual(settings_depth_epsilon.widget.enabled, enabled)
                self.assertEqual(settings_contact_cutoff.widget.enabled, enabled)
                self.assertEqual(settings_discard_contacts.widget.enabled, enabled)
                self.assertEqual(settings_max_local_depth_mode.widget.enabled, enabled)
                self.assertEqual(settings_any_hit.widget.enabled, not enabled)

            await check_depth_setting(True)
            await check_depth_setting(False)

        async def check_settings_states(settings_enabled: bool):
            settings_frame = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]")
            self.assertIsNotNone(settings_frame)
            settings_frame_stack = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]")
            if not settings_enabled:
                print("The warning 'Can't find any widgets at path' is expected here, safe to ignore...")
                self.assertIsNone(settings_frame_stack)
                return
            self.assertIsNotNone(settings_frame_stack)

            settings_frame_scope = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/CollapsableFrame[0]")
            self.assertIsNotNone(settings_frame_scope)
            settings_frame_main = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[0]")
            self.assertIsNotNone(settings_frame_main)
            settings_frame_advanced = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[1]")
            self.assertIsNotNone(settings_frame_advanced)
            settings_frame_depth = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[2]")
            self.assertIsNotNone(settings_frame_depth)
            settings_frame_multithread = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[3]")
            self.assertIsNotNone(settings_frame_multithread)
            settings_frame_debug = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/VStack[0]/HStack[1]/ScrollingFrame[0]/VStack[0]/VStack[0]/CollapsableFrame[4]")
            self.assertIsNotNone(settings_frame_debug)
            settings_frame_debug.widget.collapsed = False

            await test_dynamic_settings()
            await test_threading_settings()
            await test_depth_settings()

        clash_data = ExtensionSettings.clash_data

        create_new_query_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Create New Query'")
        self.assertIsNotNone(create_new_query_button)
        duplicate_query_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Duplicate'")
        self.assertIsNotNone(duplicate_query_button)
        delete_query_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Delete...'")
        self.assertIsNotNone(delete_query_button)
        export_query_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Export Queries...'")
        self.assertIsNotNone(export_query_button)
        import_query_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Import Queries...'")
        self.assertIsNotNone(import_query_button)
        save_props_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].text=='Save Properties'")
        self.assertIsNotNone(save_props_button)
        options_button = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/Button[*].name=='options'")
        self.assertIsNotNone(options_button)
        self.assertTrue(options_button.widget.enabled)
        clash_queries_tree = ui_test.find(f"{self.CLASH_QUERY_MANAGEMENT_WND_NAME}//Frame/**/TreeView[*].name=='clash_queries'")
        self.assertIsNotNone(clash_queries_tree)

        def check_buttons(
            create_new_query_button_enabled,
            duplicate_query_button_enabled,
            delete_query_button_enabled,
            export_query_button_enabled,
            import_query_button_enabled,
            save_props_button_enabled
        ):
            self.assertEqual(create_new_query_button.widget.enabled, create_new_query_button_enabled)
            self.assertEqual(duplicate_query_button.widget.enabled, duplicate_query_button_enabled)
            self.assertEqual(delete_query_button.widget.enabled, delete_query_button_enabled)
            self.assertEqual(export_query_button.widget.enabled, export_query_button_enabled)
            self.assertEqual(import_query_button.widget.enabled, import_query_button_enabled)
            self.assertEqual(save_props_button.widget.enabled, save_props_button_enabled)

        check_buttons(True, False, False, False, True, False)
        self.assertEqual(len(self._clash_query_window.window._tree_view.selection), 0)
        self.assertEqual(len(clash_data.fetch_all_queries()), 0)

        await check_settings_states(False)
        # check settings menu
        await options_button.click()
        self.check_menu_visibility("Settings menu###ClashQuery", 3)

        # create a new query
        await create_new_query_button.click()
        await self.wait_render()

        self.assertEqual(len(self._clash_query_window.window._tree_view.selection), 1)
        queries = clash_data.fetch_all_queries()
        self.assertEqual(len(queries), 1)

        check_buttons(True, True, True, True, True, True)
        await check_settings_states(True)

        # check selection
        clash_queries_tree.widget.selection = clash_queries_tree.widget.model.filtered_children  # select all
        await self.wait_render()

        # check save
        first_query = next(iter(queries.values()))
        timestamp = first_query.last_modified_timestamp
        await asyncio.sleep(0.1)
        await save_props_button.click()
        await self.wait_render()
        queries = clash_data.fetch_all_queries()
        self.assertEqual(len(queries), 1)
        first_query = next(iter(queries.values()))
        self.assertNotEqual(timestamp, first_query.last_modified_timestamp)
        timestamp = first_query.last_modified_timestamp

        # check duplication
        await duplicate_query_button.click()
        await self.wait_render()

        # we have a new selection but # of selected items is still the same
        self.assertEqual(len(self._clash_query_window.window._tree_view.selection), 1)

        # check if save on selection change triggered
        queries = clash_data.fetch_all_queries()
        self.assertEqual(len(queries), 2)
        it = iter(queries.values())
        first_query = next(it)
        self.assertNotEqual(timestamp, first_query.last_modified_timestamp)
        second_query = next(it)
        self.assertEqual(self._clash_query_window.window._tree_view.selection[0].clash_query.last_modified_timestamp, second_query.last_modified_timestamp)

        # check select all
        self._clash_query_window.window._tree_view.clear_selection()
        for i in self._clash_query_window.window._model._filtered_children:
            self._clash_query_window.window._tree_view.extend_selection(i)
        await self.wait_render()

        check_buttons(True, True, True, True, True, False)

        # check duplication of multiple items
        await duplicate_query_button.click()
        await self.wait_render()

        self.assertEqual(len(self._clash_query_window.window._tree_view.selection), 2)
        self.assertEqual(len(clash_data.fetch_all_queries()), 4)

        # check context menu
        await clash_queries_tree.right_click()
        self.check_menu_visibility("Context menu###ClashQuery", 8)

        # check select all again
        self._clash_query_window.window._tree_view.clear_selection()
        for i in self._clash_query_window.window._model._filtered_children:
            self._clash_query_window.window._tree_view.extend_selection(i)
        await self.wait_render()

        # check delete
        await delete_query_button.click()
        await self.wait_render()

        self.assertEqual(len(self._clash_query_window.window._tree_view.selection), 0)
        self.assertEqual(len(clash_data.fetch_all_queries()), 0)
