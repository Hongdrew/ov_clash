# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from functools import partial
from typing import Optional, List, Dict, Tuple, Set, Union, Callable
import asyncio
import carb.settings
import omni.usd
import omni.ui as ui
import omni.kit.app
import omni.kit.actions.core
from omni.kit.hotkeys.core import get_hotkey_registry, HotkeyFilter
from omni.kit.widget.searchfield import SearchField
from omni.kit.widget.highlight_label import HighlightLabel
from pxr import Sdf
from .styles import Styles, ICON_PATH, format_int
from .grouping import group, GroupNode, dump_groups_to_json
from .settings import ExtensionSettings
from .utils import find_common_parent_path
from .clash_detect_viewmodel import ClashDetectTableModel, ClashDetectTableRowItem
from .clash_detect_delegate import ClashDetectTableDelegate


__all__ = []


class ClashTable(ui.AbstractItem):
    """
    UI item representing a table of clashes for a group node.

    This class wraps a GroupNode and exposes its clashing pairs as a set of ClashDetectTableRowItem.
    Used as a leaf item in the GroupsModel and tree view to display the clashes associated with a group.
    """

    def __init__(self, group_node: GroupNode):
        """Initialize ClashTable with a group node."""
        super().__init__()
        self._group_node = group_node

    @property
    def clashing_pairs(self) -> Set[ClashDetectTableRowItem]:
        """Return the set of clashing pairs for this group node."""
        return self._group_node.clashing_pairs if self._group_node else set()

    def destroy(self):
        """Release references held by this ClashTable."""
        self._group_node = None


class GroupTableItem(ui.AbstractItem):
    """
    UI item representing a group node in the groups tree view.

    This class wraps a GroupNode and exposes properties for use in the UI, such as
    clashing pairs, total clashes, group path, group kind, and child/group structure.
    Used as the main item type in the GroupsModel and tree view.
    """

    def __init__(self, group_node: GroupNode, parent_path: Optional[Sdf.Path] = None):
        """Initialize a GroupTableItem."""
        super().__init__()
        self._group_node = group_node
        self._parent_path = parent_path

    @property
    def clashing_pairs(self) -> Set[ClashDetectTableRowItem]:
        """Return the set of clashing pairs for this group."""
        return self._group_node.clashing_pairs if self._group_node else set()

    @property
    def total_clashes(self) -> int:
        """Return the total number of clashes for this group."""
        return self._group_node.total_clashes if self._group_node else 0

    @property
    def group_path(self) -> Sdf.Path:
        """Return the Sdf.Path of this group."""
        return self._group_node.group_path if self._group_node else Sdf.Path()

    @property
    def group_path_str(self) -> str:
        """Return the group path string, trimmed by parent path if set."""
        path_str = str(self._group_node.group_path) if self._group_node else ""
        if self._parent_path:
            path_str = path_str.replace(str(self._parent_path), "")
        return path_str

    @property
    def group_kind(self) -> str:
        """Return the kind/type of this group."""
        return self._group_node.group_kind if self._group_node else ""

    @property
    def has_children(self) -> bool:
        """Return True if this group has children or clashing pairs."""
        children = len(self._group_node.children) > 0 if self._group_node else False
        clashes = len(self.clashing_pairs) > 0 if self._group_node else False
        return children or clashes

    def destroy(self):
        """Release the reference to the group node."""
        self._group_node = None


