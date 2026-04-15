# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Callable, Optional, List
from functools import partial
import carb
import carb.settings
import omni.ui as ui
import omni.kit.app
import omni.kit.clipboard
import omni.client
import omni.usd
from omni.kit.widget.searchfield import SearchField
from omni.kit.property.usd.relationship import RelationshipTargetPicker
from omni.kit.widget.prompt import Prompt
import omni.kit.actions.core
from omni.kit.hotkeys.core import get_hotkey_registry, HotkeyFilter
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.utils import to_json_str_safe, from_json_str_safe
from .clash_query_delegate import ClashQueryTableDelegate
from .clash_query_viewmodel import ClashQueryTableColumnEnum, ClashQueryTableModel, ClashQueryTableRowItem
from .clash_query_stats_window import ClashQueryStatsWindow
from .clash_detect_settings import ClashDetectionSettings, ClashDetectionSettingsUI
from .settings import ExtensionSettings
from .styles import Styles
from .utils import pick_target_file, show_notification

__all__ = []


class ClashQueryPropertyModel:
    """A model for managing the properties of a clash query.

    This class provides methods to create and save properties of a clash query. It supports operations such as creating models from a clash query and saving models back to a clash query.
    """

    def __init__(self):
        """Initializes the ClashQueryPropertyModel instance."""
        self._query_name_model = None
        self._query_comment_model = None
        self._object_a_path_model = None
        self._object_b_path_model = None

    @property
    def query_name_model(self):
        """Gets the model for the query name.

        Returns:
            ui.SimpleStringModel: The model for query name.
        """
        return self._query_name_model

    @property
    def query_comment_model(self):
        """Gets the model for the query comment.

        Returns:
            ui.SimpleStringModel: The model for query comment.
        """
        return self._query_comment_model

    @property
    def object_a_path_model(self):
        """Gets the model for the object A path.

        Returns:
            ui.SimpleStringModel: The model for object A path.
        """
        return self._object_a_path_model

    @property
    def object_b_path_model(self):
        """Gets the model for the object B path.

        Returns:
            ui.SimpleStringModel: The model for object B path.
        """
        return self._object_b_path_model

    def create_from(self, clash_query: ClashQuery, settings: Optional[ClashDetectionSettings] = None) -> ClashDetectionSettings:
        """
        Initializes the models for the properties of a clash query and loads clash detection settings.

        This method updates (or creates, if necessary) the property models for query name, comment,
        object A path, and object B path according to the given `clash_query`.
        It also loads the clash detection settings from the provided query into the `settings` object.

        Args:
            clash_query (ClashQuery): The clash query instance from which to extract properties and clash detection settings.
            settings (Optional[ClashDetectionSettings]): An optional existing settings object to update. If None, a new instance is created.

        Returns:
            ClashDetectionSettings: The updated or newly created settings instance with values from the provided `clash_query`.
        """
        if not settings:
            settings = ClashDetectionSettings()

        if not self._query_name_model:
            self._query_name_model = ui.SimpleStringModel(clash_query.query_name)
        else:
            self._query_name_model.set_value(clash_query.query_name)

        if not self._query_comment_model:
            self._query_comment_model = ui.SimpleStringModel(clash_query.comment)
        else:
            self._query_comment_model.set_value(clash_query.comment)

        if not self._object_a_path_model:
            self._object_a_path_model = ui.SimpleStringModel(clash_query.object_a_path)
        else:
            self._object_a_path_model.set_value(clash_query.object_a_path)

        if not self._object_b_path_model:
            self._object_b_path_model = ui.SimpleStringModel(clash_query.object_b_path)
        else:
            self._object_b_path_model.set_value(clash_query.object_b_path)

        if len(clash_query.clash_detect_settings) > 0:
            settings.load_values_from_dict(clash_query.clash_detect_settings)
        else:
            settings.reset_settings_to_default()

        return settings

    def save_to(self, clash_query: ClashQuery, settings: ClashDetectionSettings):
        """Saves the current model to a clash query.

        Args:
            clash_query (ClashQuery): The clash query to save to.
            settings (ClashDetectionSettings): The settings to be saved.
        """
        if self._query_name_model:
            clash_query.query_name = self._query_name_model.as_string
        if self._query_comment_model:
            clash_query.comment = self._query_comment_model.as_string
        if self._object_a_path_model:
            clash_query.object_a_path = self._object_a_path_model.as_string
        if self._object_b_path_model:
            clash_query.object_b_path = self._object_b_path_model.as_string
        clash_query.clash_detect_settings = settings.convert_values_to_dict()


