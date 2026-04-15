# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List
import omni.ui as ui
from enum import IntEnum, auto
from omni.physxclashdetectioncore.clash_info import ClashInfo
from .clash_state_viewmodel import ClashStateStr
from .clash_priority_viewmodel import ClashPriorityStr
from .pic_viewmodel import PersonInChargeColumnModel
from .models import (
    SortableSimpleStringModel,
    SortableSimpleIntModel,
    SortableSimpleFloatModel,
    SortablePathModel,
    TableModel,
)
from omni.physxclashdetectioncore.clash_info import ClashState
from .utils import get_yes_no_str, get_time_delta_str, string_match
from .styles import format_timestamp

__all__ = []


class ClashDetectTableColumnEnum(IntEnum):
    """An enumeration.

    This enumeration defines the columns used in the clash detection table.
    """

    OVERLAP_NUM = 0
    PRESENT = auto()
    OVERLAP_TYPE = auto()
    MIN_DISTANCE = auto()
    TOLERANCE = auto()
    LOCAL_COLL_DEPTH = auto()
    DEPTH_EPSILON = auto()
    PEN_DEPTH_PX = auto()
    PEN_DEPTH_NX = auto()
    PEN_DEPTH_PY = auto()
    PEN_DEPTH_NY = auto()
    PEN_DEPTH_PZ = auto()
    PEN_DEPTH_NZ = auto()
    OVERLAP_TRIS = auto()
    CLASH_START_TIME = auto()
    CLASH_END_TIME = auto()
    NUM_CLASH_RECORDS = auto()
    OBJECT_A = auto()
    OBJECT_B = auto()
    STATE = auto()
    PRIORITY = auto()
    PIC = auto()
    CREATION_TIMESTAMP = auto()
    LAST_MODIFIED_TIMESTAMP = auto()
    COMMENT = auto()


class ClashDetectTableRowItem(ui.AbstractItem):
    """TableRowItem represents a single row in our table.

    Args:
        row_num (int): The number of the row.
        clash_info (ClashInfo): Information related to the clash.
        row_models (List[ui.AbstractValueModel]): Models representing the row values.
    """

    def __init__(self, row_num, clash_info: ClashInfo, row_models: List[ui.AbstractValueModel]):
        """Initializes a ClashDetectTableRowItem instance."""
        super().__init__()
        self._row_num = row_num
        self._clash_info = clash_info
        self._row_models = row_models if row_models is not None else []

    def destroy(self):
        """Destroys the ClashDetectTableRowItem by clearing its clash info and row models."""
        self._clash_info = None
        self._row_models = []

    @property
    def row_num(self):
        """Gets the row number.

        Returns:
            int: The row number.
        """
        return self._row_num

    @property
    def clash_info(self) -> ClashInfo | None:
        """Gets the clash information associated with this row.

        Returns:
            ClashInfo: The clash information.
        """
        return self._clash_info

    @property
    def object_a_path(self) -> str:
        """Gets the clashing object A path associated with this row.

        Returns:
            str: The object A path.
        """
        return self._clash_info.object_a_path if self._clash_info else ""

    @property
    def object_b_path(self) -> str:
        """Gets the clashing object B path associated with this row.

        Returns:
            str: The object B path.
        """
        return self._clash_info.object_b_path if self._clash_info else ""

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
        """Checks if the row matches the given search text.

        Args:
            search_text (str): The text to search for.

        Returns:
            bool: True if the row matches the search text.
        """
        # NOTE: this check ignores specific formatting for each cell
        if not search_text:
            return True
        search_text_lc = search_text.lower()
        for col in self._row_models:
            if not col:
                continue
            if isinstance(col, SortablePathModel):
                if string_match(search_text_lc, col.full_path.lower()):
                    return True
                if string_match(search_text_lc, col.name.lower()):
                    return True
            else:
                if string_match(search_text_lc, col.as_string.lower()):
                    return True
        return False


