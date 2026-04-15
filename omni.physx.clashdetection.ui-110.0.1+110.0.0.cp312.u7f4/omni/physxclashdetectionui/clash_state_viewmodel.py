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
import carb
from omni.physxclashdetectioncore.clash_info import ClashState
from .clash_info_dropdown_viewmodel import ClashInfoDropdownModel

__all__ = []


class ClashStateStr:
    """A utility class for converting ClashState enums to their string representations.

    This class provides a static method to convert different ClashState enum values into corresponding human-readable string labels. It is useful for displaying clash states in a user-friendly format in various UI components.

    """

    @staticmethod
    def get_state_str(clash_state: ClashState) -> str:
        """Converts a ClashState enum value to its corresponding string representation.

        Args:
            clash_state (ClashState): The state to convert to string.

        Returns:
            str: The string representation of the clash state.
        """
        if clash_state == ClashState.NEW:
            return "New"
        elif clash_state == ClashState.APPROVED:
            return "Approved"
        elif clash_state == ClashState.RESOLVED:
            return "Resolved"
        elif clash_state == ClashState.CLOSED:
            return "Closed"
        elif clash_state == ClashState.INVALID:
            return "Invalid"
        elif clash_state == ClashState.ACTIVE:
            return "Active"
        carb.log_error("Unknown clash state")
        return "<???>"


class ClashStateComboBoxItem(ui.AbstractItem):
    """A class representing a combo box item for clash states.

    This class inherits from the omni.ui.AbstractItem and is used to create items in a combo box that represent various clash states. It provides functionality to initialize the item with a given clash state and to compare items based on their string representation.

    Args:
        clash_state (ClashState): The initial clash state to be represented by this combo box item.
    """

    def __init__(self, clash_state: ClashState):
        """Initializes the ClashStateComboBoxItem with a given clash state."""
        super().__init__()
        self._clash_state = clash_state
        self.model = ui.SimpleStringModel(ClashStateStr.get_state_str(self._clash_state))

    def __lt__(self, other):  # sorting
        return self.model.as_string < other.model.as_string

    @property
    def clash_state(self):
        """Gets the current clash state.

        Returns:
            ClashState: The current clash state.
        """
        return self._clash_state


class ClashStateComboBoxModel(ClashInfoDropdownModel):
    """A model for managing clash state combo box items.

    This class extends the ClashInfoDropdownModel to handle items representing different clash states in a combo box. It allows for the initialization of these items and defines a callback function for when the selected value changes.

    Args:
        items (list): A list of items to be displayed in the combo box.
        value_changed_fnc (function): A function to be called when the selected value changes.
    """

    def __init__(self, items, value_changed_fnc):
        """Initializes the ClashStateComboBoxModel with the given items and value change function."""
        super().__init__(items, value_changed_fnc)
