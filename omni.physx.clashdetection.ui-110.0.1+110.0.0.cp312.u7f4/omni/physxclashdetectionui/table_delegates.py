# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# General purpose table delegates

from typing import Dict, Callable, Any, Optional
import omni.ui as ui
from .styles import Styles

__all__ = []


class TableColumnDef:
    """A class for defining the properties and behavior of a table column.

    This class is used to specify various attributes and functionalities for
    table columns, such as alignment, default width, minimum width, and sorting
    behavior.

    Args:
        name (str): The name of the column.
        alignment (ui.Alignment): The alignment of the column content.
        default_width: The default width of the column.
        min_width: The minimum width of the column.
        is_sort_column (bool): Indicates if the column is used for sorting.
        sort_direction (bool): The direction of sorting; True for ascending and
            False for descending.
        table_delegate (Optional[TableDelegate]): The table delegate this column belongs to.
    """

    def __init__(
        self,
        name: str = "",
        alignment: ui.Alignment = ui.Alignment.LEFT,
        default_width=None,
        min_width=None,
        is_sort_column: bool = False,
        sort_direction: bool = False,  # Specify False if data must be sorted in descending order; otherwise True.
        table_delegate: Optional["TableDelegate"] = None, # table delegate this column belongs to
        tooltip: str = "",
    ):
        """Initializes a new instance of TableColumnDef."""
        self._name = name
        self._alignment = alignment
        self._default_width = default_width if default_width is not None else ui.Fraction(1)
        self._min_width = min_width if min_width is not None else ui.Pixel(0)
        self._is_sort_column = is_sort_column
        self._sort_direction = sort_direction
        self._cell_sorting_state = None
        self._table_delegate = table_delegate
        self._tooltip = tooltip

    def destroy(self):
        """Destroys the table column definition, clearing its state."""
        self._cell_sorting_state = None
        self._table_delegate = None

    @property
    def name(self):
        """Gets the name of the table column.

        Returns:
            str: The name of the column.
        """
        return self._name

    @property
    def tooltip(self) -> str:
        """Gets the tooltip of the table column.

        Returns:
            str: The tooltip of the column.
        """
        return self._tooltip

    @property
    def alignment(self):
        """Gets the alignment of the table column.

        Returns:
            ui.Alignment: The alignment setting of the column.
        """
        return self._alignment

    @property
    def default_width(self):
        """Gets the default width of the table column.

        Returns:
            ui.AbstractMeasure: The default width of the column.
        """
        return self._default_width

    @property
    def min_width(self):
        """Gets the minimum width of the table column.

        Returns:
            ui.AbstractMeasure: The minimum width of the column.
        """
        return self._min_width

    @property
    def is_sort_column(self):
        """Gets the sort column status.

        Returns:
            bool: True if this is the sort column, otherwise False.
        """
        return self._is_sort_column

    @property
    def sort_direction(self):  # True = ascending, False = descending
        """Gets the sort direction of the table column.

        Returns:
            bool: True if ascending, False if descending.
        """
        return self._sort_direction

    def set_sort(self, is_sort_column: bool = True, sort_direction: bool = True):
        """Sets the sort status for the column.

        Args:
            is_sort_column (bool): Indicates if this is the sort column.
            sort_direction (bool): True for ascending, False for descending.
        """
        self._is_sort_column = is_sort_column
        self._sort_direction = sort_direction
        if self._cell_sorting_state:
            self._cell_sorting_state.visible = self._is_sort_column

    # base implementation to override
    def render_header_inner(self):
        """Renders the inner content of the header."""
        ui.Label(
            self._name,
            tooltip=self._tooltip,
            style={"margin": Styles.MARGIN_DEFAULT},
            alignment=self._alignment
        )

    def render_header(self, sort_fnc: Callable[[Any], None], column_id):
        """Renders the header with sorting functionality.

        Args:
            sort_fnc (Callable[[Any], None]): Function to sort the column.
            column_id: The ID of the column.
        """
        with ui.ZStack():
            with ui.HStack():
                ui.Spacer(width=1)
                with ui.HStack(mouse_pressed_fn=lambda x, y, b, m: sort_fnc(column_id)):
                    self.render_header_inner()
                ui.Spacer(width=1)
            self._cell_sorting_state = ui.VStack()
            with self._cell_sorting_state:
                ui.Spacer(height=ui.Fraction(1))
                ui.Rectangle(
                    height=2,
                    alignment=ui.Alignment.BOTTOM,
                    style={"background_color": Styles.COLOR_BORDER, "margin": 0},
                    visible=self.is_sort_column,
                )

    def render_cell(self, value_model: ui.AbstractValueModel, row_model: ui.AbstractItem, model: ui.AbstractItemModel):
        """Renders a cell in the table.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ui.AbstractItem): The row model for the cell.
            model (ui.AbstractItemModel): The overall table model.
        """
        string = value_model.as_string if value_model else ""
        ui.Label(string, alignment=self._alignment, tooltip=string)

    def hide_active_editor(self, refresh_row: bool = False):
        """Hides the active editor if a column has an active editor."""
        pass


