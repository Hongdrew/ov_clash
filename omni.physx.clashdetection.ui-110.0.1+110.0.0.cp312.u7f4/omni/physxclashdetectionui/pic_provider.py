# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# Person In Charge provider
# - provides list of relevant users for assigning to individual clashes
# username must be unique
from typing import ValuesView

__all__ = []


class PersonInCharge:
    """A class representing a person in charge of handling specific tasks or assignments.

    This class provides mechanisms for managing and accessing information about an individual responsible for certain duties. Each person is uniquely identified by their username.

    Args:
        username (str): The unique identifier for the person in charge. An empty string is allowed to support a placeholder person.
        first_name (str): The first name of the person.
        last_name (str): The last name of the person.
        email (str): The email address of the person.
    """

    def __init__(
        self,
        username: str = "",  # empty username is allowed so <Empty> person is supported
        first_name: str = "",
        last_name: str = "",
        email: str = "",
    ) -> None:
        """Initializes a new instance of the PersonInCharge class."""
        self._username = username
        self._first_name = first_name
        self._last_name = last_name
        self._email = email

    def __lt__(self, other) -> bool:  # sorting
        return self.full_name < other.full_name

    @property
    def username(self) -> str:
        """Gets the username.

        Returns:
            str: The unique username of the person.
        """
        return self._username

    @property
    def first_name(self) -> str:
        """Gets the first name.

        Returns:
            str: The first name of the person.
        """
        return self._first_name

    @property
    def last_name(self) -> str:
        """Gets the last name.

        Returns:
            str: The last name of the person.
        """
        return self._last_name

    @property
    def email(self) -> str:
        """Gets the email address.

        Returns:
            str: The email address of the person.
        """
        return self._email

    @property
    def full_name(self) -> str:
        """Gets the full name.

        Returns:
            str: The full name of the person.
        """
        if not self.first_name:
            if not self.last_name:
                return self.username
            else:
                return self.last_name
        else:
            if not self.last_name:
                return self.first_name
            else:
                return f"{self.first_name} {self.last_name}"

    @property
    def full_name_email(self) -> str:
        """Gets the full name with email address.

        Returns:
            str: The full name and email address of the person.
        """
        if not self.email:
            return self.full_name
        else:
            return f"{self.full_name} <{self.email}>"


class PersonsInCharge:
    """A class for managing and retrieving persons in charge.

    This class manages a collection of PersonInCharge objects, which represent users that can be assigned to specific tasks or clashes. It provides methods to retrieve these users and ensures that there is always a default 'none' user available.

    The class also includes an abstract method `fetch` that must be overridden in subclasses to populate the list of users from a specified source.
    """

    pic_none = PersonInCharge("", "<None>")

    def __init__(self) -> None:
        """Initializes the PersonsInCharge instance."""
        self.reset()

    def reset(self) -> None:
        """Resets the PersonsInCharge instance to its initial state."""
        self._pic_dict = dict()
        self._pic_dict[""] = PersonsInCharge.pic_none

    def get_items(self) -> ValuesView[PersonInCharge]:
        """Retrieves all PersonInCharge items.

        Returns:
            ValuesView[PersonInCharge]: A view of all persons in charge.
        """
        return self._pic_dict.values()

    def get_person(self, username) -> PersonInCharge:
        """never returns None - if person is not found, returns 'pic_none'

        Args:
            username (str): The username of the person to retrieve.

        Returns:
            PersonInCharge: The person with the specified username or 'pic_none'.
        """
        return self._pic_dict.get(username, PersonsInCharge.pic_none)

    # override in subclass
    def fetch(self, source: str) -> bool:
        """Fetches users from an arbitrary source.
        This is an abstract method to be overridden by a custom fetch implementation.

            Args:
                source (str): The source from which to fetch users.

            Returns:
                bool: Always returns False.
        """
        return False
