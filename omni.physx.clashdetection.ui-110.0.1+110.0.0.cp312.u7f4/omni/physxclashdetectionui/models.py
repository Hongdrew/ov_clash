# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# General purpose models

from typing import Dict, List
import carb
import omni.ui as ui
from .table_delegates import TableColumnDef
from .filtering import parse_filter_expression, apply_filter

__all__ = []


class SortableSimpleStringModel(ui.SimpleStringModel):
    """A class for managing and sorting string values.

    This class extends the SimpleStringModel to include functionality for comparison, allowing instances to be sorted based on their string values.

    Args:
        default_value (str): The initial string value for the model.
    """

    def __init__(self, default_value: str = "") -> None:
        """Initializes a SortableSimpleStringModel instance."""
        super().__init__(default_value)

    def __lt__(self, other):  # sorting
        return self.as_string < other.as_string


class SortableSimpleIntModel(ui.SimpleIntModel):
    """A class for handling sortable integer models.

    This class extends the functionality of SimpleIntModel by adding support for sorting.

    Args:
        default_value (int): The default integer value for the model.

    Keyword Args:
        as_int (int): The integer representation of the model.
        as_string (str): The string representation of the model.
        as_float (float): The float representation of the model.
    """

    def __init__(self, default_value: int = 0, **kwargs) -> None:
        """Initializes the SortableSimpleIntModel with an optional default value and additional keyword arguments."""
        super().__init__(default_value, **kwargs)

    def __lt__(self, other):  # sorting
        return self.as_int < other.as_int


class SortableSimpleFloatModel(ui.SimpleFloatModel):
    """A class for managing and sorting float values.

    This class extends the SimpleFloatModel to include comparison operations, enabling sorting of float values.

    Args:
        default_value (float): The initial float value for the model.

    Keyword Args:
        referencer: A reference to another model or component.
        controller: The controller managing the model.
        readonly (bool): Indicates if the model is read-only.
        visible (bool): Indicates if the model is visible.
        enabled (bool): Indicates if the model is enabled.
        tool_tip (str): A tooltip for the model.
        type_name (str): The type name for the model.
        __meta__: Metadata for the model.
    """

    def __init__(self, default_value: float = 0.0, **kwargs) -> None:
        """Initializes the SortableSimpleFloatModel with a default float value."""
        super().__init__(default_value, **kwargs)

    def __lt__(self, other):  # sorting
        return self.as_float < other.as_float


class SortablePathModel(SortableSimpleStringModel):
    """A class for handling sortable path strings.

    This class extends SortableSimpleStringModel to provide additional functionality for handling and sorting strings that represent paths. It overrides the default sorting behavior to compare the full paths of the strings.

    Args:
        default_value (str): The default value of the path string.
    """

    def __init__(self, default_value: str = "") -> None:
        """Initializes the SortablePathModel with a default string value."""
        super().__init__(default_value)

    def __lt__(self, other):  # sorting
        return self.full_path < other.full_path

    @property
    def full_path(self) -> str:
        """Gets the full path as a string.

        Returns:
            str: The full path string.
        """
        return self.as_string

    @property
    def name(self) -> str:
        """Gets the name derived from the full path.

        Returns:
            str: The name extracted from the full path.
        """
        full_path = self.full_path
        last_slash_index = full_path.rfind("/")
        if last_slash_index != -1:
            return full_path[last_slash_index + 1:]
        return full_path