class EditableColumn(TableColumnDef):
    """A class for creating editable table columns.

    This class extends TableColumnDef to provide functionality for editable table cells. It supports double-click editing and row refresh upon edit completion.

    Args:
        name (str): The name of the column.
        alignment (ui.Alignment): The alignment of the column content. Defaults to ui.Alignment.LEFT.
        default_width: The default width of the column. Defaults to ui.Fraction(1).
        min_width: The minimum width of the column. Defaults to ui.Pixel(0).
        is_sort_column (bool): Whether the column is sortable. Defaults to False.
        sort_direction (bool): The direction to sort the column. Specify False for descending and True for ascending. Defaults to False.
        table_delegate (Optional[TableDelegate]): The table delegate this column belongs to.
    """

    def __init__(
        self,
        name: str = "",
        alignment: ui.Alignment = ui.Alignment.LEFT,
        default_width=None,
        min_width=None,
        is_sort_column: bool = False,
        sort_direction: bool = False,  # Specify False if data must be sorted in descending order; otherwise True.
        table_delegate: Optional["TableDelegate"] = None,  # table delegate this column belongs to
    ):
        """Initializes the EditableColumn instance."""
        super().__init__(name, alignment, default_width, min_width, is_sort_column, sort_direction, table_delegate)
        self._edit_subscription = None
        # we refresh the whole row on column update as it may have updated other fields as well
        self.__refresh_row: Dict[Any, Callable[[], None]] = {}

    def destroy(self):
        """Cleans up resources associated with the EditableColumn instance."""
        self._refresh_row_fnc = None
        self._edit_subscription = None
        super().destroy()

    def render_cell(self, value_model: ui.AbstractValueModel, row_model: ui.AbstractItem, model: ui.AbstractItemModel):
        """Renders the cell content.

        Args:
            value_model (ui.AbstractValueModel): The model representing the cell's value.
            row_model (ui.AbstractItem): The model representing the row.
            model (ui.AbstractItemModel): The model representing the entire table.
        """
        string = value_model.as_string
        stack = ui.ZStack(height=0)
        with stack:
            ui.Label(string, alignment=self._alignment, tooltip=string)
            field = ui.StringField(value_model, visible=False)
        # Start editing when double-clicked
        stack.set_mouse_double_clicked_fn(lambda x, y, b, m, f=field: self._on_dbl_clicked(b, f))
        self.__refresh_row[field.model] = lambda fm=field.model, rm=row_model, m=model: (
            self.serialize_and_refresh_row(fm, rm, m)
        )

    # to override
    def serialize_and_refresh_row(self, field_model, row_model: ui.AbstractItem, model: ui.AbstractItemModel):
        """Serializes the field and refreshes the row.

        Args:
            field_model (ui.AbstractValueModel): The model representing the field value.
            row_model (ui.AbstractItem): The model representing the row.
            model (ui.AbstractItemModel): The model representing the entire table.
        """
        pass

    def _on_dbl_clicked(self, button, field):
        """Called when the user clicked the item in TreeView"""
        if button != 0:
            return
        # Make Field visible when double-clicked
        field.visible = True
        field.focus_keyboard()
        # When editing is finished (enter pressed of mouse clicked outside of the viewport)
        self._edit_subscription = field.model.subscribe_end_edit_fn(lambda m, f=field: self._on_end_edit(m, f))

    def _on_end_edit(self, model, field):
        """Called when the user is editing the item and pressed Enter or clicked outside of the item"""
        field.visible = False
        refresh_row_fnc = self.__refresh_row.get(model)
        if refresh_row_fnc:
            refresh_row_fnc()
        self._edit_subscription = None


