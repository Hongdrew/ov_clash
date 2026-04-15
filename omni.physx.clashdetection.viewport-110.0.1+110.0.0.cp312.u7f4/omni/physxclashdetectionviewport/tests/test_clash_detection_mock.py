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
import carb.settings
import omni.kit
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.timeline
import omni.ui as ui
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectionui.settings import ExtensionSettings


class TestClashDetectionMock:
    async def wait(self, frames=1):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()  # type: ignore

    def find_controls(self):
        self.CLASH_WND_NAME = "Clash Detection"
        clash_window = ui_test.find(self.CLASH_WND_NAME)
        assert clash_window is not None
        clash_window.widget.position_x = 0 # type: ignore
        clash_window.widget.position_y = 0 # type: ignore

        self._run_clash_detection = ui_test.find(
            f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Run Clash Detection'"
        )
        assert self._run_clash_detection is not None
        self._clash_results_tree = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/TreeView[*].name=='clash_results'")
        assert self._clash_results_tree is not None
        self._clash_query_combobox = ui_test.find(
            f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'"
        )
        assert self._clash_query_combobox is not None
        assert isinstance(self._clash_results_tree.widget, ui.TreeView)
        self._results_widget = self._clash_results_tree.widget
        self._timeline_slider = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/FloatSlider[*].name=='timeline_slider'")
        assert self._timeline_slider is not None

    def clear_controls(self):
        if hasattr(self, "_results_widget"):
            del self._results_widget
        if hasattr(self, "_run_clash_detection"):
            del self._run_clash_detection
        if hasattr(self, "_clash_results_tree"):
            del self._clash_results_tree
        if hasattr(self, "_clash_query_combobox"):
            del self._clash_query_combobox
        if hasattr(self, "_timeline_slider"):
            del self._timeline_slider

    async def create_new_query(self, name: str, duplicate: bool, dynamic: bool, soft: bool):

        my_query = ClashQuery(
            query_name=name,
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: dynamic,
                SettingId.SETTING_DYNAMIC_START_TIME.name: 0.0,
                SettingId.SETTING_DYNAMIC_END_TIME.name: 2.0,
                SettingId.SETTING_TOLERANCE.name: 20.0 if soft else 0.0,
                SettingId.SETTING_DUP_MESHES.name: duplicate,
            },
            comment="UI test query",
        )
        if ExtensionSettings.clash_data:
            new_id = ExtensionSettings.clash_data.insert_query(my_query, True, True)
            return new_id
        else:
            raise Exception("Missing ExtensionSettings.clash_data")

    async def select_clash_detection_query(self, index: int):
        settings = carb.settings.get_settings()
        settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        assert isinstance(self._clash_query_combobox.widget, ui.ComboBox)
        model = self._clash_query_combobox.widget.model  # ClashInfoDropdownModel
        model.select_item_index(index)  # type: ignore

    async def run_clash_detection(self):
        print(f"Running clash detection...")
        await self._run_clash_detection.click()
        await self.wait(10)
        while not self._run_clash_detection.widget.enabled:
            await self.wait(1)
        print(f"Total clashes detected: {len(self._results_widget.model.filtered_children)}.")

    async def unselect_clash_result(self):
        self._results_widget.selection = []

    async def set_timeline(self, time):
        await self.wait(1)
        assert ExtensionSettings.clash_selection
        assert ExtensionSettings.clash_data
        omni.timeline.get_timeline_interface().set_current_time(time)
        await self.wait(1)
        if len(self._results_widget.selection) > 0:
            ci = self._results_widget.selection[0].clash_info  # type: ignore
            ci.clash_frame_info_items = ExtensionSettings.clash_data.fetch_clash_frame_info_by_clash_info_id(
                ci.identifier
            )
            ExtensionSettings.clash_selection.update_selection(time, [ci])
        else:
            ExtensionSettings.clash_selection.update_selection(time, [])

    async def select_clash_result(self, index: int, time: float):
        try:
            self._results_widget.selection = [self._results_widget.model.filtered_children[index]]  # type: ignore
            await self.set_timeline(time)
        except Exception as e:
            carb.log_error(f"select_clash_result({index}) exception: {e}")
