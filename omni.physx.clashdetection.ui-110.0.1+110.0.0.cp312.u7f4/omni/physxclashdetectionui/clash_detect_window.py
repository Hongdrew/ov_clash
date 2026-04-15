# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import ValuesView, Sequence, List, Callable, Optional, Tuple, Any
import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import carb
import carb.input
import carb.settings
from pxr import Usd, UsdGeom, Sdf, Gf
import omni.usd
import omni.client
import omni.ui as ui
import omni.kit.app
import omni.kit.clipboard
import omni.timeline
from omni.kit.widget.prompt import Prompt
import omni.kit.actions.core
from omni.kit.hotkeys.core import get_hotkey_registry, HotkeyFilter
from .styles import Styles, format_int
from .clash_detect_viewmodel import ClashDetectTableModel, ClashDetectTableColumnEnum, ClashDetectTableRowItem
from .clash_detect_delegate import ClashDetectTableDelegate
from .table_delegates import TableColumnDef
from omni.physxclashdetectioncore.clash_info import ClashInfo, ClashFrameInfo
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_detect_export import export_to_html, export_to_json, ExportColumnDef
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.utils import OptimizedProgressUpdate, clamp_value
from omni.physxclashdetectioncore.usd_utils import get_prim_matrix
from .clash_bake_view import ClashBakeView
from .clash_detect_settings import ClashDetectionSettings
from .clash_query_window import ClashQueryWindow
from .clash_query_dropdown_viewmodel import ClashQueryDropdownModel, ClashQueryComboBoxItem
from .clash_query_viewmodel import ClashQueryTableModel
from .selection.clash_selection import QueryId
from .settings import ExtensionSettings
from .extension_settings import ExtensionSettingsWindow
from .usd_utils import omni_get_path_name_of_current_stage
from .utils import (
    get_current_user_name,
    pick_target_file,
    show_notification,
    whole_string_encapsulation_ctrl_chars,
    get_datetime_str,
    DeferredAction
)
from .filter_window import FilterWindow
from .groups_window import GroupsWindow


__all__ = []


