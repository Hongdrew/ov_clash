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
from typing import Optional, List
from enum import IntEnum, auto
import carb.input
import omni.ui as ui
import omni.kit.app
import omni.kit.clipboard
from omni.kit.widget.searchfield import SearchField
from omni.physxclashdetectioncore.clash_info import ClashState
from .models import SortableSimpleStringModel, SortableSimpleIntModel, TableModel
from .utils import string_match
from .settings import ExtensionSettings
from .table_delegates import TableColumnDef, TableDelegate
from .helpers import get_clash_query_summary
from .styles import Styles


__all__ = []


class ClashQueryStatsTableColumnEnum(IntEnum):
    """An enumeration.

    This enumeration defines the columns for the Clash Query Table.
    """

    QUERY_NAME = 0
    CLASH_STATE_NEW = auto()
    CLASH_STATE_ACTIVE = auto()
    CLASH_STATE_APPROVED = auto()
    CLASH_STATE_RESOLVED = auto()
    CLASH_STATE_CLOSED = auto()
    CLASH_STATE_INVALID = auto()
    TOTAL_CLASH_PAIRS = auto()

class QueryStats:
    """
    Holds statistics for a single clash query, including counts for each clash state and a summary.

    Args:
        query_id (int): Unique identifier for the query.
        query_name (str): Name of the query.
        query_summary (str, optional): Summary or description of the query. Defaults to "".
        num_new (int, optional): Number of clashes in 'new' state. Defaults to -1.
        num_active (int, optional): Number of clashes in 'active' state. Defaults to -1.
        num_approved (int, optional): Number of clashes in 'approved' state. Defaults to -1.
        num_resolved (int, optional): Number of clashes in 'resolved' state. Defaults to -1.
        num_closed (int, optional): Number of clashes in 'closed' state. Defaults to -1.
        num_invalid (int, optional): Number of clashes in 'invalid' state. Defaults to -1.
        total_clashes (int, optional): Total number of clash pairs. Defaults to -1.
    """

    def __init__(
        self,
        query_id: int,
        query_name: str,
        query_summary: str = "",
        num_new: int = -1,
        num_active: int = -1,
        num_approved: int = -1,
        num_resolved: int = -1,
        num_closed: int = -1,
        num_invalid: int = -1,
        total_clashes: int = -1,
    ):
        self.query_id = query_id
        self.query_name = query_name
        self.query_summary = query_summary
        self.num_new = num_new
        self.num_active = num_active
        self.num_approved = num_approved
        self.num_resolved = num_resolved
        self.num_closed = num_closed
        self.num_invalid = num_invalid
        self.total_clashes = total_clashes


class ClashQueryStatsTableRowItem(ui.AbstractItem):
    """
    A class for representing a row item in the Clash Query Stats table.

    This class is used to represent a row item in the Clash Query Stats table.
    It contains the query stats and the row models.
    """

    def __init__(self, query_stats: QueryStats, row_models: List[ui.AbstractValueModel]):
        """Initializes a ClashQueryStatsTableRowItem instance."""
        super().__init__()
        self._query_stats = query_stats
        self._row_models = row_models if row_models is not None else []

    def destroy(self):
        """Destroys the ClashQueryStatsTableRowItem by clearing its clash info and row models."""
        self._query_stats = None
        self._row_models = []

    @property
    def query_stats(self) -> QueryStats | None:
        """Gets the query stats associated with this row.

        Returns:
            QueryStats: The query stats.
        """
        return self._query_stats

    @property
    def row_models(self) -> List[ui.AbstractValueModel]:
        """Gets the list of row models.

        Returns:
            List[ui.AbstractValueModel]: The list of row models.
        """
        return self._row_models

    @row_models.setter
    def row_models(self, value: List[ui.AbstractValueModel]):
        """Sets the list of row models.

        Args:
            value (List[ui.AbstractValueModel]): The list of row models.
        """
        self._row_models = value

    def matches_filter(self, search_text: str) -> bool:
        """Checks if the row matches the given filter text.

        Args:
            search_text (str): The text to filter rows by.

        Returns:
            bool: True if the row matches the filter, False otherwise.
        """
        # NOTE: this check ignores specific formatting for each cell
        if not search_text:
            return True
        search_text_lc = search_text.lower()
        for col in self._row_models:
            if col and string_match(search_text_lc, col.as_string.lower()):
                return True
        return False


