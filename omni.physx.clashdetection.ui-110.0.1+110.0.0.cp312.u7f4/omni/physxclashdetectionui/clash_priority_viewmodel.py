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
from .clash_info_dropdown_viewmodel import ClashInfoDropdownModel

__all__ = []


class ClashPriorityStr:
    """A utility class for handling clash priority strings.

    This class provides a static method for converting an integer priority value into a formatted string representation. It is designed to be used for formatting and displaying priority levels in a consistent manner across the application.
    """

    @staticmethod
    def get_priority_str(priority: int) -> str:
        """Converts a priority integer to a formatted string.

        Args:
            priority (int): The priority level to be formatted.

        Returns:
            str: Formatted priority string.
        """
        # to help the most common strings to get interned (reused), state them explicitly
        if priority == 0:
            return "P-0"
        elif priority == 1:
            return "P-1"
        elif priority == 2:
            return "P-2"
        elif priority == 3:
            return "P-3"
        elif priority == 4:
            return "P-4"
        elif priority == 5:
            return "P-5"
        return f"P-{priority}"


class ClashPriorityComboBoxItem(ui.AbstractItem):
    """A class representing an item in a combo box with a specific clash priority.

    This class inherits from `ui.AbstractItem` and is used to manage items in a combo box that are sorted based on their string representation of a clash priority.

    Args:
        clash_priority (int): The priority value for this combo box item.
    """

    def __init__(self, clash_priority: int):
        """Initializes the ClashPriorityComboBoxItem with the given clash priority."""
        super().__init__()
        self._clash_priority = clash_priority
        self.model = ui.SimpleStringModel(ClashPriorityStr.get_priority_str(self._clash_priority))

    def __lt__(self, other):  # sorting
        return self.model.as_string < other.model.as_string  # sort by string representation, not by internal value

    @property
    def clash_priority(self):
        """Gets the clash priority.

        Returns:
            int: The clash priority value.
        """
        return self._clash_priority


class ClashPriorityComboBoxModel(ClashInfoDropdownModel):
    """A class for managing the model of a combo box for clash priorities.

    This class is designed to handle the data for a combo box that displays clash priorities.
    It extends the ClashInfoDropdownModel and provides integration with the UI framework.

    Args:
        items (list): A list of items to be displayed in the combo box.
        value_changed_fnc (function): A callback function that is called when the value of the combo box changes.
    """

    def __init__(self, items, value_changed_fnc):
        """Initializes the ClashPriorityComboBoxModel with given items and callback function."""
        super().__init__(items, value_changed_fnc)