class GroupsModel(ui.AbstractItemModel):
    """
    Model for managing group and clash table items in the groups tree view.

    This model maintains a mapping of group nodes and their UI representations, handles search/filtering,
    and provides access to group and clash table items for the UI. It supports updating, clearing, and
    retrieving all group items, as well as managing the cached item structure for efficient UI rendering.
    """

    def __init__(self):
        """Initialize GroupsModel, which manages group node dict, caches item children, and tracks current search string for the groups tree view."""
        super().__init__()
        self._node_dict: Optional[Dict[Optional[Sdf.Path], GroupNode]] = None
        self.__cached_items: Dict[Union[GroupTableItem, ClashTable], List[Union[GroupTableItem, ClashTable]]] = {}
        self._search_words = ""

    def destroy(self):
        """Clear cached items and node dict, releasing all model state for cleanup."""
        self.__cached_items.clear()
        self._node_dict = None

    @property
    def search_words(self) -> str:
        """Get the current search string used for filtering group items."""
        return self._search_words

    @property
    def num_of_cached_items(self) -> int:
        """Return the number of top-level items currently cached in the model."""
        return len(self.__cached_items.keys())

    @property
    def num_of_groups(self) -> int:
        """Return the number of cached items that are GroupTableItem instances."""
        return sum(1 for item in self.__cached_items.keys() if item and isinstance(item, GroupTableItem))

    @property
    def num_of_clash_tables(self) -> int:
        """Return the number of cached items that are ClashTable instances."""
        return sum(1 for item in self.__cached_items.keys() if item and isinstance(item, ClashTable))

    def clear(self):
        """Clear the cached items and reset the search string to empty."""
        self.__cached_items.clear()
        self._search_words = ""

    def set_node_dict(self, node_dict: Optional[Dict[Optional[Sdf.Path], GroupNode]]):
        """Assign a new group node dictionary and trigger an update of the model items."""
        self._node_dict = node_dict
        self.update_items()

    def update_items(self):
        """Notify the UI that the model's items have changed, prompting a refresh."""
        self._item_changed(None)  # type: ignore

    def get_all_group_items(self) -> List[GroupTableItem]:
        """Return a flat list of all cached GroupTableItem children from all parent items."""
        if not self.__cached_items:
            return []
        return [
            child
            for children in self.__cached_items.values()
            for child in children
            if isinstance(child, GroupTableItem)
        ]

    def get_item_children(self, item) -> List[Union[GroupTableItem, ClashTable]]:
        """Return the list of children (GroupTableItem or ClashTable) for a given item, using cache if available, and filter by search if set."""
        if not self._node_dict:
            return []
        if item in self.__cached_items:
            return self.__cached_items[item]
        if item is None or isinstance(item, GroupTableItem):
            group_node = self._node_dict[item.group_path if item else None]  # get root group node
            if len(group_node.children) > 0:
                if self._search_words:
                    def has_descendant_match(node, search):
                        if search in str(node.group_path).lower():
                            return True
                        return any(has_descendant_match(child, search) for child in node.children)

                    search = self._search_words
                    lst = [
                        GroupTableItem(child, group_node.group_path if group_node else None)
                        for child in group_node.children
                        if search in str(child.group_path).lower() or has_descendant_match(child, search)
                    ]
                else:
                    lst = [
                        GroupTableItem(child, group_node.group_path if group_node else None)
                        for child in group_node.children
                    ]
                lst = sorted(lst, key=lambda item: str(item.group_path))
            elif len(group_node.clashing_pairs) > 0:
                lst = [ClashTable(group_node)]
            else:
                lst = []
        else:
            lst = []
        self.__cached_items[item] = lst
        return lst

    def get_item_value_model_count(self, item: Union[GroupTableItem, ClashTable]):
        """Return the number of value models for the given item and column (always 1 for this model)."""
        return 1

    def get_item_value_model(self, item: Union[GroupTableItem, ClashTable], column_id: int):
        """Return the value model (string or None) for the given item and column, used for display in the tree view."""
        if column_id == 0:
            if isinstance(item, GroupTableItem):
                return item.group_path_str
            elif isinstance(item, ClashTable):
                return None
        return None

    def search(self, search_words: str):
        """Set the search string, clear the cache, and notify the UI to refresh the filtered items."""
        self.__cached_items.clear()
        self._search_words = search_words
        self._item_changed(None)  # type: ignore