class ClashQueryStatsTableModel(TableModel):
    """A class for representing a table model for the Clash Query Stats table.

    This class is used to represent a table model for the Clash Query Stats table.
    It maintains a list of ClashQueryStatsTableRowItems, each representing a row in the table.
    """

    def __init__(self):
        super().__init__()


    def create_row(self, qs: QueryStats):
        """Creates a list of value models for a table row based on clash information.

        Args:
            qs (QueryStats): Information about the query stats.

        Returns:
            List[ui.AbstractValueModel]: List of value models representing the row data.
        """

        row_models = [
            SortableSimpleStringModel(qs.query_name),
            SortableSimpleIntModel(qs.num_new) if qs.num_new != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.num_active) if qs.num_active != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.num_approved) if qs.num_approved != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.num_resolved) if qs.num_resolved != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.num_closed) if qs.num_closed != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.num_invalid) if qs.num_invalid != -1 else SortableSimpleStringModel("-"),
            SortableSimpleIntModel(qs.total_clashes) if qs.total_clashes != -1 else SortableSimpleStringModel("-"),
        ]

        assert len(row_models) == len(ClashQueryStatsTableColumnEnum)

        return row_models

    def get_item_value_model_count(self, item: ClashQueryStatsTableRowItem):
        """Returns the number of columns for a given item.

        Args:
            item (ClashQueryStatsTableRowItem): The row item.

        Returns:
            int: The number of columns in the table.
        """
        return len(ClashQueryStatsTableColumnEnum)

    def add_row(self, query_stats: QueryStats, update_items=False) -> ClashQueryStatsTableRowItem:
        """Adds a new row to the table.

        Args:
            query_stats (QueryStats): Information about the query stats.
            update_items (bool): Whether to update items after adding the row.

        Returns:
            ClashQueryStatsTableRowItem: The newly added row item.
        """
        row_models = self.create_row(query_stats)
        new_row = ClashQueryStatsTableRowItem(query_stats, row_models)
        self._children.append(new_row)
        if update_items:
            self._item_changed(new_row)
            self.update_items()
        return new_row

    def update_row(self, table_row: ClashQueryStatsTableRowItem):
        """Updates a specific row in the table.

        Args:
            table_row (ClashQueryStatsTableRowItem): The row item to update.
        """
        if not table_row.query_stats:
            return
        table_row.row_models = self.create_row(table_row.query_stats)
        self._item_changed(table_row)

    def get_item_value_model(self, item: ClashQueryStatsTableRowItem, column_id):
        """Return the value model for a given item and column.

        Args:
            item (ClashQueryStatsTableRowItem): The row item.
            column_id (int): The column ID.

        Returns:
            ui.AbstractValueModel: The value model for the specified column.
        """
        return item._row_models[column_id]

    def delete_row(self, row_item: ClashQueryStatsTableRowItem, update_items=False):
        """Deletes a specific row from the table.

        Args:
            row_item (ClashQueryStatsTableRowItem): The row item to delete.
            update_items (bool): Whether to update items after deleting the row.
        """
        if row_item:
            row_item.destroy()
        super().delete_row(row_item, update_items)

    def destroy(self):
        """Destroys the table model and its children."""
        for r in self.children:
            r.destroy()
        super().destroy()

    def clear(self):
        """Clears all rows from the table."""
        for r in self.children:
            r.destroy()
        super().clear()