class TableModel(ui.AbstractItemModel):
    """
    TableModel defines our table structure.
    It maintains a list of TableRowItems, each representing a row in the table.
    """

    def __init__(self):
        """Initializes the TableModel instance."""
        super().__init__()
        self._children = []
        self._filtered_children = []
        self._search_text = ""
        self._sort_column_id = -1  # -1 means no sort
        self._sort_direction = False  # True = ascending, False = descending
        self._filter_expression = ""
        self._filter_expression_tree = None
        self._column_dict: dict[str, int] = {}

    def destroy(self):
        """Destroys the TableModel, clearing all children and filtered children."""
        self._children = []
        self._filtered_children = []
        self._filter_expression = ""
        self._filter_expression_tree = None
        self._column_dict = {}

    @property
    def children(self):
        """Gets the list of child items.

        Returns:
            list: List of child items.
        """
        return self._children

    @property
    def filtered_children(self):
        """Gets the list of filtered child items.

        Returns:
            list: List of filtered child items.
        """
        return self._filtered_children

    def set_filter_text(self, search_text: str):
        """Sets the filter text and updates items.

        Args:
            search_text (str): The text to filter items.
        """
        self._search_text = search_text
        self.update_items()

    def set_filter_expression(self, filter_expression: str, columns: Dict[int, TableColumnDef]) -> bool:
        """
        Set the filter expression for the table and update the filtered items.

        The filter expression is a string parsed into a filter tree (FilterNode) using the Filtering class.
        This tree is used to filter table rows based on the provided column definitions.

        Args:
            filter_expression (str): The filter expression string to apply.
            columns (Dict[int, TableColumnDef]): Mapping of column indices to column definitions.

        Returns:
            bool: True if the filter was applied successfully, False if the expression was invalid.
        """
        if self._filter_expression == filter_expression:
            return True
        if not filter_expression or len(filter_expression) == 0:  # remove filter
            self._filter_expression = ""
            self._filter_expression_tree = None
            self._column_dict = {}
            self.update_items()
            return True
        new_expression_tree = parse_filter_expression(filter_expression)
        if new_expression_tree is None:
            carb.log_error(f"Invalid filter expression: {filter_expression}")
            return False
        self._column_dict: dict[str, int] = {col.name.upper(): i for i, col in columns.items()}  # upper-cased column names
        self._filter_expression = filter_expression
        self._filter_expression_tree = new_expression_tree
        self.update_items()
        return True

    @property
    def search_text(self):
        """Gets the current search text.

        Returns:
            str: The current search text.
        """
        return self._search_text

    @property
    def sort_column_id(self):
        """Gets the current sort column ID.

        Returns:
            int: The current sort column ID.
        """
        return self._sort_column_id

    @property
    def sort_direction(self):
        """Gets the current sort direction.

        Returns:
            bool: The current sort direction.
        """
        return self._sort_direction

    def clear(self):
        """Clears all children and filtered children, and notifies item change."""
        self._children = []
        self._filtered_children = []
        self._item_changed(None)  # type: ignore

    def set_sort(self, sort_column_id: int, sort_direction: bool = True, update_items: bool = True):
        """Sets the sort column ID and direction, optionally updates items.

        Args:
            sort_column_id (int): The ID of the column to sort.
            sort_direction (bool): The direction of the sort. Default is True (ascending).
            update_items (bool): Whether to update items. Default is True.
        """
        self._sort_column_id = sort_column_id
        self._sort_direction = sort_direction
        if update_items:
            self.update_items()

    def update_items(self):
        """Updates the list of filtered children based on the search text, filter expression, and sort order."""
        def get_column_value(row: List[ui.AbstractValueModel], col_name: str) -> object:
            column_index = self._column_dict.get(col_name, None)
            val = row[column_index] if column_index is not None else None
            if val is None:
                return None
            if isinstance(val, ui.SimpleStringModel):
                return val.as_string.upper()  # we are upper-casing strings in the expression tree so we can work case insensitive (always in upper case)
            if isinstance(val, ui.SimpleIntModel):
                return val.as_int
            if isinstance(val, ui.SimpleFloatModel):
                return val.as_float
            return val.as_string

        if self._search_text or self._filter_expression_tree:
            self._filtered_children = [
                c
                for c in self._children
                if (
                    c.matches_filter(
                        self._search_text
                    )
                    and apply_filter(
                        self._filter_expression_tree,
                        lambda col_name: get_column_value(c.row_models, col_name)
                    )
                )
            ]
        else:
            self._filtered_children = self._children.copy()

        if self._filtered_children and len(self._filtered_children) > 0:
            num_rows = len(self._filtered_children[0].row_models)
            if self._sort_column_id > -1 and self._sort_column_id < num_rows:
                self._filtered_children.sort(
                    key=lambda c: c.row_models[self._sort_column_id], reverse=not self._sort_direction
                )
        self._item_changed(None)  # type: ignore

    def get_item_with_identifier(self, identifier: int):
        """Gets an item with the specified identifier.

        Args:
            identifier (int): The identifier of the item to find.

        Returns:
            ui.AbstractItem: The item with the given identifier, or None if not found.
        """
        for item in self._filtered_children:
            if item.clash_info.identifier == identifier:
                return item
        return None

    def get_item_children(self, item: ui.AbstractItem):
        """Returns the children of the given item.
        As we are dealing with a flat list, we only return the children of root.
        For any other item, return an empty list.

        Args:
            item (ui.AbstractItem): The item to get children for.

        Returns:
            list: The list of children for the given item.
        """
        if item is not None:
            return []
        return self._filtered_children

    def delete_row(self, row_item: ui.AbstractItem, update_items=False):
        """Deletes the specified row item, optionally updates items.

        Args:
            row_item (ui.AbstractItem): The row item to delete.
            update_items (bool): Whether to update items after deletion.
        """
        self._children.remove(row_item)
        if update_items:
            self.update_items()
