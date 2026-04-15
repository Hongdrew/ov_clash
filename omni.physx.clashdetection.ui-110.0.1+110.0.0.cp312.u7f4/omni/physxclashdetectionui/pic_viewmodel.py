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
from .pic_provider import PersonInCharge
from .settings import ExtensionSettings
from .clash_info_dropdown_viewmodel import ClashInfoDropdownModel
from .models import SortableSimpleStringModel

__all__ = []


class PersonInChargeColumnModel(SortableSimpleStringModel):
    """A class for managing and displaying the person in charge column.

    This class extends the SortableSimpleStringModel to provide functionality for handling the person in charge data, including setting and retrieving the person's information based on their username.

    Args:
        pic_username (str): The username of the person in charge.
    """

    def __init__(self, pic_username: str = ""):
        """Initializes the PersonInChargeColumnModel instance."""
        super().__init__(pic_username)
        self._pic = None
        self.set_value(pic_username)

    def set_value(self, value: str) -> None:
        """Sets the value for the PersonInChargeColumnModel.

        Args:
            value (str): The value to be set.
        """
        assert ExtensionSettings.users is not None
        self._pic = ExtensionSettings.users.get_person(value)
        super().set_value(self._pic.full_name)

    @property
    def pic(self):
        """Gets the person in charge.

        Returns:
            PersonInCharge: The person in charge object.
        """
        return self._pic


class PersonInChargeComboBoxItem(ui.AbstractItem):
    """A class representing an item in a ComboBox for a person in charge.

    This class encapsulates the logic for handling a person in charge item within a ComboBox, providing sorting capabilities and access to the underlying person in charge details.

    Args:
        pic (PersonInCharge): The person in charge object to be represented in the ComboBox item.
    """

    def __init__(self, pic: PersonInCharge):
        """Initializes the PersonInChargeComboBoxItem instance."""
        super().__init__()
        self._pic = pic
        self.model = ui.SimpleStringModel(self._pic.full_name_email)

    def __lt__(self, other):  # sorting
        return self.model.as_string < other.model.as_string

    @property
    def pic(self):
        """Gets the person in charge instance.

        Returns:
            PersonInCharge: The person in charge instance.
        """
        return self._pic


class PersonInChargeComboBoxModel(ClashInfoDropdownModel):
    """A model for managing a combo box of persons in charge.

    This class provides the functionality to handle a combo box where each item represents a person in charge. It extends the ClashInfoDropdownModel to include additional features specific to persons in charge.

    Args:
        items (list): A list of items to be displayed in the combo box.
        value_changed_fnc (function): A callback function to be called when the selected value changes.
    """

    def __init__(self, items, value_changed_fnc):
        """Initializes the PersonInChargeComboBoxModel with items and a value changed function."""
        super().__init__(items, value_changed_fnc)