class ClashDetectionWindow:
    """A class for managing the Clash Detection window.

    This class provides functionality to create, manage, and update the Clash Detection window. It handles user interactions, clash detection processing, and updates to the UI elements.
    """

    WINDOW_NAME = "Clash Detection"
    PROGRESS_WINDOW_NAME = "Clash Detection Progress"

    class CustomProgressValueModel(ui.AbstractValueModel):
        """A model representing a custom progress value.

        This class provides methods to set and retrieve a progress value in various formats such as integer, float, and string. It is used primarily to update progress bars in the UI.
        """

        def __init__(self):
            """Initializes the CustomProgressValueModel."""
            super().__init__()
            self._value = 0

        def set_value(self, value: float): # type: ignore
            """Sets the value of the model.

            Args:
                value (int): The new value to set.
            """
            try:
                value = value
            except ValueError:
                value = 0
            if value != self._value:
                self._value = value
                self._value_changed()  # Tell the widget that the model has changed

        def get_value_as_float(self):
            """Returns the value as a float.

            Returns:
                float: The value as a float divided by 100.0.
            """
            return float(self._value)

        def get_value_as_int(self):
            """Returns the value as an integer.

            Returns:
                int: The value as an integer.
            """
            return int(self._value * 100.0)

        def get_value_as_string(self):
            """Returns the value as a string.

            Returns:
                str: The value as a percentage string.
            """
            return f"{self.get_value_as_float() * 100.0:.2f}%"

    def __init__(self, clash_detect: ClashDetection, clash_bake_view: ClashBakeView):
        """Initializes the ClashDetectionWindow."""
        self._window = None
        self._tree_view = None
        self._model = None
        self._clash_detect = clash_detect
        self._clash_detect_settings = ClashDetectionSettings()
        self._lock = asyncio.Lock()
        self._async_pipeline_cookie = None
        self._clash_detect_task = None  # clash detection task
        self._cancel_processing = False
        self._cancel_processing_reason = ""
        self._current_query_total_num_of_clashes = 0
        self._query_window = None
        self._deferred_search_action = None
        self._groups_window = None

        # window UI components
        self._query_combo_box = None
        self._query_combo_model = None
        self._delegate = None
        self._carb_subs = []  # array of carb.Subscription
        self._search_model = None
        self._search_label = None
        self._clear_search_button = None
        self._filter_expression = ""
        self._filter_expression_in_use = False
        self._progress_bar = None
        self._progress_bar_model = None
        self._progress_window_label = None
        self._progress_window = None
        self._export_clash_clear_frames_model = ui.SimpleIntModel(5)
        self._export_clash_render_frames_model = ui.SimpleIntModel(100)
        self._progbar_export_screenshots = None
        self._export_screenshot_progress_bar_model = None
        self._progbar_create_markers = None
        self._create_markers_progress_bar_model = None
        self._num_of_items_label = None
        self._timeline_slider = None
        self._timeline_slider_model = None
        self._run_clash_detection_button = None
        self._delete_row_button = None
        self._btn_export = None
        self._btn_groups = None
        self._btn_refresh = None
        self._btn_filter = None
        self._warning_label = None
        self._settings_menu = None
        self._context_menu = None
        self._export_menu = None
        self._clash_bake_view = clash_bake_view
        self._export_only_filtered_items = True
        self._export_clash_screenshots = True
        self._inspecting_ci = None

        ExtensionSettings.clash_query = None
        self._anim_recorder = None
        self._simulation_mode = omni.timeline.get_timeline_interface().is_playing()
        self._settings_subs = omni.kit.app.SettingChangeSubscription(
            ExtensionSettings.SETTING_RELOAD_UI, self._reload_ui_setting_changed
        )

        # delete selected items action & hotkey
        action_ext_id = self.__class__.__module__
        action_name = "delete_selected"
        self._delete_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.delete_selected_with_prompt(),
            display_name="Delete Selected Clash Detection Results",
            tag="Clash Detection Results Window",
        )

        self._delete_hotkey = None
        if self._delete_action:
            self._delete_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "DEL",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(
                    windows=[ClashDetectionWindow.WINDOW_NAME]
                ),  # This hotkey only takes effect when mouse in this window
            )

        # clear selection action & hotkey
        action_name = "cancel_clash_detection_clear_selection"
        self._clear_selection_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self._cancel_clash_detection_clear_selection(),
            display_name="Cancel Clash Detection Process and Clear Selection in Clash Detection Results",
            tag="Clash Detection Results Window",
        )

        self._clear_selection_hotkey = None
        if self._clear_selection_action:
            self._clear_selection_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "ESCAPE",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(
                    windows=[ClashDetectionWindow.WINDOW_NAME]
                ),  # This hotkey only takes effect when mouse in this window
            )

        # select all action & hotkey
        action_name = "select_all"
        self._select_all_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.select_all_clashes(),
            display_name="Select All Clash Detection Results",
            tag="Clash Detection Results Window",
        )

        self._select_all_hotkey = None
        if self._select_all_action:
            self._select_all_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "Ctrl+A",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(
                    windows=[ClashDetectionWindow.WINDOW_NAME]
                ),  # This hotkey only takes effect when mouse in this window
            )

        # run max local depth computation for all frames for selected clash entries
        action_name = "run_max_local_depth_computation_on_selection"
        self._max_local_depth_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self._start_max_local_depth_task(True),
            display_name="Run max local depth computation for all frames for selected clash entries",
            tag="Clash Detection Results Window",
        )

        # run penetration depth computation for all frames in all 6 directions for selected clash entries
        action_name = "run_full_penetration_depth_computation_on_selection"
        self._penetration_depth_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self._start_penetration_depth_task(None, True),
            display_name="Run penetration depth computation for all frames in all 6 directions for selected clash entries",
            tag="Clash Detection Results Window",
        )

        # run penetration depth computation for all frames in all 6 directions for selected clash entries
        action_name = "set_custom_filter_expression"
        self._set_custom_filter_expression_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda filter_str: self.apply_filter(filter_str if filter_str else "", True),
            display_name="Set custom filter expression",
            tag="Clash Detection Results Window",
        )

        try:
            from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore

            ext_instance = get_markup_instance()
            ext_instance.set_open_callback(self._on_markup_callback)
        except:
            pass

    def destroy_window(self):
        """Destroys the Clash Detection window and its resources."""
        if self._delete_hotkey:
            get_hotkey_registry().deregister_hotkey(self._delete_hotkey)
            self._delete_hotkey = None
        if self._delete_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._delete_action)
            self._delete_action = None
        if self._clear_selection_hotkey:
            get_hotkey_registry().deregister_hotkey(self._clear_selection_hotkey)
            self._clear_selection_hotkey = None
        if self._clear_selection_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._clear_selection_action)
            self._clear_selection_action = None
        if self._select_all_hotkey:
            get_hotkey_registry().deregister_hotkey(self._select_all_hotkey)
            self._select_all_hotkey = None
        if self._select_all_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._select_all_action)
            self._select_all_action = None
        if self._penetration_depth_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._penetration_depth_action)
            self._penetration_depth_action = None
        if self._max_local_depth_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._max_local_depth_action)
            self._max_local_depth_action = None
        if self._set_custom_filter_expression_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._set_custom_filter_expression_action)
            self._set_custom_filter_expression_action = None
        if self._deferred_search_action:
            self._deferred_search_action.destroy()
            self._deferred_search_action = None

        if self._clash_bake_view:
            self._clash_bake_view.destroy()
            del self._clash_bake_view
        self._inspecting_ci = None
        self._query_combo_box = None
        self._warning_label = None
        self._btn_groups = None
        self._btn_export = None
        self._btn_filter = None
        self._btn_refresh = None
        self._delete_row_button = None
        self._run_clash_detection_button = None
        if self._settings_menu:
            self._settings_menu.hide()
            self._settings_menu.destroy()
            self._settings_menu = None
        self._export_menu = None
        self._context_menu = None
        self._create_markers_progress_bar_model = None
        self._progbar_create_markers = None
        self._export_screenshot_progress_bar_model = None
        self._progbar_export_screenshots = None
        self._progress_bar = None
        self._progress_bar_model = None
        self._progress_window_label = None
        if self._progress_window:
            self._progress_window.visible = False
            self._progress_window.destroy()
            self._progress_window = None
        self._num_of_items_label = None
        self._timeline_slider = None
        self._timeline_slider_model = None
        self._search_model = None
        self._search_label = None
        self._clear_search_button = None
        self._filter_expression = ""

        if self._tree_view:
            self._tree_view = None
        if self._window:
            self._window.undock()
            self._window.visible = False
            self._window.destroy()
            self._window = None

    def destroy(self):
        """Destroys the ClashDetectionWindow and cleans up resources."""
        try:
            from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore

            ext_instance = get_markup_instance()
            ext_instance.set_open_callback(None)
        except:
            pass
        self._clash_bake_view.disable_clash_bake()
        self.cancel_running_task()  # make sure we don't release while task is still running
        self._clash_detect_task = None
        self._cancel_processing = False
        self._cancel_processing_reason = ""
        self._async_pipeline_cookie = None
        self._lock = None
        if self._query_window:
            self._query_window.destroy()
            self._query_window = None
        if self._groups_window:
            self._groups_window.destroy()
            self._groups_window = None
        self.destroy_window()
        self.destroy_model()

        if self._anim_recorder:
            self._anim_recorder.destroy()
            self._anim_recorder = None
        self._clash_detect = None
        self._settings_subs = None
        self._carb_subs = []

    @property
    def window(self):
        """Gets the current window instance.

        Returns:
            ui.Window: The current window instance.
        """
        return self._window

    def create_model(self):
        """Creates the model for clash detection data."""
        if not self._model:
            self._model = ClashDetectTableModel()
        if not self._delegate:
            self._delegate = ClashDetectTableDelegate(model=self._model, on_item_click=self._tree_view_on_item_click)
        if not self._query_combo_model:
            self._query_combo_model = ClashQueryDropdownModel(
                self.create_clash_query_combo_items(), self.on_clash_query_selection_changed
            )

    def destroy_model(self):
        """Destroys the model and cleans up resources."""
        self.cancel_running_task()  # make sure we don't release while task is still running
        if self._query_combo_model:
            self._query_combo_model.destroy()
            self._query_combo_model = None
        if self._delegate:
            self._delegate.destroy()
            self._delegate = None
        if self._model:
            self._model.destroy()
            self._model = None

    def _reload_ui_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            if self._query_window:
                self._query_window.load()
            if self._groups_window:
                self._groups_window.load()
            self.reload()

    def on_stage_event(self, event_type):
        """Handles stage events.

        Args:
            event (int): The stage event to handle.
        """
        if event_type == omni.usd.StageEventType.CLOSING:
            self._update_clash_bake_globals()
            self._clash_bake_view.disable_clash_bake()
        elif event_type == omni.usd.StageEventType.OPENED:
            self.reload()
            self._update_clash_bake_globals()
            self._clash_bake_view.disable_clash_bake()
        elif event_type == omni.usd.StageEventType.SAVED:
            self.update_ui()
        elif event_type == omni.usd.StageEventType.SIMULATION_START_PLAY:
            self._simulation_mode = True
            self.update_ui()
        elif event_type == omni.usd.StageEventType.SIMULATION_STOP_PLAY:
            self._simulation_mode = False
            self.update_ui()
        if self._query_window:
            self._query_window.on_stage_event(event_type)
        if self._groups_window:
            self._groups_window.on_stage_event(event_type)

    def _update_clash_bake_globals(self):
        self._clash_bake_view.set_usd_context_name(ExtensionSettings.usd_context_name)
        self._clash_bake_view.set_debug_logging(ExtensionSettings.debug_logging)
        self._clash_bake_view.set_clash_query(ExtensionSettings.clash_query)
        self._clash_bake_view.set_clash_viewport(ExtensionSettings.clash_viewport)

    def update_ui(self):
        """Updates the user interface elements."""
        if self._warning_label and ExtensionSettings.clash_data:
            if not ExtensionSettings.clash_data.data_structures_compatible:
                self._warning_label.visible = True
                self._warning_label.text = (
                    "ERROR: Serializer has internal data incompatibility. See log for more details."
                )
            else:
                self._warning_label.visible = False

        cd_in_progress = self._clash_detect_task is not None and not self._clash_detect_task.done()
        self._clash_bake_view.update_ui(cd_in_progress)
        if self._progress_window:
            self._progress_window.visible = cd_in_progress
        if self._run_clash_detection_button:
            self._run_clash_detection_button.enabled = (
                ExtensionSettings.clash_query is not None
                and not self._simulation_mode
                and not cd_in_progress
            )
        if self._progress_bar:
            self._progress_bar.visible = cd_in_progress
        if self._query_combo_box:
            self._query_combo_box.enabled = not cd_in_progress
        if self._delete_row_button:
            self._delete_row_button.enabled = self._tree_view and len(self._tree_view.selection) and not cd_in_progress
        if self._btn_export:
            self._btn_export.enabled = ExtensionSettings.clash_query is not None and not cd_in_progress
        if self._btn_groups:
            self._btn_groups.enabled = ExtensionSettings.clash_query is not None and not cd_in_progress
        if self._btn_refresh:
            self._btn_refresh.enabled = not cd_in_progress
        if self._btn_filter:
            self._btn_filter.tooltip = (
                "Filter in use: " + self._filter_expression
                if self._filter_expression_in_use and len(self._filter_expression) > 0 else "No filter in use"
            )
            self._btn_filter.set_style(
                Styles.FILTER_BUTTON_ACTIVE_STYLE
                if self._filter_expression_in_use
                else Styles.FILTER_BUTTON_INACTIVE_STYLE
            )
        if self._num_of_items_label and self._model:
            items_cnt = len(self._model.filtered_children)
            items_str = "items" if items_cnt != 1 else "item"
            self._num_of_items_label.text = f"Showing {format_int(items_cnt)} {items_str}"
            self._num_of_items_label.tooltip = (
                f"Total clashes for this query in the clash DB: {format_int(self._current_query_total_num_of_clashes)}"
            )
        if self._timeline_slider:
            self._timeline_slider.visible = False

    def create_clash_query_combo_items(self):
        """Creates items for the clash query combo box."""
        if not ExtensionSettings.clash_data:
            return []
        queries = ExtensionSettings.clash_data.fetch_all_queries()
        query_models = [ClashQueryComboBoxItem(query) for query in queries.values()]
        query_models.sort()
        return query_models

    def refresh_query_combo_model(self):
        """Refreshes the clash query combo box model."""
        if not self._query_combo_model or self._query_combo_model.items is None:
            return
        selected_query_id = self._query_combo_model.selected_query_id()
        if selected_query_id == -1 and ExtensionSettings.clash_query is not None:
            selected_query_id = ExtensionSettings.clash_query.identifier
        self._query_combo_model.items.clear()
        query_models = self.create_clash_query_combo_items()
        self._query_combo_model.items.extend(query_models)
        found = False
        if selected_query_id != -1:
            for index, item in enumerate(self._query_combo_model.items):
                if item.clash_query and item.clash_query.identifier == selected_query_id:
                    self._query_combo_model.select_item_index(index)
                    ExtensionSettings.clash_query = item.clash_query
                    if ExtensionSettings.clash_selection:
                        ExtensionSettings.clash_selection.update_query_id(QueryId(ExtensionSettings.clash_query.identifier))
                    found = True
                    break
        if not found:
            ExtensionSettings.clash_query = None
            if self._model:
                self._model.clear()
            self._query_combo_model.select_item_index(-1)
        self._query_combo_model.items_changed()

    def on_clash_query_selection_changed(self, clash_query: Optional[ClashQuery]):
        """Handles changes in the clash query selection.

        Args:
            clash_query (ClashQuery): The selected clash query.
        """
        if ExtensionSettings.clash_query is None and clash_query is None:
            return
        if ExtensionSettings.clash_query is not None and clash_query is not None:
            if ExtensionSettings.clash_query.identifier == clash_query.identifier:
                return
        if self._groups_window:
            self._groups_window.destroy()
            self._groups_window = None
        ExtensionSettings.clash_query = clash_query
        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.update_query_id(
                QueryId(ExtensionSettings.clash_query.identifier if ExtensionSettings.clash_query else 0)
            )
        self.fill_table_with_overlap_data()
        if self._clash_bake_view:
            self._update_clash_bake_globals()
            self._clash_bake_view.on_query_changed()
        self.update_ui()

    def refresh_table(self):
        """Refreshes the data table with clash detection results."""
        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.clear_selection()
        self.clear_search_text()
        self.clear_filter()
        if self._tree_view:
            self._tree_view.selection = []
        self._tree_selection_changed(None)
        self.fill_table_with_overlap_data()
        self.update_ui()

    def get_current_frame_selection(self, model) -> Tuple[Optional[ClashInfo], Optional[ClashFrameInfo], Optional[float]]:
        """Gets the current frame selection.

        Args:
            model (ui.SimpleFloatModel): The model to get the current frame from.

        Returns:
            tuple[Optional[ClashInfo], Optional[ClashFrameInfo], Optional[float]]: ClashInfo and timecode, both optional.
        """
        if not self._tree_view:
            return None, None, None
        if len(self._tree_view.selection) == 0:
            return None, None, None
        selection = self._tree_view.selection[0]
        ci = selection.clash_info
        if ci.clash_frame_info_items is None:
            return None, None, None
        val = model.as_float
        index = ci.get_frame_info_index_by_timecode(val)
        cfi = ci.clash_frame_info_items[index]
        model.set_value(cfi.timecode)
        if len(self._tree_view.selection) <= 0:
            return None, None, None
        selection = self._tree_view.selection[0]
        ci = selection.clash_info
        val = model.as_float
        return ci, cfi, val

    def build_window(self):
        """Builds the Clash Detection window UI."""
        self.create_model()

        def build_query_selector():
            with ui.VStack(height=0):
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._warning_label = ui.Label("", width=0, name="warning_text", visible=True)
                    ui.Spacer()
                with ui.HStack():
                    ui.Label("Selected Clash Query:")
                    ui.Spacer()
                    with ui.HStack(width=0, style={"padding": Styles.MARGIN_DEFAULT, "margin": Styles.MARGIN_DEFAULT}):
                        self._num_of_items_label = ui.Label("", width=0, alignment=ui.Alignment.RIGHT_CENTER)
                        ui.Spacer(width=5)
                        ui.Button(
                            "Show Clash Viewport",
                            width=150,
                            clicked_fn=self._open_clash_viewport_window,
                        )
                        ui.Button(
                            "Query Management",
                            width=150,
                            clicked_fn=self._open_query_management_window,
                        )
                        ui.Spacer(style={"margin": -Styles.MARGIN_DEFAULT})
                with ui.ZStack(height=0):
                    self._query_combo_box = ui.ComboBox(self._query_combo_model, name="clash_query_combo")
                    with ui.VStack():
                        ui.Spacer()
                        ui.Rectangle(
                            height=2,
                            alignment=ui.Alignment.BOTTOM,
                            style={"background_color": Styles.COLOR_BORDER, "margin": 0},
                        )
            ui.Spacer(height=5)

        def build_toolbar():
            with ui.HStack(height=0):
                self._run_clash_detection_button = ui.Button(
                    "Run Clash Detection", width=150, clicked_fn=self.run_clash_detection
                )
                self._delete_row_button = ui.Button(
                    "Delete Selected", width=120, clicked_fn=self.delete_selected_with_prompt
                )
                self._btn_export = ui.Button(
                    "Export...",
                    width=100,
                    clicked_fn=lambda: self._export_menu.show() if self._export_menu else None
                )
                self._btn_groups = ui.Button(
                    "Grouped View",
                    width=100,
                    clicked_fn=self._open_groups_window, tooltip="Show grouped clashes by kind"
                )

                if self._clash_bake_view:
                    self._clash_bake_view.build_clash_bake_toolbar()

                self._btn_refresh = ui.Button(
                    name="refresh",
                    tooltip="Reload results list and reset selection / filtering.\nThis does not trigger any clash detection computation.",
                    width=Styles.IMG_BUTTON_SIZE_H,
                    height=Styles.IMG_BUTTON_SIZE_V,
                    image_width=Styles.IMG_BUTTON_SIZE_H,
                    image_height=Styles.IMG_BUTTON_SIZE_V,
                    clicked_fn=self.refresh_table,
                )
                self._export_screenshot_progress_bar_model = ClashDetectionWindow.CustomProgressValueModel()
                self._progbar_export_screenshots = ui.ProgressBar(
                    self._export_screenshot_progress_bar_model,
                    visible=False,
                    width=140,
                    alignment=ui.Alignment.RIGHT,
                    tooltip="Click here to cancel exporting screenshots",
                    mouse_pressed_fn=lambda x, y, button, modifiers: self.cancel_export(),
                )

                self._create_markers_progress_bar_model = ClashDetectionWindow.CustomProgressValueModel()
                self._progbar_create_markers = ui.ProgressBar(
                    self._create_markers_progress_bar_model,
                    visible=False,
                    width=140,
                    alignment=ui.Alignment.RIGHT,
                    tooltip="Click here to cancel creating markers",
                    mouse_pressed_fn=lambda x, y, button, modifiers: self.cancel_markers(),
                )

                with ui.VStack(height=0):
                    ui.Spacer(height=1)  # artificial padding (shift down) to vertically align with buttons
                    with ui.HStack(height=0):
                        def slider_value_changed(model, s):
                            ci, cfi, timecode = s.get_current_frame_selection(model)
                            if s and cfi:
                                max_local_depth_str = "N/A" if ci.is_soft_clash else f"{cfi.max_local_depth:{'.8f'}}"
                                s._timeline_slider.tooltip = (
                                    f"Overlap Timecode: {cfi.timecode:{'.8f'}}\n"
                                    f"Number of overlapping tris: {cfi.overlap_tris}\n"
                                    f"Minimal overlapping distance: {cfi.min_distance:{'.8f'}}\n"
                                    f"Maximal local depth: {max_local_depth_str}\n"
                                    f"Penetration depth:\n"
                                    f"  +X: {cfi.penetration_depth_px:.8f}, -X: {cfi.penetration_depth_nx:.8f}\n"
                                    f"  +Y: {cfi.penetration_depth_py:.8f}, -Y: {cfi.penetration_depth_ny:.8f}\n"
                                    f"  +Z: {cfi.penetration_depth_pz:.8f}, -Z: {cfi.penetration_depth_nz:.8f}\n"
                                    "\nDrag the slider to inspect other clashing frames."
                                )
                            if ExtensionSettings.clash_timeline_slider_immediate_update:
                                slider_end_edit(model, s)
                            else:
                                if ci:
                                    omni.timeline.get_timeline_interface().set_current_time(timecode)

                        def slider_begin_edit(model, s):
                            ci, cfi, timecode = s.get_current_frame_selection(model)
                            if ci and cfi:
                                omni.timeline.get_timeline_interface().set_current_time(timecode)
                                if ExtensionSettings.clash_selection:
                                    ExtensionSettings.clash_selection.set_current_timecode(timecode)

                        def slider_end_edit(model, s):
                            ci, cfi, timecode = s.get_current_frame_selection(model)
                            if ci and cfi:
                                omni.timeline.get_timeline_interface().set_current_time(timecode)
                                if ExtensionSettings.clash_selection:
                                    ExtensionSettings.clash_selection.update_selection(timecode, [ci])

                        self._timeline_slider_model = ui.SimpleFloatModel(0.0)

                        self._carb_subs.append(
                            self._timeline_slider_model.subscribe_begin_edit_fn(lambda m: slider_begin_edit(m, self))
                        )
                        self._carb_subs.append(
                            self._timeline_slider_model.subscribe_value_changed_fn(lambda m: slider_value_changed(m, self))
                        )
                        self._carb_subs.append(
                            self._timeline_slider_model.subscribe_end_edit_fn(lambda m: slider_end_edit(m, self))
                        )
                        self._timeline_slider = ui.FloatSlider(
                            width=200,
                            name="timeline_slider",
                            model=self._timeline_slider_model,
                            format="%.2f",
                            min=0.0,
                            max=0.0,
                            step=0.0,
                            precision=2,
                            tooltip="Drag the slider to inspect clashing frames",
                        )
                        ui.Spacer(width=5)

                        # Search functionality
                        # The following can be replaced with omni.kit.widget.searchfield
                        with ui.ZStack(height=0):
                            ui.Rectangle(
                                style_type_name_override="SearchFieldFrame",
                                tooltip="Enter search string for case insensitive search.\n"
                                        "Encapsulate it with `back quotes` to match whole word.",
                            )
                            with ui.HStack(height=23):
                                self._search_model = ui.StringField(name="search", width=ui.Fraction(1)).model
                                self._clear_search_button = ui.Button(
                                    name="clear_search",
                                    tooltip="Clear search string",
                                    visible=False,
                                    width=Styles.IMG_BUTTON_SIZE_H,
                                    height=Styles.IMG_BUTTON_SIZE_V,
                                    image_width=Styles.IMG_BUTTON_SIZE_H,
                                    image_height=Styles.IMG_BUTTON_SIZE_V,
                                    clicked_fn=lambda m=self._search_model: clear_search(m),
                                )

                            self._search_label = ui.HStack(spacing=5)
                            with self._search_label:
                                ui.Spacer(width=3)
                                with ui.VStack(width=0):  # VStack to vertically center the search icon
                                    ui.Spacer()
                                    ui.Image(
                                        name="search_icon", width=Styles.IMG_BUTTON_SIZE_H, height=Styles.IMG_BUTTON_SIZE_V
                                    )
                                    ui.Spacer()
                                ui.Label("Search", name="search_label")

                            def search_begin_edit():
                                if self._search_label:
                                    self._search_label.visible = False
                                if self._clear_search_button:
                                    self._clear_search_button.visible = True

                            def search_value_changed(model):
                                # delay the search by 0.5 seconds
                                if not self._deferred_search_action:
                                    self._deferred_search_action = DeferredAction(
                                        lambda: self.search_by_text_deferred(model.as_string)
                                    )
                                self._deferred_search_action.set_next_action_at(datetime.now() + timedelta(seconds=0.75))

                            def search_end_edit(model):
                                self.set_search_text(model)

                            def clear_search(model):
                                self.clear_search_text()

                            self._carb_subs += [
                                self._search_model.subscribe_begin_edit_fn(lambda _: search_begin_edit()),
                                self._search_model.subscribe_value_changed_fn(lambda m: search_value_changed(m)),
                                self._search_model.subscribe_end_edit_fn(lambda m: search_end_edit(m)),
                            ]

                self._btn_filter = ui.Button(
                    name="filter",
                    tooltip="Filter",
                    width=Styles.IMG_BUTTON_SIZE_H,
                    height=Styles.IMG_BUTTON_SIZE_V,
                    image_width=Styles.IMG_BUTTON_SIZE_H,
                    image_height=Styles.IMG_BUTTON_SIZE_V,
                    clicked_fn=self.show_filter_window,
                )
                ui.Button(
                    name="options",
                    tooltip="Settings",
                    width=Styles.IMG_BUTTON_SIZE_H,
                    height=Styles.IMG_BUTTON_SIZE_V,
                    image_width=Styles.IMG_BUTTON_SIZE_H,
                    image_height=Styles.IMG_BUTTON_SIZE_V,
                    mouse_pressed_fn=lambda x, y, b, m: self._settings_menu.show(x, y) if self._settings_menu else None,
                )
            ui.Spacer(height=3)

        def build_table():
            build_toolbar()

            if not self._model or not self._delegate:
                return

            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                style_type_name_override="TreeView",
            ):
                self._tree_view = ui.TreeView(
                    self._model,
                    name="clash_results",
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=self._delegate.get_default_column_widths(),
                    min_column_widths=self._delegate.get_min_column_widths(),
                    resizeable_on_columns_resized=True,
                )
                self._tree_view.set_selection_changed_fn(self._tree_selection_changed)
                self._tree_view.set_mouse_double_clicked_fn(self._tree_view_on_double_click)
                self._tree_view.set_mouse_released_fn(self._tree_view_on_click)
                self._tree_view.set_key_pressed_fn(self._tree_view_on_key_pressed)

        def build_menu():
            self._context_menu = ui.Menu(
                "Context menu###Clash",
                tearable=False,
                menu_compatibility=False,
            )

            # settings menu
            self._settings_menu = ExtensionSettingsWindow()

            # export menu
            def set_export_only_filtered_items(value):
                self._export_only_filtered_items = value

            def set_export_clash_screenshots(value):
                self._export_clash_screenshots = value

            self._export_menu = ui.Menu(
                "Export menu###Clash",
                tearable=False,
                menu_compatibility=False,
            )
            with self._export_menu:
                ui.Separator("Export")
                ui.MenuItem("Export Report to JSON...", triggered_fn=self.export_to_json)
                ui.MenuItem("Export Report to HTML...", triggered_fn=self.export_to_html)
                ui.Separator()
                ui.MenuItem(
                    "Export only filtered items",
                    tooltip="You can choose to export the whole table or only currently visible items",
                    checkable=True,
                    hide_on_click=False,
                    checked=self._export_only_filtered_items,
                    checked_changed_fn=lambda c: set_export_only_filtered_items(c),
                )
                ui.MenuItem(
                    "Export clash screenshots",
                    tooltip="You can choose to export screenshots from clash detection viewport (if viewport extension is enabled)",
                    checkable=True,
                    hide_on_click=False,
                    checked=self._export_clash_screenshots,
                    checked_changed_fn=lambda c: set_export_clash_screenshots(c),
                )
                try:
                    from omni.kit.viewport.menubar.core import SliderMenuDelegate
                except Exception as e:
                    SliderMenuDelegate = None
                if SliderMenuDelegate:
                    ui.Separator("Screenshot Options")

                    ui.MenuItem(
                        "Pre-Wait Frames",
                        hide_on_click=False,
                        delegate=SliderMenuDelegate(
                                min=0,
                                max=200,
                                model=self._export_clash_clear_frames_model,
                                slider_class=ui.IntSlider, # type: ignore
                                tooltip="Number of frames to wait before taking a screenshot",
                            )
                    )
                    ui.MenuItem(
                        "Post-Wait Frames",
                        hide_on_click=False,
                        delegate=SliderMenuDelegate(
                                min=0,
                                max=200,
                                model=self._export_clash_render_frames_model,
                                slider_class=ui.IntSlider, # type: ignore
                                tooltip="Number of frames to wait after rendering the screenshot",
                            )
                    )

            self._update_clash_bake_globals()

        def build_progress_window():
            self._progress_window = ui.Window(
                ClashDetectionWindow.PROGRESS_WINDOW_NAME,
                width=620, height=100,
                flags=(
                    ui.WINDOW_FLAGS_NO_RESIZE
                    | ui.WINDOW_FLAGS_NO_SCROLLBAR
                    | ui.WINDOW_FLAGS_MODAL if not ExtensionSettings.development_mode else 0
                    | ui.WINDOW_FLAGS_NO_CLOSE
                ),
                visible=False,
            )

            with self._progress_window.frame:
                with ui.VStack(height=0):
                    ui.Spacer(height=4)
                    self._progress_window_label = ui.Label("", width=0, height=20)
                    ui.Spacer(height=10)
                    with ui.HStack(height=0):
                        self._progress_bar_model = ClashDetectionWindow.CustomProgressValueModel()
                        self._progress_bar = ui.ProgressBar(self._progress_bar_model, name="progress_bar")
                        ui.Spacer(width=4)
                        ui.Button("Cancel", width=120, clicked_fn=self.cancel_processing)

                self._progress_window.set_key_pressed_fn(
                    lambda key, mod, pressed: (
                        self.cancel_processing() if key == int(carb.input.KeyboardInput.ESCAPE) and pressed else None
                    )
                )

        self._window = ui.Window(ClashDetectionWindow.WINDOW_NAME, visible=False)
        self._window.frame.set_style(Styles.CLASH_WND_STYLE)
        build_menu()
        with self._window.frame:
            with ui.VStack():
                build_query_selector()
                build_table()
        build_progress_window()
        self.update_ui()

    def cancel_running_task(self):
        """Cancels the currently running clash detection task."""
        if self._clash_detect_task:
            if not self._clash_detect_task.done():
                self._clash_detect_task.cancel()
                asyncio.get_event_loop().run_until_complete(self._clash_detect_task)

    async def cancel_running_task_async(self):
        """Asynchronously cancels the currently running clash detection task."""
        if self._clash_detect_task:
            if not self._clash_detect_task.done():
                self._clash_detect_task.cancel()
                await self._clash_detect_task

    def on_clash_query_changed(self, model: ClashQueryTableModel, item: Optional[ClashQuery]):
        """Handles changes in the clash query model.

        Args:
            model (ClashQueryTableModel): The clash query table model.
            item (ClashQuery): The changed clash query item.
        """
        # We ignore whole query model changes, that indicates model.clear() or load(), not item changes
        # But it can indicate deletion as we do not send update on deletion of each row,
        # so we need to check if number of items is the same
        if item is not None or (
            self._query_combo_model
            and self._query_combo_model.items
            and model.get_row_count() != len(self._query_combo_model.items)
        ):
            self.refresh_query_combo_box()

    def _open_clash_viewport_window(self):
        try:
            from omni.physxclashdetectionviewport.clash_viewport_settings import ClashViewportSettings
            carb.settings.get_settings().set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, True)
        except:
            show_notification(
                "Clash Detection Viewport extension is not installed.\n"
                "Please install and enable it to use this feature.",
                error=True,
            )

    def _open_query_management_window(self):
        if not self._query_window:
            self._query_window = ClashQueryWindow()
            self._query_window.subscribe_query_changed(self.on_clash_query_changed)
        else:
            self._query_window.update_ui(False, True)
            self._query_window.visible = True

    def _open_groups_window(self):
        if not self._model:
            return
        if self._groups_window:
            self._groups_window.destroy()
        self._groups_window = GroupsWindow(self._model.children, self._tree_view, self._tree_view_on_item_click)
        self._groups_window.update_ui()

    def _get_timeline_span(self) -> Tuple[float, float, float]:  # start_time, end_time, codes_per_second
        """Gets the start time, end time and time codes per second from the timeline.

        Returns:
            tuple[float, float, float]: A tuple containing:
                - start_time: The start time in seconds
                - end_time: The end time in seconds
                - codes_per_second: Number of time codes per second
        """
        if not self._clash_detect or not self._clash_detect._clash_detect_api:
            return 0.0, 0.0, 0.0
        timeline_data = self._clash_detect._clash_detect_api.get_timeline_data()
        start_time = 0.0 if timeline_data.startTime < 0.0 else timeline_data.startTime
        end_time = 0.0 if timeline_data.endTime < 0.0 else timeline_data.endTime
        codes_per_second = timeline_data.timeCodesPerSecond
        settings = self._clash_detect_settings.convert_values_to_dict()
        dynamic = settings.get(SettingId.SETTING_DYNAMIC.name, False)
        setting_find_duplicates = settings.get(SettingId.SETTING_DUP_MESHES.name, False)
        if dynamic and not setting_find_duplicates:
            setting_start_time = settings.get(SettingId.SETTING_DYNAMIC_START_TIME.name, 0.0)
            setting_end_time = settings.get(SettingId.SETTING_DYNAMIC_END_TIME.name, 0.0)
            if setting_start_time != 0.0:
                start_time = setting_start_time
            if setting_end_time != 0.0:
                end_time = setting_end_time
            # clamp start and end time to fit into timeline range
            start_time = clamp_value(start_time, timeline_data.startTime, timeline_data.endTime)
            end_time = clamp_value(end_time, timeline_data.startTime, timeline_data.endTime)
            return start_time, end_time, codes_per_second
        else:
            setting_static_time = settings.get(SettingId.SETTING_STATIC_TIME.name, 0.0)
            setting_static_time_start = setting_static_time
            setting_static_time_end = setting_static_time
            # make the range a bit bigger [-1 frame, +1 frame]
            if codes_per_second > 0 and setting_static_time != 0.0:
                setting_static_time_start -= 1.0 / codes_per_second
                setting_static_time_end += 1.0 / codes_per_second
            setting_static_time_start = clamp_value(setting_static_time_start, start_time, end_time)
            setting_static_time_end = clamp_value(setting_static_time_end, start_time, end_time)
            return setting_static_time_start, setting_static_time_end, codes_per_second

    def _get_num_results_found_str(self) -> str:
        found_str = "No clashes detected"
        if not self._clash_detect:
            return found_str
        overlaps = self._clash_detect.get_nb_overlaps()
        duplicates = self._clash_detect.get_nb_duplicates()
        if overlaps != 0 or duplicates != 0:
            num_results_parts = []
            if overlaps > 0:
                s = "es" if overlaps > 1 else ""
                num_results_parts.append(f"{format_int(overlaps)} clash{s}")
            if duplicates > 0:
                settings = self._clash_detect_settings.convert_values_to_dict()
                setting_find_duplicates = settings.get(SettingId.SETTING_DUP_MESHES.name, False)
                if setting_find_duplicates:
                    s = "s" if duplicates > 1 else ""
                    num_results_parts.append(f"{format_int(duplicates)} duplicate{s}")
            found_str = " and ".join(num_results_parts) + " detected"
        return found_str

    async def _convert_curve_anim(
        self,
        stage: Usd.Stage,
        clash_query: ClashQuery,
        start_time: float,
        end_time: float,
        codes_per_second: float,
        progress_update: OptimizedProgressUpdate,
    ) -> None:
        """Converts curve animation to USD time sampled data for clash detection.

        Takes animated curves in the stage and converts them to time sampled USD data that can be
        processed by the clash detection system. This is needed because the clash detection cannot
        directly process curve animations.

        Args:
            stage: The USD stage containing the animated curves
            clash_query: The clash query defining which prims to process
            start_time: Start time of the animation range to convert
            end_time: End time of the animation range to convert
            codes_per_second: Number of time samples per second to generate
            progress_update: Progress updater for providing UI feeack during conversion

        Note:
            Requires the physx.clashdetection.anim extension to be enabled.
        """
        try:
            from omni.physxclashdetectionanim.scripts.anim_recorder import AnimRecorder
            if not self._anim_recorder:
                self._anim_recorder = AnimRecorder()
        except Exception as e:
            self._anim_recorder = None
            carb.log_warn(
                "For curve anim support please enable physx.clashdetection.anim extension.\n"
                f"Import FAILED with exception: {e}"
            )
            return

        # TODO: Optimize the following code to get list of animated prims from the anim engine (currently unavailable)
        def is_xform(prim: Usd.Prim) -> bool:
            return prim.IsA(UsdGeom.Xformable)

        if clash_query.object_a_path or clash_query.object_b_path:
            prim_paths_a, int_paths_a = ClashDetection.get_list_of_prims_int_paths(stage, clash_query.object_a_path, True, is_xform)
            prim_paths_b, int_paths_b = ClashDetection.get_list_of_prims_int_paths(stage, clash_query.object_b_path, True, is_xform)
        else:
            # A special case - obj A and obj B paths empty means processing of the whole stage
            prim_paths_a, int_paths_a = ClashDetection.get_list_of_prims_int_paths(stage, "/", True, is_xform)
            int_paths_b = []

        if self._progress_bar and self._progress_bar_model and self._progress_window_label:
            self._progress_bar.style = {
                "color": Styles.COLOR_PROGRESS_BAR_ANIM, "secondary_color": Styles.COLOR_2ND_PROGRESS_BAR_ANIM
            }
            progress_info_text = "Converting curve anim to time sampled data..."
            self._progress_window_label.text = progress_info_text
            self._progress_bar.tooltip = progress_info_text
            self._progress_bar_model.set_value(0)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        if ExtensionSettings.debug_logging:
            carb.log_info(f"Recording curve anim from time {start_time} to {end_time} into session layer.")

        time_length = abs(end_time - start_time)
        for current_timecode in self._anim_recorder.run(
            stage, int_paths_a + int_paths_b, start_time, end_time, codes_per_second
        ):
            if self._cancel_processing:
                break
            if current_timecode < start_time:  # this can happen as user specified time might not match the timeline
                start_time = current_timecode
                time_length = abs(end_time - start_time)
            progress_value = (current_timecode - start_time) / time_length
            if progress_update.update(progress_value):
                if self._progress_bar_model:
                    self._progress_bar_model.set_value(progress_value)
                await omni.kit.app.get_app().next_update_async()  # type: ignore

        await omni.kit.app.get_app().next_update_async()  # type: ignore
        # in case timeline event was triggered and deltas were reintroduced
        if self._anim_recorder and time_length > 0.0:
            self._anim_recorder.reset_overridden_session_prim_props()

    async def _run_clash_pipeline(
        self,
        progress_update: OptimizedProgressUpdate,
    ) -> None:
        """Executes the clash detection pipeline steps and updates the UI progress.

        Args:
            progress_update: Helper object that optimizes UI progress updates by throttling update frequency.
        """
        if (
            not self._clash_detect
            or not self._progress_bar
            or not self._progress_bar_model
            or not self._progress_window_label
        ):
            return
        self._progress_bar.style = {
            "color": Styles.COLOR_PROGRESS_BAR_CLASH, "secondary_color": Styles.COLOR_2ND_PROGRESS_BAR_CLASH
        }
        num_steps = self._clash_detect.create_pipeline()
        if ExtensionSettings.debug_logging:
            carb.log_info(f"Initializing clash detection, will be executing {num_steps} steps.")

        if ExtensionSettings.use_async_clash_pipeline:
            self._async_pipeline_cookie = self._clash_detect.run_async_pipeline()
            while self._clash_detect.is_async_pipeline_running(self._async_pipeline_cookie):
                if self._cancel_processing or self._clash_detect.is_out_of_memory:
                    self._clash_detect.cancel_async_pipeline(self._async_pipeline_cookie)
                    break
                step_data = self._clash_detect.get_async_pipeline_step_data(self._async_pipeline_cookie)
                if progress_update.update(step_data.progress):
                    if step_data.name:
                        self._progress_window_label.text = step_data.name
                        self._progress_bar.tooltip = step_data.name
                    self._progress_bar_model.set_value(step_data.progress)
                    await omni.kit.app.get_app().next_update_async()  # type: ignore
                await asyncio.sleep(0.1)
            self._clash_detect.finish_async_pipeline(self._async_pipeline_cookie)
            self._async_pipeline_cookie = None
        else:
            for i in range(num_steps):
                if self._cancel_processing or self._clash_detect.is_out_of_memory:
                    break
                step_data = self._clash_detect.get_pipeline_step_data(i)
                if progress_update.update(step_data.progress):
                    if step_data.name:
                        self._progress_window_label.text = step_data.name
                        self._progress_bar.tooltip = step_data.name
                    self._progress_bar_model.set_value(step_data.progress)
                    await omni.kit.app.get_app().next_update_async()  # type: ignore
                self._clash_detect.run_pipeline_step(i)

    async def _fetch_and_save_clash_data(
        self,
        stage: Usd.Stage,
        clash_data: ClashData,
        clash_query: ClashQuery,
        progress_update: OptimizedProgressUpdate,
    ) -> None:
        """Fetches and saves clash data from the clash detection engine.

        Args:
            stage: The USD stage containing the geometry to process
            clash_data: Container for storing and managing clash information
            clash_query: The clash query containing search parameters and settings
            progress_update: Helper object for optimizing progress bar updates
        """
        if (
            not self._clash_detect
            or not self._progress_bar
            or not self._progress_bar_model
            or not self._progress_window_label
        ):
            return
        self._progress_bar.style = {
            "color": Styles.COLOR_PROGRESS_BAR_FETCH, "secondary_color": Styles.COLOR_2ND_PROGRESS_BAR_FETCH
        }
        progress_info_text = f"{self._get_num_results_found_str()}. Processing and storing new and existing clashes..."
        self._progress_window_label.text = progress_info_text
        self._progress_bar.tooltip = progress_info_text
        self._progress_bar_model.set_value(0)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        start_time = time.time()
        for progress_value in self._clash_detect.fetch_and_save_overlaps(stage, clash_data, clash_query):
            if progress_value < 0.0:
                self._cancel_processing = True
                self._cancel_processing_reason = "Failed to fetch and save / update clash data.\nSee log for details."
            if self._cancel_processing or self._clash_detect.is_out_of_memory:
                break
            if progress_update.update(progress_value):
                elapsed_time = time.time() - start_time
                eta = (elapsed_time / progress_value) - elapsed_time if progress_value > 0 else 0
                self._progress_bar_model.set_value(progress_value)
                eta_str = f"ETA: {int(eta//3600)}h {int((eta%3600)//60)}m." if eta > 60 else "ETA: less than a minute."
                self._progress_bar.tooltip = f"{progress_info_text}\n{eta_str}"
                self._progress_window_label.text = f"{progress_info_text} {eta_str}"
                await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def _run_clash_detection(self) -> None:
        """
        Performs asynchronous scene processing to detect clashes.

        This method performs the following tasks:
        1. Initializes the clash detection pipeline and prepares the progress bar UI.
        2. Optionally converts curve animation data into time-sampled USD animation data if applicable.
        3. Executes the clash detection pipeline step-by-step, updating progress in the UI.
        4. Fetches and saves detected clash data, displaying it in a table.

        The method handles user cancellation and exceptions gracefully, ensuring proper cleanup of UI elements.
        """
        ctx = omni.usd.get_context(ExtensionSettings.usd_context_name)
        if not ctx:
            return
        stage = ctx.get_stage()  # type: ignore
        cd = ExtensionSettings.clash_data
        cq = ExtensionSettings.clash_query
        if not stage or not cd or not cq or not self._clash_detect:
            return

        # Clear current clash bake layer to avoid meshes added by it from being used in the clash detection, generating
        # false / fake clashes between real geometry and their visual representation.
        self._clash_bake_view.clear_clash_bake()
        # Also hide all clash meshes in the main viewport just in case
        if ExtensionSettings.clash_viewport:
            ExtensionSettings.clash_viewport.hide_all_clash_meshes()

        if self._progress_bar_model:
            self._progress_bar_model.set_value(0)
        if self._progress_window_label:
            self._progress_window_label.text = "Initializing..."

        self.update_ui()
        return_immediately = False
        progress_update = OptimizedProgressUpdate(0.2, 1.2)

        start_time, end_time, codes_per_second = self._get_timeline_span()
        time_length = abs(end_time - start_time)
        populate_results = False

        try:
            if time_length > 0.0:
                progress_update.start()
                await self._convert_curve_anim(stage, cq, start_time, end_time, codes_per_second, progress_update)

            progress_update.start()
            await self._run_clash_pipeline(progress_update)

            progress_update.start()
            await self._fetch_and_save_clash_data(stage, cd, cq, progress_update)

            populate_results = True
            if self._progress_bar:
                item_count_info = "Populating results..."
                if self._cancel_processing:
                    item_count_info += "\n<clash detection was interrupted>"
                item_count_info += f"\n{self._get_num_results_found_str()}."
                self._progress_bar.tooltip = item_count_info
                await omni.kit.app.get_app().next_update_async()  # type: ignore

        except asyncio.CancelledError:
            # forcefully canceled - this only happens when in object release state (destructor) -> exit immediately
            carb.log_info("Clash detection was forcefully canceled.")
            return_immediately = True
        except Exception as e:
            carb.log_error(f"_run_clash_detection exception: {e}")
        finally:
            if not return_immediately:
                if ExtensionSettings.use_async_clash_pipeline and self._async_pipeline_cookie:
                    self._clash_detect.finish_async_pipeline(self._async_pipeline_cookie)
                    self._async_pipeline_cookie = None
                if self._cancel_processing:
                    if ExtensionSettings.show_prompts:
                        show_notification(
                            f"Clash detection was canceled.\n"
                            f"Reason: {self._cancel_processing_reason}\n"
                            f"{self._get_num_results_found_str()}.",
                            error=True,
                            log_error_as_warning=True,
                        )
                    self._cancel_processing = False
                    self._cancel_processing_reason = ""
                elif self._clash_detect.is_out_of_memory:
                    show_notification(
                        "Clash detection was interrupted.\n"
                        "Reason: Not enough system memory (RAM).\n"
                        "Please limit scope of the clash query and try again.\n"
                        f"{self._get_num_results_found_str()}.",
                        error=True,
                        duration=-1,
                    )
                else:
                    if ExtensionSettings.show_prompts:
                        show_notification(f"Clash detection process completed.\n{self._get_num_results_found_str()}.")
                await omni.kit.app.get_app().next_update_async()  # type: ignore
                self._clash_detect_task = None
                self._clash_detect.reset()  # reset the clash detection engine, free up used memory
                if populate_results:
                    self.fill_table_with_overlap_data()
                if self._progress_bar:
                    self._progress_bar.style = {}
                    self._progress_bar.visible = False
                self.update_ui()

    def setup_clash_detection(self) -> bool:
        """Sets up the clash detection process.

        Returns:
            bool: True if setup is successful, False otherwise.
        """
        # if the clash detection is already running, do noting
        if self._clash_detect_task and not self._clash_detect_task.done():
            return True

        if not self._clash_detect:
            return False

        cq = ExtensionSettings.clash_query
        if cq is None:
            return False

        ctx = omni.usd.get_context(ExtensionSettings.usd_context_name)
        if not ctx:
            return False

        stage = ctx.get_stage()  # type: ignore
        if not stage:
            return False

        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.clear_selection()
        self.clear_search_text()
        self.clear_filter(False)

        # It is handy to use ClashDetectionSettings here as it will add missing values if needed
        # Thing is, in the UI, default values may differ from clash detection engine
        # By updating the settings we are sure that missing fields have the same defaults as in the UI
        self._clash_detect_settings = ClashDetectionSettings()
        if len(cq.clash_detect_settings) > 0:
            self._clash_detect_settings.load_values_from_dict(cq.clash_detect_settings)
        updated_clash_detect_settings = self._clash_detect_settings.convert_values_to_dict()

        if not self._clash_detect.set_scope(
            stage,
            cq.object_a_path,
            cq.object_b_path,
            updated_clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, False)
        ):
            return False

        if not self._clash_detect.set_settings(updated_clash_detect_settings, stage):
            return False

        return True

    def run_clash_detection(self):
        """Runs the clash detection process."""
        if not self.setup_clash_detection():
            show_notification("Failed to setup clash detection, see log for error details.", True)
            return
        self._clash_detect_task = asyncio.ensure_future(self._run_clash_detection())

    def cancel_processing(self):
        """Cancels the current processing task if it is running."""
        if self._clash_detect_task and not self._clash_detect_task.done():
            self._cancel_processing = True
            self._cancel_processing_reason = "Aborted by user."

    def apply_filter(self, filter_expression: str, use_filter: bool) -> bool:
        """Applies a filter expression to the clash detection results."""
        if not self._model or not self._delegate:
            show_notification("Apply Filter: Model or delegate not found.", True)
            return False
        self._filter_expression = filter_expression
        self._filter_expression_in_use = use_filter and len(filter_expression) > 0
        if self._filter_expression_in_use:
            if self._model.set_filter_expression(self._filter_expression, self._delegate.columns):
                self.update_ui()
                return True
            else:
                self._filter_expression_in_use = False
                show_notification("Invalid filter expression, see log for details.", True)
                self.update_ui()
                return False
        else:
            self._model.set_filter_expression("", {})  # remove any filter
            self.update_ui()
        return True

    def show_filter_window(self):
        FilterWindow(
            filter_expression=self._filter_expression,
            use_filter=self._filter_expression_in_use,
            apply_filter_fn=self.apply_filter,
        ).show()

    def reset(self):
        """Resets the clash detection settings and clears the model."""
        if self._clash_detect:
            self._clash_detect.reset()
        if self._model:
            self._model.clear()
            self._model.update_items()
        if self._query_combo_model:
            ExtensionSettings.clash_query = None
            self._query_combo_model.select_item_index(-1)  # invalidate current selection
            self._query_combo_model.clear_items()
            self._query_combo_model.items_changed()
        self.clear_search_text()
        self.clear_filter()
        self.update_ui()

    def reload(self):
        """Reloads the clash detection window and refreshes the query combo box."""
        self.reset()
        self.refresh_query_combo_box()

    def refresh_query_combo_box(self):
        """Refreshes the items in the query combo box."""
        self.refresh_query_combo_model()
        # NOTE: self.fill_table_with_overlap_data() will be triggered automatically by combo box item change
        self.update_ui()

    def select_all_clashes(self):
        """Selects all clashes in the tree view."""
        if self._model and len(self._model.filtered_children) > 0 and self._tree_view:
            self._tree_view.selection = self._model.filtered_children
            self._tree_selection_changed(None)

    def fill_table_with_overlap_data(self):
        """Fills the table with overlap data from the current clash query."""
        if not self._model:
            return

        self._model.clear()

        if not ExtensionSettings.clash_query or not ExtensionSettings.clash_data:
            return

        query_id = ExtensionSettings.clash_query.identifier
        row_limit = ExtensionSettings.clash_pairs_table_display_limit
        self._current_query_total_num_of_clashes = ExtensionSettings.clash_data.get_overlaps_count_by_query_id(query_id)

        if ExtensionSettings.debug_logging:
            carb.log_info(
                f"fill_table_with_overlap_data: fetching all {format_int(self._current_query_total_num_of_clashes)} "
                f"overlaps for current query id {query_id}, with limit of {format_int(row_limit)} overlaps..."
            )

        overlaps_dict = ExtensionSettings.clash_data.find_all_overlaps_by_query_id(
            query_id, False, num_overlaps_to_load=row_limit
        )

        total_rows = len(overlaps_dict.values())
        if ExtensionSettings.debug_logging:
            carb.log_info(f"fill_table_with_overlap_data: adding {format_int(total_rows)} rows to the model...")

        if total_rows > 0:
            for i, clash_info in enumerate(overlaps_dict.values(), 1):
                if ExtensionSettings.debug_logging and i % 100000 == 0:
                    carb.log_info(
                        f"fill_table_with_overlap_data: {format_int(i)} rows added to the model so far..."
                    )
                self._model.add_row(clash_info)
            if ExtensionSettings.debug_logging:
                carb.log_info(
                    f"fill_table_with_overlap_data: finished adding rows, added {format_int(i)} rows in total." # type: ignore
                )
            overlaps_dict.clear()

        if self._current_query_total_num_of_clashes > row_limit:
            show_notification(
                "Maximum number of rows in the clash results table reached.\n"
                f"Only the first {format_int(row_limit)} out of {format_int(self._current_query_total_num_of_clashes)} "
                "rows are displayed in the table.",
                error=True, duration=-1, also_write_log=True, log_error_as_warning=True
            )
            carb.log_warn(
                "fill_table_with_overlap_data: Reached the table row limit. "
                f"Table will show only the first {format_int(row_limit)} rows out of "
                f"{format_int(self._current_query_total_num_of_clashes)}."
            )

        if ExtensionSettings.debug_logging:
            carb.log_info("fill_table_with_overlap_data: updating table delegate...")

        if self._delegate and self._model.sort_column_id == -1:  # set sort columns only when unset, otherwise keep current setting
            self._delegate.sort(ClashDetectTableColumnEnum.OVERLAP_TRIS, False, False)  # descending

        if ExtensionSettings.debug_logging:
            carb.log_info("fill_table_with_overlap_data: updating the table model (filtering, sorting, etc.)...")

        self._model.update_items()
        self.update_ui()

        if ExtensionSettings.debug_logging:
            carb.log_info("fill_table_with_overlap_data: finished.")

    def delete_selected_with_prompt(self):
        """Delete with confirmation message box."""
        if not self._tree_view or len(self._tree_view.selection) == 0:
            return
        if self._clash_detect_task and not self._clash_detect_task.done():  # clash detection is running
            return
        if ExtensionSettings.show_prompts:
            Prompt(
                "Delete Clash Records",
                "Delete selected clash records?",
                ok_button_text="Yes",
                cancel_button_text="No",
                ok_button_fn=self.delete_selected,
                modal=True,
            ).show()
        else:
            self.delete_selected()

    def delete_selected(self):
        """Deletes the selected items from the clash detection results."""
        if not self._model or not self._tree_view or len(self._tree_view.selection) == 0 or not ExtensionSettings.clash_data:
            return
        for s in self._tree_view.selection:  # type: ignore
            clash_identifier = s.clash_info.identifier
            if ExtensionSettings.clash_data.remove_overlap_by_id(clash_identifier, False) == 1:
                self._model.delete_row(s, False)
        ExtensionSettings.clash_data.commit()
        self._model.update_items()
        self._tree_selection_changed(None)

    def set_search_text(self, model):
        """Sets the search text for filtering results.

        Args:
            model (ui.StringField): The search text model.
        """
        if self._window:
            self.search_by_text(model.as_string)
            if self._search_label:
                self._search_label.visible = not model.as_string
            if self._clear_search_button and self._search_label:
                self._clear_search_button.visible = not self._search_label.visible

    def clear_selection(self):
        """Clears the current selection in the tree view."""
        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.clear_selection()
        if self._tree_view:
            self._tree_view.selection = []
        self._tree_selection_changed(None)

    def clear_search_text(self):
        """Clears the search text field and updates the model."""
        if self._window:
            if self._search_model:
                self._search_model.set_value("")
            if self._search_label:
                self._search_label.visible = True
            if self._clear_search_button:
                self._clear_search_button.visible = False
            if self._model and self._search_model:
                self._model.set_filter_text(self._search_model.as_string)

    def clear_filter(self, delete_also_filter_expression_str: bool = True):
        """Clears the filter expression and updates the model."""
        if delete_also_filter_expression_str:
            self._filter_expression = ""
        self._filter_expression_in_use = False
        if self._model:
            self._model.set_filter_expression("", {})  # remove any filter

    def search_by_text(self, search_text: str):
        """Sets the search filter string to the models and widgets

        Args:
            search_text (str): The search text to filter results.
        """
        if self._model:
            self._model.set_filter_text(search_text)

        self.update_ui()

    def search_by_text_deferred(self, search_text: str) -> bool:
        """
        Deferred search handler for the search field.

        Args:
            search_text (str): The search text to filter results.

        Returns:
            bool: Always returns False to indicate the deferred action should stop.
        """

        self.search_by_text(search_text)

        if self._deferred_search_action:
            self._deferred_search_action.destroy()
            self._deferred_search_action = None
        return False

    def _cancel_clash_detection_clear_selection(self):
        # stop clash detection if running
        self.cancel_processing()
        self.clear_selection()

    @staticmethod
    def _get_export_column_defs(columns: ValuesView[TableColumnDef]):
        return [
            ExportColumnDef(idx, cd.name, True if cd.alignment == ui.Alignment.RIGHT else False)
            for idx, cd in enumerate(columns)
        ]

    async def _get_export_rows(
        self,
        images_dir: str,
        column_defs: List[ExportColumnDef],
        row_items: List[ClashDetectTableRowItem],
    ) -> List[List[str]]:
        if not ExtensionSettings.clash_data:
            return []
        columns_count = len(column_defs)
        total_infos = len(row_items)
        rows_list = []
        screenshot_export_error = False
        relative_path = os.path.basename(images_dir)
        clear_frames = self._export_clash_clear_frames_model.as_int
        render_frames = self._export_clash_render_frames_model.as_int
        if ExtensionSettings.clash_viewport:
            ExtensionSettings.clash_viewport.setup_for_screenshot_export()
        for index, rm in enumerate(row_items):
            if not rm or not hasattr(rm, 'clash_info') or not hasattr(rm, 'row_models'):
                continue
            if columns_count != len(rm.row_models):
                carb.log_error(
                    f"Number of defined columns ({columns_count}) does not correspond to number of columns in the row ({len(rm.row_models)})"
                )
                continue
            progress_value = index / total_infos
            if self._export_screenshot_progress_bar_model:
                self._export_screenshot_progress_bar_model.set_value(progress_value)
            rows_list.append([rm.row_models[cd.order].as_string for cd in column_defs])
            if self._export_clash_screenshots and rm.clash_info:
                try:
                    file_path = f"{images_dir}/{rm.clash_info.overlap_id}.png"
                    rm.clash_info._clash_frame_info_items = (
                        ExtensionSettings.clash_data.fetch_clash_frame_info_by_clash_info_id(rm.clash_info.identifier)
                    )
                    timecode = rm.clash_info.start_time
                    omni.timeline.get_timeline_interface().set_current_time(
                        timecode
                    )  # This is important to properly export dynamic clashes
                    if ExtensionSettings.clash_viewport:
                        await ExtensionSettings.clash_viewport.export_screenshot_to_file(
                            rm.clash_info, timecode, str(file_path), index, total_infos, clear_frames, render_frames
                        )
                    rm.clash_info._clash_frame_info_items = None  # Free memory
                    relative_image_path = f"{relative_path}/{rm.clash_info.overlap_id}.png"
                    rows_list[index].append(relative_image_path)
                except asyncio.CancelledError as e:
                    raise e
                except Exception as e:
                    if not screenshot_export_error:  # Only print error for first row
                        show_notification(f"Error during export: {e}", True)
                    screenshot_export_error = True
        if (
            self._export_clash_screenshots and not screenshot_export_error
        ):  # If there was no error in screenshot exports, we add its column
            column_defs.append(ExportColumnDef(len(column_defs), "Image"))
        if ExtensionSettings.clash_viewport:
            ExtensionSettings.clash_viewport.teardown_for_screenshot_export()
        return rows_list

    async def export_async(
        self, file_path, write_function: Callable[[str, List[ExportColumnDef], Sequence[Sequence[str]]], None]
    ):
        """Exports clash detection results asynchronously.

        Args:
            file_path (str): The file path for the export.
            write_function (Callable[[str, List[ExportColumnDef], Sequence[Sequence[str]]], None]): The function to write the export data.
        """
        if not self._model or not self._delegate:
            return
        old_timecode = omni.timeline.get_timeline_interface().get_current_time()
        try:
            source_url = omni.client.break_url(file_path)
            base_html_export_dir = os.path.dirname(source_url.path)
            relative_images_export_dir = f"{Path(file_path).stem}_images"
            images_dir_url = omni.client.make_url(
                scheme=source_url.scheme,
                host=source_url.host,
                port=source_url.port,
                path=f"{base_html_export_dir}/{relative_images_export_dir}",
            )
            if self._export_clash_screenshots:
                result = await omni.client.create_folder_async(images_dir_url)
                if result == omni.client.Result.ERROR_ALREADY_EXISTS:
                    carb.log_warn(f"Directory '{images_dir_url}' already exists. Skipping creation.")
                elif result != omni.client.Result.OK:
                    raise Exception(f'Error {result}. Failed to create directory "{images_dir_url}"')

            if self._btn_export:
                self._btn_export.visible = False
            self._clash_bake_view.set_visible(False)
            if self._progbar_export_screenshots:
                self._progbar_export_screenshots.visible = True
            column_defs = self._get_export_column_defs(self._delegate.columns.values())
            rows = await self._get_export_rows(
                images_dir_url,
                column_defs,
                self._model.filtered_children if self._export_only_filtered_items else self._model.children,
            )
            write_function(file_path, column_defs, rows)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            carb.log_error(e)
        omni.timeline.get_timeline_interface().set_current_time(old_timecode)
        if self._btn_export:
            self._btn_export.visible = True
        self._clash_bake_view.set_visible(True)
        if self._progbar_export_screenshots:
            self._progbar_export_screenshots.visible = False
        self._export_future = None

    def get_export_additional_info(self) -> dict[str, str]:
        return {
            "Author": get_current_user_name(),
            "Date": get_datetime_str(datetime.now()),
            "Query Name": ExtensionSettings.clash_query.query_name if ExtensionSettings.clash_query else "None",
        }

    def start_html_export(self, file_path):
        """Starts the export of clash detection results to an HTML file.

        Args:
            file_path (str): The file path for the HTML export.
        """

        def write_html(file_path: str, column_defs: List[ExportColumnDef], rows: Sequence[Sequence[str]]):
            html_bytes = export_to_html(
                "Clash Detection Results",
                omni_get_path_name_of_current_stage(),
                column_defs,
                rows,
                self.get_export_additional_info(),
            )
            if omni.client.write_file(file_path, html_bytes) != omni.client.Result.OK:  # type: ignore
                carb.log_error(f"Failed writing HTML file to '{file_path}'.")

        self._export_future = asyncio.ensure_future(self.export_async(file_path, write_html))

    def export_to_html(self):
        """Opens a file dialog to export clash detection results to an HTML file."""
        pick_target_file(
            "Save Clash Detection Results to HTML file",
            [("*.html", "HTML Files"), ("*", "All Files")],
            ".html",
            self.start_html_export
        )

    def start_json_export(self, file_path):
        """Starts the export of clash detection results to a JSON file.

        Args:
            file_path (str): The file path for the JSON export.
        """

        def write_json(file_path: str, column_defs: List[ExportColumnDef], rows: Sequence[Sequence[str]]):
            json_bytes = export_to_json(column_defs, rows, self.get_export_additional_info())
            if omni.client.write_file(file_path, json_bytes) != omni.client.Result.OK:  # type: ignore
                carb.log_error(f"Failed writing JSON file to '{file_path}'.")

        self._export_future = asyncio.ensure_future(self.export_async(file_path, write_json))

    def export_to_json(self):
        """Opens a file dialog to export clash detection results to a JSON file."""
        pick_target_file(
            "Save Clash Detection Results to JSON file",
            [("*.json", "JSON Files"), ("*", "All Files")],
            ".json",
            self.start_json_export
        )

    def cancel_export(self):
        """Cancels the ongoing export task."""
        if self._export_future:
            self._export_future.cancel()
            self._export_future = None

    async def _async_generate_clash_meshes(self, just_clear: bool):
        if (
            not self._tree_view
            or len(self._tree_view.selection) == 0
            or not self._progress_bar_model
            or not self._clash_bake_view
        ):
            return
        self.update_ui()
        self._update_clash_bake_globals()
        if self._progbar_export_screenshots:
            self._progbar_export_screenshots.visible = True
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        if not self._progbar_export_screenshots:
            return
        old_tooltip = self._progbar_export_screenshots.tooltip
        try:
            clash_infos = [selection.clash_info for selection in self._tree_view.selection]  # type: ignore
            self._progbar_export_screenshots.tooltip = "Click here to cancel clash baking process..." if not just_clear else "Click here to cancel clash clearing process..."
            await self._clash_bake_view.process(clash_infos, just_clear, self._export_screenshot_progress_bar_model) # type: ignore
        except asyncio.CancelledError:
            pass
        except Exception as e:
            carb.log_error(e)
        finally:
            self._progbar_export_screenshots.tooltip = old_tooltip
            self._cancel_processing = False
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            if self._progbar_export_screenshots:
                self._progbar_export_screenshots.visible = False
            self.update_ui()

    def generate_clash_meshes(self):
        self._export_future = asyncio.ensure_future(self._async_generate_clash_meshes(just_clear=False))

    def clear_clash_meshes(self):
        self._export_future = asyncio.ensure_future(self._async_generate_clash_meshes(just_clear=True))

    def _inspect_clashing_frames(self):
        if (
            not self._tree_view
            or len(self._tree_view.selection) == 0
            or not self._timeline_slider
            or not self._timeline_slider_model
        ):
            return

        selection = self._tree_view.selection[0]
        ci = selection.clash_info

        if self._inspecting_ci != ci:
            if self._inspecting_ci is not None:
                self._inspecting_ci.clash_frame_info_items = None  # free memory
                self._inspecting_ci = None
            if ci.clash_frame_info_items is None or len(ci.clash_frame_info_items) < ci.num_records:  # data not yet fully loaded
                # load frame data for the selected item
                if ExtensionSettings.clash_data:
                    ci.clash_frame_info_items = ExtensionSettings.clash_data.fetch_clash_frame_info_by_clash_info_id(
                        ci.identifier
                    )
            self._inspecting_ci = ci

        self._timeline_slider_model.set_value(ci.start_time)
        self._timeline_slider.min = ci.start_time
        self._timeline_slider.max = ci.end_time
        self._timeline_slider.step = 0.01
        self._timeline_slider.visible = True if ci.num_records > 1 else False

        timecode = self._timeline_slider_model.as_float
        omni.timeline.get_timeline_interface().set_current_time(timecode)
        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.update_selection(ci.start_time, [ci])
        self._timeline_slider_model._value_changed()

    def _tree_view_on_key_pressed(self, key: int, modifiers: int, is_down: bool):
        pass

    def _tree_view_on_double_click(self, x, y, b, m):
        self._inspect_clashing_frames()

    def __on_menu_item_select_object_a(self):
        if not self._tree_view:
            return
        selection: list[str] = [entry.clash_info.object_a_path for entry in self._tree_view.selection]  # type: ignore
        omni.usd.get_context(ExtensionSettings.usd_context_name).get_selection().set_selected_prim_paths(selection, True)

    def __on_menu_item_select_object_b(self):
        if not self._tree_view:
            return
        selection: list[str] = [entry.clash_info.object_b_path for entry in self._tree_view.selection]  # type: ignore
        omni.usd.get_context(ExtensionSettings.usd_context_name).get_selection().set_selected_prim_paths(selection, True)

    def __on_menu_item_select_object_ab(self):
        if not self._tree_view:
            return
        selection = [
            path
            for entry in self._tree_view.selection  # type: ignore
            for path in [entry.clash_info.object_a_path, entry.clash_info.object_b_path]
        ]
        omni.usd.get_context(ExtensionSettings.usd_context_name).get_selection().set_selected_prim_paths(selection, True)

    def _on_markup_callback(self):
        try:
            from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore

            ext_instance = get_markup_instance()
            name = ext_instance.current_markup.name
            parts = name.split("_")
            query_id = int(parts[1])
            overlap_id = int(parts[2])

            # Select the query
            if self._query_combo_model and self._query_combo_model.items:
                query_index = 0
                for item in self._query_combo_model.items:
                    if item.clash_query and item.clash_query.identifier == query_id:
                        self._query_combo_model.select_item_index(query_index)
                        break
                query_index += 1

            # Select the item
            if self._model:
                item = self._model.get_item_with_identifier(overlap_id)
                if item is not None and self._tree_view:
                    self._tree_view.selection = [item]

        except Exception as e:
            carb.log_error(e)

    async def create_markups(self, selection):
        """Creates markups for the selected clash items.

        Args:
            selection (list): The selected items for which to create markups.
        """
        ext_instance = None
        current_time = 0.0
        try:
            if self._progbar_create_markers:
                self._progbar_create_markers.visible = True
            current_time = omni.timeline.get_timeline_interface().get_current_time()

            from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore

            ext_instance = get_markup_instance()
            ext_instance.set_open_callback(None)
            num_total_items = len(selection)
            current_item_idx = 0
            for selected_item in selection:
                clash_info = selected_item.clash_info
                omni.timeline.get_timeline_interface().set_current_time(clash_info.start_time)
                if ExtensionSettings.clash_viewport:
                    ExtensionSettings.clash_viewport.display_clash_by_clash_info([clash_info], clash_info.start_time)
                for _ in range(10):  # Wait rendering to settle
                    await omni.kit.app.get_app().next_update_async()  # type: ignore
                current_item_idx = current_item_idx + 1
                name = f"Clash_{clash_info.query_id}_{clash_info.identifier}"
                markup = ext_instance.get_markup(name)
                if markup:
                    ext_instance.delete_markup(markup)
                ext_instance.create_markup(name)
                if self._create_markers_progress_bar_model:
                    self._create_markers_progress_bar_model.set_value(current_item_idx / num_total_items)
                ext_instance.end_edit_markup(ext_instance.editing_markup, save=True)
                for _ in range(5):  # Wait markup screenshot
                    await omni.kit.app.get_app().next_update_async()  # type: ignore
        except asyncio.CancelledError:
            pass
        except Exception as e:
            carb.log_error(e)
        finally:
            if ext_instance:
                ext_instance.set_open_callback(self._on_markup_callback)
            if self._progbar_create_markers:
                self._progbar_create_markers.visible = False
            self._create_markups_future = None
            omni.timeline.get_timeline_interface().set_current_time(current_time)

    def cancel_markers(self):
        """Cancels the creation of markers."""
        if self._create_markups_future:
            self._create_markups_future.cancel()
            self._create_markups_future = None

    def __on_menu_item_create_markup(self):
        if not self._tree_view:
            return
        self._create_markups_future = asyncio.ensure_future(self.create_markups(self._tree_view.selection))

    def _copy_each_selected_row_to_clipboard(self, include_clash_id: bool = True, include_column_names: bool = True):
        if not self._tree_view:
            return
        string = ""
        if include_column_names:
            if include_clash_id:
                string += "Clash ID\t"
            string += "\t".join(col_def.name for col_def in self._delegate.columns.values()) + "\n" # type: ignore
        for selected_item in self._tree_view.selection:  # type: ignore
            if include_clash_id:
                string += selected_item.clash_info.overlap_id + "\t"
            for row_model in selected_item.row_models:
                string += row_model.as_string + "\t"
            string += "\n"
        omni.kit.clipboard.copy(string)

    def _copy_each_selected_item_to_clipboard(self, custom_action_fnc: Callable[[ClashInfo], str]):
        if not self._tree_view:
            return
        string = ""
        for selected_item in self._tree_view.selection:  # type: ignore
            string += custom_action_fnc(selected_item.clash_info)
            string += "\n"
        omni.kit.clipboard.copy(string)

    def _limit_view_to_object(self, object_name: str):
        if not self._search_model:
            return
        self._search_model.set_value(
            whole_string_encapsulation_ctrl_chars + object_name + whole_string_encapsulation_ctrl_chars
        )
        self.set_search_text(self._search_model)

    def _serialize_clash_info_to_json(self):
        """Opens a file dialog to serializes clash detection result(s) to a JSON file."""
        def do_json_serialization(file_path: str) -> bool:
            if not self._tree_view or not ExtensionSettings.clash_data:
                return False
            from omni.physxclashdetectioncore.utils import to_json_str_safe
            cis = []
            for entry in self._tree_view.selection:  # type: ignore
                clash_info = ExtensionSettings.clash_data.find_all_overlaps_by_overlap_id(
                    [entry.clash_info.identifier],
                    True
                )
                for ci in clash_info.values():
                    cis.append(ci.serialize_to_dict())
            json_str = to_json_str_safe(cis, indent=4)
            if json_str and len(json_str) > 0:
                json_bytes = json_str.encode("utf-8")
                if json_bytes and len(json_bytes) > 0:
                    if omni.client.write_file(file_path, json_bytes) == omni.client.Result.OK:  # type: ignore
                        carb.log_info(f"Successfully wrote JSON file to '{file_path}'.")
                        return True
            return False

        pick_target_file(
            "Save Full Clash Detection Results to JSON file",
            [("*.json", "JSON Files"), ("*", "All Files")],
            ".json",
            lambda file_path: (
                show_notification("Errors encountered, see log for error details.", True)
                if not do_json_serialization(file_path)
                else None
            )
        )

    def _deserialize_clash_info_from_json(self):
        """Opens a file dialog to deserializes clash detection result(s) from a JSON file."""
        def do_json_deserialization(file_path: str) -> bool:
            if not self._model or not self._tree_view or not ExtensionSettings.clash_data:
                return False

            from omni.physxclashdetectioncore.utils import from_json_str_safe
            result, version, content = omni.client.read_file(file_path)  # type: ignore
            if result != omni.client.Result.OK:  # type: ignore
                carb.log_error(f"ClashInfo Import Failed: Failed loading JSON file from '{file_path}'.")
                return False

            json_str = memoryview(content).tobytes().decode("utf-8")
            if len(json_str) == 0:
                carb.log_error(f"ClashInfo Import Failed: Loaded JSON file '{file_path}' is empty.")
                return False

            r = True
            loaded_clash_infos = from_json_str_safe(json_str)
            new_rows = []
            for clash_info_dict in loaded_clash_infos:
                new_clash_info = ClashInfo.deserialize_from_dict(clash_info_dict)
                if not new_clash_info:
                    carb.log_error("Errors reported while importing clash info!")
                    r = False
                    continue  # continue error despite unsuccessful deserializaation

                new_id = -1
                update_row = False
                if new_clash_info.identifier != -1:  # try to update the clash info with this identifier in the database
                    if ExtensionSettings.clash_data.update_overlap(new_clash_info, True, False) > 0:
                        new_id = new_clash_info.identifier
                        update_row = True

                if new_id == -1:  # insert the clash info into the database
                    if ExtensionSettings.clash_query:
                        new_clash_info._query_id = ExtensionSettings.clash_query.identifier  # assign it to current query
                    new_id = ExtensionSettings.clash_data.insert_overlap(new_clash_info, True, True, False)

                if new_id > 0:  # retrieve the clash info from the database
                    new_clash_info = ExtensionSettings.clash_data.find_all_overlaps_by_overlap_id([new_id], True)
                    if len(new_clash_info) > 1:
                        carb.log_error("There are more ClashInfo items with the same id!")
                    for clash_info in new_clash_info.values():
                        if update_row:
                            # Find existing row with matching clash info
                            clash_key = (clash_info.identifier, clash_info.query_id)
                            existing_row = next(
                                (row for row in self._model.children
                                 if (row.clash_info.identifier, row.clash_info.query_id) == clash_key),
                                None
                            )
                            # Update existing row if found
                            if existing_row:
                                existing_row._clash_info = clash_info
                                self._model.update_row(existing_row)
                                new_rows.append(existing_row)
                        else:
                            new_row = self._model.add_row(clash_info, True)
                            new_rows.append(new_row)
                else:
                    carb.log_error("Error inserting new clash info!")
                    r = False

            self._tree_view.selection = new_rows
            if ExtensionSettings.clash_data:
                ExtensionSettings.clash_data.commit()
            return r

        pick_target_file(
            "Load Full Clash Detection Results from JSON file",
            [("*.json", "JSON Files"), ("*", "All Files")],
            ".json",
            lambda file_path: (
                show_notification("Errors encountered, see log for error details.", True)
                if not do_json_deserialization(file_path)
                else None
            ),
            "Import"
        )

    def _compute_depth(
        self,
        depth_fnc: Callable[
            [
                ClashDetection,
                ClashInfo,
                ClashFrameInfo,
                int,
                Sdf.Path,
                Gf.Matrix4d,
                Sdf.Path,
                Gf.Matrix4d,
                ClashQuery,
                Optional[Tuple[float, float, float]],
            ],
            None
        ],
        finalize_fnc: Optional[Callable[[ClashInfo], None]],
        clash_detect: ClashDetection,
        ci: ClashInfo,
        clash_query: ClashQuery,
        clash_data: ClashData,
        stage: Usd.Stage,
        current_time: float,
        all_clashing_frames: bool,
        dir: Optional[Tuple[float, float, float]],
        clash_num: int,
    ) -> bool:
        """
        Compute penetration depth(s) for a single clash entry, and update the database and clash info accordingly.

        This method fetches the frame information and corresponding USD prims for the given clash,
        then applies the supplied `depth_fnc` to compute the relevant depth information,
        either for all clashing frames or the frame closest to the current timeline time,
        and updates both the in-memory and database representations.

        Args:
            depth_fnc (Callable[
                [
                    ClashDetection,
                    ClashInfo,
                    ClashFrameInfo,
                    int,
                    Sdf.Path,
                    Gf.Matrix4d,
                    Sdf.Path,
                    Gf.Matrix4d,
                    ClashQuery,
                    Optional[Tuple[float, float, float]],
                ],
                None
            ]): Function to compute depth information per frame.
            finalize_fnc (Optional[Callable[[ClashInfo], None]]): Post-processing function for the clash info after depths are computed.
            clash_detect (ClashDetection): Instance of the clash detection API.
            ci (ClashInfo): Clash info object with object paths and frame data.
            clash_query (ClashQuery): Query/filter parameters for clash detection.
            clash_data (ClashData): Data/model access object for database I/O.
            stage (Usd.Stage): The USD stage used to access objects.
            current_time (float): Current timeline time, for picking closest frame if needed.
            all_clashing_frames (bool): Whether to process all clashing frames or just the closest one.
            dir (Optional[Tuple[float, float, float]]): Direction vector for depth computation (if needed by depth_fnc).
            clash_num (int): Display/UI index number of this clash.

        Returns:
            bool: True if depths were successfully computed and stored, False otherwise.
        """
        if not depth_fnc:
            carb.log_error(f"Clash #{clash_num}: Depth computation function is not set!")
            return False

        if not ci.object_a_path or not ci.object_b_path:
            carb.log_error(f"Clash #{clash_num}: Object A or Object B path is not set!")
            return False

        # load needed frame info items into memory
        ci.clash_frame_info_items = clash_data.fetch_clash_frame_info_by_clash_info_id(
            ci.identifier
        )
        if ci.clash_frame_info_items is None or len(ci.clash_frame_info_items) == 0:
            carb.log_error(f"Clash #{clash_num}: Clash frame info items is empty!")
            return False

        if all_clashing_frames:
            for cfi in ci.clash_frame_info_items:
                matrix_a = get_prim_matrix(stage, ci.object_a_path, cfi.timecode)
                matrix_b = get_prim_matrix(stage, ci.object_b_path, cfi.timecode)

                if not matrix_a or not matrix_b:
                    carb.log_error(f"Clash #{clash_num}: Failed to get matrix for object A or B at timecode {cfi.timecode:.3f}!")
                    continue

                depth_fnc(
                    clash_detect,
                    ci, cfi,
                    clash_num,
                    Sdf.Path(ci.object_a_path), matrix_a, Sdf.Path(ci.object_b_path), matrix_b, clash_query,
                    dir
                )
        else:
            # Find the frame index in ci.frames that has the closest time to current_time
            ci_frame_index = ci.get_frame_info_index_by_timecode(current_time)
            closest_frame = ci.clash_frame_info_items[ci_frame_index]
            carb.log_info(f"Closest clashing frame to current time {current_time} is frame#{ci_frame_index} at timecode {closest_frame.timecode} -> adjusting timeline to this timecode if necessary")
            timecode = closest_frame.timecode
            omni.timeline.get_timeline_interface().set_current_time(timecode)

            matrix_a = get_prim_matrix(stage, ci.object_a_path, timecode)
            matrix_b = get_prim_matrix(stage, ci.object_b_path, timecode)

            if not matrix_a or not matrix_b:
                carb.log_error(f"Clash #{clash_num}: Failed to get matrix for object A or B at timecode {timecode:.3f}!")

            depth_fnc(
                clash_detect,
                ci, closest_frame,
                clash_num,
                Sdf.Path(ci.object_a_path), matrix_a, Sdf.Path(ci.object_b_path), matrix_b, clash_query,
                dir
            )

        if finalize_fnc:
            finalize_fnc(ci)

        # serialize the results
        if clash_data.update_overlap(ci, True, False) > 0:
            clash_data.commit()
            # Keep only the first frame in ci.clash_frame_info_items
            ci.clash_frame_info_items = [ci.clash_frame_info_items[0]]
        else:
            carb.log_error(f"Clash #{clash_num} failed to update!")
            return False

        return True

    async def _run_depth_computation(
        self,
        depth_fnc: Callable[
            [
                ClashDetection,
                ClashInfo,
                ClashFrameInfo,
                int,
                Sdf.Path,
                Gf.Matrix4d,
                Sdf.Path,
                Gf.Matrix4d,
                ClashQuery,
                Optional[Tuple[float, float, float]],
            ],
            None
        ],
        finalize_fnc: Optional[Callable[[ClashInfo], None]],
        all_clashing_frames: bool,
        dir: Optional[Tuple[float, float, float]]
    ):
        """
        Run depth computations for selected clash entries asynchronously, updating data and UI.

        For each selected clash, runs `_compute_depth` using the provided functions and arguments.
        Handles progress reporting, error counting, user cancelation, and asynchronous UI updates.

        The behavior of the depth computation depends on the depth function and direction argument:
            - If `dir` is None, computes penetration depth(s) for all principal directions and saves results to the DB.
            - If `dir` is a vector, computes penetration depth and applies depenetration transformation to USD.
        After processing all, updates the UI and notifies the user of status.

        Args:
            depth_fnc (Callable[
                [
                    ClashDetection,
                    ClashInfo,
                    ClashFrameInfo,
                    int,
                    Sdf.Path,
                    Gf.Matrix4d,
                    Sdf.Path,
                    Gf.Matrix4d,
                    ClashQuery,
                    Optional[Tuple[float, float, float]],
                ],
                None
            ]): Function to compute depth information per frame.
            finalize_fnc (Optional[Callable[[ClashInfo], None]]): Post-processing function for the clash info after depths are computed.
            all_clashing_frames (bool): Whether to process all clashing frames or only the closest frame.
            dir (Optional[Tuple[float, float, float]]): Direction for depenetration. If None, all axes are used.

        Returns:
            None
        """
        if (
            not depth_fnc
            or not self._tree_view
            or not self._delegate
            or not self._clash_detect
            or not self._model
            or not ExtensionSettings.clash_data
            or not ExtensionSettings.clash_query
        ):
            return

        stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
        if not stage:
            return

        error_count = 0
        canceled = False
        tree_selection = self._tree_view.selection
        item_count = len(tree_selection)
        clash_query = ExtensionSettings.clash_query
        clash_data = ExtensionSettings.clash_data
        current_time = omni.timeline.get_timeline_interface().get_current_time()
        clash_detect = self._clash_detect

        self.update_ui()

        try:
            for idx, selection in enumerate(tree_selection):  # type: ignore
                if self._cancel_processing:
                    canceled = True
                    break

                if self._progress_window_label:
                    self._progress_window_label.text = f"Processing clash #{selection.row_num}..."

                progress = (idx + 1) / item_count
                if self._progress_bar_model:
                    self._progress_bar_model.set_value(progress)

                if selection.clash_info:
                    if not self._compute_depth(
                        depth_fnc,
                        finalize_fnc,
                        clash_detect,
                        selection.clash_info,
                        clash_query,
                        clash_data,
                        stage,
                        current_time,
                        all_clashing_frames,
                        dir,
                        selection.row_num
                    ):
                        error_count += 1

                    # Update row in the results list view
                    self._model.update_row(selection)

                    await omni.kit.app.get_app().next_update_async()  # type: ignore

        except asyncio.CancelledError:
            canceled = True
        except Exception as e:
            carb.log_error(f"Depth computation exception: {e}")
            error_count += 1
        finally:
            self._clash_detect_task = None
            self._cancel_processing = False
            self._tree_selection_changed(None)
            self.update_ui()

        if canceled:
            show_notification("Canceled by user.", True)
        else:
            if error_count > 0 or (ExtensionSettings.show_prompts and len(tree_selection) > 0):
                show_notification(
                    f"{len(tree_selection)} items processed with {error_count} errors.",
                    error_count > 0
                )

    def _start_max_local_depth_task(self,all_frames: bool = False):
        """
        Schedule an asynchronous task to compute the maximum local penetration depth.

        Args:
            all_frames (bool): If True, computes depths for all clashing frames. Otherwise, just the closest.
        """
        def depth_fnc(
            clash_detect: ClashDetection,
            ci: ClashInfo,
            cfi: ClashFrameInfo,
            clash_num: int,
            object_a_path: Sdf.Path,
            matrix_a: Gf.Matrix4d,
            object_b_path: Sdf.Path,
            matrix_b: Gf.Matrix4d,
            clash_query: ClashQuery,
            dir: Optional[Tuple[float, float, float]]
        ):
            """Compute and record the max local penetration depth for a single frame."""
            cfi.max_local_depth = clash_detect.compute_max_local_depth(
                object_a_path, matrix_a,
                object_b_path, matrix_b,
                clash_query
            )
            if ExtensionSettings.debug_logging:
                carb.log_info(f"Clash #{clash_num}, frame at timecode {cfi.timecode:.3f}: Max local depth: {cfi.max_local_depth:.3f}")

        def finalize_fnc(ci: ClashInfo):
            """After all frames are computed, set the clash's overall max local depth from per-frame values."""
            max_local_depth = -1.0
            for cfi in ci.clash_frame_info_items:
                if cfi.max_local_depth > max_local_depth:
                    max_local_depth = cfi.max_local_depth
            ci.max_local_depth = max_local_depth

        self._clash_detect_task = asyncio.ensure_future(
            self._run_depth_computation(
                depth_fnc,
                finalize_fnc,
                all_frames,
                None
            )
        )

    def _start_penetration_depth_task(self, dir: Optional[Tuple[float, float, float]], all_frames: bool = False):
        """
        Schedule an asynchronous task to compute penetration depths and, optionally, depenetrate.

        Args:
            dir (Optional[Tuple[float, float, float]]): If None, compute depths for all axis directions (+/-X, +/-Y, +/-Z).
                If a direction is given, compute depth and perform depenetration for that direction.
            all_frames (bool): If True, computes depths for all clashing frames. Otherwise, just the closest.
        """
        def depth_fnc(
            clash_detect: ClashDetection,
            ci: ClashInfo,
            cfi: ClashFrameInfo,
            clash_num: int,
            object_a_path: Sdf.Path,
            matrix_a: Gf.Matrix4d,
            object_b_path: Sdf.Path,
            matrix_b: Gf.Matrix4d,
            clash_query: ClashQuery,
            dir: Optional[Tuple[float, float, float]]
        ):
            """Compute penetration depth(s) for a single frame along principal axes, or apply depenetration."""

            def penetration_depth(dir: Tuple[float, float, float]) -> Any:
                """Compute penetration/depenetration information along a certain direction."""
                dep_data = clash_detect.compute_penetration_depth(
                    object_a_path, matrix_a,
                    object_b_path, matrix_b,
                    clash_query,
                    dir
                )
                if dep_data is None:
                    carb.log_error(f"Clash #{clash_num}: direction {dir}: Depenetration failed!")
                    return None
                if ExtensionSettings.debug_logging:
                    carb.log_info(f"Clash #{clash_num}, frame at timecode {cfi.timecode:.3f}: direction {dep_data.dir}: Depenetration depth: {dep_data.depth:.3f}")
                return dep_data

            if dir is None:
                # Compute penetration depths for all 6 Cartesian directions and populate on clash frame object.
                pd_px = penetration_depth((1.0, 0.0, 0.0))
                pd_nx = penetration_depth((-1.0, 0.0, 0.0))
                pd_py = penetration_depth((0.0, 1.0, 0.0))
                pd_ny = penetration_depth((0.0, -1.0, 0.0))
                pd_pz = penetration_depth((0.0, 0.0, 1.0))
                pd_nz = penetration_depth((0.0, 0.0, -1.0))

                cfi.penetration_depth_px = pd_px.depth if pd_px is not None else -1.0
                cfi.penetration_depth_nx = pd_nx.depth if pd_nx is not None else -1.0
                cfi.penetration_depth_py = pd_py.depth if pd_py is not None else -1.0
                cfi.penetration_depth_ny = pd_ny.depth if pd_ny is not None else -1.0
                cfi.penetration_depth_pz = pd_pz.depth if pd_pz is not None else -1.0
                cfi.penetration_depth_nz = pd_nz.depth if pd_nz is not None else -1.0
            else:
                # For a specific direction, perform penetration and a depenetration move of object A.
                pd = penetration_depth((-dir[0], -dir[1], -dir[2]))  # reverse direction for depenetration

                # Depenetrate
                dir_vect = Gf.Vec3d(*pd.dir)
                dir_vect.Normalize()
                dir_vect *= pd.depth
                disp_mtx = matrix_a;
                trans = disp_mtx.ExtractTranslation();
                trans -= dir_vect;
                disp_mtx.SetTranslateOnly(trans);

                # Execute undoable transform
                omni.kit.commands.execute(
                    "TransformPrimCommand",
                    path=object_a_path,
                    new_transform_matrix=disp_mtx
                )
                # non-undoable transform
                # xformable = UsdGeom.Xformable(object_a_prim)
                # op = xformable.MakeMatrixXform()
                # op.Set(disp_mtx)

        def finalize_fnc(ci: ClashInfo):
            """After depths are computed per frame, aggregate max penetration along each axis in the clash info."""
            max_px_depth = -1.0
            max_nx_depth = -1.0
            max_py_depth = -1.0
            max_ny_depth = -1.0
            max_pz_depth = -1.0
            max_nz_depth = -1.0
            for cfi in ci.clash_frame_info_items:
                if cfi.penetration_depth_px > max_px_depth:
                    max_px_depth = cfi.penetration_depth_px
                if cfi.penetration_depth_nx > max_nx_depth:
                    max_nx_depth = cfi.penetration_depth_nx
                if cfi.penetration_depth_py > max_py_depth:
                    max_py_depth = cfi.penetration_depth_py
                if cfi.penetration_depth_ny > max_ny_depth:
                    max_ny_depth = cfi.penetration_depth_ny
                if cfi.penetration_depth_pz > max_pz_depth:
                    max_pz_depth = cfi.penetration_depth_pz
                if cfi.penetration_depth_nz > max_nz_depth:
                    max_nz_depth = cfi.penetration_depth_nz
            ci.penetration_depth_px = max_px_depth
            ci.penetration_depth_nx = max_nx_depth
            ci.penetration_depth_py = max_py_depth
            ci.penetration_depth_ny = max_ny_depth
            ci.penetration_depth_pz = max_pz_depth
            ci.penetration_depth_nz = max_nz_depth

        self._clash_detect_task = asyncio.ensure_future(
            self._run_depth_computation(
                depth_fnc,
                finalize_fnc,
                all_frames,
                dir
            )
        )

    def _add_depth_menu_items(self):
        """
        Add menu items for various depth and depenetration operations.

        This method installs menu commands that let users:
          - Compute the maximum local penetration depth for the current frame or all clashing frames.
          - Compute penetration depths along each Cartesian axis for the current frame or all frames.
          - In development mode, apply depenetration transforms along each axis (+X, -X, +Y, -Y, +Z, -Z).
        """
        task_running = self._clash_detect_task is not None and not self._clash_detect_task.done()

        ui.MenuItem(
            "Compute Max Local Depth for current frame",
            triggered_fn=lambda: self._start_max_local_depth_task(False),
            enabled=not task_running
        )
        ui.MenuItem(
            "Compute Max Local Depth for all clashing frames",
            triggered_fn=lambda: self._start_max_local_depth_task(True),
            enabled=not task_running
        )

        ui.MenuItem(
            "Compute Penetration Depths for current frame",
            triggered_fn=lambda: self._start_penetration_depth_task(None),
            enabled=not task_running
        )
        ui.MenuItem(
            "Compute Penetration Depths for all clashing frames",
            triggered_fn=lambda: self._start_penetration_depth_task(None, True),
            enabled=not task_running
        )
        # dev stuff
        if ExtensionSettings.development_mode:
            ui.MenuItem(
                "Depenetrate +X",
                triggered_fn=lambda: self._start_penetration_depth_task((1.0, 0.0, 0.0)),
                enabled=not task_running
            )
            ui.MenuItem(
                "Depenetrate -X",
                triggered_fn=lambda: self._start_penetration_depth_task((-1.0, 0.0, 0.0)),
                enabled=not task_running
            )
            ui.MenuItem(
                "Depenetrate +Y",
                triggered_fn=lambda: self._start_penetration_depth_task((0.0, 1.0, 0.0)),
                enabled=not task_running
            )
            ui.MenuItem(
                "Depenetrate -Y",
                triggered_fn=lambda: self._start_penetration_depth_task((0.0, -1.0, 0.0)),
                enabled=not task_running
            )
            ui.MenuItem(
                "Depenetrate +Z",
                triggered_fn=lambda: self._start_penetration_depth_task((0.0, 0.0, 1.0)),
                enabled=not task_running
            )
            ui.MenuItem(
                "Depenetrate -Z",
                triggered_fn=lambda: self._start_penetration_depth_task((0.0, 0.0, -1.0)),
                enabled=not task_running
            )

    def show_context_menu(self):
        if not self._tree_view or not self._context_menu:
            return

        self._context_menu.clear()
        markup_instance = None
        try:
            from omni.kit.markup.core import get_instance as get_markup_instance  # type: ignore

            markup_instance = get_markup_instance()
        except:
            pass

        empty_menu = False
        with self._context_menu:  # type: ignore
            num_selected = len(self._tree_view.selection)
            if num_selected == 1:
                clash_info = self._tree_view.selection[0].clash_info
                if clash_info:
                    def get_obj_name(full_path: str) -> str:
                        last_slash_index = full_path.rfind("/")
                        if last_slash_index != -1:
                            return full_path[last_slash_index + 1:]
                        return full_path
                    obj_a_name = get_obj_name(clash_info.object_a_path)
                    obj_b_name = get_obj_name(clash_info.object_b_path)
                    if clash_info.num_records > 1:
                        ui.MenuItem("Inspect Clashing Frames on Timeline", triggered_fn=self._inspect_clashing_frames)
                    else:
                        ui.MenuItem("Inspect Clashing Frame", triggered_fn=self._inspect_clashing_frames)
                    ui.Separator()
                    ui.MenuItem(
                        "Generate Clash Mesh",
                        enabled=self._clash_bake_view.can_generate_clash_mesh(),
                        triggered_fn=self.generate_clash_meshes
                    )
                    ui.MenuItem(
                        "Clear Clash Mesh",
                        enabled=self._clash_bake_view.can_generate_clash_mesh(),
                        triggered_fn=self.clear_clash_meshes
                    )
                    ui.Separator()
                    self._add_depth_menu_items()
                    ui.Separator()
                    ui.MenuItem(f"Select Object A ({obj_a_name})", triggered_fn=self.__on_menu_item_select_object_a)
                    ui.MenuItem(f"Select Object B ({obj_b_name})", triggered_fn=self.__on_menu_item_select_object_b)
                    ui.MenuItem("Select Object A and B", triggered_fn=self.__on_menu_item_select_object_ab)
                    ui.Separator()
                    if markup_instance:
                        ui.MenuItem("Create Markup", triggered_fn=self.__on_menu_item_create_markup)
                    else:
                        ui.MenuItem("Create Markup [needs omni.kit.markup.core]", enabled=False)
                    ui.Separator()
                    ui.MenuItem(
                        f"Filter View to Only Show Object A ({obj_a_name}) Clashes",
                        triggered_fn=lambda: self._limit_view_to_object(clash_info.object_a_path),
                    )
                    ui.MenuItem(
                        f"Filter View to Only Show Object B ({obj_b_name}) Clashes",
                        triggered_fn=lambda: self._limit_view_to_object(clash_info.object_b_path),
                    )
                    ui.Separator()
                    ui.MenuItem(
                        "Copy Selected Clash ID to Clipboard",
                        triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.overlap_id),
                    )
                    ui.MenuItem(
                        f"Copy Selected Object A ({obj_a_name}) Path to Clipboard",
                        triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.object_a_path),
                    )
                    ui.MenuItem(
                        f"Copy Selected Object B ({obj_b_name}) Path to Clipboard",
                        triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.object_b_path),
                    )
                    ui.MenuItem(
                        "Copy Selected Row to Clipboard",
                        triggered_fn=self._copy_each_selected_row_to_clipboard
                    )
            elif num_selected > 1:
                ui.MenuItem(
                    "Generate Clash Meshes",
                    enabled=self._clash_bake_view.can_generate_clash_mesh(),
                    triggered_fn=self.generate_clash_meshes
                )
                ui.MenuItem(
                    "Clear Clash Meshes",
                    enabled=self._clash_bake_view.can_generate_clash_mesh(),
                    triggered_fn=self.clear_clash_meshes
                )
                ui.Separator()
                self._add_depth_menu_items()
                ui.Separator()
                ui.MenuItem(f"Select {num_selected} Objects A", triggered_fn=self.__on_menu_item_select_object_a)
                ui.MenuItem(f"Select {num_selected} Objects B", triggered_fn=self.__on_menu_item_select_object_b)
                ui.MenuItem(f"Select {num_selected} Objects A and B", triggered_fn=self.__on_menu_item_select_object_ab)
                ui.Separator()
                if markup_instance:
                    ui.MenuItem(f"Create {num_selected} Markups", triggered_fn=self.__on_menu_item_create_markup)
                else:
                    ui.MenuItem(f"Create {num_selected} Markups [needs omni.kit.markup.core]", enabled=False)
                ui.Separator()
                ui.MenuItem(
                    f"Copy {num_selected} Clash IDs to Clipboard",
                    triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.overlap_id),
                )
                ui.MenuItem(
                    f"Copy {num_selected} Selected Object A Paths to Clipboard",
                    triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.object_a_path),
                )
                ui.MenuItem(
                    f"Copy {num_selected} Selected Object B Paths to Clipboard",
                    triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda ci: ci.object_b_path),
                )
                ui.MenuItem(
                    f"Copy {num_selected} Selected Rows to Clipboard",
                    triggered_fn=self._copy_each_selected_row_to_clipboard,
                )
            else:
                empty_menu = True

            # dev stuff
            if ExtensionSettings.development_mode:
                ui.Separator("Dev Menu")
                ui.MenuItem(
                    "Serialize Selected Full Clash Info to JSON...", triggered_fn=self._serialize_clash_info_to_json
                )
                ui.MenuItem(
                    "Deserialize Full Clash Info from JSON...", triggered_fn=self._deserialize_clash_info_from_json
                )
                empty_menu = False

        if not empty_menu and self._context_menu:
            self._context_menu.show()

    def _tree_view_on_click(self, x, y, b, m):
        # mouse right click on empty space
        if b == 1 and self._tree_view and self._context_menu and not self._context_menu.shown:
            self._tree_view.selection = []
            self.show_context_menu()

    def _tree_view_on_item_click(self, button, item):
        if button == 1 and self._tree_view:
            # If the selection doesn't contain the node we click, we should clear the selection and select the node.
            if item not in self._tree_view.selection:
                self._tree_view.selection = [item]
            self.show_context_menu()

    async def _update_selection_next_frame(self, ci_selection):
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        # We MUST read time after next_update_async to get the actual "current_time"!
        current_time = omni.timeline.get_timeline_interface().get_current_time()
        if ExtensionSettings.clash_selection:
            ExtensionSettings.clash_selection.update_selection(current_time, ci_selection)
        if self._delegate:
            self._delegate.hide_all_active_editors()
        self.update_ui()

    def _tree_selection_changed(self, items):
        if not self._tree_view or not self._delegate:
            return

        ci_selection = [selection.clash_info for selection in self._tree_view.selection]  # type: ignore

        if len(self._tree_view.selection) > 0:
            try:
                from omni.physxclashdetectionviewport import ClashViewportSettings
                display_limit = carb.settings.get_settings().get_as_int(ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT)
            except:
                display_limit = 1
            index = 0
            for selection in self._tree_view.selection: # type: ignore
                if index >= display_limit:
                    break
                index += 1
                ci = selection.clash_info
                omni.timeline.get_timeline_interface().set_current_time(ci.start_time)

                # free frame inspection memory
                if self._inspecting_ci is not None:
                    self._inspecting_ci.clash_frame_info_items = None
                    self._inspecting_ci = None

                # load first clashing frame if not loaded already
                if not ci.clash_frame_info_items:
                    if ExtensionSettings.clash_data:
                        ci.clash_frame_info_items = ExtensionSettings.clash_data.fetch_clash_frame_info_by_clash_info_id(
                            ci.identifier, num_frames_to_load=1
                        )

        self._delegate.hide_all_active_editors()
        self.update_ui()
        asyncio.ensure_future(self._update_selection_next_frame(ci_selection))