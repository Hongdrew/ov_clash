# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any, Dict, Optional
import carb
import json
from datetime import datetime
from .utils import get_current_user_name, to_json_str_safe, dict_to_obj, obj_to_dict


class ClashQuery:
    """A class for managing and executing clash detection queries.

    A class that is designed to manage settings for clash detection queries.
    It includes functionality to serialize and deserialize settings, manage query metadata and update timestamps.

    Args:
        identifier (int): Unique identifier for the clash query. -1 means not yet assigned / uninitialized.
        query_name (str): Name of the clash query.
        object_a_path (str): Path to the first object involved in the clash detection. Can contain multiple paths separated by space/tab/newline.
        object_b_path (str): Path to the second object involved in the clash detection. Can contain multiple paths separated by space/tab/newline.
        clash_detect_settings (Optional[Dict[str, Any]]): Settings for the clash detection process.
        creation_timestamp (Optional[datetime]): Timestamp when the query was created.
        last_modified_timestamp (Optional[datetime]): Timestamp when the query was last modified.
        last_modified_by (str): Name of the user who last modified the query.
        comment (str): Additional comments or notes about the query.
    """

    VERSION = 3

    def __init__(
        self,
        identifier: int = -1,  # unique identifier, -1 means not yet assigned / uninitialized
        query_name: str = "",
        object_a_path: str = "",
        object_b_path: str = "",
        clash_detect_settings: Optional[Dict[str, Any]] = None,
        creation_timestamp: Optional[datetime] = None,
        last_modified_timestamp: Optional[datetime] = None,
        last_modified_by: str = "",
        comment: str = "",
    ) -> None:
        """Initializes a new instance of the ClashQuery class."""
        self._identifier = identifier
        self._query_name = query_name
        self._object_a_path = object_a_path
        self._object_b_path = object_b_path
        self._clash_detect_settings = clash_detect_settings if clash_detect_settings is not None else dict()
        self._creation_timestamp = creation_timestamp if creation_timestamp is not None else datetime.now()
        self._last_modified_timestamp = (
            last_modified_timestamp if last_modified_timestamp is not None else datetime.now()
        )
        self._last_modified_by = last_modified_by if last_modified_by else get_current_user_name()
        self._comment = comment

    def serialize_to_dict(self) -> Dict[str, Any]:
        """Converts the ClashQuery instance to a dictionary in JSON-serializable format.

        Returns:
            Dict[str, Any]: Dictionary containing the serialized ClashQuery data.
        """
        return obj_to_dict(self)

    @classmethod
    def deserialize_from_dict(cls, data: Dict[str, Any], reset_identifier: bool = False) -> 'ClashQuery | None':
        """Deserializes a ClashQuery instance from a JSON-serializable dictionary format.

        Args:
            data (Dict[str, Any]): Dictionary containing serialized ClashQuery data.
            reset_identifier (bool): If True, resets the identifier to -1 after deserialization.

        Returns:
            ClashQuery | None: New ClashQuery instance if deserialization succeeds, None if it fails.
        """
        new_instance = cls()

        if dict_to_obj(new_instance, data):
            if reset_identifier:
                new_instance._identifier = -1
            return new_instance

        return None

    def load_settings_from_str(self, settings_str: str) -> bool:
        """Deserializes settings values from the json string.

        Args:
            settings_str (str): The JSON string containing settings.

        Returns:
            bool: True on success, otherwise False.
        """
        if not settings_str or len(settings_str) == 0:
            return False
        try:
            self._clash_detect_settings = json.loads(settings_str)
        except Exception as e:
            carb.log_error(f"Failed to load clash detect settings from json string.\nException: {e}")
            return False
        return True

    def get_settings_as_str(self) -> str:
        """Serializes setting values to the json string and returns the string.

        Returns:
            str: The JSON string representation of settings.
        """
        return to_json_str_safe(self._clash_detect_settings)

    def update_last_modified_timestamp(self) -> None:
        """Updates last modified timestamp with current date & time."""
        self.last_modified_timestamp = datetime.now()

    @property
    def identifier(self) -> int:
        """Read-only property that returns the unique identifier of the query.

        Returns:
            int: The unique identifier.
        """
        return self._identifier

    @property
    def query_name(self) -> str:
        """Gets the query name.

        Returns:
            str: The query name.
        """
        return self._query_name if self._query_name else ""

    @query_name.setter
    def query_name(self, value: str):
        """Sets the query name.

        Setting this property updates the last modified timestamp.

        Args:
            value (str): The new query name.
        """
        self._query_name = value
        self.update_last_modified_timestamp()

    @property
    def object_a_path(self) -> str:
        """Gets the object A path.

        Can contain multiple paths separated by space/tab/newline.

        Returns:
            str: The path for object A.
        """
        return self._object_a_path if self._object_a_path else ""

    @object_a_path.setter
    def object_a_path(self, value: str):
        """Sets the object A path.

        Can contain multiple paths separated by space/tab/newline.
        Setting this property updates the last modified timestamp.

        Args:
            value (str): The new path for object A.
        """
        self._object_a_path = value
        self.update_last_modified_timestamp()

    @property
    def object_b_path(self) -> str:
        """Gets the object B path.

        Can contain multiple paths separated by space/tab/newline.

        Returns:
            str: The path for object B.
        """
        return self._object_b_path if self._object_b_path else ""

    @object_b_path.setter
    def object_b_path(self, value: str):
        """Sets the object B path.

        Can contain multiple paths separated by space/tab/newline.
        Setting this property updates the last modified timestamp.

        Args:
            value (str): The new path for object B.
        """
        self._object_b_path = value
        self.update_last_modified_timestamp()

    @property
    def clash_detect_settings(self) -> Dict[str, Any]:
        """Gets the clash detect settings.

        Returns:
            Dict[str, Any]: The clash detect settings.
        """
        return self._clash_detect_settings

    @clash_detect_settings.setter
    def clash_detect_settings(self, value: Dict[str, Any]):
        """Sets the clash detect settings.

        Setting this property updates the last modified timestamp.

        Args:
            value (Dict[str, Any]): The new clash detect settings.
        """
        self._clash_detect_settings = value if value is not None else dict()
        self.update_last_modified_timestamp()

    @property
    def creation_timestamp(self) -> datetime:
        """Gets the creation timestamp.

        Returns:
            datetime: The creation timestamp.
        """
        return self._creation_timestamp

    @property
    def last_modified_timestamp(self) -> datetime:
        """Gets the last modified timestamp.

        Returns:
            datetime: The last modified timestamp.
        """
        return self._last_modified_timestamp

    @last_modified_timestamp.setter
    def last_modified_timestamp(self, value: datetime):
        """Sets the last modified timestamp.

        Setting this property updates the last modified by user to the current user.

        Args:
            value (datetime): The new last modified timestamp.
        """
        self._last_modified_timestamp = value
        self._last_modified_by = get_current_user_name()

    @property
    def last_modified_by(self) -> str:
        """Read-only property that returns the name of the user who last modified the query.

        Returns:
            str: The user who last modified.
        """
        return self._last_modified_by if self._last_modified_by else ""

    @property
    def comment(self) -> str:
        """Gets the comment.

        Returns:
            str: The comment.
        """
        return self._comment if self._comment else ""

    @comment.setter
    def comment(self, value: str):
        """Sets the comment.

        Setting this property updates the last modified timestamp.

        Args:
            value (str): The new comment.
        """
        self._comment = value
        self.update_last_modified_timestamp()
