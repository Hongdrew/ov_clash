# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Optional
import omni.ui as ui
from omni.physxclashdetectioncore.clash_info import ClashInfo

__all__ = []


class ClashInfoDropdownModel(ui.AbstractItemModel):
    """A class for managing a dropdown model for clash information.

    This class extends the ui.AbstractItemModel to handle a list of items and their associated clash information. It triggers a callback function when the selected value changes.

    Args:
        items (list): A list of items to be displayed in the dropdown.
        value_changed_fnc (function): A callback function to be called when the value changes.
    """

    def __init__(self, items, value_changed_fnc):
        """Initializes the ClashInfoDropdownModel."""
        super().__init__()
        self._clash_info = None
        self._value_changed_fnc = value_changed_fnc
        self._current_index = ui.SimpleIntModel(-1)
        self._current_index.add_value_changed_fn(lambda _: self._item_changed(None))  # type: ignore
        self.add_item_changed_fn(self._on_item_changed)
        self._items = items  # List[ClashStateComboBoxItem]

    def destroy(self):
        """Cleans up and destroys the model."""
        self._items = None
        self._value_changed_fnc = None
        self._clash_info = None

    @property
    def items(self):
        """Gets the list of items.

        Returns:
            list: List of items.
        """
        return self._items

    def _on_item_changed(self, model, item):
        if self._items is not None and len(self._items) > 0:
            idx = self._current_index.get_value_as_int()
            if idx >= len(self._items):
                self._current_index.set_value(len(self._items) - 1)
            else:
                if self._value_changed_fnc:
                    self._value_changed_fnc(self._items[idx], self._clash_info)

    def set_clash_info(self, clash_info: Optional[ClashInfo]):
        """Sets the clash information for the model.

        Args:
            clash_info (ClashInfo): The clash information to set.
        """
        self._clash_info = clash_info

    def select_item_index(self, index):
        """Selects an item by its index.

        Args:
            index (int): The index of the item to select.
        """
        self._current_index.set_value(index)

    # AbstractItemModel interfaces
    def get_item_value_model(self, item=None, column_id=0):
        """Gets the value model of an item.

        Args:
            item (optional): The item to get value model from.
            column_id (int): The column ID of the item.

        Returns:
            SimpleIntModel: The value model of the item.
        """
        if item is None:
            return self._current_index
        return item.model

    def get_item_children(self, item):
        """Gets the children of an item.

        Args:
            item: The item to get children from.

        Returns:
            list: The children of the item.
        """
        return self._items
