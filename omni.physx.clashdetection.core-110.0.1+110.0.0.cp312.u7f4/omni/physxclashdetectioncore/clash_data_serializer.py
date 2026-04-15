# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, Sequence, Callable, Optional
from abc import ABC, abstractmethod
from .clash_info import ClashInfo, ClashFrameInfo, ClashState
from .clash_query import ClashQuery


class AbstractClashDataSerializer(ABC):
    """A base class for serializing and managing clash data.

    This abstract class defines the necessary methods for handling clash data serialization, including opening and closing files, managing data compatibility, and performing CRUD operations on clash data and related information. Implementations of this class should provide concrete definitions for the abstract methods.
    """

    def __init__(self) -> None:
        """Initializes the AbstractClashDataSerializer class."""
        self._on_modified_fnc = None

    @abstractmethod
    def open(self, file_path_name: str) -> None:
        """Creates a file or opens an existing.

        Args:
            file_path_name (str): Path of the file to open.
        """
        pass

    @abstractmethod
    def get_file_path(self) -> str:
        """Returns the serializer file path.

        Returns:
            str: The file path of the serializer.
        """
        pass

    @abstractmethod
    def get_file_size(self) -> int:
        """Returns the serializer file size in bytes.

        Returns:
            int: The file size in bytes.
        """
        pass

    @abstractmethod
    def data_structures_compatible(self) -> bool:
        """Returns True if the serializer has no compatibility issues (data structures, tables).

        Returns:
            bool: True if compatible, False otherwise.
        """
        pass

    @abstractmethod
    def data_structures_migration_to_latest_version_possible(self) -> bool:
        """Returns True if the serializer can migrate data structures to the latest version.

        Returns:
            bool: True if migration to the latest version is possible.
        """
        pass

    @abstractmethod
    def deferred_file_creation_until_first_write_op(self) -> bool:
        """Returns True if the serializer will postpone file creation until first write op is requested.

        Returns:
            bool: True if deferred creation is enabled, False otherwise.
        """
        pass

    @abstractmethod
    def set_deferred_file_creation_until_first_write_op(self, value: bool):
        """Sets if the serializer must postpone file creation until first write op is requested.

        Args:
            value (bool): Whether to defer file creation.
        """
        pass

    def set_on_modified_fnc(self, on_modified_fnc: Optional[Callable[[str], None]]):
        """Sets on_modified_fnc.

        Args:
            on_modified_fnc (Optional[Callable[[str], None]]): The function to call when modified.
        """
        self._on_modified_fnc = on_modified_fnc

    @property
    def on_modified_fnc(self) -> Optional[Callable[[str], None]]:
        """Gets on_modified_fnc.

        Returns:
            Optional[Callable[[str], None]]: The on_modified function.
        """
        return self._on_modified_fnc

    @abstractmethod
    def is_open(self) -> bool:
        """Returns if the serializer is ready.

        Returns:
            bool: True if open, False otherwise.
        """
        pass

    @abstractmethod
    def save(self) -> bool:
        """Saves data to the target file.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the opened file."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Writes any unwritten data to the file. Committing bigger batches is advised."""
        pass


    # Data Structures Migration

    @abstractmethod
    def migrate_data_structures_to_latest_version(self, file_path_name: str) -> bool:
        """Migrates data structures to the latest versions.

        Args:
            file_path_name (str): Path to the clash data.

        Returns:
            bool: True if migration was successful, False otherwise.
        """
        pass

    # Overlaps (ClashInfo)

    @abstractmethod
    def insert_overlap(
        self, clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool
    ) -> int:
        """Inserts clash data. If already present, insertion is skipped.

        Args:
            clash_info (ClashInfo): Clash information to insert.
            insert_also_frame_info (bool): Whether to insert frame info.
            update_identifier (bool): Whether to update the identifier.
            commit (bool): Whether to commit the operation.

        Returns:
            int: ID of the new record.
        """
        pass

    @abstractmethod
    def update_overlap(self, clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int:
        """Updates clash data if present in the DB.

        Args:
            clash_info (ClashInfo): Clash information to update.
            update_also_frame_info (bool): Whether to update frame info.
            commit (bool): Whether to commit the operation.

        Returns:
            int: Number of affected records.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_overlaps_count_by_query_id(self, clash_query_id: int) -> int:
        """
        Gets the total number of overlaps for a specific query ID.

        Args:
            clash_query_id (int): The ID of the query to count overlaps for.

        Returns:
            int: The total number of overlaps for the query. Returns 0 if no results found.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def remove_all_overlaps_by_query_id(self, clash_query_id: int, commit: bool) -> int:
        """Deletes specified clash data related to query_id. If not present, nothing happens.

        Args:
            clash_query_id (int): The query ID to remove.
            commit (bool): Whether to commit the operation.

        Returns:
            int: Number of deleted rows.
        """

    @abstractmethod
    def remove_overlap_by_id(self, overlap_id: int, commit: bool) -> int:
        """Deletes specified clash data. If not present, nothing happens.

        Args:
            overlap_id (int): The overlap ID to remove.
            commit (bool): Whether to commit the operation.

        Returns:
            int: Number of deleted rows.
        """
        pass

    # Frames (ClashFrameInfo)

    @abstractmethod
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
        pass

    @abstractmethod
    def get_clash_frame_info_count_by_clash_info_id(self, clash_info_id: int) -> int:
        """
        Gets the total number of frame info records for a specific clash info ID.

        Args:
            clash_info_id (int): The ID of the clash info to count frame info records for.

        Returns:
            int: The total number of frame info records. Returns 0 if no results found.
        """
        pass

    @abstractmethod
    def insert_clash_frame_info_from_clash_info(self, clash_info: ClashInfo, commit: bool) -> int:
        """Inserts clash_frame_info from ClashInfo.

        Args:
            clash_info (ClashInfo): The ClashInfo object to extract frame info from.
            commit (bool): Whether to commit the change.

        Returns:
            int: Number of affected records.
        """
        pass

    @abstractmethod
    def insert_clash_frame_info(self, clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int:
        """Inserts clash_frame_info.

        Args:
            clash_frame_info (ClashFrameInfo): The ClashFrameInfo object to insert.
            clash_info_id (int): The ID of the associated ClashInfo.
            commit (bool): Whether to commit the change.

        Returns:
            int: ID of the new record.
        """
        pass

    @abstractmethod
    def remove_clash_frame_info_by_clash_info_id(self, clash_info_id: int, commit: bool) -> int:
        """Deletes specified clash_frame_info data.

        Args:
            clash_info_id (int): The ID of the associated ClashInfo.
            commit (bool): Whether to commit the change.

        Returns:
            int: Number of deleted rows.
        """
        pass

    # Queries (ClashQuery)

    @abstractmethod
    def fetch_all_queries(self) -> Dict[int, ClashQuery]:
        """Returns all clash queries.

        Returns:
            Dict[int, ClashQuery]: Dictionary of all clash queries. Key is query identifier, value is ClashQuery object.
        """
        pass

    @abstractmethod
    def insert_query(self, clash_query: ClashQuery, update_identifier: bool, commit: bool) -> int:
        """Inserts clash query.

        Args:
            clash_query (ClashQuery): The ClashQuery object to insert.
            update_identifier (bool): Whether to update the identifier.
            commit (bool): Whether to commit the change.

        Returns:
            int: ID of the new record.
        """
        pass

    @abstractmethod
    def find_query(self, clash_query_id: int) -> Optional[ClashQuery]:
        """Returns specified clash query.

        Args:
            clash_query_id (int): The ID of the ClashQuery to find.

        Returns:
            Optional[ClashQuery]: The found ClashQuery or None.
        """
        pass

    @abstractmethod
    def update_query(self, clash_query: ClashQuery, commit: bool) -> int:
        """Updates clash query if present in the DB.

        Args:
            clash_query (ClashQuery): The ClashQuery object to update.
            commit (bool): Whether to commit the change.

        Returns:
            int: Number of affected records.
        """
        pass

    @abstractmethod
    def remove_query_by_id(self, query_id: int, commit: bool) -> int:
        """Deletes specified clash data.

        Args:
            query_id (int): The ID of the query to remove.
            commit (bool): Whether to commit the change.

        Returns:
            int: Number of deleted rows.
        """
        pass