class ClashQueryNameColumn(TableColumnDef):
    """A class for defining the 'Last Modified' column in a table.

    This class is used to represent the 'Last Modified' column within the Clash Query table.
    It sets up the column with a specific title, alignment, and width, and is responsible for rendering each cell
    in this column with the appropriate timestamp and user information.
    """

    def __init__(self):
        """Initializes the LastModifiedColumn with specific alignment and size."""
        super().__init__("Query Name", ui.Alignment.LEFT, 200, 100)

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashQueryStatsTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell with the query name.

        Args:
            value_model (ui.AbstractValueModel): Model containing the timestamp value.
            row_model (ClashQueryStatsTableRowItem): Model containing the row data.
            model (ui.AbstractItemModel): Model containing the table data.
        """
        if not row_model.query_stats:
            return
        query_name = value_model.as_string
        tooltip = row_model.query_stats.query_summary
        ui.Label(
            query_name,
            alignment=self.alignment,
            tooltip=tooltip,
        )


class ClashQueryStatsTableDelegate(TableDelegate):
    """
    Table delegate for the Clash Query Stats table.

    Sets up column definitions and rendering logic for displaying
    clash query statistics, including query name and various clash state counts.
    """

    def __init__(self, **kwargs):
        """Initializes the ClashQueryStatsTableDelegate and its columns."""
        super().__init__(**kwargs)
        self._columns = {
            ClashQueryStatsTableColumnEnum.QUERY_NAME: ClashQueryNameColumn(),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_NEW: TableColumnDef("New", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_APPROVED: TableColumnDef("Approved", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_RESOLVED: TableColumnDef("Resolved", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_CLOSED: TableColumnDef("Closed", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_INVALID: TableColumnDef("Invalid", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.CLASH_STATE_ACTIVE: TableColumnDef("Active", ui.Alignment.RIGHT, 80, 40),
            ClashQueryStatsTableColumnEnum.TOTAL_CLASH_PAIRS: TableColumnDef("Total", ui.Alignment.RIGHT, ui.Fraction(1), 40),
        }


class ClashQueryStatsWindow(ui.Window):
    """
    ClashQueryStatsWindow provides a modal UI window for displaying statistics
    about clash queries. It shows a table of queries with counts for each clash
    state (New, Approved, Resolved, Closed, Invalid, Active, Total), supports
    searching/filtering, and allows interaction via context menu and keyboard.
    """
    def __init__(
        self,
        width=800,
        height=600,
        position_x=None,
        position_y=None,
    ) -> None:
        """Initialize the Clash Query Stats window."""
        window_title = "Clash Query Stats"
        super().__init__(
            window_title,
            width=width,
            height=height,
            flags=0,
            visibility_changed_fn=self._on_visibility_changed,
        )
        if position_x is not None:
            self.position_x = position_x
        if position_y is not None:
            self.position_y = position_y
        self.frame.set_style(Styles.CLASH_STATS_WND_STYLE)
        self.set_key_pressed_fn(self._on_key_pressed)
        self._model = None
        self._delegate = None
        self._tree_view = None
        self._context_menu = None
        self._search_field = None
        self._loading_task = None
        self._progress_label = None

    def destroy(self) -> None:
        """Destroy the Clash Query Stats window."""
        self._model = None
        if self._delegate:
            self._delegate.destroy()
            self._delegate = None
        self._tree_view = None
        self._context_menu = None
        self._search_field = None
        self.cancel_running_task()  # make sure we don't destroy while task is still running
        self._loading_task = None
        self._progress_label = None
        super().destroy()

    async def _destroy_window_in_next_frame(self):
        """Destroy the window in the next frame."""
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.destroy()

    def _destroy_window(self):
        """Destroy the window."""
        asyncio.ensure_future(self._destroy_window_in_next_frame())

    def _on_key_pressed(self, key, mod, pressed):
        """Handle key presses."""
        if not pressed:
            return
        if key == int(carb.input.KeyboardInput.ESCAPE):
            self.visible = False

    def _on_visibility_changed(self, visible: bool):
        """Handle visibility changes."""
        if not visible:
            self._destroy_window()

    def create_model(self):
        """Create the model for the window."""
        if not self._model:
            self._model = ClashQueryStatsTableModel()
        if not self._delegate:
            self._delegate = ClashQueryStatsTableDelegate(
                model=self._model,
                on_item_click=self._tree_view_on_item_click
            )

    async def _loading_task_async(self):
        """
        Asynchronous task to load and update clash query statistics.

        Iterates over each row in the model, fetches the latest clash state counts
        for each query from the ExtensionSettings.clash_data backend, updates the
        QueryStats fields, and refreshes the model row. Handles cancellation and
        logs errors. Intended to be run as a background task to keep the UI responsive.
        """
        if not self._model or not ExtensionSettings.clash_data:
            return
        try:
            if self._progress_label:
                self._progress_label.text = "Working..."
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            cd = ExtensionSettings.clash_data
            for row in self._model.children:
                query_stats = row.query_stats
                query_id = query_stats.query_id
                count_by_state = cd.get_overlaps_count_by_query_id_grouped_by_state(query_id)
                total_clashes_count = sum(count_by_state.values())
                query_stats.num_new = count_by_state.get(ClashState.NEW, 0)
                query_stats.num_active = count_by_state.get(ClashState.ACTIVE, 0)
                query_stats.num_approved = count_by_state.get(ClashState.APPROVED, 0)
                query_stats.num_resolved = count_by_state.get(ClashState.RESOLVED, 0)
                query_stats.num_closed = count_by_state.get(ClashState.CLOSED, 0)
                query_stats.num_invalid = count_by_state.get(ClashState.INVALID, 0)
                query_stats.total_clashes = total_clashes_count
                self._model.update_row(row)
        except asyncio.CancelledError:
            carb.log_info("DB loading task was forcefully canceled.")
        except Exception as e:
            carb.log_error(f"_db_task exception: {e}")
        finally:
            self._loading_task = None
            if self._progress_label:
                self._progress_label.text = ""

    def _run_loading_task(self):
        """Runs the database task."""
        if self._loading_task and not self._loading_task.done():
            self.cancel_running_task()
        self._loading_task = asyncio.ensure_future(self._loading_task_async())

    def cancel_running_task(self):
        """Cancels the currently running task."""
        if self._loading_task and not self._loading_task.done():
            self._loading_task.cancel()

    def load(self):
        """Load the data for the window."""
        if not self._model or not ExtensionSettings.clash_data:
            return
        self.reset()
        cd = ExtensionSettings.clash_data
        query_stats = []
        for query in cd.fetch_all_queries().values():
            query_stats.append(
                QueryStats(
                    query.identifier,
                    query.query_name,
                    get_clash_query_summary(query)
                )
            )
        query_stats.sort(key=lambda x: x.query_name, reverse=False)
        for qs in query_stats:
            self._model.add_row(qs)
        if self._delegate:
            self._delegate.sort(ClashQueryStatsTableColumnEnum.QUERY_NAME, True, False)  # ascending
        self.update_items()
        self._run_loading_task()

    async def _load_in_next_frame(self):
        """Destroy the window in the next frame."""
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.load()

    def update_ui(self, clear_selection=True):
        """Update the UI elements based on the current state.

        Args:
            clear_selection (bool): Whether to clear the selection.
        """
        if not self._tree_view or not ExtensionSettings.clash_data:
            return

        if clear_selection:
            self._tree_selection_changed(None)

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
        self.cancel_running_task()
        if self._loading_task:
            asyncio.get_event_loop().run_until_complete(self._loading_task)
        if self._model:
            self._model.clear()
        self.update_items()

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        if self._model and self._tree_view:
            self._model.set_filter_text(" ".join(search_words).lower() if search_words else "")
            self.update_ui()

    def build_ui(self):
        """Build the window UI."""
        self.create_model()

        def build_menu():
            self._context_menu = ui.Menu(
                "Context menu###ClashQueryStatsWindow",
                tearable=False,
                menu_compatibility=False,
            )
            with self._context_menu:
                ui.MenuItem(
                    "Copy to Clipboard (CSV)",
                    tooltip="Copy the selected rows to the clipboard as a Comma Separated Values (CSV)",
                    enabled=True,
                    triggered_fn=self._copy_each_selected_row_to_clipboard,
                )

        def build_top_toolbar():
            with ui.HStack(height=0):
                ui.Button(
                    "Refresh",
                    name="refresh",
                    tooltip="Refresh Stats",
                    width=90,
                    clicked_fn=self.load
                )
                ui.Spacer(width=3)
                self._search_field = SearchField(
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=True,
                    show_tokens=False,
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
                    name="stats",
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=self._delegate.get_default_column_widths(),
                    min_column_widths=self._delegate.get_min_column_widths(),
                    resizeable_on_columns_resized=True,
                )
                self._tree_view.set_selection_changed_fn(self._tree_selection_changed)
                self._tree_view.set_mouse_released_fn(self._tree_view_on_click)

        def build_bottom_bar():
            ui.Spacer(height=3)
            with ui.HStack(height=0):
                self._progress_label = ui.Label("", style={"margin": 3})
                ui.Spacer()
                ui.Button("Close", width=100, clicked_fn=self._destroy_window)

        build_menu()
        with self.frame:
            with ui.VStack():
                build_top_toolbar()
                build_tree()
                build_bottom_bar()

        self.update_ui()

    def _tree_selection_changed(self, items):
        """Handle selection change in the tree view.

        Args:
            items: The newly selected items in the tree view.
        """
        if not self._tree_view or not self._delegate:
            return

    def _copy_each_selected_row_to_clipboard(self):
        """Copy the currently selected rows to the clipboard as tab-separated values."""
        if not self._tree_view or not self._delegate:
            return
        col_names = [col_def.name for col_def in self._delegate.columns.values()]
        string = "\t".join(col_names) + "\n"
        string += "\n".join(
            "\t".join(row_model.as_string for row_model in selected_item.row_models)
            for selected_item in self._tree_view.selection  # type: ignore
        )
        omni.kit.clipboard.copy(string)

    def _tree_view_on_click(self, x, y, b, m):
        """Handle mouse right click on empty space."""
        pass

    def _tree_view_on_item_click(self, button, item):
        """Handle mouse click events on a tree view item.

        Args:
            button: Mouse button pressed.
            item: The item that was clicked.
        """
        if button == 1 and self._tree_view and self._context_menu and not self._context_menu.shown:
            # If the selection doesn't contain the node we click, we should clear the selection and select the node.
            if item not in self._tree_view.selection:
                self._tree_view.selection = [item]
            self._context_menu.show()

    def show(self):
        """Show the Clash Query Stats window."""
        self.build_ui()
        self.visible = True
        self.focus()
        self.load()
