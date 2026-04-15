==============
clash_data
==============

.. module:: omni.physxclashdetectioncore.clash_data

This module provides the main interface for managing clash detection data within a USD stage.

Classes
=======

ClashData
---------

.. class:: ClashData(clash_data_serializer: AbstractClashDataSerializer)

   A class for handling clash detection data within a USD stage.

   This class manages the creation, modification, and deletion of clash detection data layers in a USD stage. It interfaces with a specified serializer to handle the persistence of clash data and ensures compatibility and integrity of the data structures.

   :param clash_data_serializer: The serializer used to manage the persistence of clash detection data.
   :type clash_data_serializer: AbstractClashDataSerializer

   **Class Constants:**

   .. attribute:: CLASH_DATA_LAYER_FILE_EXT
      :type: str
      :value: ".clashDetection"

      File extension for clash data layer files.

   .. attribute:: CLASH_DATA_FILE_EXT
      :type: str
      :value: ".clashdata"

      File extension for clash data files.

   .. attribute:: CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH
      :type: str
      :value: "clashDbPath"

      Custom layer data key for clash database path.

   .. attribute:: CLASH_DATA_LAYER_CUSTOM_MODIFIED
      :type: str
      :value: "clashDbModified"

      Custom layer data key for modification status.

   **Methods:**

   .. method:: __init__(clash_data_serializer: AbstractClashDataSerializer)

      Initializes the ClashData object.

      :param clash_data_serializer: The serializer to use for data persistence.
      :type clash_data_serializer: AbstractClashDataSerializer

   .. method:: destroy() -> None

      Cleans up resources and resets object state.

   .. method:: open(stage_id: Optional[int], force_reload_layer: bool = False) -> None

      Creates a file or opens an existing one.

      :param stage_id: Stage ID of the stage to work with.
      :type stage_id: Optional[int]
      :param force_reload_layer: Force reload target layer to ensure it doesn't come from the stage cache.
      :type force_reload_layer: bool

   .. method:: is_open() -> bool

      Checks if the serializer is ready.

      :return: True if the serializer is ready.
      :rtype: bool

   .. method:: save() -> bool

      Saves data to the target file.

      :return: True if the save operation was successful.
      :rtype: bool

   .. method:: save_as(usd_file_path: str) -> bool

      Saves data to a new target file.

      :param usd_file_path: The new file path to save to.
      :type usd_file_path: str
      :return: True if the save operation was successful.
      :rtype: bool

   .. method:: saved() -> None

      Performs operations after save.

   .. method:: close() -> None

      Closes the opened file.

   .. method:: commit() -> None

      Writes any unwritten data to the file.

   .. method:: migrate_data_structures_to_latest_version(file_path_name: str) -> bool

      Migrates data structures to the latest versions.

      :param file_path_name: Path to the clash data.
      :type file_path_name: str
      :return: True if migration was successful, False otherwise.
      :rtype: bool

   .. method:: insert_overlap(clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool) -> int

      Inserts clash data. If already present, insertion is skipped.

      :param clash_info: The clash information to insert.
      :type clash_info: ClashInfo
      :param insert_also_frame_info: Insert frame info as well.
      :type insert_also_frame_info: bool
      :param update_identifier: Update the identifier.
      :type update_identifier: bool
      :param commit: Commit the changes.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: update_overlap(clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int

      Updates clash data if present in the database.

      :param clash_info: The clash information to update.
      :type clash_info: ClashInfo
      :param update_also_frame_info: Update frame info as well.
      :type update_also_frame_info: bool
      :param commit: Commit the changes.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: find_all_overlaps_by_query_id(clash_query_id: int, fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0, num_overlaps_to_load: int = -1, first_overlap_offset: int = 0) -> Dict[str, ClashInfo]

      Finds all overlaps associated with a specific query ID.

      :param clash_query_id: The ID of the query to search for overlaps.
      :type clash_query_id: int
      :param fetch_also_frame_info: If True, fetches frame information.
      :type fetch_also_frame_info: bool
      :param num_frames_to_load: The maximum number of frames to load. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load. Defaults to 0.
      :type first_frame_offset: int
      :param num_overlaps_to_load: The maximum number of overlaps to load. Defaults to -1 (all overlaps).
      :type num_overlaps_to_load: int
      :param first_overlap_offset: The offset for the first overlap to load. Defaults to 0.
      :type first_overlap_offset: int
      :return: A dictionary where keys are overlap IDs and values are ClashInfo objects.
      :rtype: Dict[str, ClashInfo]

   .. method:: get_overlaps_count_by_query_id(clash_query_id: int) -> int

      Gets the total number of overlaps for a specific query ID.

      :param clash_query_id: The ID of the query to count overlaps for.
      :type clash_query_id: int
      :return: The total number of overlaps for the query. Returns 0 if no results found.
      :rtype: int

   .. method:: get_overlaps_count_by_query_id_grouped_by_state(clash_query_id: int) -> Dict[ClashState, int]

      Gets the total number of overlaps for a specific query ID grouped by state.

      :param clash_query_id: The ID of the query to count overlaps for.
      :type clash_query_id: int
      :return: A dictionary where keys are ClashState values and values are counts.
      :rtype: Dict[ClashState, int]

   .. method:: find_all_overlaps_by_overlap_id(overlap_id: Sequence[int], fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Dict[str, ClashInfo]

      Finds all overlaps by their overlap IDs.

      :param overlap_id: A sequence of overlap IDs to search for.
      :type overlap_id: Sequence[int]
      :param fetch_also_frame_info: If True, fetches frame information.
      :type fetch_also_frame_info: bool
      :param num_frames_to_load: The maximum number of frames to load. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load. Defaults to 0.
      :type first_frame_offset: int
      :return: A dictionary where keys are overlap IDs and values are ClashInfo objects.
      :rtype: Dict[str, ClashInfo]

   .. method:: remove_all_overlaps_by_query_id(clash_query_id: int, commit: bool) -> int

      Deletes specified clash data related to query_id.

      :param clash_query_id: ID of the clash query.
      :type clash_query_id: int
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: remove_overlap_by_id(overlap_id: int, commit: bool) -> int

      Deletes specified clash data.

      :param overlap_id: ID of the overlap.
      :type overlap_id: int
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_clash_frame_info_by_clash_info_id(clash_info_id: int, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Sequence[ClashFrameInfo]

      Fetches frame information associated with a specific clash.

      :param clash_info_id: The ID of the clash for which frame information is to be fetched.
      :type clash_info_id: int
      :param num_frames_to_load: The maximum number of frames to load. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load. Defaults to 0.
      :type first_frame_offset: int
      :return: A list of ClashFrameInfo objects.
      :rtype: Sequence[ClashFrameInfo]

   .. method:: get_clash_frame_info_count_by_clash_info_id(clash_info_id: int) -> int

      Gets the total number of frame info records for a specific clash info ID.

      :param clash_info_id: The ID of the clash info to count frame info records for.
      :type clash_info_id: int
      :return: The total number of frame info records. Returns 0 if no results found.
      :rtype: int

   .. method:: insert_clash_frame_info_from_clash_info(clash_info: ClashInfo, commit: bool) -> int

      Inserts clash_frame_info. If already present, insertion is skipped.

      :param clash_info: Clash info to insert.
      :type clash_info: ClashInfo
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: insert_clash_frame_info(clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int

      Inserts clash_frame_info. If already present, insertion is skipped.

      :param clash_frame_info: Clash frame info to insert.
      :type clash_frame_info: ClashFrameInfo
      :param clash_info_id: ID of the clash info.
      :type clash_info_id: int
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: remove_clash_frame_info_by_clash_info_id(clash_info_id: int, commit: bool) -> int

      Deletes specified clash_frame_info data.

      :param clash_info_id: ID of the clash info.
      :type clash_info_id: int
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_all_queries() -> Dict[int, ClashQuery]

      Returns all clash queries.

      :return: Dictionary of clash queries. Key is query identifier, value is ClashQuery object.
      :rtype: Dict[int, ClashQuery]

   .. method:: insert_query(clash_query: ClashQuery, update_identifier: bool = True, commit: bool = True) -> int

      Inserts clash query. If already present, insertion is skipped.

      :param clash_query: Clash query to insert.
      :type clash_query: ClashQuery
      :param update_identifier: Update identifier if True.
      :type update_identifier: bool
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: find_query(clash_query_id: int) -> Optional[ClashQuery]

      Returns specified clash query.

      :param clash_query_id: ID of the clash query.
      :type clash_query_id: int
      :return: The clash query or None if not present.
      :rtype: Optional[ClashQuery]

   .. method:: update_query(clash_query: ClashQuery, commit: bool = True) -> int

      Updates clash query if present in the DB.

      :param clash_query: Clash query to update.
      :type clash_query: ClashQuery
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: remove_query_by_id(query_id: int, commit: bool = True) -> int

      Deletes specified clash data.

      :param query_id: ID of the query.
      :type query_id: int
      :param commit: Commit changes to the database.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   **Properties:**

   .. attribute:: stage_id
      :type: Optional[int]

      Gets the associated stage ID.

   .. attribute:: stage
      :type: Optional[Usd.Stage]

      Gets the associated stage.

   .. attribute:: usd_file_path
      :type: str

      Gets the stage file path.

   .. attribute:: serializer_path
      :type: str

      Gets the serializer file path.

   .. attribute:: data_structures_compatible
      :type: bool

      Gets whether the serializer has no compatibility issues.

   .. attribute:: data_structures_migration_to_latest_version_possible
      :type: bool

      Returns True if the serializer can migrate data structures to the latest version.

   .. attribute:: deferred_file_creation_until_first_write_op
      :type: bool

      Gets whether the serializer will postpone file creation until the first write operation.

      Can also be set to control this behavior.


Functions
=========

.. function:: serializer_data_op(fnc)

   Decorator to identify serializer data operation.

   Handy for tests to quickly find out that a method was added or removed.

   :param fnc: The function to be registered as a serializer data operation.
   :type fnc: function
   :return: The registered function.
   :rtype: function


Module Variables
================

.. data:: Serializer_data_operations
   :type: List

   List of functions decorated with @serializer_data_op.

