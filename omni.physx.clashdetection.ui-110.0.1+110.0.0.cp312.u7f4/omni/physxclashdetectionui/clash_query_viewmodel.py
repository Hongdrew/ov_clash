# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, cast
from enum import IntEnum, auto
import omni.ui as ui
from omni.physxclashdetectioncore.clash_query import ClashQuery
from .models import SortableSimpleStringModel, TableModel
from .utils import string_match
from .styles import format_timestamp

__all__ = []


class ClashQueryTableColumnEnum(IntEnum):
    """An enumeration.

    This enumeration defines the columns for the Clash Query Table.
    """

    QUERY_NAME = 0
    CREATION_TIMESTAMP = auto()
    LAST_MODIFIED_TIMESTAMP = auto()
    COMMENT = auto()


class ClashQueryTableRowItem(ui.AbstractItem):
    """TableRowItem represents a single row in our table.

    Args:
        row_num (int): The row number in the table.
        clash_query (ClashQuery): The clash query associated with the row.
        row_models (List[ui.AbstractValueModel]): The list of value models for the row.
    """

    def __init__(self, row_num, clash_query: ClashQuery, row_models: List[ui.AbstractValueModel]):
        """Initializes a ClashQueryTableRowItem instance."""
        super().__init__()
        self._row_num = row_num
        self._clash_query = clash_query
        self._row_models = row_models if row_models is not None else []

    def destroy(self):
        """Destroys the ClashQueryTableRowItem instance and clears its data."""
        self._clash_query = None
        self._row_models = []

    @property
    def row_num(self):
        """Gets the row number.

        Returns:
            int: The row number.
        """
        return self._row_num

    @property
    def clash_query(self) -> ClashQuery | None:
        """Gets the clash query.

        Returns:
            ClashQuery: The associated clash query.
        """
        return self._clash_query

    @property
    def row_models(self):
        """Gets the row models.

        Returns:
            List[ui.AbstractValueModel]: The list of row models.
        """
        return self._row_models

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


class ClashQueryTableModel(TableModel):
    """TableModel defines our table structure.
    It maintains a list of TableRowItems, each representing a row in the table.
    """
    def __init__(self):
        super().__init__()
        self._last_row_num = 0

    @staticmethod
    def fill_row(
        row_models: List[ui.AbstractValueModel] | List[None],
        clash_query: ClashQuery
    ):
        """Fills the given row models with data from the clash query.

        Args:
            row_models (List[ui.AbstractValueModel]): List of models to be filled.
            clash_query (ClashQuery): The clash query providing the data.
        """

        def create_or_set(col_idx, model, value):
            if not row_models[col_idx]:
                row_models[col_idx] = model
            row_models[col_idx].set_value(value)

        create_or_set(
            ClashQueryTableColumnEnum.QUERY_NAME,
            SortableSimpleStringModel(),
            clash_query.query_name
        )
        create_or_set(
            ClashQueryTableColumnEnum.CREATION_TIMESTAMP,
            SortableSimpleStringModel(),
            format_timestamp(clash_query.creation_timestamp)
        )
        create_or_set(
            ClashQueryTableColumnEnum.LAST_MODIFIED_TIMESTAMP,
            SortableSimpleStringModel(),
            format_timestamp(clash_query.last_modified_timestamp),
        )
        create_or_set(
            ClashQueryTableColumnEnum.COMMENT,
            SortableSimpleStringModel(),
            clash_query.comment
        )

    def add_row(self, clash_query: ClashQuery, update_items=False) -> ClashQueryTableRowItem:
        """Adds a new row to the table with the provided clash query.

        Args:
            clash_query (ClashQuery): The clash query to add as a new row.
            update_items (bool): Flag to update items after adding.

        Returns:
            ClashQueryTableRowItem: The newly added row item.
        """
        row_models = [None] * len(ClashQueryTableColumnEnum)
        self.fill_row(row_models, clash_query)
        new_row = ClashQueryTableRowItem(self._last_row_num, clash_query, cast(List[ui.AbstractValueModel], row_models))
        self._children.append(new_row)
        if update_items:
            self._item_changed(new_row)
            self.update_items()
        return new_row

    def get_item_value_model_count(self, item: ClashQueryTableRowItem):
        """Returns the number of columns for a given item.

        Args:
            item (ClashQueryTableRowItem): The item to count columns for.

        Returns:
            int: The number of columns.
        """
        return len(ClashQueryTableColumnEnum)

    def update_row(self, table_row: ClashQueryTableRowItem):
        """Updates the given table row with new data.

        Args:
            table_row (ClashQueryTableRowItem): The table row to update.
        """
        if not table_row or not table_row.clash_query:
            return
        self.fill_row(table_row.row_models, table_row.clash_query)
        self._item_changed(table_row)

    def get_row_count(self) -> int:
        """Returns the number of rows in the table.

        Returns:
            int: The number of rows.
        """
        return len(self._children)

    def get_item_value_model(self, item: ClashQueryTableRowItem, column_id):
        """Returns the value model for a given item and column.

        Args:
            item (ClashQueryTableRowItem): The item to get the value model for.
            column_id (int): The column ID to retrieve the model from.

        Returns:
            ui.AbstractValueModel: The value model for the specified column.
        """
        return item._row_models[column_id]

    def delete_row(self, row_item: ClashQueryTableRowItem, update_items=False):
        """Deletes the specified row from the table.

        Args:
            row_item (ClashQueryTableRowItem): The row item to delete.
            update_items (bool): Flag to update items after deletion.
        """
        if row_item:
            row_item.destroy()
        super().delete_row(row_item, update_items)

    def destroy(self):
        """Destroys the table model and clears all rows."""
        for r in self.children:
            r.destroy()
        self._last_row_num = 0
        super().destroy()

    def clear(self):
        """Clears all rows from the table."""
        for r in self.children:
            r.destroy()
        self._last_row_num = 0
        super().clear()
