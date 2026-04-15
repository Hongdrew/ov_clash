# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ui as ui
from .table_delegates import TableColumnDef, EditableColumn, TableDelegate
from .clash_query_viewmodel import ClashQueryTableRowItem, ClashQueryTableColumnEnum, ClashQueryTableModel
from .settings import ExtensionSettings

__all__ = []


class LastModifiedColumn(TableColumnDef):
    """A class for defining the 'Last Modified' column in a table.

    This class is used to represent the 'Last Modified' column within the Clash Query table. It sets up the column with a specific title, alignment, and width, and is responsible for rendering each cell in this column with the appropriate timestamp and user information.
    """

    def __init__(self):
        """Initializes the LastModifiedColumn with specific alignment and size."""
        super().__init__("Last Modified", ui.Alignment.LEFT, 160, 60)

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashQueryTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell with the last modified timestamp and username.

        Args:
            value_model (ui.AbstractValueModel): Model containing the timestamp value.
            row_model (ClashQueryTableRowItem): Model containing the row data.
            model (ui.AbstractItemModel): Model containing the table data.
        """
        timestamp = value_model.as_string
        username = row_model.clash_query.last_modified_by if row_model.clash_query else ""
        tooltip = f"{timestamp} by {username}"
        ui.Label(timestamp, alignment=self.alignment, tooltip=tooltip)


class NameColumn(EditableColumn):
    """A class representing a column for editing query names in a table.

    This class is used to define and manage the behavior and presentation of the 'Query Name' column in a table.
    It provides methods to handle the serialization and refreshing of row data when the query name is edited.
    """

    def __init__(self):
        """Initializes the NameColumn with specific parameters."""
        super().__init__("Query Name", ui.Alignment.LEFT, 160, 60)

    def serialize_and_refresh_row(self, field_model, row_model: ClashQueryTableRowItem, model: ClashQueryTableModel):
        """Serializes the query name and refreshes the row model.

        Args:
            field_model (ui.AbstractValueModel): Model containing the query name.
            row_model (ClashQueryTableRowItem): The row item containing the clash query.
            model (ClashQueryTableModel): The table model to be updated.
        """
        cq = row_model.clash_query
        if cq:
            cq.query_name = field_model.as_string
            if ExtensionSettings.clash_data and ExtensionSettings.clash_data.update_query(cq, True):
                model.update_row(row_model)


class CommentColumn(EditableColumn):
    """A class for managing and editing the 'Comment' column in a clash query table.

    This class allows for the creation and management of the 'Comment' field within the table, providing methods to initialize the column, serialize the data, and refresh the row in the table model.
    """

    def __init__(self):
        """Initializes the CommentColumn with a specific title, alignment, and size."""
        super().__init__("Comment", ui.Alignment.LEFT, ui.Fraction(1), 20)

    def serialize_and_refresh_row(self, field_model, row_model: ClashQueryTableRowItem, model: ClashQueryTableModel):
        """Serializes the comment field and refreshes the row.

        Args:
            field_model (ui.AbstractValueModel): Model containing the comment data.
            row_model (ClashQueryTableRowItem): Row model to update.
            model (ClashQueryTableModel): Table model to refresh.
        """
        cq = row_model.clash_query
        if cq:
            cq.comment = field_model.as_string
            if ExtensionSettings.clash_data and ExtensionSettings.clash_data.update_query(cq, True):
                model.update_row(row_model)


class ClashQueryTableDelegate(TableDelegate):
    """Delegate is the representation layer.
    It creates custom widgets for each item in the table as per the TreeView's request.

    Keyword Args:
        columns (dict): A dictionary mapping column enums to their respective column definitions.
        alignment (ui.Alignment): The alignment of the table cells.
        fraction (ui.Fraction): The fraction of the space occupied by the filler column.
    """

    def __init__(self, **kwargs):
        """Initializes the ClashQueryTableDelegate class."""
        super().__init__(**kwargs)
        self._columns = {
            ClashQueryTableColumnEnum.QUERY_NAME: NameColumn(),
            ClashQueryTableColumnEnum.CREATION_TIMESTAMP: TableColumnDef("First Created", ui.Alignment.LEFT, 160, 60),
            ClashQueryTableColumnEnum.LAST_MODIFIED_TIMESTAMP: LastModifiedColumn(),
            ClashQueryTableColumnEnum.COMMENT: CommentColumn(),
        }
