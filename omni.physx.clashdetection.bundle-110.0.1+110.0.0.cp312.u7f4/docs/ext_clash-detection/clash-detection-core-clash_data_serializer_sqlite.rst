==================================
clash_data_serializer_sqlite
==================================

.. module:: omni.physxclashdetectioncore.clash_data_serializer_sqlite

This module provides SQLite-based serialization for clash detection data.

Classes
=======

ClashDataSerializerSqlite
--------------------------

.. class:: ClashDataSerializerSqlite()

   A class for serializing and deserializing clash data using SQLite database.

   This class provides functionality to read, write, update, and delete clash data and clash queries in an SQLite database.
   It ensures compatibility with specific versions of clash data structures and manages database connections and transactions.

   It supports deferred database creation until the first write operation to avoid creating empty database files.
   The class also includes methods for checking table compatibility, creating necessary database tables, and inserting,
   updating, and querying clash data and clash queries.

   **Class Constants:**

   .. attribute:: CLASH_DB_FILE_EXT
      :type: str
      :value: ".clashdb"

      File extension for clash database files.

   .. attribute:: SUPPORTED_CLASH_QUERY_VERSION
      :type: int
      :value: 3

      Supported version of ClashQuery data structure.

   .. attribute:: SUPPORTED_CLASH_INFO_VERSION
      :type: int
      :value: 16

      Supported version of ClashInfo data structure.

   .. attribute:: SUPPORTED_CLASH_FRAME_INFO_VERSION
      :type: int
      :value: 6

      Supported version of ClashFrameInfo data structure.

   **Methods:**

   .. method:: __init__()

      Initializes the ClashDataSerializerSqlite instance.

   .. method:: check_serializer_compatibility_with_data_structures() -> bool
      :staticmethod:

      Checks if the serializer is compatible with current data structures.

      :return: True if compatible with current data structures.
      :rtype: bool

   .. method:: check_compatibility_of_tables() -> bool

      Checks if the current database tables are compatible.

      :return: True if tables are compatible.
      :rtype: bool

   .. method:: check_possibility_of_tables_migration() -> bool

      Checks if migration of all tables to the latest version is possible.

      :return: True if migration of all tables to the latest version is possible.
      :rtype: bool

   .. method:: migrate_table(table_name: str, target_version: int, commit: bool = True) -> bool

      Run all migration steps for the given table from start_version to target_version in a single transaction.

      :param table_name: Name of the table to migrate.
      :type table_name: str
      :param target_version: Target version to migrate to.
      :type target_version: int
      :param commit: Whether to commit the transaction. Defaults to True.
      :type commit: bool
      :return: True if the full sequence succeeds; on failure, rolls back and returns False.
      :rtype: bool

   .. method:: open(file_path_name: str) -> None

      Creates a file or opens an existing one.

      :param file_path_name: Path to the file to be opened.
      :type file_path_name: str

   .. method:: get_file_path() -> str

      Returns the serializer file path.

      :return: The serializer file path.
      :rtype: str

   .. method:: get_file_size() -> int

      Returns the serializer file size in bytes.

      :return: The file size in bytes.
      :rtype: int

   .. method:: get_free_list_size() -> int

      Returns the size of SQLite's freelist in bytes.

      The freelist contains pages that were previously used but are now free.
      These pages can be reused for new data.

      :return: The total size of free pages in bytes.
      :rtype: int

   .. method:: data_structures_compatible() -> bool

      Returns True if the serializer has no compatibility issues (data structures, tables).

      :return: True if no compatibility issues.
      :rtype: bool

   .. method:: data_structures_migration_to_latest_version_possible() -> bool

      Returns True if the serializer can migrate data structures to the latest version.

      :return: True if migration to the latest version is possible.
      :rtype: bool

   .. method:: migrate_data_structures_to_latest_version(file_path_name: str) -> bool

      Migrates data structures to the latest version.

      The single transaction design ensures atomic schema updates. Either all steps commit successfully or
      the entire sequence is rolled back, preserving the pre-migration state on error.

      :param file_path_name: Path to the clash data.
      :type file_path_name: str
      :return: True if migration was successful, False otherwise.
      :rtype: bool

   .. method:: deferred_file_creation_until_first_write_op() -> bool

      Returns True if the serializer will postpone file creation until the first write operation is requested.

      :return: True if file creation is deferred until first write.
      :rtype: bool

   .. method:: set_deferred_file_creation_until_first_write_op(value: bool) -> None

      Sets if the serializer must postpone file creation until the first write operation is requested.

      :param value: True to defer file creation, False otherwise.
      :type value: bool

   .. method:: is_open() -> bool

      Returns if the serializer is ready.

      :return: True if the serializer is ready.
      :rtype: bool

   .. method:: save() -> bool

      Saves data to the target file.

      :return: True if save was successful, False otherwise.
      :rtype: bool

   .. method:: close() -> None

      Closes the opened file.

   .. method:: commit() -> None

      Commits any unwritten data to the target file.

   .. method:: vacuum() -> None

      Defragments the database and reclaims freed space.

   .. method:: insert_overlap(clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool) -> int

      Inserts clash data. If already present, insertion is skipped.

      :param clash_info: Clash information to insert.
      :type clash_info: ClashInfo
      :param insert_also_frame_info: Whether to insert frame info as well.
      :type insert_also_frame_info: bool
      :param update_identifier: Update identifier if needed.
      :type update_identifier: bool
      :param commit: Commit the transaction.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: update_overlap(clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int

      Updates clash data if present in the database.

      :param clash_info: Clash information to update.
      :type clash_info: ClashInfo
      :param update_also_frame_info: Whether to update frame info as well.
      :type update_also_frame_info: bool
      :param commit: Commit the transaction.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: find_all_overlaps_by_query_id(clash_query_id: int, fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0, num_overlaps_to_load: int = -1, first_overlap_offset: int = 0) -> Dict[str, ClashInfo]

      Finds all overlaps associated with a specific query ID.

      This method retrieves all ClashInfo objects corresponding to the given clash_query_id
      from the database and optionally fetches additional frame information for each clash.

      :param clash_query_id: The ID of the query to search for overlaps.
      :type clash_query_id: int
      :param fetch_also_frame_info: If True, fetches frame information associated with each ClashInfo object.
      :type fetch_also_frame_info: bool
      :param num_frames_to_load: The maximum number of frames to load when fetching frame information. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load when fetching frame information. Defaults to 0.
      :type first_frame_offset: int
      :param num_overlaps_to_load: The maximum number of overlaps to load. Defaults to -1 (all overlaps).
      :type num_overlaps_to_load: int
      :param first_overlap_offset: The offset for the first overlap to load. Defaults to 0.
      :type first_overlap_offset: int
      :return: A dictionary where the keys are overlap IDs (as strings) and the values are the corresponding ClashInfo objects. Empty dict if no results.
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
      :return: A dictionary where keys are ClashState enum values and values are counts. Empty dict if no results.
      :rtype: Dict[ClashState, int]

   .. method:: find_all_overlaps_by_overlap_id(overlap_id: Sequence[int], fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Dict[str, ClashInfo]

      Finds all overlaps by their overlap IDs.

      This method retrieves all ClashInfo objects associated with the given overlap IDs
      and optionally fetches additional frame information for each clash.

      :param overlap_id: A sequence of overlap IDs to search for.
      :type overlap_id: Sequence[int]
      :param fetch_also_frame_info: If True, fetches frame information associated with each ClashInfo object.
      :type fetch_also_frame_info: bool
      :param num_frames_to_load: The maximum number of frames to load. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load. Defaults to 0.
      :type first_frame_offset: int
      :return: A dictionary where keys are overlap IDs and values are ClashInfo objects. Empty dict if no results.
      :rtype: Dict[str, ClashInfo]

   .. method:: remove_all_overlaps_by_query_id(clash_query_id: int, commit: bool) -> int

      Deletes specified clash data related to query_id.

      :param clash_query_id: The ID of the clash query.
      :type clash_query_id: int
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: remove_overlap_by_id(overlap_id: int, commit: bool) -> int

      Deletes specified clash data.

      :param overlap_id: The ID of the overlap.
      :type overlap_id: int
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_clash_frame_info_by_clash_info_id(clash_info_id: int, num_frames_to_load: int = -1, first_frame_offset: int = 0) -> Sequence[ClashFrameInfo]

      Fetches frame information associated with a specific clash.

      This method retrieves ClashFrameInfo records from the database for a given
      clash_info_id, ordered by timecode. It supports limiting the number of frames
      fetched and applying an offset to the starting frame.

      :param clash_info_id: The ID of the clash for which frame information is to be fetched.
      :type clash_info_id: int
      :param num_frames_to_load: The maximum number of frames to load. Defaults to -1 (all frames).
      :type num_frames_to_load: int
      :param first_frame_offset: The offset for the first frame to load. Defaults to 0.
      :type first_frame_offset: int
      :return: A list of ClashFrameInfo objects. Empty list if no results.
      :rtype: Sequence[ClashFrameInfo]

   .. method:: get_clash_frame_info_count_by_clash_info_id(clash_info_id: int) -> int

      Gets the total number of frame info records for a specific clash info ID.

      :param clash_info_id: The ID of the clash info to count frame info records for.
      :type clash_info_id: int
      :return: The total number of frame info records. Returns 0 if no results found.
      :rtype: int

   .. method:: insert_clash_frame_info_from_clash_info(clash_info: ClashInfo, commit: bool) -> int

      Inserts clash_frame_info from ClashInfo.

      :param clash_info: The ClashInfo object.
      :type clash_info: ClashInfo
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: insert_clash_frame_info(clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int

      Inserts clash_frame_info.

      :param clash_frame_info: The ClashFrameInfo object.
      :type clash_frame_info: ClashFrameInfo
      :param clash_info_id: The ID of the clash info.
      :type clash_info_id: int
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: remove_clash_frame_info_by_clash_info_id(clash_info_id: int, commit: bool) -> int

      Deletes specified clash_frame_info data.

      :param clash_info_id: The ID of the clash info.
      :type clash_info_id: int
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: fetch_all_queries() -> Dict[int, ClashQuery]

      Returns all clash queries.

      :return: Dictionary of all clash queries. Key is query identifier, value is ClashQuery object.
      :rtype: Dict[int, ClashQuery]

   .. method:: insert_query(clash_query: ClashQuery, update_identifier: bool, commit: bool) -> int

      Inserts clash query.

      :param clash_query: The ClashQuery object.
      :type clash_query: ClashQuery
      :param update_identifier: Whether to update the identifier.
      :type update_identifier: bool
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: ID of the new record.
      :rtype: int

   .. method:: update_query(clash_query: ClashQuery, commit: bool) -> int

      Updates clash query if present in the DB.

      :param clash_query: The ClashQuery object.
      :type clash_query: ClashQuery
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of affected records.
      :rtype: int

   .. method:: remove_query_by_id(query_id: int, commit: bool) -> int

      Deletes specified clash data.

      :param query_id: The ID of the query.
      :type query_id: int
      :param commit: Whether to commit the transaction.
      :type commit: bool
      :return: Number of deleted rows.
      :rtype: int

   .. method:: find_query(clash_query_id: int) -> Optional[ClashQuery]

      Returns specified clash query.

      :param clash_query_id: The ID of the clash query.
      :type clash_query_id: int
      :return: The ClashQuery object or None if not found.
      :rtype: Optional[ClashQuery]

   **Properties:**

   .. attribute:: db_file_path_name
      :type: str

      Gets the database file path name.

   .. attribute:: deferred_db_creation_until_commit_query
      :type: bool

      Gets the deferred database creation until commit query flag.

   .. attribute:: compatible_with_data_structures
      :type: bool

      Gets the compatibility status with data structures.

   .. attribute:: db_tables_compatible
      :type: bool

      Gets the compatibility status of the database tables.


MigrationStep
-------------

.. class:: MigrationStep(sql: str, description: str, target_version: int)

   Represents a migration step to be applied to a database table when upgrading from one version to another.

   This is a frozen dataclass that encapsulates information about a single migration step.

   :param sql: The SQL command to execute as part of the migration.
   :type sql: str
   :param description: A short description of what the migration does.
   :type description: str
   :param target_version: The version of the table after applying this migration step.
   :type target_version: int

   **Attributes:**

   .. attribute:: sql
      :type: str

      The SQL command to execute.

   .. attribute:: description
      :type: str

      A description of the migration.

   .. attribute:: target_version
      :type: int

      The target version after migration.

