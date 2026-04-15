# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, Tuple, Any, Sequence, Optional
from dataclasses import dataclass
import numpy as np
import warp as wp
import sqlite3
from sqlite3 import Error
import carb
from .clash_data_serializer import AbstractClashDataSerializer
from .clash_info import ClashInfo, ClashFrameInfo, ClashState
from .clash_query import ClashQuery
from .usd_utils import serialize_matrix_to_json, deserialize_matrix_from_json
from omni.physxclashdetectioncore.utils import file_exists #, measure_execution_time


class ClashDataSerializerSqlite(AbstractClashDataSerializer):
    """A class for serializing and deserializing clash data using SQLite database.

    This class provides functionality to read, write, update, and delete clash data and clash queries in an SQLite database.
    It ensures compatibility with specific versions of clash data structures and manages database connections and transactions.

    It supports deferred database creation until the first write operation to avoid creating empty database files.
    The class also includes methods for checking table compatibility, creating necessary database tables, and inserting,
    updating, and querying clash data and clash queries.
    """

    CLASH_DB_FILE_EXT = ".clashdb"
    SUPPORTED_CLASH_QUERY_VERSION = 3
    SUPPORTED_CLASH_INFO_VERSION = 17
    SUPPORTED_CLASH_FRAME_INFO_VERSION = 6

    @dataclass(frozen=True)
    class MigrationStep:
        """
        Represents a migration step to be applied to a database table when upgrading from one version to another.

        Attributes:
            sql (str): The SQL command to execute as part of the migration.
            description (str): A short description of what the migration does.
            target_version (int): The version of the table after applying this migration step.
        """
        sql: str
        description: str
        target_version: int

    def __init__(self) -> None:
        """Initializes the ClashDataSerializerSqlite instance."""
        super().__init__()
        self._connection = None
        self._db_file_path_name = ""
        self._deferred_db_creation_until_commit_query = True  # To avoid empty clash DBs, create DB upon 1st commit DB query is executed
        self._compatible_with_data_structures = self.check_serializer_compatibility_with_data_structures()
        self._db_tables_compatible = True
        self._db_tables_migration_possible = False  # True if migration of all tables to latest version is possible
        # migrations: table name -> table version -> migration step
        self._migrations: Dict[str, Dict[int, ClashDataSerializerSqlite.MigrationStep]] = {
            "clash_info": {
                15: ClashDataSerializerSqlite.MigrationStep(
                    sql=(
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_px REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_nx REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_py REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_ny REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_pz REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_info ADD COLUMN penetration_depth_nz REAL DEFAULT -1.0;"
                    ),
                    description="Add penetration depth columns with DEFAULT -1.0",
                    target_version=16
                ),
                16: ClashDataSerializerSqlite.MigrationStep(
                    sql="CREATE INDEX IF NOT EXISTS idx_clash_info_query_id_overlap_id ON clash_info(query_id, overlap_id);",
                    description="Add index on query_id and overlap_id to optimize ORDER BY overlap_id queries like find_all_overlaps_by_query_id",
                    target_version=17
                ),
            },
            "clash_frame_info": {
                5: ClashDataSerializerSqlite.MigrationStep(
                    sql=(
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_px REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_nx REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_py REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_ny REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_pz REAL DEFAULT -1.0;"
                        "ALTER TABLE clash_frame_info ADD COLUMN penetration_depth_nz REAL DEFAULT -1.0;"
                    ),
                    description="Add penetration depth columns with DEFAULT -1.0",
                    target_version=6
                ),
            }
        }

    def __del__(self) -> None:
        self._close_connection()

    @property
    def db_file_path_name(self) -> str:
        """Gets the database file path name.

        Returns:
            str: The database file path name.
        """
        return self._db_file_path_name

    @property
    def deferred_db_creation_until_commit_query(self) -> bool:
        """Gets the deferred database creation until commit query flag.

        Returns:
            bool: The deferred DB creation flag.
        """
        return self._deferred_db_creation_until_commit_query

    @property
    def compatible_with_data_structures(self) -> bool:
        """Gets the compatibility status with data structures.

        Returns:
            bool: True if compatible with data structures.
        """
        return self._compatible_with_data_structures

    @property
    def db_tables_compatible(self) -> bool:
        """Gets the compatibility status of the database tables.

        Returns:
            bool: True if DB tables are compatible.
        """
        return self._db_tables_compatible

    @staticmethod
    def check_serializer_compatibility_with_data_structures() -> bool:
        """Checks if the serializer is compatible with current data structures.

        Returns:
            bool: True if compatible with current data structures.
        """
        if ClashInfo.VERSION != ClashDataSerializerSqlite.SUPPORTED_CLASH_INFO_VERSION:
            carb.log_error(
                f"Unsupported clash info version {ClashInfo.VERSION}. "
                f"This extension supports version {ClashDataSerializerSqlite.SUPPORTED_CLASH_INFO_VERSION}."
            )
            return False
        if ClashFrameInfo.VERSION != ClashDataSerializerSqlite.SUPPORTED_CLASH_FRAME_INFO_VERSION:
            carb.log_error(
                f"Unsupported clash frame info version {ClashFrameInfo.VERSION}. "
                f"This extension supports version {ClashDataSerializerSqlite.SUPPORTED_CLASH_FRAME_INFO_VERSION}."
            )
            return False
        if ClashQuery.VERSION != ClashDataSerializerSqlite.SUPPORTED_CLASH_QUERY_VERSION:
            carb.log_error(
                f"Unsupported clash query version {ClashQuery.VERSION}. "
                f"This extension supports version {ClashDataSerializerSqlite.SUPPORTED_CLASH_QUERY_VERSION}."
            )
            return False
        return True

    def check_compatibility_of_tables(self) -> bool:
        """Checks if the current database tables are compatible.

        Returns:
            bool: True if tables are compatible.
        """
        # check table versions
        return (
            self._check_table_version("clash_query", ClashQuery.VERSION)
            and self._check_table_version("clash_info", ClashInfo.VERSION)
            and self._check_table_version("clash_frame_info", ClashFrameInfo.VERSION)
        )

    def check_possibility_of_tables_migration(self) -> bool:
        """Checks if migration of all tables to the latest version is possible.

        Returns:
            bool: True if migration of all tables to the latest version is possible.
        """
        if self.data_structures_compatible():
            return True
        return (
            self._table_has_migration_path("clash_query", ClashQuery.VERSION)
            and self._table_has_migration_path("clash_info", ClashInfo.VERSION)
            and self._table_has_migration_path("clash_frame_info", ClashFrameInfo.VERSION)
        )

    def _has_migration_path(self, table_name: str, start_version: int, target_version: int) -> bool:
        if start_version > target_version:
            return False
        if start_version == target_version:
            return True
        migrations = self._migrations.get(table_name)
        if not migrations:
            return False
        v = start_version
        visited = set()
        while v < target_version:
            step = migrations.get(v)
            if not step:
                return False
            nxt = step.target_version
            if nxt <= v or nxt in visited:
                return False
            if nxt > target_version:
                return False
            visited.add(v)
            v = nxt
        return v == target_version

    def _table_has_migration_path(self, table_name: str, target_version: int) -> bool:
        table_version = self._load_table_version_info(table_name)
        if table_version != target_version:
            if not self._has_migration_path(table_name, table_version, target_version):
                carb.log_error(f"No migration path for table '{table_name}' from version {table_version} to {target_version} found!")
                return False
        return True

    def migrate_table(self, table_name: str, target_version: int, commit: bool = True) -> bool:
        """
        Run all migration steps for the given table from start_version to target_version in a single transaction.
        Returns True if the full sequence succeeds; on failure, rolls back and returns False.
        """
        if not self._ensure_connection():
            return False
        if not self._table_has_migration_path(table_name, target_version):
            return False
        table_version = self._load_table_version_info(table_name)
        if table_version == -1:
            carb.log_error(f"Table '{table_name}' has no version info!")
            return False
        if table_version == target_version:
            return True
        migrations = self._migrations.get(table_name)
        if not migrations:
            carb.log_error(f"No migrations found for table '{table_name}'!")
            return False
        while table_version < target_version:
            step = migrations[table_version]
            if not self._execute_script(step.sql, commit=False):
                carb.log_error(f"Migration of table '{table_name}' from version {table_version} to {step.target_version} [{step.description}] failed!")
                return False
            self._update_table_version_info(table_name, step.target_version, commit=False)
            carb.log_info(f"Migration of table '{table_name}' from version {table_version} to {step.target_version} [{step.description}] was successful.")
            table_version = step.target_version
        if commit:
            self.commit()
        return True

    def _create_connection(self, db_file_path_name: str, close_on_incompatibility: bool = True) -> bool:
        self._close_connection()
        if not self.compatible_with_data_structures:
            carb.log_error("SQL Serializer Fatal Error: internal incompatibility of data structures.")
            return False
        try:
            self._db_file_path_name = db_file_path_name

            # isolation_level="DEFERRED" - read lock is obtained when a SELECT statement is issued, but write locks
            # are deferred until the first write operation (INSERT, UPDATE, DELETE).
            # Changes are not visible to other transactions until the transaction is committed.
            self._connection = sqlite3.connect(
                self._db_file_path_name, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level="DEFERRED"
            )
        except Error as e:
            carb.log_error(f"SQLite error '{e}' occurred.")
            self._connection = None

        if not self._connection:
            return False
        self._db_tables_compatible = self.check_compatibility_of_tables()
        if not self._db_tables_compatible:
            carb.log_error(
                "SQL Serializer Fatal Error: some or all tables are not compatible with current version of extension."
            )
            self._db_tables_migration_possible = self.check_possibility_of_tables_migration()
            if self._db_tables_migration_possible:
                carb.log_info(
                    "SQL Serializer Info: Good news, migration of all tables to the latest version is possible!"
                )
            else:
                carb.log_error(
                    "SQL Serializer Fatal Error: migration of some or all tables to the latest version is not possible."
                )
            if close_on_incompatibility:
                self._close_connection()
            return False
        return True

    def _close_connection(self) -> None:
        if self._connection:
            self.commit()
            # self._dump_database_to_text_sql()  # debug code - dump db to text
            self._connection.close()
            self._connection = None
        self._db_file_path_name = ""

    def _ensure_connection(self, for_writing: bool = True) -> bool:
        """Help with taking care of deferred DB creation.
        Unless asked for connection 'for_writing', the DB is never created.
        """
        if self._connection:
            return True
        else:
            db_exists = self._db_file_path_name and file_exists(self._db_file_path_name)  # DB file already exists
            if self.deferred_db_creation_until_commit_query:
                if for_writing:
                    if self._create_connection(self._db_file_path_name):
                        if not db_exists:
                            if self._create_tables():
                                return True
                        else:
                            return True
                else:
                    if db_exists:  # DB file already exists
                        return self._create_connection(self._db_file_path_name)
        return False

    def commit(self) -> None:
        """Commits any unwritten data to the target file."""
        if self._connection:
            self._connection.commit()

    def _dump_database_to_text_sql(self, file_name: str = "") -> bool:  # DEBUG only
        if not self._connection:
            return False
        path_name = file_name
        if not path_name:
            path_name = self._db_file_path_name
        if not path_name:
            return False
        r = True
        try:
            with open(path_name + ".sql", "w") as f:
                for line in self._connection.iterdump():
                    f.write(f"{line}\n")
        except Exception as e:
            carb.log_error(f"File write exception '{e}' occurred.\nFile: '{path_name}'.")
            r = False
        return r

    #  @measure_execution_time
    def _execute_fetch_query(self, query: str, params=(), fetch_all: bool = True) -> Any:
        """returns fetched records."""
        if not self._ensure_connection(False):
            return None
        if not self._connection:
            return None
        cursor = self._connection.cursor()
        r = None
        try:
            cursor.execute(query, params)
            r = cursor.fetchall() if fetch_all is True else cursor.fetchone()
        except Error as e:
            carb.log_error(f"_execute_fetch_query: SQLite error '{e}' occurred.")
        except Exception as e:
            carb.log_error(f"_execute_fetch_query: SQLite exception '{e}' occurred.")
        finally:
            cursor.close()
        return r

    #  @measure_execution_time
    def _execute_commit_query(self, query: str, params=(), commit: bool = False) -> Tuple[int, int]:
        """returns tuple: (number of records processed, new row id)."""
        if not self._ensure_connection():
            return 0, 0
        if not self._connection:
            return 0, 0
        cursor = self._connection.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                self._connection.commit()
        except Error as e:
            carb.log_error(f"_execute_commit_query: SQLite error '{e}' occurred.")
            self._connection.rollback()
        except Exception as e:
            carb.log_error(f"_execute_commit_query: SQLite exception '{e}' occurred.")
            self._connection.rollback()
        finally:
            cursor.close()

        r = cursor.rowcount
        row_id = cursor.lastrowid if cursor.lastrowid else 0
        if self._on_modified_fnc:
            self._on_modified_fnc(self._db_file_path_name)
        return r, row_id

    #  @measure_execution_time
    def _execute_script(self, script: str, commit: bool = False) -> bool:
        """Executes a script against the database.

        Args:
            script (str): The script to execute.
            commit (bool): Whether to commit the transaction.

        Returns:
            bool: True if the script was executed successfully, False otherwise.
        """
        if not self._ensure_connection():
            return False
        if not self._connection:
            return False
        error = False
        cursor = self._connection.cursor()
        try:
            cursor.executescript(script)
            if commit:
                self._connection.commit()
        except Error as e:
            carb.log_error(f"_execute_script: SQLite error '{e}' occurred. Script: {script}")
            self._connection.rollback()
            error = True
        except Exception as e:
            carb.log_error(f"_execute_script: SQLite exception '{e}' occurred. Script: {script}")
            self._connection.rollback()
            error = True
        finally:
            cursor.close()

        if self._on_modified_fnc:
            self._on_modified_fnc(self._db_file_path_name)

        return not error

    def _table_exists(self, table_name: str) -> bool:
        sql_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        result = self._execute_fetch_query(sql_query, (table_name,), False)
        if result is not None and result[0].casefold() == table_name.casefold():
            return True
        return False

    def _save_table_version_info(self, table_name: str, version: int, commit: bool = False) -> None:
        sql_query = "INSERT INTO version_info(table_name, version) VALUES(?,?);"
        self._execute_commit_query(sql_query, (table_name, version), commit)

    def _update_table_version_info(self, table_name: str, version: int, commit: bool = False) -> None:
        sql_query = "UPDATE version_info SET version=? WHERE table_name=?;"
        self._execute_commit_query(sql_query, (version, table_name), commit)

    def _load_table_version_info(self, table_name: str) -> int:
        if not self._table_exists(table_name):
            return -1
        sql_query = "SELECT version FROM version_info WHERE table_name=?;"
        result = self._execute_fetch_query(sql_query, (table_name,), False)
        if result is not None:
            return result[0]
        return -1

    def _check_table_version(self, table_name: str, expected_version: int) -> bool:
        table_version = self._load_table_version_info(table_name)
        if table_version == -1:
            return True  # We are "compatible" with an empty database
        if table_version != expected_version:
            carb.log_error(
                f"SqliteSerializer: Incompatible DB table {table_name}! Table version = {table_version}, but expected version was {expected_version}."
            )
            return False
        return True

    def _create_tables(self) -> bool:
        """Creates Db layout only if not existing."""

        sql_set_page_size = """
            PRAGMA page_size = 8192;
        """
        self._execute_commit_query(sql_set_page_size)

        sql_create_table_clash_query = """
            CREATE TABLE IF NOT EXISTS clash_query (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_name VARCHAR(1024),
            object_a_path TEXT,
            object_b_path TEXT,
            clash_detect_settings TEXT,
            creation_timestamp TIMESTAMP,
            last_modified_timestamp TIMESTAMP,
            last_modified_by VARCHAR(255),
            comment TEXT
            );
        """
        self._execute_commit_query(sql_create_table_clash_query)

        sql_create_table_clash_info = """
            CREATE TABLE IF NOT EXISTS clash_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER,
            overlap_id VARCHAR(40) NOT NULL,
            overlap_type INTEGER,
            present INTEGER(1),
            min_distance REAL,
            max_local_depth REAL,
            depth_epsilon REAL,
            tolerance REAL,
            object_a_path VARCHAR(2048) NOT NULL,
            object_a_mesh_crc VARCHAR(40) NOT NULL,
            object_b_path VARCHAR(2048) NOT NULL,
            object_b_mesh_crc VARCHAR(40) NOT NULL,
            start_timecode REAL,
            end_timecode REAL,
            num_records INTEGER,
            overlap_tris INTEGER,
            state INTEGER,
            priority INTEGER,
            person_in_charge VARCHAR(255),
            creation_timestamp TIMESTAMP,
            last_modified_timestamp TIMESTAMP,
            last_modified_by VARCHAR(255),
            comment TEXT,
            penetration_depth_px REAL,
            penetration_depth_nx REAL,
            penetration_depth_py REAL,
            penetration_depth_ny REAL,
            penetration_depth_pz REAL,
            penetration_depth_nz REAL,
            FOREIGN KEY(query_id) REFERENCES clash_query(id)
            );
        """
        self._execute_commit_query(sql_create_table_clash_info)

        sql_create_table_clash_frame_info = """
            CREATE TABLE IF NOT EXISTS clash_frame_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clash_info_id INTEGER,
            timecode REAL,
            min_distance REAL,
            max_local_depth REAL,
            overlap_tris INTEGER,
            usd_faces_0 BLOB,
            usd_faces_1 BLOB,
            collision_outline BLOB,
            object_0_matrix TEXT,
            object_1_matrix TEXT,
            penetration_depth_px REAL,
            penetration_depth_nx REAL,
            penetration_depth_py REAL,
            penetration_depth_ny REAL,
            penetration_depth_pz REAL,
            penetration_depth_nz REAL,
            FOREIGN KEY(clash_info_id) REFERENCES clash_info(id)
            );
        """
        self._execute_commit_query(sql_create_table_clash_frame_info)

        sql_create_table_version_info = """
            CREATE TABLE IF NOT EXISTS version_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name VARCHAR(128),
            version INTEGER
            );
        """
        self._execute_commit_query(sql_create_table_version_info)

        # on delete trigger to ensure no leftover clash_frame_info items hanging in the DB
        sql_create_table_clash_info_delete_trigger = """
            CREATE TRIGGER clash_info_delete
            AFTER DELETE ON clash_info
            FOR EACH ROW
            BEGIN
                DELETE FROM clash_frame_info WHERE clash_info_id=OLD.id;
            END;
        """
        self._execute_commit_query(sql_create_table_clash_info_delete_trigger)

        # create indices for faster data retrieval
        sql_create_index_query_id = "CREATE INDEX IF NOT EXISTS idx_query_id ON clash_info (query_id);"
        self._execute_commit_query(sql_create_index_query_id)

        sql_create_index_query_id_overlap_id = (
            "CREATE INDEX IF NOT EXISTS idx_clash_info_query_id_overlap_id ON clash_info(query_id, overlap_id);"
        )
        self._execute_commit_query(sql_create_index_query_id_overlap_id)

        sql_create_index_overlap_id = "CREATE INDEX IF NOT EXISTS idx_overlap_id ON clash_info (overlap_id);"
        self._execute_commit_query(sql_create_index_overlap_id)

        sql_create_index_clash_info = (
            "CREATE INDEX IF NOT EXISTS idx_clash_info_id ON clash_frame_info (clash_info_id);"
        )
        self._execute_commit_query(sql_create_index_clash_info)

        # insert version info items only if they don't exist
        if self._load_table_version_info("clash_query") == -1:
            self._save_table_version_info("clash_query", ClashQuery.VERSION)
        if self._load_table_version_info("clash_info") == -1:
            self._save_table_version_info("clash_info", ClashInfo.VERSION)
        if self._load_table_version_info("clash_frame_info") == -1:
            self._save_table_version_info("clash_frame_info", ClashFrameInfo.VERSION)

        # write all to the file
        self.commit()

        # check table versions
        if self.check_compatibility_of_tables():
            return True

        return False

    @staticmethod
    def _create_clash_info(db_result) -> ClashInfo:
        """
        Creates a `ClashInfo` object from a database result.

        This method validates the length of the database result and initializes a `ClashInfo`
        object using the provided data.
        Boolean fields are converted from integer representations.

        Args:
            db_result: A sequence containing the database result data used to populate
                the `ClashInfo` object.

        Returns:
            ClashInfo: An instance of the `ClashInfo` class populated with the provided
            data. If the length of `db_result` does not match, an empty `ClashInfo` instance
            is returned.
        """
        expected_num_results = 30
        if len(db_result) != expected_num_results:
            carb.log_error(f"unexpected # of results, {expected_num_results} expected, got {len(db_result)}")
            return ClashInfo()
        ci = ClashInfo(*db_result[:24])
        ci._penetration_depth_px = db_result[24]
        ci._penetration_depth_nx = db_result[25]
        ci._penetration_depth_py = db_result[26]
        ci._penetration_depth_ny = db_result[27]
        ci._penetration_depth_pz = db_result[28]
        ci._penetration_depth_nz = db_result[29]
        # Fix bools
        ci._present = ci._present == 1
        return ci

    def _create_clash_info_dict_entry(
        self, db_result, fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0
    ) -> tuple[str, ClashInfo]:
        """
        Creates an entry for the clash information dictionary.

        This method processes a database result to create a `ClashInfo` object and optionally
        fetches additional frame information related to the clash. It also supports specifying
        an offset for the first frame when loading frame information.

        Args:
            db_result: The database result used to create the `ClashInfo` object.
            fetch_also_frame_info (bool): If True, fetches clash frame information associated
                with the `ClashInfo` object.
            num_frames_to_load (int, optional): The number of frames to load if fetching frame
                information. Defaults to -1, which means load all available frames.
            first_frame_offset (int, optional): The offset for the first frame to load when
                fetching frame information. Defaults to 0.

        Returns:
            tuple[str, ClashInfo]: A tuple containing the overlap ID (as a string) and the
            corresponding `ClashInfo` object.
        """
        cie = self._create_clash_info(db_result)
        if fetch_also_frame_info:
            #  also load clash_frame_info items
            cie._clash_frame_info_items = self.fetch_clash_frame_info_by_clash_info_id(
                cie.identifier, num_frames_to_load, first_frame_offset
            )
        return cie.overlap_id, cie

    def vacuum(self) -> None:
        """Defragments the database and reclaims freed space."""
        if not self._connection:
            return
        sql_query = """
            VACUUM;
        """
        self._execute_commit_query(sql_query, commit=True)

    # overrides
    def open(self, file_path_name: str) -> None:
        """Creates a file or opens an existing one.

        Args:
            file_path_name (str): Path to the file to be opened.
        """
        self._db_tables_compatible = True
        self._db_tables_migration_possible = False
        if self.deferred_db_creation_until_commit_query:
            self._close_connection()  # make sure we don't leave previous connection hanging
            self._db_file_path_name = file_path_name
            return
        self._create_connection(file_path_name)
        if self.is_open():
            self._create_tables()

    def get_file_path(self) -> str:
        """Returns the serializer file path.

        Returns:
            str: The serializer file path.
        """
        return self.db_file_path_name

    def get_file_size(self) -> int:
        """Returns the serializer file size in bytes.

        Returns:
            int: The file size in bytes.
        """
        if not self._connection:
            return 0
        cursor = self._connection.cursor()

        # Get the page count and page size
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]

        # Calculate the total size
        total_size_bytes = page_count * page_size

        return total_size_bytes

    def get_free_list_size(self) -> int:
        """Returns the size of SQLite's freelist in bytes.

        The freelist contains pages that were previously used but are now free.
        These pages can be reused for new data.

        Returns:
            int: The total size of free pages in bytes.
        """
        if not self._connection:
            return 0
        cursor = self._connection.cursor()

        # Get the page count and page size
        cursor.execute("PRAGMA freelist_count;")
        freelist_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]

        freelist_size_bytes = freelist_count * page_size

        return freelist_size_bytes

    def data_structures_compatible(self) -> bool:
        """Returns True if the serializer has no compatibility issues (data structures, tables).

        Returns:
            bool: True if no compatibility issues.
        """
        return self.compatible_with_data_structures and self.db_tables_compatible

    def data_structures_migration_to_latest_version_possible(self) -> bool:
        """Returns True if the serializer can migrate data structures to the latest version.

        Returns:
            bool: True if migration to the latest version is possible.
        """
        if self.data_structures_compatible():
            return True

        return self._db_tables_migration_possible

    def migrate_data_structures_to_latest_version(self, file_path_name: str) -> bool:
        """Migrates data structures to the latest version.
        The single transaction design ensures atomic schema updates. Either all steps commit successfully or
        the entire sequence is rolled back, preserving the pre-migration state on error.

        Args:
            file_path_name (str): Path to the clash data.

        Returns:
            bool: True if migration was successful, False otherwise.
        """
        self._create_connection(file_path_name, False)
        if not self._connection:
            carb.log_error("Failed to create connection for migration!")
            return False

        result = False

        if (
            self.migrate_table("clash_query", ClashQuery.VERSION, commit=False)
            and self.migrate_table("clash_info", ClashInfo.VERSION, commit=False)
            and self.migrate_table("clash_frame_info", ClashFrameInfo.VERSION, commit=False)
        ):
            self.commit()
            result = True

        self._close_connection()
        return result

    def deferred_file_creation_until_first_write_op(self) -> bool:
        """Returns True if the serializer will postpone file creation until the first write operation is requested.

        Returns:
            bool: True if file creation is deferred until first write.
        """
        return self.deferred_db_creation_until_commit_query

    def set_deferred_file_creation_until_first_write_op(self, value: bool) -> None:
        """Sets if the serializer must postpone file creation until the first write operation is requested.

        Args:
            value (bool): True to defer file creation, False otherwise.
        """
        self._deferred_db_creation_until_commit_query = value

    def is_open(self) -> bool:
        """Returns if the serializer is ready.

        Returns:
            bool: True if the serializer is ready.
        """
        if self._connection is None:
            if self.deferred_db_creation_until_commit_query:
                if self._db_file_path_name:
                    return True  # in case of deferred DB creation return True if tmp DB filename is properly setup
        return self._connection is not None

    def save(self) -> bool:
        """Saves data to the target file.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        if not self.is_open():
            return False
        self.commit()

        db_fragmentation = (
            float(self.get_free_list_size()) / float(self.get_file_size())
            if self.get_file_size() > 0 else 0.0
        )
        # Only vacuum if DB is fragmented over 10%
        if db_fragmentation > 0.1:
            carb.log_info(
                f"DB fragmentation is {db_fragmentation:.2%} "
                f"({self.get_free_list_size()} bytes), vacuuming..."
            )
            self.vacuum()
        return True

    def close(self) -> None:
        """Closes the opened file."""
        self._close_connection()

    def insert_overlap(
        self, clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool
    ) -> int:
        """Inserts clash data. If already present, insertion is skipped.

        Args:
            clash_info (ClashInfo): Clash information to insert.
            insert_also_frame_info (bool): Whether to insert frame info as well.
            update_identifier (bool): Update identifier if needed.
            commit (bool): Commit the transaction.

        Returns:
            int: ID of the new record.
        """
        if not clash_info:
            return 0

        sql_query = """
            INSERT INTO clash_info(query_id, overlap_id, overlap_type, present,
                min_distance, max_local_depth, depth_epsilon, tolerance,
                object_a_path, object_a_mesh_crc,
                object_b_path, object_b_mesh_crc,
                start_timecode, end_timecode, num_records, overlap_tris,
                state, priority, person_in_charge,
                creation_timestamp, last_modified_timestamp, last_modified_by,
                comment,
                penetration_depth_px, penetration_depth_nx,
                penetration_depth_py, penetration_depth_ny,
                penetration_depth_pz, penetration_depth_nz)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """
        r = self._execute_commit_query(
            sql_query,
            (
                clash_info.query_id,
                clash_info.overlap_id,
                clash_info.overlap_type,
                1 if clash_info.present else 0,
                clash_info.min_distance,
                clash_info.max_local_depth,
                clash_info.depth_epsilon,
                clash_info.tolerance,
                clash_info.object_a_path,
                clash_info.object_a_mesh_crc,
                clash_info.object_b_path,
                clash_info.object_b_mesh_crc,
                clash_info.start_time,
                clash_info.end_time,
                clash_info.num_records,
                clash_info.overlap_tris,
                clash_info.state,
                clash_info.priority,
                clash_info.person_in_charge,
                clash_info.creation_timestamp,
                clash_info.last_modified_timestamp,
                clash_info.last_modified_by,
                clash_info.comment,
                clash_info.penetration_depth_px,
                clash_info.penetration_depth_nx,
                clash_info.penetration_depth_py,
                clash_info.penetration_depth_ny,
                clash_info.penetration_depth_pz,
                clash_info.penetration_depth_nz,
            ),
            commit,
        )
        new_id = r[1]

        if new_id > 0:
            if update_identifier:
                clash_info._identifier = new_id
            if (
                insert_also_frame_info
                and clash_info.clash_frame_info_items is not None
                and len(clash_info.clash_frame_info_items) > 0
            ):
                num_saved = self.insert_clash_frame_info_from_clash_info(clash_info, commit)
                if num_saved != len(clash_info.clash_frame_info_items):
                    return 0   # indicate an error happened while saving, rollback happens automatically

        return new_id

    def update_overlap(self, clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int:
        """Updates clash data if present in the database.

        Args:
            clash_info (ClashInfo): Clash information to update.
            update_also_frame_info (bool): Whether to update frame info as well.
            commit (bool): Commit the transaction.

        Returns:
            int: Number of affected records.
        """
        if not clash_info:
            return 0

        sql_query = """
            UPDATE clash_info
            SET query_id = ?, overlap_id = ?, overlap_type = ?, present = ?,
                min_distance = ?, max_local_depth = ?, depth_epsilon = ?, tolerance = ?,
                object_a_path = ?, object_a_mesh_crc = ?,
                object_b_path = ?, object_b_mesh_crc = ?,
                start_timecode = ?, end_timecode = ?, num_records = ?, overlap_tris = ?,
                state = ?, priority = ?, person_in_charge = ?,
                creation_timestamp = ?, last_modified_timestamp = ?, last_modified_by = ?,
                comment = ?,
                penetration_depth_px = ?, penetration_depth_nx = ?,
                penetration_depth_py = ?, penetration_depth_ny = ?,
                penetration_depth_pz = ?, penetration_depth_nz = ?
            WHERE id = ?;
        """
        r = self._execute_commit_query(
            sql_query,
            (
                clash_info.query_id,
                clash_info.overlap_id,
                clash_info.overlap_type,
                1 if clash_info.present else 0,
                clash_info.min_distance,
                clash_info.max_local_depth,
                clash_info.depth_epsilon,
                clash_info.tolerance,
                clash_info.object_a_path,
                clash_info.object_a_mesh_crc,
                clash_info.object_b_path,
                clash_info.object_b_mesh_crc,
                clash_info.start_time,
                clash_info.end_time,
                clash_info.num_records,
                clash_info.overlap_tris,
                clash_info.state,
                clash_info.priority,
                clash_info.person_in_charge,
                clash_info.creation_timestamp,
                clash_info.last_modified_timestamp,
                clash_info.last_modified_by,
                clash_info.comment,
                clash_info.penetration_depth_px,
                clash_info.penetration_depth_nx,
                clash_info.penetration_depth_py,
                clash_info.penetration_depth_ny,
                clash_info.penetration_depth_pz,
                clash_info.penetration_depth_nz,
                clash_info.identifier,
            ),
            commit,
        )
        ret = r[0]

        if ret > 0 and update_also_frame_info:
            # remove and re-add all associated clash frame info items
            self.remove_clash_frame_info_by_clash_info_id(clash_info.identifier, commit)
            if clash_info.clash_frame_info_items is not None and len(clash_info.clash_frame_info_items) > 0:
                cnt = self.insert_clash_frame_info_from_clash_info(clash_info, commit)
                if cnt != len(clash_info.clash_frame_info_items):
                    return 0  # indicate an error happened while saving, rollback happens automatically

        return ret

    # @measure_execution_time
    def find_all_overlaps_by_query_id(
        self,
        clash_query_id: int,
        fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0,
        num_overlaps_to_load: int = -1, first_overlap_offset: int = 0
    ) -> Dict[str, ClashInfo]:
        """
        Finds all overlaps associated with a specific query ID.

        This method retrieves all `ClashInfo` objects corresponding to the given `clash_query_id`
        from the database and optionally fetches additional frame information for each clash.

        Args:
            clash_query_id (int): The ID of the query to search for overlaps.
            fetch_also_frame_info (bool): If True, fetches frame information associated with
                each `ClashInfo` object.
            num_frames_to_load (int, optional): The maximum number of frames to load when
                fetching frame information. Defaults to -1, which means all available frames
                are loaded.
            first_frame_offset (int, optional): The offset for the first frame to load when
                fetching frame information. Defaults to 0.
            num_overlaps_to_load (int, optional): The maximum number of overlaps to load. Defaults
                to -1, which means all available overlaps are loaded.
            first_overlap_offset (int, optional): The offset for the first overlap to load. Defaults
                to 0.

        Returns:
            Dict[str, ClashInfo]: A dictionary where the keys are overlap IDs (as strings)
            and the values are the corresponding `ClashInfo` objects.
            If no results are found, an empty dictionary is returned.
        """
        sql_query = """
            SELECT * FROM clash_info WHERE query_id=? ORDER BY overlap_id ASC
        """
        sql_query += f"LIMIT {num_overlaps_to_load} OFFSET {first_overlap_offset};" if num_overlaps_to_load != -1 else ";"
        results = self._execute_fetch_query(sql_query, (clash_query_id,))
        if not results or len(results) == 0:
            return dict()

        # dict is supposed to preserve order in modern Python (Python 3.7+)
        return dict(
            self._create_clash_info_dict_entry(item, fetch_also_frame_info, num_frames_to_load, first_frame_offset)
            for item in results
        )

    def get_overlaps_count_by_query_id(self, clash_query_id: int) -> int:
        """
        Gets the total number of overlaps for a specific query ID.

        Args:
            clash_query_id (int): The ID of the query to count overlaps for.

        Returns:
            int: The total number of overlaps for the query. Returns 0 if no results found.
        """
        sql_query = "SELECT COUNT(*) FROM clash_info WHERE query_id=?;"
        result = self._execute_fetch_query(sql_query, (clash_query_id,))
        return result[0][0] if result else 0

    def get_overlaps_count_by_query_id_grouped_by_state(self, clash_query_id: int) -> Dict[ClashState, int]:
        """
        Gets the total number of overlaps for a specific query ID grouped by state.

        Args:
            clash_query_id (int): The ID of the query to count overlaps for.

        Returns:
            Dict[ClashState, int]: A dictionary where the keys are state values (as integers)
            and the values are the corresponding counts of overlaps for that state.
            If no results are found, an empty dictionary is returned.
        """
        sql_query = "SELECT state, COUNT(*) FROM clash_info WHERE query_id=? GROUP BY state;"
        result = self._execute_fetch_query(sql_query, (clash_query_id,))
        return {ClashState(int(state)): count for state, count in result} if result else dict()

    def find_all_overlaps_by_overlap_id(
        self,
        overlap_id: Sequence[int],
        fetch_also_frame_info: bool, num_frames_to_load: int = -1, first_frame_offset: int = 0
    ) -> Dict[str, ClashInfo]:
        """
        Finds all overlaps by their overlap IDs.

        This method retrieves all `ClashInfo` objects associated with the given overlap IDs
        and optionally fetches additional frame information for each clash.

        Args:
            overlap_id (Sequence[int]): A sequence of overlap IDs to search for.
            fetch_also_frame_info (bool): If True, fetches frame information associated with
                each `ClashInfo` object.
            num_frames_to_load (int, optional): The maximum number of frames to load when
                fetching frame information. Defaults to -1, which means all available frames
                are loaded.
            first_frame_offset (int, optional): The offset for the first frame to load when
                fetching frame information. Defaults to 0.

        Returns:
            Dict[str, ClashInfo]: A dictionary where the keys are overlap IDs (as strings)
            and the values are the corresponding `ClashInfo` objects.
            If no results are found, an empty dictionary is returned.
        """
        if not overlap_id or len(overlap_id) == 0:
            return dict()

        placeholders = ", ".join(["?"] * len(overlap_id))
        sql_query = f"""
            SELECT * FROM clash_info WHERE id IN({placeholders});
        """
        results = self._execute_fetch_query(sql_query, tuple(overlap_id))
        if not results or len(results) == 0:
            return dict()

        return dict(
            self._create_clash_info_dict_entry(item, fetch_also_frame_info, num_frames_to_load, first_frame_offset)
            for item in results
        )

    def remove_all_overlaps_by_query_id(self, clash_query_id: int, commit: bool) -> int:
        """Deletes specified clash data related to query_id.

        Args:
            clash_query_id (int): The ID of the clash query.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of deleted rows.
        """
        sql_query = """
            DELETE FROM clash_info WHERE query_id=?;
        """
        r = self._execute_commit_query(sql_query, (clash_query_id,), commit)
        return r[0]

    def remove_overlap_by_id(self, overlap_id: int, commit: bool) -> int:
        """Deletes specified clash data.

        Args:
            overlap_id (int): The ID of the overlap.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of deleted rows.
        """
        sql_query = """
            DELETE FROM clash_info WHERE id=?;
        """
        r = self._execute_commit_query(sql_query, (overlap_id,), commit)
        return r[0]

    # clash_frame_info
    @staticmethod
    def _create_clash_frame_info(db_result) -> ClashFrameInfo:
        expected_num_results = 17
        if len(db_result) != expected_num_results:
            carb.log_error(f"unexpected # of results, {expected_num_results} expected, got {len(db_result)}")
            return ClashFrameInfo()

        d = "cpu"  # target device for warp arrays

        usd_faces_0 = wp.empty(dtype=wp.uint32, device=d)
        usd_faces_1 = wp.empty(dtype=wp.uint32, device=d)
        collision_outline = wp.empty(dtype=wp.float32, device=d)

        if db_result[6]:
            usd_faces_0 = wp.from_numpy(np.frombuffer(db_result[6], dtype=np.uint32), dtype=wp.uint32, device=d)
        if db_result[7]:
            usd_faces_1 = wp.from_numpy(np.frombuffer(db_result[7], dtype=np.uint32), dtype=wp.uint32, device=d)
        if db_result[8]:
            collision_outline = wp.from_numpy(np.frombuffer(db_result[8], dtype=np.float32), dtype=wp.float32, device=d)

        # Fix the matrices (convert from json to matrix)
        object_0_matrix = deserialize_matrix_from_json(db_result[9])
        object_1_matrix = deserialize_matrix_from_json(db_result[10])

        # skip the db id and clash info id, we don't care about them
        cfi = ClashFrameInfo(
            db_result[2],  # timecode
            db_result[3],  # min_distance
            db_result[4],  # max_local_depth
            db_result[5],  # overlap_tris
            usd_faces_0,
            usd_faces_1,
            collision_outline,
            object_0_matrix,
            object_1_matrix,
        )

        cfi._penetration_depth_px = db_result[11]
        cfi._penetration_depth_nx = db_result[12]
        cfi._penetration_depth_py = db_result[13]
        cfi._penetration_depth_ny = db_result[14]
        cfi._penetration_depth_pz = db_result[15]
        cfi._penetration_depth_nz = db_result[16]

        return cfi

    def fetch_clash_frame_info_by_clash_info_id(
        self, clash_info_id: int, num_frames_to_load: int = -1, first_frame_offset: int = 0
    ) -> Sequence[ClashFrameInfo]:
        """
        Fetches frame information associated with a specific clash.

        This method retrieves `ClashFrameInfo` records from the database for a given
        `clash_info_id`, ordered by timecode. It supports limiting the number of frames
        fetched and applying an offset to the starting frame.

        Args:
            clash_info_id (int): The ID of the clash for which frame information is to be fetched.
            num_frames_to_load (int, optional): The maximum number of frames to load. Defaults
                to -1, which means all available frames are loaded.
            first_frame_offset (int, optional): The offset for the first frame to load. Defaults
                to 0.

        Returns:
            Sequence[ClashFrameInfo]: A list of `ClashFrameInfo` objects representing the
            fetched frame information. Returns an empty list if no results are found.
        """
        sql_query = """
            SELECT * FROM clash_frame_info
            WHERE clash_info_id=?
            ORDER BY timecode ASC
        """
        sql_query += f"LIMIT {num_frames_to_load} OFFSET {first_frame_offset};" if num_frames_to_load != -1 else ";"
        results = self._execute_fetch_query(sql_query, (clash_info_id,))
        if results is None or len(results) == 0:
            return []
        # items array can be huge, let's free each result as soon as possible
        clash_frame_info_array = []
        for idx, item in enumerate(results):
            clash_frame_info_array.append(self._create_clash_frame_info(item))
            results[idx] = None  # Explicitly free the item to free memory ASAP
        return clash_frame_info_array

    def get_clash_frame_info_count_by_clash_info_id(self, clash_info_id: int) -> int:
        """
        Gets the total number of frame info records for a specific clash info ID.

        Args:
            clash_info_id (int): The ID of the clash info to count frame info records for.

        Returns:
            int: The total number of frame info records. Returns 0 if no results found.
        """
        sql_query = "SELECT COUNT(*) FROM clash_frame_info WHERE clash_info_id=?;"
        result = self._execute_fetch_query(sql_query, (clash_info_id,))
        return result[0][0] if result else 0

    def insert_clash_frame_info_from_clash_info(self, clash_info: ClashInfo, commit: bool) -> int:
        """Inserts clash_frame_info from ClashInfo.

        Args:
            clash_info (ClashInfo): The ClashInfo object.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of affected records.
        """
        if not clash_info:
            return 0
        count = 0
        if (
            clash_info.identifier > 0
            and clash_info.clash_frame_info_items
            and len(clash_info.clash_frame_info_items) > 0
        ):
            for cfi in clash_info.clash_frame_info_items:
                if self.insert_clash_frame_info(cfi, clash_info.identifier, commit) > 0:
                    count += 1
        return count

    def insert_clash_frame_info(self, clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int:
        """Inserts clash_frame_info.

        Args:
            clash_frame_info (ClashFrameInfo): The ClashFrameInfo object.
            clash_info_id (int): The ID of the clash info.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: ID of the new record.
        """
        if not clash_frame_info:
            return 0
        sql_query = """
            INSERT INTO clash_frame_info(clash_info_id, timecode, min_distance, max_local_depth,
                overlap_tris, usd_faces_0, usd_faces_1, collision_outline,
                object_0_matrix, object_1_matrix,
                penetration_depth_px, penetration_depth_nx,
                penetration_depth_py, penetration_depth_ny,
                penetration_depth_pz, penetration_depth_nz)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """
        r = self._execute_commit_query(
            sql_query,
            (
                clash_info_id,
                clash_frame_info.timecode,
                clash_frame_info.min_distance,
                clash_frame_info.max_local_depth,
                clash_frame_info.overlap_tris,
                clash_frame_info.usd_faces_0.numpy().tobytes(),
                clash_frame_info.usd_faces_1.numpy().tobytes(),
                clash_frame_info.collision_outline.numpy().tobytes(),
                serialize_matrix_to_json(clash_frame_info.object_0_matrix),
                serialize_matrix_to_json(clash_frame_info.object_1_matrix),
                clash_frame_info.penetration_depth_px,
                clash_frame_info.penetration_depth_nx,
                clash_frame_info.penetration_depth_py,
                clash_frame_info.penetration_depth_ny,
                clash_frame_info.penetration_depth_pz,
                clash_frame_info.penetration_depth_nz,
            ),
            commit,
        )
        return r[1]

    def remove_clash_frame_info_by_clash_info_id(self, clash_info_id: int, commit: bool) -> int:
        """Deletes specified clash_frame_info data.

        Args:
            clash_info_id (int): The ID of the clash info.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of deleted rows.
        """
        sql_query = """
            DELETE FROM clash_frame_info WHERE clash_info_id=?;
        """
        r = self._execute_commit_query(sql_query, (clash_info_id,), commit)
        return r[0]

    # ClashQuery
    @staticmethod
    def _create_clash_query(db_result) -> ClashQuery:
        cq = ClashQuery(*db_result)
        # convert the clash detect settings from str to dict
        cq.load_settings_from_str(cq.clash_detect_settings)  # type: ignore
        return cq

    def _create_clash_query_dict_entry(self, db_result) -> tuple[int, ClashQuery]:
        cq = self._create_clash_query(db_result)
        return cq.identifier, cq

    def fetch_all_queries(self) -> Dict[int, ClashQuery]:
        """Returns all clash queries.

        Returns:
            Dict[int, ClashQuery]: Dictionary of all clash queries. Key is query identifier, value is ClashQuery object.
        """
        sql_query = """
            SELECT * FROM clash_query
        """
        results = self._execute_fetch_query(sql_query, ())
        if results is None or len(results) == 0:
            return dict()
        return dict(self._create_clash_query_dict_entry(item) for item in results)

    def insert_query(self, clash_query: ClashQuery, update_identifier: bool, commit: bool) -> int:
        """Inserts clash query.

        Args:
            clash_query (ClashQuery): The ClashQuery object.
            update_identifier (bool): Whether to update the identifier.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: ID of the new record.
        """
        if not clash_query:
            return 0
        sql_query = """
            INSERT INTO clash_query(query_name, object_a_path, object_b_path,
                clash_detect_settings,
                creation_timestamp, last_modified_timestamp, last_modified_by,
                comment)
            VALUES(?,?,?,?,?,?,?,?);
        """
        r = self._execute_commit_query(
            sql_query,
            (
                clash_query.query_name,
                clash_query.object_a_path,
                clash_query.object_b_path,
                clash_query.get_settings_as_str(),
                clash_query.creation_timestamp,
                clash_query.last_modified_timestamp,
                clash_query.last_modified_by,
                clash_query.comment,
            ),
            commit,
        )
        new_id = r[1]

        if new_id > 0 and update_identifier:
            clash_query._identifier = new_id

        return new_id

    def update_query(self, clash_query: ClashQuery, commit: bool) -> int:
        """Updates clash query if present in the DB.

        Args:
            clash_query (ClashQuery): The ClashQuery object.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of affected records.
        """
        if not clash_query:
            return 0
        sql_query = """
            UPDATE clash_query
            SET query_name = ?, object_a_path = ?, object_b_path = ?,
                clash_detect_settings = ?,
                last_modified_timestamp = ?, last_modified_by = ?,
                comment = ?
            WHERE id = ?;
        """
        r = self._execute_commit_query(
            sql_query,
            (
                clash_query.query_name,
                clash_query.object_a_path,
                clash_query.object_b_path,
                clash_query.get_settings_as_str(),
                clash_query.last_modified_timestamp,
                clash_query.last_modified_by,
                clash_query.comment,
                clash_query.identifier,
            ),
            commit,
        )
        return r[0]

    def remove_query_by_id(self, query_id: int, commit: bool) -> int:
        """Deletes specified clash data.

        Args:
            query_id (int): The ID of the query.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: Number of deleted rows.
        """
        sql_query = """
            DELETE FROM clash_query WHERE id=?;
        """
        r = self._execute_commit_query(sql_query, (query_id,), commit)
        return r[0]

    def find_query(self, clash_query_id: int) -> Optional[ClashQuery]:
        """Returns specified clash query.

        Args:
            clash_query_id (int): The ID of the clash query.

        Returns:
            Optional[ClashQuery]: The ClashQuery object or None if not found.
        """
        sql_query = """
            SELECT * FROM clash_query WHERE id=?;
        """
        results = self._execute_fetch_query(sql_query, (clash_query_id,))
        if not results or len(results) == 0:
            return None
        if len(results) > 1:
            carb.log_error(f"SQLite: unexpected # of results, only 1 expected, got {len(results)}")
        return self._create_clash_query(results[0])