class ClashDetectTableModel(TableModel):
    """
    TableModel defines our table structure.
    It maintains a list of TableRowItems, each representing a row in the table.
    """

    def __init__(self):
        super().__init__()
        self._last_row_num = 0

        # Models cache for reuse: these are used to avoid creating duplicate models for read-only rows
        self._item_yes = SortableSimpleStringModel(get_yes_no_str(True))
        self._item_no = SortableSimpleStringModel(get_yes_no_str(False))
        self._item_priority_zero = SortableSimpleStringModel(ClashPriorityStr.get_priority_str(0))
        self._item_state_new = SortableSimpleStringModel(ClashStateStr.get_state_str(ClashState.NEW))

        self._item_one_int = SortableSimpleIntModel(1)
        self._item_zero_float = SortableSimpleFloatModel(0.0)
        self._item_minus_one_float = SortableSimpleFloatModel(-1.0)
        self._item_zero_time = SortableSimpleStringModel(get_time_delta_str(0))

        self._item_overlap_type_dup = SortableSimpleStringModel("Dup")
        self._item_overlap_type_hard = SortableSimpleStringModel("Hard")
        self._item_overlap_type_soft = SortableSimpleStringModel("Soft")
        self._item_overlap_type_contact = SortableSimpleStringModel("Contact")
        self._item_overlap_type_unknown = SortableSimpleStringModel("???")

        self._item_empty_pic = PersonInChargeColumnModel()

    def create_row(self, row_num, ci: ClashInfo):
        """Creates a list of value models for a table row based on clash information.

        Args:
            row_num (int): The row number to fill.
            ci (ClashInfo): Information about the clash.

        Returns:
            List[ui.AbstractValueModel]: List of value models representing the row data.
        """

        def get_clash_type_model(clash_info: ClashInfo) -> ui.SimpleStringModel:
            """Get a model for a clash type."""
            if clash_info.is_duplicate:
                return self._item_overlap_type_dup
            if clash_info.is_hard_clash:
                return self._item_overlap_type_hard
            if clash_info.is_soft_clash:
                return self._item_overlap_type_soft
            if clash_info.is_contact:
                return self._item_overlap_type_contact
            return self._item_overlap_type_unknown

        row_models = [
            SortableSimpleIntModel(row_num + 1),
            self._item_yes if ci.present else self._item_no,
            get_clash_type_model(ci),
            SortableSimpleFloatModel(ci.min_distance) if ci.min_distance != 0 else self._item_zero_float,
            SortableSimpleFloatModel(ci.tolerance) if ci.tolerance != 0 else self._item_zero_float,
            SortableSimpleFloatModel(ci.max_local_depth) if ci.max_local_depth != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.depth_epsilon) if ci.depth_epsilon != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_px) if ci.penetration_depth_px != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_nx) if ci.penetration_depth_nx != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_py) if ci.penetration_depth_py != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_ny) if ci.penetration_depth_ny != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_pz) if ci.penetration_depth_pz != -1.0 else self._item_minus_one_float,
            SortableSimpleFloatModel(ci.penetration_depth_nz) if ci.penetration_depth_nz != -1.0 else self._item_minus_one_float,
            SortableSimpleIntModel(ci.overlap_tris),
            SortableSimpleStringModel(get_time_delta_str(ci.start_time)) if ci.start_time != 0.0 else self._item_zero_time,
            SortableSimpleStringModel(get_time_delta_str(ci.end_time)) if ci.end_time != 0.0 else self._item_zero_time,
            SortableSimpleIntModel(ci.num_records) if ci.num_records != 1 else self._item_one_int,
            SortablePathModel(ci.object_a_path),
            SortablePathModel(ci.object_b_path),
            SortableSimpleStringModel(ClashStateStr.get_state_str(ci.state)) if ci.state != ClashState.NEW else self._item_state_new,
            SortableSimpleStringModel(ClashPriorityStr.get_priority_str(ci.priority)) if ci.priority != 0 else self._item_priority_zero,
            PersonInChargeColumnModel(ci.person_in_charge) if ci.person_in_charge else self._item_empty_pic,
            SortableSimpleStringModel(format_timestamp(ci.creation_timestamp)),
            SortableSimpleStringModel(format_timestamp(ci.last_modified_timestamp)),
            SortableSimpleStringModel(ci.comment),
        ]

        assert len(row_models) == len(ClashDetectTableColumnEnum)

        return row_models

    def get_item_value_model_count(self, item: ClashDetectTableRowItem):
        """Returns the number of columns for a given item.

        Args:
            item (ClashDetectTableRowItem): The row item.

        Returns:
            int: The number of columns in the table.
        """
        return len(ClashDetectTableColumnEnum)

    def add_row(self, ci: ClashInfo, update_items=False) -> ClashDetectTableRowItem:
        """Adds a new row to the table.

        Args:
            ci (ClashInfo): Information about the clash.
            update_items (bool): Whether to update items after adding the row.

        Returns:
            ClashDetectTableRowItem: The newly added row item.
        """
        row_models = self.create_row(self._last_row_num, ci)
        self._last_row_num = self._last_row_num + 1
        new_row = ClashDetectTableRowItem(self._last_row_num, ci, row_models)
        self._children.append(new_row)
        if update_items:
            self._item_changed(new_row)
            self.update_items()
        return new_row

    def add_row_item(self, row_item: ClashDetectTableRowItem, update_items=False):
        """Adds an existingrow item to the table.
        """
        self._children.append(row_item)
        if update_items:
            self._item_changed(row_item)
            self.update_items()

    def update_row(self, table_row: ClashDetectTableRowItem):
        """Updates a specific row in the table.

        Args:
            table_row (ClashDetectTableRowItem): The row item to update.
        """
        if not table_row.clash_info:
            return
        table_row.row_models = self.create_row(table_row.row_num, table_row.clash_info)
        self._item_changed(table_row)

    def get_item_value_model(self, item: ClashDetectTableRowItem, column_id):
        """Return the value model for a given item and column.

        Args:
            item (ClashDetectTableRowItem): The row item.
            column_id (int): The column ID.

        Returns:
            ui.AbstractValueModel: The value model for the specified column.
        """
        if item is None:
            return None
        return item._row_models[column_id]

    def delete_row(self, row_item: ClashDetectTableRowItem, update_items=False):
        """Deletes a specific row from the table.

        Args:
            row_item (ClashDetectTableRowItem): The row item to delete.
            update_items (bool): Whether to update items after deleting the row.
        """
        if row_item:
            row_item.destroy()
        super().delete_row(row_item, update_items)

    def destroy(self):
        """Destroys the table model and its children."""
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
