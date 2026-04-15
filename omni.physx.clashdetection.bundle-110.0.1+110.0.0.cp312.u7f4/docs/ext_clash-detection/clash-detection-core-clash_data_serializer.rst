============================
clash_data_serializer
============================

.. module:: omni.physxclashdetectioncore.clash_data_serializer

This module provides the abstract base class for clash data serialization.

Classes
=======

AbstractClashDataSerializer
----------------------------

.. class:: AbstractClashDataSerializer()

   A base class for serializing and managing clash data.

   This abstract class defines the necessary methods for handling clash data serialization, including opening and closing files, managing data compatibility, and performing CRUD operations on clash data and related information. Implementations of this class should provide concrete definitions for the abstract methods.

   **Methods:**

   .. method:: __init__()

      Initializes the AbstractClashDataSerializer class.

   .. method:: open(file_path_name: str) -> None
      :abstractmethod:

      Creates a file or opens an existing.

      :param file_path_name: Path of the file to open.
      :type file_path_name: str

   .. method:: get_file_path() -> str
      :abstractmethod:

      Returns the serializer file path.

      :return: The file path of the serializer.
      :rtype: str

   .. method:: get_file_size() -> int
      :abstractmethod:

      Returns the serializer file size in bytes.

      :return: The file size in bytes.
      :rtype: int

   .. method:: data_structures_compatible() -> bool
      :abstractmethod:

      Returns True if the serializer has no compatibility issues (data structures, tables).

      :return: True if compatible, False otherwise.
      :rtype: bool

   .. method:: data_structures_migration_to_latest_version_possible() -> bool
      :abstractmethod:

      Returns True if the serializer can migrate data structures to the latest version.

      :return: True if migration to the latest version is possible.
      :rtype: bool

   .. method:: deferred_file_creation_until_first_write_op() -> bool
      :abstractmethod:

      Returns True if the serializer will postpone file creation until first write op is requested.

      :return: True if deferred creation is enabled, False otherwise.
      :rtype: bool

   .. method:: set_deferred_file_creation_until_first_write_op(value: bool)
      :abstractmethod:

      Sets if the serializer must postpone file creation until first write op is requested.

      :param value: Whether to defer file creation.
      :type value: bool

   .. method:: set_on_modified_fnc(on_modified_fnc: Optional[Callable[[str], None]])

      Sets on_modified_fnc.

      :param on_modified_fnc: The function to call when modified.
      :type on_modified_fnc: Optional[Callable[[str], None]]

   .. method:: is_open() -> bool
      :abstractmethod:

      Returns if the serializer is ready.

      :return: True if open, False otherwise.
      :rtype: bool

   .. method:: save() -> bool
      :abstractmethod:

      Saves data to the target file.

      :return: True if save was successful, False otherwise.
      :rtype: bool

   .. method:: close() -> None
      :abstractmethod:

      Closes the opened file.

   .. method:: commit() -> None
      :abstractmethod:

      Writes any unwritten data to the file. Committing bigger batches is advised.

   .. method:: migrate_data_structures_to_latest_version(file_path_name: str) -> bool
      :abstractmethod:

      Migrates data structures to the latest versions.

      :param file_path_name: Path to the clash data.
      :type file_path_name: str
      :return: True if migration was successful, False otherwise.
      :rtype: bool

   .. method:: insert_overlap(clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool) -> int
      :abstractmethod:

      Inserts clash data. If already present, insertion is skipped.

      :param clash_info: Clash information to insert.
      :type clash_info: ClashInfo
      :param insert_also_frame_info: Whether to insert frame info.
      :type insert_also_frame_info: bool
      :param update_identifier: Whether to update the identifier.
      :type update_identifier: bool
      :param commit: Whether to commit the operation.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: update_overlap(clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int
      :abstractmethod:

      Updates clash data if present in the DB.

      :param clash_info: Clash information to update.
      :type clash_info: ClashInfo
      :param update_also_frame_info: Whether to update frame info.
      :type update_also_frame_info: bool
      :param commit: Whether to commit the operation.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: find_all_overlaps_by_query_id(clash_query_id: int, fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0, num_overlaps_to_load: int = -1, first_overlap_offset: int = 0) -> Dict[str, ClashInfo]
      :abstractmethod:

      Finds all overlaps associated with a specific query ID.

      :param clash_query_id: The ID of the query to search for overlaps.
      :type clash_query_id: int
      :param fetch_also_frame_info: If True, fetches frame information associated with each ClashInfo object.
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
      :abstractmethod:

      Gets the total number of overlaps for a specific query ID.

      :param clash_query_id: The ID of the query to count overlaps for.
      :type clash_query_id: int
      :return: The total number of overlaps for the query. Returns 0 if no results found.
      :rtype: int

   .. method:: get_overlaps_count_by_query_id_grouped_by_state(clash_query_id: int) -> Dict[ClashState, int]
      :abstractmethod:

      Gets the total number of overlaps for a specific query ID grouped by state.

      :param clash_query_id: The ID of the query to count overlaps for.
      :type clash_query_id: int
      :return: A dictionary where keys are ClashState values and values are counts.
      :rtype: Dict[ClashState, int]

   .. method:: find_all_overlaps_by_overlap_id(overlap_id: Sequence[int], fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Dict[str, ClashInfo]
      :abstractmethod:

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
      :abstractmethod:

      Deletes specified clash data related to query_id. If not present, nothing happens.

      :param clash_query_id: The query ID to remove.
      :type clash_query_id: int
      :param commit: Whether to commit the operation.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: remove_overlap_by_id(overlap_id: int, commit: bool) -> int
      :abstractmethod:

      Deletes specified clash data. If not present, nothing happens.

      :param overlap_id: The overlap ID to remove.
      :type overlap_id: int
      :param commit: Whether to commit the operation.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_clash_frame_info_by_clash_info_id(clash_info_id: int, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Sequence[ClashFrameInfo]
      :abstractmethod:

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
      :abstractmethod:

      Gets the total number of frame info records for a specific clash info ID.

      :param clash_info_id: The ID of the clash info to count frame info records for.
      :type clash_info_id: int
      :return: The total number of frame info records. Returns 0 if no results found.
      :rtype: int

   .. method:: insert_clash_frame_info_from_clash_info(clash_info: ClashInfo, commit: bool) -> int
      :abstractmethod:

      Inserts clash_frame_info from ClashInfo.

      :param clash_info: The ClashInfo object to extract frame info from.
      :type clash_info: ClashInfo
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: insert_clash_frame_info(clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int
      :abstractmethod:

      Inserts clash_frame_info.

      :param clash_frame_info: The ClashFrameInfo object to insert.
      :type clash_frame_info: ClashFrameInfo
      :param clash_info_id: The ID of the associated ClashInfo.
      :type clash_info_id: int
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: remove_clash_frame_info_by_clash_info_id(clash_info_id: int, commit: bool) -> int
      :abstractmethod:

      Deletes specified clash_frame_info data.

      :param clash_info_id: The ID of the associated ClashInfo.
      :type clash_info_id: int
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_all_queries() -> Dict[int, ClashQuery]
      :abstractmethod:

      Returns all clash queries.

      :return: Dictionary of all clash queries. Key is query identifier, value is ClashQuery object.
      :rtype: Dict[int, ClashQuery]

   .. method:: insert_query(clash_query: ClashQuery, update_identifier: bool, commit: bool) -> int
      :abstractmethod:

      Inserts clash query.

      :param clash_query: The ClashQuery object to insert.
      :type clash_query: ClashQuery
      :param update_identifier: Whether to update the identifier.
      :type update_identifier: bool
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: find_query(clash_query_id: int) -> Optional[ClashQuery]
      :abstractmethod:

      Returns specified clash query.

      :param clash_query_id: The ID of the ClashQuery to find.
      :type clash_query_id: int
      :return: The found ClashQuery or None.
      :rtype: Optional[ClashQuery]

   .. method:: update_query(clash_query: ClashQuery, commit: bool) -> int
      :abstractmethod:

      Updates clash query if present in the DB.

      :param clash_query: The ClashQuery object to update.
      :type clash_query: ClashQuery
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: remove_query_by_id(query_id: int, commit: bool) -> int
      :abstractmethod:

      Deletes specified clash data.

      :param query_id: The ID of the query to remove.
      :type query_id: int
      :param commit: Whether to commit the change.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   **Properties:**

   .. attribute:: on_modified_fnc
      :type: Optional[Callable[[str], None]]

      Gets the on_modified function callback.