class GroupsDelegate(ui.AbstractItemDelegate):
    """
    Delegate for rendering and handling interactions in the Groups tree view.

    This delegate is responsible for building headers and widgets for each item in the groups tree,
    managing selection and click events, and handling the lifecycle of any sub-table views (such as
    embedded clash tables) associated with group nodes. It also provides hooks for custom item click
    handling and integrates with the main clash detection results tree view if provided.
    """

    def __init__(self, **kwargs):
        """
        Initialize the GroupsDelegate.

        Args:
            model (GroupsModel): The model representing the group data.
            on_item_click (Callable, optional): Callback for item click events.
            on_item_double_click (Callable, optional): Callback for item double-click events.
            clash_detect_results_tree_view (ui.TreeView, optional): Reference to the main clash detection tree view.
            clash_detect_results_tree_view_click (Callable, optional): Callback for click events in the main clash detection tree view.

        This delegate manages rendering, selection, and event handling for group and clash table items in the groups tree view.
        """
        super().__init__()
        self._model = kwargs["model"]
        self._on_item_click = kwargs.get("on_item_click", None)
        self._on_item_double_click = kwargs.get("on_item_double_click", None)
        self._clash_detect_results_tree_view = kwargs.get("clash_detect_results_tree_view", None)
        self._clash_detect_results_tree_view_click = kwargs.get("clash_detect_results_tree_view_click", None)
        self.__clash_table_cache: Dict[
            Union[GroupTableItem, ClashTable],
            Tuple[
                ClashDetectTableModel,
                ClashDetectTableDelegate,
                ui.TreeView
            ]
        ] = {}

    def destroy(self):
        """Release references and destroy cached sub-table views."""
        self._on_item_click = None
        self._on_item_double_click = None
        self._model = None
        self._clash_detect_results_tree_view = None
        self._clash_detect_results_tree_view_click = None
        for clash_table_model, clash_table_delegate, clash_table_view in self.__clash_table_cache.values():
            clash_table_view.destroy()
            clash_table_delegate.destroy()
            # table model contains borrowed ClashDetectTableRowItem instances, so we cannot destroy them via
            # clash_table_model.destroy(), instead we only clear the model list using super() destroy()
            super(type(clash_table_model), clash_table_model).destroy()
        self.__clash_table_cache.clear()

    def build_header(self, column_id: int):
        """Build header cell for the given column."""
        if column_id == 0:
            with ui.ZStack(style=Styles.TABLE_CELL_STYLE):
                ui.Label("Group")

    def build_widget(
        self,
        model: GroupsModel,
        item: Union[GroupTableItem, ClashTable],
        column_id: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """Builds the main cell widget for a group or clash table item."""
        def tree_selection_changed(
            source_tree_view: ui.TreeView,
            items,
        ):
            """Sync selection with the main clash results tree view."""
            if not self._clash_detect_results_tree_view:
                return
            selection = []
            if len(items) > 0:
                for cti in self.__clash_table_cache.values():
                    if cti[2] == source_tree_view:
                        continue
                    cti[2].selection = []
                for item in items:
                    if isinstance(item, ClashDetectTableRowItem):
                        selection.append(item)
            self._clash_detect_results_tree_view.selection = selection

        def build_clash_table(item: ClashTable):
            """Builds a clash table view for the given item."""
            if len(item.clashing_pairs) == 0:
                return ui.Label("No clashes.")
            clash_table_model = ClashDetectTableModel()
            for clash_pair in item.clashing_pairs:
                clash_table_model.add_row_item(clash_pair, False)
            clash_table_model.update_items()
            clash_table_delegate = ClashDetectTableDelegate(
                model=clash_table_model,
                on_item_click=self._clash_detect_results_tree_view_click
            )
            clash_table_view = ui.TreeView(
                clash_table_model,
                name="clash_results",
                delegate=clash_table_delegate,
                root_visible=True,
                header_visible=True,
                columns_resizable=True,
                column_widths=clash_table_delegate.get_default_column_widths(),
                min_column_widths=clash_table_delegate.get_min_column_widths(),
            )
            self.__clash_table_cache[item] = (clash_table_model, clash_table_delegate, clash_table_view)
            clash_table_view.set_selection_changed_fn(partial(tree_selection_changed, clash_table_view))
            if self._clash_detect_results_tree_view is not None and self._clash_detect_results_tree_view.model is not None:
                clash_table_delegate.sort(
                    self._clash_detect_results_tree_view.model.sort_column_id,
                    self._clash_detect_results_tree_view.model.sort_direction,
                    True
                )
            return clash_table_view

        if not model:
            return

        if column_id == 0:
            with ui.HStack():
                if isinstance(item, GroupTableItem):
                    total_clashes_str = f"({item.total_clashes} clashes total)"
                    group_path_str = item.group_path_str
                    full_path_str = str(item.group_path) if item.group_path else ""
                    with ui.HStack(
                        width=0,
                        mouse_pressed_fn=lambda x, y, b, _: self._on_item_click(b, item) if self._on_item_click else None,
                        mouse_double_clicked_fn=lambda x, y, b, _: self._on_item_double_click(b, item) if self._on_item_double_click else None,
                    ):
                        ui.Label(item.group_kind, tooltip=full_path_str)
                        ui.Spacer(width=2)
                        if model.search_words:
                            HighlightLabel(
                                group_path_str,
                                tooltip=full_path_str,
                                highlight=model.search_words,
                                style=Styles.HIGHLIGHT_LABEL_STYLE
                            )
                        else:
                            ui.Label(
                                group_path_str,
                                tooltip=full_path_str,
                                style=Styles.HIGHLIGHT_LABEL_STYLE
                            )
                        ui.Spacer(width=2)
                        ui.Label(total_clashes_str)
                elif isinstance(item, ClashTable):
                    build_clash_table(item)

    def build_branch(
            self,
            model: GroupsModel,
            item: Union[GroupTableItem, ClashTable],
            column_id: int = 0,
            level: int = 0,
            expanded: bool = False,
    ):
        """Builds the branch (tree expander) UI for a group or clash table item."""
        if column_id == 0:
            with ui.HStack(width=20 * (level + 1), height=0):
                if isinstance(item, GroupTableItem) and item.has_children:
                    with ui.ZStack():
                        with ui.VStack(height=20):
                            ui.Spacer()
                            ui.Rectangle(height=22)
                            ui.Spacer()
                        with ui.VStack():
                            ui.Spacer()
                            with ui.HStack():
                                ui.Spacer()
                                ui.Image(f"{ICON_PATH}/{'minus' if expanded else 'plus'}.svg", width=10, height=10)
                                ui.Spacer(width=5)
                            super().build_branch(model, item, column_id, level, expanded)
                            ui.Spacer()
                else:
                    ui.Spacer(width=10)
                    with ui.VStack():
                        super().build_branch(model, item, column_id, level, expanded)
                        ui.Spacer(width=10)


class GroupsWindow(ui.Window):
    """
    GroupsWindow displays and manages the UI for viewing and interacting with clash groups.

    This window presents grouped clash results in a tree/table view, allowing users to inspect, filter,
    and interact with grouped clash data. It leverages GroupsModel for data, GroupsTableDelegate for rendering,
    and supports custom styling and window management. The window is typically opened from the main clash
    detection UI to provide a grouped perspective on detected clashes.
    """
    def __init__(
        self,
        clash_row_items: List[ClashDetectTableRowItem],
        clash_detect_results_tree_view: Optional[ui.TreeView] = None,
        clash_detect_results_tree_view_click: Optional[Callable[[int, ClashDetectTableRowItem], None]] = None,
        width=1200,
        height=650,
        position_x=80,
        position_y=50,
    ) -> None:
        """Initialize the FilterWindow."""
        window_title = "Clash Groups"
        super().__init__(
            window_title,
            width=width,
            height=height,
            visibility_changed_fn=self._on_visibility_changed,
        )
        if position_x is not None:
            self.position_x = position_x
        if position_y is not None:
            self.position_y = position_y
        self.frame.set_style(Styles.GROUPS_WND_STYLE)
        self.frame.set_build_fn(self.build_window)
        self._clash_row_items = clash_row_items
        self._model = None
        self._tree_view = None
        self._context_menu = None
        self._delegate = None
        self._node_dict = None
        self._clash_detect_results_tree_view = clash_detect_results_tree_view
        self._clash_detect_results_tree_view_click = clash_detect_results_tree_view_click
        self._grouping_task = None
        self._search_field = None
        self._num_of_groups_label = None
        self._settings_menu = None
        self._show_empty_groups = True
        carb.settings.get_settings().set_default_bool(
            ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, self._show_empty_groups
        )
        self._settings_subs = omni.kit.app.SettingChangeSubscription(
            ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, self._show_empty_groups_setting_changed
        )
        # fetch current value from settings
        self._show_empty_groups_setting_changed(None, carb.settings.ChangeEventType.CHANGED)

        action_ext_id = self.__class__.__module__

        # clear selection action & hotkey
        action_name = "clear_selection"
        self._clear_selection_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: self.clear_selection(),
            display_name="Clear Selection",
            tag="Clash Detection Group View Window",
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
            lambda: self.select_all_groups(),
            display_name="Select All Groups",
            tag="Clash Detection Group View Window",
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

    def _show_empty_groups_setting_changed(self, item, event_type):
        """Update state when the show empty groups setting changes."""
        if event_type == carb.settings.ChangeEventType.CHANGED:
            show_empty_groups = carb.settings.get_settings().get_as_bool(
                ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS
            )
            self._show_empty_groups = show_empty_groups
            self.load()

    def destroy(self) -> None:
        """Destroy the GroupsWindow and clean up resources."""
        self.visible = False
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
        self._tree_view = None
        if self._delegate:
            self._delegate.destroy()
            self._delegate = None
        self.frame.set_build_fn(None)  # type: ignore
        if self._model:
            self._model.destroy()
            self._model = None
        self._clash_row_items = None
        self._node_dict = None
        self._clash_detect_results_tree_view = None
        self._clash_detect_results_tree_view_click = None
        if self._search_field:
            self._search_field.destroy()
            self._search_field = None
        self.cancel_running_task()  # make sure we don't destroy while task is still running
        self._grouping_task = None
        self._num_of_groups_label = None
        self._settings_menu = None
        super().destroy()

    def _on_visibility_changed(self, visible: bool):
        """Handle visibility changes."""
        pass

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        """Handle search events in the search field."""
        if self._model and self._tree_view:
            self._model.search(" ".join(search_words).lower() if search_words else "")
            self._tree_view.set_expanded(None, True, True)
            self.update_ui()

    def create_model(self):
        """Create the model and delegate for the GroupsWindow."""
        # Create model for the table
        if not self._model:
            self._model = GroupsModel()
            if self._node_dict:
                self._model.set_node_dict(self._node_dict)
        # Create a delegate that will help render our table
        if not self._delegate:
            self._delegate = GroupsDelegate(
                model=self._model,
                on_item_click=self._tree_view_on_item_click,
                on_item_double_click=self._tree_view_on_item_double_click,
                clash_detect_results_tree_view=self._clash_detect_results_tree_view,
                clash_detect_results_tree_view_click=self._clash_detect_results_tree_view_click
            )

    def update_items(self, clear_selection=True):
        """Update the items in the model."""
        if self._model:
            self._model.update_items()
        self.update_ui(clear_selection)

    def reset(self):
        """Reset the GroupsWindow to its initial state."""
        if self._node_dict:
            self._node_dict.clear()
        if not self._model or not self._delegate:
            return
        self._model.clear()
        self._model.set_node_dict(None)
        self.update_items()

    async def _grouping_task_async(self):
        """Asynchronously load and update group statistics."""
        if not self._model or not ExtensionSettings.clash_data:
            return
        try:
            if self._num_of_groups_label:
                self._num_of_groups_label.text = "Grouping..."
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            stage = omni.usd.get_context().get_stage()  # type: ignore
            cq = ExtensionSettings.clash_query
            if not stage or not cq or not self._clash_row_items:
                return
            self._root_prim_path = find_common_parent_path([cq.object_a_path, cq.object_b_path])
            self._node_dict = group(stage, self._clash_row_items, discard_empty_groups=not self._show_empty_groups)
            if not self._node_dict:
                return
            self._model.set_node_dict(self._node_dict)
        except asyncio.CancelledError:
            carb.log_info("Grouping task was forcefully canceled.")
        except Exception as e:
            carb.log_error(f"Grouping task exception: {e}")
        finally:
            self._grouping_task = None
            if self._num_of_groups_label:
                self._num_of_groups_label.text = ""
            self.update_ui()

    def _run_grouping_task(self):
        """Run the grouping task asynchronously."""
        if self._grouping_task and not self._grouping_task.done():
            self.cancel_running_task()
        self._grouping_task = asyncio.ensure_future(self._grouping_task_async())

    def cancel_running_task(self):
        """Cancel the currently running grouping task."""
        if self._grouping_task and not self._grouping_task.done():
            self._grouping_task.cancel()
            # asyncio.get_event_loop().run_until_complete(self._loading_task)

    def load(self):
        """Load the queries and populate the model."""
        if not self._model or not self._delegate:
            return
        self.reset()
        self.update_items()
        self._run_grouping_task()

    def dump(self):
        """Dump the current group data to JSON."""
        if not self._node_dict:
            return
        dump_groups_to_json(self._node_dict, self._node_dict[None])

    def build_window(self):
        """Build the GroupsWindow UI."""
        self.create_model()

        def build_menu():
            self._context_menu = ui.Menu(
                "Context menu###GroupsWindow",
                tearable=False,
                menu_compatibility=False,
            )
            with self._context_menu:
                ui.Separator("Groups")
                ui.MenuItem("Select in Stage", triggered_fn=self.select_objects_in_scene)
                ui.Separator()
                ui.MenuItem("Expand All Children", triggered_fn=self.expand_all_children)
                ui.MenuItem("Collapse All Children", triggered_fn=self.collapse_all_children)

            self._settings_menu = ui.Menu(
                "Settings menu###GroupsWindow",
                tearable=False,
                menu_compatibility=False,
            )
            with self._settings_menu:
                ui.Separator("Settings")
                ui.MenuItem(
                    "Show Also Empty Groups",
                    checkable=True,
                    hide_on_click=False,
                    checked=self._show_empty_groups,
                    checked_changed_fn=lambda v: carb.settings.get_settings().set_bool(
                        ExtensionSettings.SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS, v
                    ),
                )

        def build_top_toolbar():
            with ui.HStack(height=25):
                ui.Button(
                    name="refresh",
                    tooltip="Refresh groups tree",
                    width=Styles.IMG_BUTTON_SIZE_H,
                    height=Styles.IMG_BUTTON_SIZE_V,
                    image_width=Styles.IMG_BUTTON_SIZE_H,
                    image_height=Styles.IMG_BUTTON_SIZE_V,
                    clicked_fn=self.load,
                )
                if ExtensionSettings.development_mode:
                    ui.Button(
                        "Dump",
                        tooltip="Dump the groups to the console",
                        width=130,
                        clicked_fn=self.select_all_groups
                    )
                ui.Spacer(width=5)
                self._num_of_groups_label = ui.Label("", width=0, alignment=ui.Alignment.RIGHT_CENTER)
                ui.Spacer(width=5)
                self._search_field = SearchField(
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=True,
                    style=Styles.GROUPS_WND_STYLE,
                    show_tokens=False,
                )
                ui.Spacer(width=3)
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

        def build_tree():
            if not self._model or not self._delegate:
                return

            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                style_type_name_override="TreeView",
            ):
                self._tree_view = ui.TreeView(
                    self._model,
                    name="groups",
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=[ui.Fraction(1)],
                    min_column_widths=[0],
                )
                self._tree_view.set_selection_changed_fn(self._tree_selection_changed)
                self._tree_view.set_key_pressed_fn(self._tree_view_on_key_pressed)

        build_menu()
        with self.frame:
            with ui.VStack():
                build_top_toolbar()
                build_tree()

        self.load()

    def _toggle_all_children_tree_nodes(self, expanded: bool):
        """Expand or collapse all child nodes of the selected tree items."""
        if not self._tree_view or len(self._tree_view.selection) == 0:
            return
        for item in self._tree_view.selection:  # type: ignore
            if isinstance(item, GroupTableItem):
                self._tree_view.set_expanded(item, expanded, recursive=True)

    def select_objects_in_scene(self):
        """Select the objects in the scene corresponding to the selection."""
        if not self._tree_view or len(self._tree_view.selection) == 0:
            return
        selection: list[str] = [str(entry.group_path) for entry in self._tree_view.selection]  # type: ignore
        omni.usd.get_context(ExtensionSettings.usd_context_name).get_selection().set_selected_prim_paths(selection, True)

    def expand_all_children(self):
        """Expand all child nodes of the selected tree items."""
        self._toggle_all_children_tree_nodes(True)

    def collapse_all_children(self):
        """Collapse all child nodes of the selected tree items."""
        self._toggle_all_children_tree_nodes(False)

    def update_ui(self, clear_selection=True):
        """Update the UI elements based on the current state."""
        if not self._tree_view:
            return

        if clear_selection:
            self._tree_view.selection = []
            self._tree_selection_changed(None)

        if self._search_field:
            search_text = self._model.search_words if self._model else ""
            if not search_text and self._search_field.text:
                self._search_field.clear()

        if self._num_of_groups_label:
            groups_cnt = len(self._node_dict.keys()) - 2 if self._node_dict else 0  # subtract None and root group
            groups_str = "groups" if groups_cnt != 1 else "group"
            if self._model and self._model.search_words:
                groups_cnt_filtered = self._model.num_of_groups
                label_text = f"Showing {format_int(groups_cnt_filtered)} of {format_int(groups_cnt)} {groups_str}"
            else:
                label_text = f"Total {format_int(groups_cnt)} {groups_str}"
            self._num_of_groups_label.text = label_text

    def on_stage_event(self, event_type):
        """Handle stage events such as closing, opening, or saving."""
        if event_type == omni.usd.StageEventType.CLOSING:
            self.reset()
        elif event_type == omni.usd.StageEventType.OPENED:
            self.load()
        elif event_type == omni.usd.StageEventType.SAVED:  # covers SAVE AS scenario
            self.update_ui(False)

    def show_context_menu(self):
        """Show the context menu for the tree view."""
        if not self._tree_view or not self._context_menu:
            return
        self._context_menu.show()

    def _tree_selection_changed(self, items):
        """Handle selection changes in the tree view."""
        self.update_ui(False)

    def _tree_view_on_item_click(self, button, item):
        """Handle single click on a tree view item."""
        if button == 1 and self._tree_view:
            # If the selection doesn't contain the node we click, we should clear the selection and select the node.
            if item not in self._tree_view.selection:
                self._tree_view.selection = [item]
            self.show_context_menu()

    def _tree_view_on_item_double_click(self, button, item):
        """Handle double click on a tree view item."""
        if not self._tree_view or len(self._tree_view.selection) == 0:
            return
        selection = self._tree_view.selection[0]
        if isinstance(selection, GroupTableItem):
            self._tree_view.set_expanded(selection, not self._tree_view.is_expanded(selection), recursive=False)

    def _tree_view_on_key_pressed(self, key: int, modifiers: int, is_down: bool):
        """Handle key press events in the tree view."""
        pass

    def select_all_groups(self):
        """Select all groups in the tree view."""
        if self._model and self._tree_view:
            all_group_items = self._model.get_all_group_items()
            self._tree_view.selection = all_group_items
            self._tree_selection_changed(None)

    def clear_selection(self):
        """Clear the current selection in the tree view."""
        if self._tree_view:
            self._tree_view.selection = []
        self._tree_selection_changed(None)
