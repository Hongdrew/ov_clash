# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, Callable, Optional
import omni.ui as ui
from omni.physxclashdetectioncore.clash_query import ClashQuery
from .helpers import get_clash_query_summary

__all__ = []


class ClashQueryComboBoxItem(ui.AbstractItem):
    """A class for creating combo box items for clash queries.

    This class generates items to be used in a combo box, representing different clash queries with detailed information including dynamic/static status, tolerance type, and object paths.

    Args:
        clash_query (ClashQuery): The clash query object containing the details for the combo box item.
    """

    def __init__(self, clash_query: ClashQuery):
        """Initializes the ClashQueryComboBoxItem instance."""
        super().__init__()
        self._clash_query = clash_query
        # our UI doesn't work properly with exactly equal combo box strings. Let's make them always unique.
        text = f"{get_clash_query_summary(clash_query)}###{clash_query.identifier}"
        self.model = ui.SimpleStringModel(text)

    def destroy(self):
        """Destroys the ClashQueryComboBoxItem instance, releasing resources."""
        self._clash_query = None
        self.model = None

    def __eq__(self, other):
        same_instance = isinstance(other, self.__class__)
        if not same_instance:
            return False
        return self.model == other.model

    def __lt__(self, other):  # sorting
        if not self.model or not other or not other.model:
            return False
        return self.model.as_string < other.model.as_string

    @property
    def clash_query(self):
        """Gets the ClashQuery instance.

        Returns:
            ClashQuery: The current ClashQuery instance.
        """
        return self._clash_query


class ClashQueryDropdownModel(ui.AbstractItemModel):
    """A class for managing a dropdown model with clash query items.

    This class handles the selection and management of items within a dropdown menu, specifically designed to manage instances of `ClashQueryComboBoxItem`. It facilitates item selection, clearing, and updating, along with executing a callback function when the selected item changes.

    Args:
        items (list): A list of `ClashQueryComboBoxItem` objects to be managed by the dropdown.
        value_changed_fnc (function): A callback function to be executed when the selected item's value changes.
    """

    def __init__(self, items: List[ClashQueryComboBoxItem], value_changed_fnc: Callable[[Optional[ClashQuery]], None]):
        """Initializes the ClashQueryDropdownModel instance."""
        super().__init__()
        self._value_changed_fnc = value_changed_fnc
        self._current_index = ui.SimpleIntModel(-1)
        self._current_index.add_value_changed_fn(lambda _: self._item_changed(None))  # type: ignore
        self.add_item_changed_fn(self._on_item_changed)
        self._items = items

    def destroy(self):
        """Destroys the ClashQueryDropdownModel instance, clearing items and resetting internal state."""
        self.clear_items()
        self._items = None
        self._value_changed_fnc = None

    @property
    def items(self):
        """Gets the list of items in the model.

        Returns:
            list: The list of items.
        """
        return self._items

    def clear_items(self):
        """Clears all items from the model."""
        if self._items:
            for item in self._items:
                item.destroy()
            self._items.clear()

    def items_changed(self):
        """To be called when items change."""
        self._item_changed(None)  # type: ignore

    def _on_item_changed(self, model, item):
        if self._items is not None and len(self._items) > 0:
            idx = self._current_index.get_value_as_int()
            if idx >= len(self._items):
                self._current_index.set_value(len(self._items) - 1)
            else:
                if self._value_changed_fnc:
                    self._value_changed_fnc(self._items[idx].clash_query if idx != -1 else None)

    def select_item_index(self, index):
        """Selects an item based on the given index.

        Args:
            index (int): The index of the item to select.
        """
        self._current_index.set_value(index)

    def selected_query_id(self) -> int:
        """Returns query_id of selected query. Returns -1 if nothing is selected.

        Returns:
            int: The identifier of the selected query or -1 if none selected.
        """
        idx = self._current_index.get_value_as_int()
        if self._items:
            if idx != -1 and len(self._items) > idx:
                return self._items[idx].clash_query.identifier
        return -1

    # AbstractItemModel interfaces
    def get_item_value_model(self, item=None, column_id=0):
        """Retrieves the value model for a given item and column.

        Args:
            item (optional): The item for which to get the value model.
            column_id (int): The column identifier.

        Returns:
            ui.SimpleStringModel or ui.SimpleIntModel: The value model associated with the item or current index.
        """
        if item is None:
            return self._current_index
        return item.model  # type: ignore

    def get_item_children(self, item):
        """Gets the children of the given item.

        Args:
            item: The item whose children are to be retrieved.

        Returns:
            list: The children of the item.
        """
        return self._items