class ClashQueryWindow(ui.Window):
    """A class for managing the Clash Query window.

    This class provides a user interface for creating, duplicating, deleting,
    and editing clash queries. It allows users to manage clash detection
    settings and view the results in a structured manner.

    Args:
        title (str): The title of the window.
        width (int): The width of the window.
        height (int): The height of the window.
        position_x (int): The x-coordinate of the window's position.
        position_y (int): The y-coordinate of the window's position.
    """

    SPLITTER_OFFSET = 400  # NOTE: this is offset from the right edge of the query window, not left
    LEFT_PANE_MIN_WIDTH = 150
    RIGHT_PANE_MIN_WIDTH = 24

    def __init__(self, title: str = "", width=1020, height=682, position_x=45, position_y=27) -> None:
        """Initialize the ClashQueryWindow."""
        window_title = title if title else "Clash Query Management"
        super().__init__(window_title, width=width, height=height, position_x=position_x, position_y=position_y)
        self._tree_view = None
        self._model = None
        self._delegate = None
        self._property_splitter = None
        self._window_size = (width, height)  # Set to default window size if window not specified
        self._splitter_offset = self.SPLITTER_OFFSET
        self.frame.set_style(Styles.CLASH_WND_STYLE)
        self.frame.set_build_fn(self.build_window)
        self.set_width_changed_fn(self._on_window_width_changed)
        self.set_visibility_changed_fn(self._on_window_visibility_changed)
        self._query_changed_fnc: Optional[Callable[[ClashQueryTableModel, Optional[ClashQuery]], None]] = None
        self._clash_detect_settings = ClashDetectionSettings()
        self._selected_query_for_edit: Optional[ClashQueryTableRowItem] = None
        self._selected_query_property = ClashQueryPropertyModel()
        self._create_new_query_button = None
        self._delete_selected_query_button = None
        self._duplicate_selected_query_button = None
        self._export_selected_query_button = None
        self._import_query_from_file_button = None
        self._save_query_properties_button = None
        self._property_frame = None
        self.__model_changed_sub = None
        self._search_field = None
        self._context_menu = None
        self._settings_menu = None
        self._stats_summary_window = None
        self._save_current_query_on_selection_change = True
        self._timecodes_in_frames = False

        carb.settings.get_settings().set_default_bool(
            ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE, self._save_current_query_on_selection_change
        )
        carb.settings.get_settings().set_default_bool(
            ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES, self._timecodes_in_frames
        )

        self._settings_subs = [
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE, self._query_autosave_setting_changed
            ),
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES, self._timecodes_in_frames_setting_changed
            ),
        ]

        self._query_autosave_setting_changed(
            None, carb.settings.ChangeEventType.CHANGED
        )  # fetch current value from settings

        # fetch current value
        self._timecodes_in_frames = carb.settings.get_settings().get_as_bool(
            ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES
        )
        self._clash_detect_settings.set_timecodes_in_frames(self._timecodes_in_frames)

        action_ext_id = self.__class__.__module__
        action_name = "delete_selected"
        self._delete_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.delete_query_with_prompt(),
            display_name="Delete Selected Clash Queries",
            tag="Clash Detection Query Management Window",
        )

        self._delete_hotkey = None
        if self._delete_action:
            self._delete_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "DEL",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(windows=[window_title]),  # This hotkey only takes effect when mouse in this window
            )

        # clear selection action & hotkey
        action_name = "clear_selection"
        self._clear_selection_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.clear_selection(),
            display_name="Clear Selection",
            tag="Clash Detection Query Management Window",
        )

        self._clear_selection_hotkey = None
        if self._clear_selection_action:
            self._clear_selection_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "ESCAPE",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(windows=[window_title]),  # This hotkey only takes effect when mouse in this window
            )

        # select all action & hotkey
        action_name = "select_all"
        self._select_all_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.select_all_queries(),
            display_name="Select All Queries",
            tag="Clash Detection Query Management Window",
        )

        self._select_all_hotkey = None
        if self._select_all_action:
            self._select_all_hotkey = get_hotkey_registry().register_hotkey(
                action_ext_id,
                "Ctrl+A",
                action_ext_id,
                action_name,
                filter=HotkeyFilter(windows=[window_title]),  # This hotkey only takes effect when mouse in this window
            )

    def destroy(self) -> None:
        """Destroy the ClashQueryWindow and clean up resources."""
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
        if self._search_field:
            self._search_field.destroy()
            self._search_field = None
        if self._stats_summary_window:
            self._stats_summary_window.destroy()
            self._stats_summary_window = None
        self._settings_subs = None
        self._settings_menu = None
        self._context_menu = None
        self.__model_changed_sub = None
        self._property_frame = None
        self._save_query_properties_button = None
        self._delete_selected_query_button = None
        self._duplicate_selected_query_button = None
        self._export_selected_query_button = None
        self._import_query_from_file_button = None
        self._create_new_query_button = None
        self._selected_query_property = None
        self._selected_query_for_edit = None
        if self._clash_detect_settings:
            self._clash_detect_settings.destroy()
            self._clash_detect_settings = None
        self._query_changed_fnc = None
        self._property_splitter = None
        self.visible = False
        self._tree_view = None
        if self._delegate:
            self._delegate.destroy()
            self._delegate = None
        self.set_width_changed_fn(None)  # type: ignore
        self.frame.set_build_fn(None)  # type: ignore
        if self._model:
            self._model.destroy()
            self._model = None
        super().destroy()

    def _query_autosave_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            enabled = carb.settings.get_settings().get_as_bool(ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE)
            self._save_current_query_on_selection_change = enabled

    def _timecodes_in_frames_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._timecodes_in_frames = carb.settings.get_settings().get_as_bool(
                ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES
            )
            if self._tree_view:
                sel = self._tree_view.selection
                if sel and len(sel) > 0:
                    self._tree_view.selection = []
                    if self._clash_detect_settings:
                        self._clash_detect_settings.set_timecodes_in_frames(self._timecodes_in_frames)
                    self._tree_view.selection = sel

    def subscribe_query_changed(self, query_changed_fnc: Callable[[ClashQueryTableModel, Optional[ClashQuery]], None]):
        """Subscribe to query change events.

        Args:
            query_changed_fnc (Callable[[ClashQueryTableModel, Optional[ClashQuery]], None]): Function to call on query change.
        """
        self._query_changed_fnc = query_changed_fnc

    def create_model(self):
        """Create the model for the ClashQuery table."""
        # Create model for the table
        if not self._model:
            self._model = ClashQueryTableModel()
            self.__model_changed_sub = self._model.add_item_changed_fn(self._on_model_changed)
        # Create a delegate that will help render our table
        if not self._delegate:
            self._delegate = ClashQueryTableDelegate(model=self._model, on_item_click=self._tree_view_on_item_click)

    def on_stage_event(self, event_type):
        """Handle stage events.

        Args:
            event (omni.usd.StageEventType): The stage event to be handled.
        """
        if event_type == omni.usd.StageEventType.CLOSING:
            self.reset()
        elif event_type == omni.usd.StageEventType.OPENED:
            self.load()
        elif event_type == omni.usd.StageEventType.SAVED:  # covers SAVE AS scenario
            self.update_ui(False)

    def _on_model_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem) -> None:
        if (
            self._query_changed_fnc
            and isinstance(model, ClashQueryTableModel)
        ):
            if item and not isinstance(item, ClashQueryTableRowItem):
                return

            if self._selected_query_for_edit and self._selected_query_for_edit.clash_query and self._selected_query_property:
                self._clash_detect_settings = self._selected_query_property.create_from(
                    self._selected_query_for_edit.clash_query,
                    self._clash_detect_settings
                )

            self._query_changed_fnc(model, item.clash_query if item is not None else None)

    def update_items(self, clear_selection=True):
        """Update the items in the model.

        Args:
            clear_selection (bool): Whether to clear the selection.
        """
        if self._model:
            self._model.update_items()
        self.update_ui(clear_selection)

    def reset(self):
        """Reset the ClashQueryWindow to its initial state."""
        if self._stats_summary_window:
            self._stats_summary_window.reset()
        if self._model:
            self._model.clear()
        self.update_items()

    def load(self):
        """Load the queries and populate the model."""
        self._selected_query_for_edit = None
        if not self._model or not self._delegate or not ExtensionSettings.clash_data:
            return
        if self._stats_summary_window:
            self._stats_summary_window.load()
        self._model.clear()
        queries = ExtensionSettings.clash_data.fetch_all_queries()
        if queries:
            for query in queries.values():
                self._model.add_row(query)
            self._delegate.sort(ClashQueryTableColumnEnum.QUERY_NAME, True, False)  # ascending
            self.update_items()
        else:
            self.update_ui()

    def save_edited_query(self) -> bool:
        """Save the current edits to the selected query.

        Returns:
            bool: True if the query was saved successfully.
        """
        if (
            not self._selected_query_for_edit
            or not self._selected_query_property
            or not self._model
            or not self._clash_detect_settings
            or not ExtensionSettings.clash_data
        ):
            return False
        query = self._selected_query_for_edit.clash_query
        r = False
        if query:
            self._selected_query_property.save_to(query, self._clash_detect_settings)
            r = ExtensionSettings.clash_data.update_query(query, True) == 1
            self._model.update_row(self._selected_query_for_edit)  # refresh values in currently edited row
            self._on_model_changed(self._model, self._selected_query_for_edit)
        return r

    def create_new_query(self):
        """Create a new ClashQuery and add it to the model."""
        if not self._model or not ExtensionSettings.clash_data:
            return
        new_query = ClashQuery(query_name="New Query")
        new_id = ExtensionSettings.clash_data.insert_query(new_query, True, True)
        if new_id and new_id > 0:
            new_query.query_name = f"{new_query.query_name} {new_query.identifier}"
            if ExtensionSettings.clash_data.update_query(new_query, True) == 1:
                new_row = self._model.add_row(new_query, True)
                if self._tree_view:
                    self._tree_view.selection = [new_row]

    def duplicate_query(self):
        """Duplicate the selected ClashQuery."""
        if (
            not self._model
            or not self._tree_view
            or len(self._tree_view.selection) == 0
            or not ExtensionSettings.clash_data
        ):
            return
        new_rows = []
        for s in self._tree_view.selection:  # type: ignore
            new_id = ExtensionSettings.clash_data.insert_query(s.clash_query, False, False)
            if new_id > 0:
                new_query = ExtensionSettings.clash_data.find_query(new_id)
                if new_query:
                    new_row = self._model.add_row(new_query, True)
                    new_rows.append(new_row)
        self._tree_view.selection = new_rows
        ExtensionSettings.clash_data.commit()

    def delete_query_with_prompt(self):
        """Delete with confirmation message box because the operation will also delete all associated clash entries."""
        if not self._tree_view or len(self._tree_view.selection) == 0:
            return
        if ExtensionSettings.show_prompts:
            Prompt(
                "Delete Query",
                "Delete selected queries?\n\nPlease note that all associated clashes will also be deleted!",
                ok_button_text="Yes",
                cancel_button_text="No",
                ok_button_fn=self.delete_query,
                modal=True,
            ).show()
        else:
            self.delete_query()

    def delete_query(self):
        """Delete the selected queries without a confirmation prompt."""
        if (
            not self._model
            or not self._tree_view
            or len(self._tree_view.selection) == 0
            or not ExtensionSettings.clash_data
        ):
            return
        for s in self._tree_view.selection:  # type: ignore
            query_id = s.clash_query.identifier if s.clash_query else -1
            if ExtensionSettings.clash_data.remove_query_by_id(query_id, False) == 1:
                self._model.delete_row(s, False)
                count = ExtensionSettings.clash_data.remove_all_overlaps_by_query_id(query_id, False)
                if ExtensionSettings.debug_logging:
                    carb.log_info(f"Removing query {query_id} together with {count} clash info items.")
        ExtensionSettings.clash_data.commit()
        self.update_items()
        self._tree_selection_changed(None)

    def save_queries_to_json_file(self, file_path: str, selection) -> bool:
        """Exports selected clash detection queries to a JSON file.

        Args:
            file_path (str): The file path for the JSON export.
            selection: Selection of ClashQueries to export
        """
        def do_export(file_path: str, selection) -> bool:
            queries = [s.clash_query.serialize_to_dict() for s in selection]
            if len(queries) == 0:
                carb.log_error("Query Export Failed: Nothing to write!")
                return False
            json_str = to_json_str_safe(queries, indent=4)
            if len(json_str) == 0:
                carb.log_error("Query Export Failed: Nothing to write!")
                return False
            json_bytes = json_str.encode("utf-8")
            if len(json_bytes) == 0:
                carb.log_error("Query Export Failed: Nothing to write!")
                return False
            if omni.client.write_file(file_path, json_bytes) != omni.client.Result.OK:
                carb.log_error(f"Query Export Failed: Failed writing JSON file to '{file_path}'.")
                return False
            return True

        if do_export(file_path, selection):
            show_notification(f"Export was successful.\nTarget: {file_path}")
            return True
        else:
            show_notification(
                f"Error(s) encountered while exporting queries to file\n{file_path}\nSee log for details.", True
            )
        return False

    def export_query_with_prompt(self):
        """Export the selected queries to a user picked JSON file."""

        if not self._tree_view or len(self._tree_view.selection) == 0:
            return

        pick_target_file(
            "Export Clash Detection Queries to JSON file",
            [("*.json", "JSON Files"), ("*", "All Files")],
            ".json",
            lambda fn: self.save_queries_to_json_file(fn, self._tree_view.selection)  # type: ignore
        )

    def import_queries_from_json_file(self, file_path: str) -> bool:
        """Imports clash detection queries from a JSON file.

        Args:
            file_path (str): The file path for the JSON file to import.
            wnd (ClashQueryWindow): ClashQueryWindow that will receive imported queries.
        """
        def do_import(file_path: str, wnd: ClashQueryWindow) -> bool:
            if not ExtensionSettings.clash_data or not wnd._model:
                return False

            result, version, content = omni.client.read_file(file_path)
            if result != omni.client.Result.OK:
                carb.log_error(f"Query Import Failed: Failed loading JSON file from '{file_path}'.")
                return False

            json_str = memoryview(content).tobytes().decode("utf-8")
            if len(json_str) == 0:
                carb.log_error(f"Query Import Failed: Loaded JSON file '{file_path}' is empty.")
                return False

            r = True
            loaded_queries = from_json_str_safe(json_str)
            if not isinstance(loaded_queries, list):
                carb.log_error("Query Import Failed: Expected list of queries, got invalid format.")
                return False

            new_rows = []
            for query_dict in loaded_queries:
                if not isinstance(query_dict, dict):
                    carb.log_error("Query Import Failed: Expected query dictionary, got invalid format.")
                    r = False
                    continue  # continue error despite unsuccessful deserializaation

                new_query = ClashQuery.deserialize_from_dict(query_dict, True)
                if not new_query:
                    carb.log_error("Errors reported while importing clash query!")
                    r = False
                    continue  # continue error despite unsuccessful deserializaation

                new_id = ExtensionSettings.clash_data.insert_query(new_query, False, False)
                if new_id > 0:
                    new_query = ExtensionSettings.clash_data.find_query(new_id)
                    if new_query:
                        new_row = wnd._model.add_row(new_query, True)
                        new_rows.append(new_row)
                else:
                    carb.log_error(f"Error inserting new clash query '{new_query.query_name}'!")
                    r = False

            if wnd._tree_view:
                wnd._tree_view.selection = new_rows
            ExtensionSettings.clash_data.commit()
            return r

        if do_import(file_path, self):
            show_notification(f"Import was successful.\nSource: {file_path}.")
            return True
        else:
            show_notification(f"Error(s) encountered while importing file\n{file_path}\nSee log for details.", True)

        return False

    def import_query_with_prompt(self):
        """Imports clash detection queries from a user picked JSON file."""

        pick_target_file(
            "Import Clash Detection Queries from JSON file",
            [("*.json", "JSON Files"), ("*", "All Files")],
            ".json",
            lambda fn: self.import_queries_from_json_file(fn),
            button_label="Import"
        )

    def show_query_stats_summary_window(self):
        """Show the query statistics summary."""
        if self._stats_summary_window:
            self._stats_summary_window.destroy()
        self._stats_summary_window = ClashQueryStatsWindow()
        self._stats_summary_window.show()

    def _on_window_visibility_changed(self, visible: bool):
        if not visible:  # window is closed, clear query selection
            self.clear_selection()

    def _on_window_width_changed(self, new_width):
        if not self._property_splitter:
            return
        self._window_size = (new_width, self._window_size[1])
        # Limit how far splitter can move, otherwise will break
        self._property_splitter.offset_x = max(self.LEFT_PANE_MIN_WIDTH, self._window_size[0] - self._splitter_offset)

    def _on_property_splitter_dragged(self, position_x):
        if not self._property_splitter:
            return
        new_offset = self._window_size[0] - position_x
        # Limit how far splitter can move, otherwise will break
        self._splitter_offset = max(self.RIGHT_PANE_MIN_WIDTH, new_offset)
        self._property_splitter.offset_x = max(self.LEFT_PANE_MIN_WIDTH, self._window_size[0] - self._splitter_offset)

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        if self._model and self._tree_view:
            if self._save_current_query_on_selection_change and self._selected_query_for_edit:
                self.save_edited_query()
            self._model.set_filter_text(" ".join(search_words).lower() if search_words else "")
            self.update_ui()

    def build_window(self):
        """Build the ClashQueryWindow UI."""
        self.create_model()

        def build_menu():
            self._settings_menu = ui.Menu(
                "Settings menu###ClashQuery",
                tearable=False,
                menu_compatibility=False,
            )
            with self._settings_menu:
                ui.Separator("Settings")
                ui.MenuItem(
                    "Display and Edit Timecodes as Frames",
                    tooltip="If enabled, timecodes in settings property list will be displayed as frames instead of seconds",
                    checkable=True,
                    hide_on_click=False,
                    checked=self._timecodes_in_frames,
                    checked_changed_fn=lambda v: carb.settings.get_settings().set_bool(
                        ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES, v
                    ),
                )
                ui.MenuItem(
                    "Save Edited Query on Selection Change",
                    tooltip="If enabled, the query properties will be saved automatically when selection changes",
                    checkable=True,
                    hide_on_click=False,
                    checked=self._save_current_query_on_selection_change,
                    checked_changed_fn=lambda v: carb.settings.get_settings().set_bool(
                        ExtensionSettings.SETTING_QUERY_WINDOW_AUTOSAVE, v
                    ),
                )
            self._context_menu = ui.Menu(
                "Context menu###ClashQuery",
                tearable=False,
                menu_compatibility=False,
            )

        def build_top_toolbar():
            with ui.HStack(height=25):
                self._create_new_query_button = ui.Button(
                    "Create New Query",
                    tooltip="Create New Query",
                    width=130,
                    clicked_fn=self.create_new_query
                )
                self._duplicate_selected_query_button = ui.Button(
                    "Duplicate",
                    tooltip="Duplicate Selected Queries",
                    width=90,
                    clicked_fn=self.duplicate_query
                )
                self._delete_selected_query_button = ui.Button(
                    "Delete...",
                    tooltip="Delete Selected Queries",
                    width=90,
                    clicked_fn=self.delete_query_with_prompt
                )
                self._stats_summary_button = ui.Button(
                    "Statistics",
                    tooltip="Show Query Statistics - Clashes counts per clash state",
                    width=90,
                    clicked_fn=self.show_query_stats_summary_window
                )
                ui.Spacer(width=3)
                self._search_field = SearchField(
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=True,
                    show_tokens=False,
                )
                ui.Spacer(width=3)
                self._export_selected_query_button = ui.Button(
                    "Export Queries...",
                    tooltip="Export Selected Queries",
                    width=120,
                    clicked_fn=self.export_query_with_prompt
                )
                self._import_query_from_file_button = ui.Button(
                    "Import Queries...",
                    tooltip="Import Queries from a JSON file",
                    width=120,
                    clicked_fn=self.import_query_with_prompt
                )
                self._save_query_properties_button = ui.Button(
                    "Save Properties",
                    width=120,
                    clicked_fn=self.save_edited_query
                )
                ui.Button(
                    name="options",
                    tooltip="Settings",
                    width=Styles.IMG_BUTTON_SIZE_H,
                    height=Styles.IMG_BUTTON_SIZE_V,
                    image_width=Styles.IMG_BUTTON_SIZE_H,
                    image_height=Styles.IMG_BUTTON_SIZE_V,
                    clicked_fn=lambda: self._settings_menu.show() if self._settings_menu else None,
                )
            ui.Spacer(height=3)

        def build_table():
            if not self._model or not self._delegate:
                return

            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                style_type_name_override="TreeView",
            ):
                self._tree_view = ui.TreeView(
                    self._model,
                    name="clash_queries",
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=self._delegate.get_default_column_widths(),
                    min_column_widths=self._delegate.get_min_column_widths(),
                    resizeable_on_columns_resized=False,
                )
                self._tree_view.set_selection_changed_fn(self._tree_selection_changed)
                self._tree_view.set_mouse_double_clicked_fn(self._tree_view_on_double_click)
                self._tree_view.set_mouse_released_fn(self._tree_view_on_click)
                self._tree_view.set_key_pressed_fn(self._tree_view_on_key_pressed)

        build_menu()
        with self.frame:
            with ui.VStack():
                build_top_toolbar()

                with ui.HStack():
                    with ui.ZStack(width=0):
                        with ui.HStack():
                            build_table()

                        self._property_splitter = ui.Placer(
                            offset_x=self._window_size[0] - self._splitter_offset,
                            drag_axis=ui.Axis.X,
                            draggable=True,
                        )
                        with self._property_splitter:
                            ui.Rectangle(width=4, style_type_name_override="Splitter")
                        self._property_splitter.set_offset_x_changed_fn(self._on_property_splitter_dragged)

                    # Right panel
                    with ui.ScrollingFrame(
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    ):
                        self._property_frame = ui.VStack()
                        self._build_property_view()
        self.load()
        self.update_ui(False, True)

    def _build_property_view(self):
        def build_base_view():
            frame = ui.CollapsableFrame("Base", height=0, style=Styles.NOTICE_WIDGET_STYLE)
            with frame:
                with ui.VStack(style={"margin": 1}, spacing=4):
                    ui.Label("Note: clash detection only works with meshes, not shapes.", name="warning_text")
                    ui.Label("Query Name:")
                    ui.StringField(self._selected_query_property.query_name_model if self._selected_query_property else None)
                    ui.Label("Query Comment:")
                    ui.StringField(self._selected_query_property.query_comment_model if self._selected_query_property else None)

            ui.Spacer(height=3)

        def build_path_widget(label_text, path_model):
            def pick_paths(model):
                ctx = omni.usd.get_context(ExtensionSettings.usd_context_name)
                if not ctx:
                    return
                stage = ctx.get_stage()  # type: ignore
                additional_widget_kwargs = {
                    "target_name": "Searchset",
                    "target_plural_name": "Searchset",
                    "modal_window": True,
                }
                stage_picker = RelationshipTargetPicker(
                    stage,
                    [],
                    None,
                    additional_widget_kwargs,
                )

                def on_stage_picker_paths_selected(paths, model):
                    model.set_value(model.as_string + " " + paths[0] if len(paths) > 0 else model.as_string)

                stage_picker.show(1, lambda paths, model=model: on_stage_picker_paths_selected(paths, model))

            def drop_path(event, model) -> bool:
                if event.mime_data:
                    paths_to_add = ""
                    for path in event.mime_data.split():
                        paths_to_add += f" {path.strip()}"
                    if paths_to_add:
                        # Concisely append the dropped path, separated by a space if needed
                        model.set_value(f"{model.as_string}{paths_to_add}".strip())
                return True

            def update_path_model_tooltip(model: ui.AbstractValueModel, field: ui.StringField, tooltip: str):
                string_value = model.as_string
                field.tooltip = f"{string_value}\n\n{tooltip}" if string_value else tooltip

            tooltip_str = """ Hint:
            *   If both Searchset A and Searchset B are empty -> process full scene.
            *   If only the Searchset A list contains items -> limit processing only to Searchset A items.
            *   If Searchset A and Searchset B lists contain items -> process Searchset A against Searchset B.

            NOTE: Each searchset can contain multiple paths separated by spaces. """

            ui.Label(label_text, tooltip=tooltip_str)
            with ui.HStack():
                string_field = ui.StringField(
                    path_model,
                    accept_drop_fn=lambda url: url[0] == "/" if len(url) > 0 else False,
                    drop_fn=lambda event, m=path_model: drop_path(event, m),
                )

                update_path_model_tooltip(path_model, string_field, tooltip_str)
                path_model.add_value_changed_fn(lambda m: update_path_model_tooltip(m, string_field, tooltip_str))

                ui.Button("Pick...", width=80, clicked_fn=partial(pick_paths, path_model))

        def build_scope_view():
            obj_a_path = self._selected_query_property.object_a_path_model if self._selected_query_property else None
            obj_b_path = self._selected_query_property.object_b_path_model if self._selected_query_property else None
            frame = ui.CollapsableFrame("Scope", height=0)
            with frame:
                with ui.VStack(style={"margin": 1}, spacing=4):
                    build_path_widget("Searchset A", obj_a_path)
                    build_path_widget("Searchset B", obj_b_path)
                    ui.Spacer(height=3)

        if not self._property_frame:
            return
        self._property_frame.clear()
        if self._selected_query_for_edit is None:
            return
        with self._property_frame:
            build_base_view()
            build_scope_view()
            if self._clash_detect_settings:
                ClashDetectionSettingsUI.build_ui(self._property_frame, self._clash_detect_settings)

    def select_all_queries(self):
        """Selects all queries in the tree view."""
        if self._model and self._tree_view and len(self._model.filtered_children) > 0:
            self._tree_view.selection = self._model.filtered_children
            self._tree_selection_changed(None)

    def clear_selection(self):
        """Clears the current selection in the tree view."""
        if self._tree_view:
            self._tree_view.selection = []
        self._tree_selection_changed(None)

    def update_ui(self, clear_selection=True, select_active_query=False):
        """Update the UI elements based on the current state.

        Args:
            clear_selection (bool): Whether to clear the selection.
            select_active_query (bool): Whether to select the query currently selected in the query dropdown in the results window.
        """
        if not self._tree_view or not ExtensionSettings.clash_data:
            return

        clash_data_open = ExtensionSettings.clash_data.is_open()

        if self._create_new_query_button:
            self._create_new_query_button.enabled = clash_data_open
        if self._duplicate_selected_query_button:
            self._duplicate_selected_query_button.enabled = clash_data_open and len(self._tree_view.selection) > 0
        if self._delete_selected_query_button:
            self._delete_selected_query_button.enabled = clash_data_open and len(self._tree_view.selection) > 0
        if self._export_selected_query_button:
            self._export_selected_query_button.enabled = clash_data_open and len(self._tree_view.selection) > 0
        if self._import_query_from_file_button:
            self._import_query_from_file_button.enabled = clash_data_open
        if self._save_query_properties_button:
            self._save_query_properties_button.enabled = clash_data_open and self._selected_query_for_edit is not None

        if clear_selection:
            self._tree_view.selection = []

        if select_active_query and ExtensionSettings.clash_query and self._model:
            for item in self._model.children:
                if item.clash_query.identifier == ExtensionSettings.clash_query.identifier:
                    self._tree_view.selection = [item]
                    break

    def _tree_selection_changed(self, items):
        if self._save_current_query_on_selection_change and self._selected_query_for_edit:
            self.save_edited_query()

        self._selected_query_for_edit = None

        if self._tree_view and len(self._tree_view.selection) == 1:
            self._selected_query_for_edit = self._tree_view.selection[0]
            if self._selected_query_for_edit and self._selected_query_property:
                self._clash_detect_settings = self._selected_query_property.create_from(
                    self._selected_query_for_edit.clash_query,
                    self._clash_detect_settings
                )

        self._build_property_view()
        self.update_ui(False)

    def _copy_each_selected_item_to_clipboard(self, custom_action_fnc: Callable[[ClashQuery], str]):
        string = ""
        if not self._tree_view:
            return
        for selected_item in self._tree_view.selection:  # type: ignore
            string += custom_action_fnc(selected_item.clash_query)
            string += "\n"
        omni.kit.clipboard.copy(string)

    def __show_context_menu(self):
        if self._context_menu is None or not self._tree_view:
            return
        self._context_menu.clear()
        with self._context_menu:  # type: ignore
            num_selected = len(self._tree_view.selection)
            query_str = "Query" if num_selected <= 1 else f"{num_selected} Queries"
            ui.MenuItem(
                "Create New Query",
                enabled=self._create_new_query_button.enabled if self._create_new_query_button else False,
                triggered_fn=self.create_new_query,
            )
            ui.MenuItem(
                f"Duplicate Selected {query_str}",
                enabled=self._duplicate_selected_query_button.enabled if self._duplicate_selected_query_button else False,
                triggered_fn=self.duplicate_query,
            )
            ui.MenuItem(
                f"Delete Selected {query_str}...",
                enabled=self._delete_selected_query_button.enabled if self._delete_selected_query_button else False,
                triggered_fn=self.delete_query_with_prompt,
            )
            ui.Separator()
            ui.MenuItem(
                f"Export Selected {query_str}...",
                enabled=self._export_selected_query_button.enabled if self._export_selected_query_button else False,
                triggered_fn=self.export_query_with_prompt,
            )
            ui.MenuItem(
                "Import Queries...",
                enabled=self._import_query_from_file_button.enabled if self._import_query_from_file_button else False,
                triggered_fn=self.import_query_with_prompt,
            )
            ui.Separator()
            ui.MenuItem(
                "Copy Name of Selected Query to Clipboard" if num_selected <= 1
                else f"Copy Names of {num_selected} Selected Queries to Clipboard",
                triggered_fn=lambda: self._copy_each_selected_item_to_clipboard(lambda q: q.query_name),
            )
        self._context_menu.show()

    def _tree_view_on_click(self, x, y, b, m):
        # mouse right click on empty space
        if b == 1 and self._tree_view and self._context_menu and not self._context_menu.shown:
            self._tree_view.selection = []
            self.__show_context_menu()

    def _tree_view_on_item_click(self, button, item):
        if button == 1 and self._tree_view:
            # If the selection doesn't contain the node we click, we should clear the selection and select the node.
            if item not in self._tree_view.selection:
                self._tree_view.selection = [item]
            self.__show_context_menu()

    def _tree_view_on_key_pressed(self, key: int, modifiers: int, is_down: bool):
        pass

    def _tree_view_on_double_click(self, x, y, b, m):
        pass