class TableDelegate(ui.AbstractItemDelegate):
    """Delegate is the representation layer.
    It creates custom widgets for each item in the table as per the TreeView's request.

    Keyword Args:
        model: The model associated with the table.
    """

    def __init__(self, **kwargs):
        """Initializes the TableDelegate instance."""
        super().__init__()
        self._columns: Dict[int, TableColumnDef] = dict()
        self._model = kwargs["model"]
        self._on_item_click = kwargs.get("on_item_click", None)

    def destroy(self):
        """Destroys all columns and clears the columns dictionary."""
        if self._columns:
            for _, c in self._columns.items():
                c.destroy()
            self._columns = dict()
        self._on_item_click = None
        self._model = None

    @property
    def columns(self):
        """Gets the dictionary of table columns.

        Returns:
            Dict[int, TableColumnDef]: The dictionary of table columns.
        """
        return self._columns

    def get_default_column_widths(self):
        """Retrieves the default widths for all columns.

        Returns:
            list: A list of default column widths.
        """
        return [c.default_width for c in self._columns.values()]

    def get_min_column_widths(self):
        """Retrieves the minimum widths for all columns.

        Returns:
            list: A list of minimum column widths.
        """
        return [c.min_width for c in self._columns.values()]

    def hide_all_active_editors(self):
        """Hides all active editors in the columns."""
        for col in self._columns.values():
            col.hide_active_editor()

    def sort(self, column_id: int, sort_direction: int = -1, update_items: bool = True):
        """Sorts the table based on the specified column and direction.

        Args:
            column_id (int): The ID of the column to sort by.
            sort_direction (int): The direction to sort (1 for ascending, 0 for descending).
            update_items (bool): Whether to update items after sorting.
        """
        column = self._columns[column_id]
        for col in self._columns.values():
            if col == column:
                if sort_direction == -1:
                    col.set_sort(True, col.sort_direction if not col.is_sort_column else not col.sort_direction)
                else:
                    col.set_sort(True, sort_direction is True)
            else:
                col.set_sort(False, True)
        if self._model:
            self._model.set_sort(column_id, column.sort_direction, update_items)

    def build_branch(self, model, item: ui.AbstractItem, column_id, level, expanded):
        """Creates a branch widget that opens or closes the subtree.

        Args:
            model (ui.AbstractItemModel): The model of the table.
            item (ui.AbstractItem): The item in the table.
            column_id (int): The ID of the column.
            level (int): The level of the item in the hierarchy.
            expanded (bool): Whether the branch is expanded.
        """
        pass

    def build_header(self, column_id: int):
        """Creates a header for each column.

        Args:
            column_id (int): The ID of the column.
        """
        column = self._columns[column_id]
        if column:
            column.render_header(self.sort, column_id)

    def build_widget(self, model, item: ui.AbstractItem, column_id, level, expanded):
        """Creates a widget for each cell in the table.

        Args:
            model (ui.AbstractItemModel): The model of the table.
            item (ui.AbstractItem): The item in the table.
            column_id (int): The ID of the column.
            level (int): The level of the item in the hierarchy.
            expanded (bool): Whether the branch is expanded.
        """
        column = self._columns[column_id]
        if column:
            value_model = model.get_item_value_model(item, column_id)
            if value_model:
                with ui.ZStack(
                    style=Styles.TABLE_CELL_STYLE,
                    mouse_pressed_fn=lambda x, y, b, _: self._on_item_click(b, item) if self._on_item_click else None,
                ):
                    column.render_cell(value_model, item, model)
