===============
clash_query
===============

.. module:: omni.physxclashdetectioncore.clash_query

This module provides the ClashQuery class for managing clash detection query parameters.

Classes
=======

ClashQuery
----------

.. class:: ClashQuery(identifier: int = -1, query_name: str = "", object_a_path: str = "", object_b_path: str = "", clash_detect_settings: Optional[Dict[str, Any]] = None, creation_timestamp: Optional[datetime] = None, last_modified_timestamp: Optional[datetime] = None, last_modified_by: str = "", comment: str = "")

   A class for managing and executing clash detection queries.

   A class that is designed to manage settings for clash detection queries.
   It includes functionality to serialize and deserialize settings, manage query metadata and update timestamps.

   :param identifier: Unique identifier for the clash query. -1 means not yet assigned / uninitialized. Defaults to -1.
   :type identifier: int
   :param query_name: Name of the clash query. Defaults to "".
   :type query_name: str
   :param object_a_path: Path to the first object involved in the clash detection. Can contain multiple paths separated by space/tab/newline. Defaults to "".
   :type object_a_path: str
   :param object_b_path: Path to the second object involved in the clash detection. Can contain multiple paths separated by space/tab/newline. Defaults to "".
   :type object_b_path: str
   :param clash_detect_settings: Settings for the clash detection process. Defaults to None.
   :type clash_detect_settings: Optional[Dict[str, Any]]
   :param creation_timestamp: Timestamp when the query was created. Defaults to None (current time).
   :type creation_timestamp: Optional[datetime]
   :param last_modified_timestamp: Timestamp when the query was last modified. Defaults to None (current time).
   :type last_modified_timestamp: Optional[datetime]
   :param last_modified_by: Name of the user who last modified the query. Defaults to "" (current user).
   :type last_modified_by: str
   :param comment: Additional comments or notes about the query. Defaults to "".
   :type comment: str

   **Class Constants:**

   .. attribute:: VERSION
      :type: int
      :value: 3

      Version of the ClashQuery data structure.

   **Methods:**

   .. method:: serialize_to_dict() -> Dict[str, Any]

      Converts the ClashQuery instance to a dictionary in JSON-serializable format.

      :return: Dictionary containing the serialized ClashQuery data.
      :rtype: Dict[str, Any]

   .. method:: deserialize_from_dict(data: Dict[str, Any], reset_identifier: bool = False) -> ClashQuery | None
      :classmethod:

      Deserializes a ClashQuery instance from a JSON-serializable dictionary format.

      :param data: Dictionary containing serialized ClashQuery data.
      :type data: Dict[str, Any]
      :param reset_identifier: If True, resets the identifier to -1 after deserialization. Defaults to False.
      :type reset_identifier: bool
      :return: New ClashQuery instance if deserialization succeeds, None if it fails.
      :rtype: ClashQuery | None

   .. method:: load_settings_from_str(settings_str: str) -> bool

      Deserializes settings values from the json string.

      :param settings_str: The JSON string containing settings.
      :type settings_str: str
      :return: True on success, otherwise False.
      :rtype: bool

   .. method:: get_settings_as_str() -> str

      Serializes setting values to the json string and returns the string.

      :return: The JSON string representation of settings.
      :rtype: str

   .. method:: update_last_modified_timestamp() -> None

      Updates last modified timestamp with current date & time.

   **Properties:**

   .. attribute:: identifier
      :type: int

      Read-only property that returns the unique identifier of the query.

   .. attribute:: query_name
      :type: str

      Gets or sets the query name. Setting this property updates the last modified timestamp.

   .. attribute:: object_a_path
      :type: str

      Gets or sets the object A path. Can contain multiple paths separated by space/tab/newline.
      Setting this property updates the last modified timestamp.

   .. attribute:: object_b_path
      :type: str

      Gets or sets the object B path. Can contain multiple paths separated by space/tab/newline.
      Setting this property updates the last modified timestamp.

   .. attribute:: clash_detect_settings
      :type: Dict[str, Any]

      Gets or sets the clash detect settings. Setting this property updates the last modified timestamp.

   .. attribute:: creation_timestamp
      :type: datetime

      Gets the creation timestamp.

   .. attribute:: last_modified_timestamp
      :type: datetime

      Gets or sets the last modified timestamp. Setting this property updates the last modified by user to the current user.

   .. attribute:: last_modified_by
      :type: str

      Read-only property that returns the name of the user who last modified the query.

   .. attribute:: comment
      :type: str

      Gets or sets the comment. Setting this property updates the last modified timestamp.


Example
=======

Creating and using a ClashQuery:

.. code-block:: python

   from omni.physxclashdetectioncore.clash_query import ClashQuery
   from omni.physxclashdetectioncore.clash_detect_settings import SettingId

   # Create a new clash query
   query = ClashQuery(
       query_name="Full Scene Hard Clash Detection",
       object_a_path="",  # Empty means full scene
       object_b_path="",  # Empty means full scene
       clash_detect_settings={
           SettingId.SETTING_TOLERANCE.name: 0.0,  # Hard clashes
           SettingId.SETTING_DYNAMIC.name: False,  # Static detection
           SettingId.SETTING_LOGGING.name: True
       },
       comment="Initial clash detection for the project"
   )

   # Serialize to dictionary
   query_dict = query.serialize_to_dict()

   # Deserialize from dictionary
   restored_query = ClashQuery.deserialize_from_dict(query_dict)

