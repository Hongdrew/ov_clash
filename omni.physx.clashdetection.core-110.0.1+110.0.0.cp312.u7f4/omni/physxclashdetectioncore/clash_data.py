# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, Sequence, Optional
import os
import carb
from carb.eventdispatcher import get_eventdispatcher
from pxr import Usd, Sdf, UsdUtils
import omni.kit.usd.layers as usd_layers
from .clash_data_serializer import AbstractClashDataSerializer
from .clash_info import ClashInfo, ClashFrameInfo, ClashState
from .clash_query import ClashQuery
from .clash_detect_layer_utils import ClashDetectLayerHelper
from .utils import file_exists, get_unique_temp_file_path_name, safe_delete_file, is_local_url
from .config import ExtensionConfig
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry


# decorator to identify serializer data operation.
# Handy for tests to quickly find out that a method was added or removed
Serializer_data_operations = []


def serializer_data_op(fnc):
    """Decorator to identify serializer data operation.
    Handy for tests to quickly find out that a method was added or removed.

    Args:
        fnc (function): The function to be registered as a serializer data operation.

    Returns:
        function: The registered function.
    """
    Serializer_data_operations.append(fnc)
    return fnc


class ClashData:
    """A class for handling clash detection data within a USD stage.

    This class manages the creation, modification, and deletion of clash detection data layers in a USD stage. It interfaces with a specified serializer to handle the persistence of clash data and ensures compatibility and integrity of the data structures.

    Args:
        clash_data_serializer (AbstractClashDataSerializer): The serializer used to manage the persistence of clash detection data.
    """

    CLASH_DATA_LAYER_FILE_EXT = ".clashDetection"
    CLASH_DATA_FILE_EXT = ".clashdata"
    CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH = "clashDbPath"
    CLASH_DATA_LAYER_CUSTOM_MODIFIED = "clashDbModified"

    def __init__(self, clash_data_serializer: AbstractClashDataSerializer) -> None:
        """Initializes the ClashData object."""
        self._serializer = clash_data_serializer
        if self._serializer:
            self._serializer.set_on_modified_fnc(self._on_serializer_file_modified)
        self._stage_id: Optional[int] = None
        self._usd_file_path: str = ""
        self._target_layer: Optional[Sdf.Layer] = None
        self._old_target_layer_identifier: str = ""  # do not hold a reference to the layer itself, use its identifier only.
        # dict of all clash data layers we ever loaded. The dict contains {layer identifier: temp clash data file path}.
        self._loaded_layers: dict[str, str] = dict()
        self.__layers_event_sub = None
        layers = usd_layers.get_layers()
        if layers:
            self.__layers_event_sub = get_eventdispatcher().observe_event(
                observer_name="ClashData SUBLAYERS_CHANGED Layer Event",
                event_name=usd_layers.layer_event_name(usd_layers.LayerEventType.SUBLAYERS_CHANGED),  # type: ignore
                on_event=lambda _: self.__on_layer_changed_event(),
                filter=layers.get_event_key()
            )

    def destroy(self) -> None:
        """Cleans up resources and resets object state."""
        self.__layers_event_sub = None
        self._loaded_layers = dict()
        if self._serializer:
            self._serializer.set_on_modified_fnc(None)
            self._serializer = None
        self._usd_file_path = ""
        self._target_layer = None
        self._old_target_layer_identifier = ""
        self._stage_id = None

    @property
    def stage_id(self) -> Optional[int]:
        """Gets the associated stage ID.

        Returns:
            Optional[int]: The associated stage ID.
        """
        return self._stage_id

    @property
    def stage(self) -> Optional[Usd.Stage]:
        """Gets the associated stage.

        Returns:
            Optional[Usd.Stage]: The associated stage.
        """
        if not self._stage_id:
            return None
        return UsdUtils.StageCache.Get().Find(Usd.StageCache.Id.FromLongInt(self._stage_id))

    @property
    def usd_file_path(self) -> str:
        """Gets the stage file path.

        Returns:
            str: The stage file path.
        """
        return self._usd_file_path

    @property
    def serializer_path(self) -> str:
        """Gets the serializer file path.

        Returns:
            str: The serializer file path.
        """
        if self._serializer:
            return self._serializer.get_file_path()
        return ""

    @property
    def data_structures_compatible(self) -> bool:
        """Gets whether the serializer has no compatibility issues.

        Returns:
            bool: True if no compatibility issues.
        """
        if self._serializer:
            return self._serializer.data_structures_compatible()
        return True

    @property
    def data_structures_migration_to_latest_version_possible(self) -> bool:
        """Returns True if the serializer can migrate data structures to the latest version.

        Returns:
            bool: True if migration to the latest version is possible.
        """
        if self._serializer:
            return self._serializer.data_structures_migration_to_latest_version_possible()
        return True

    @property
    def deferred_file_creation_until_first_write_op(self) -> bool:
        """Gets whether the serializer will postpone file creation until the first write operation.

        Returns:
            bool: True if file creation is postponed.
        """
        if self._serializer:
            return self._serializer.deferred_file_creation_until_first_write_op()
        return False

    @deferred_file_creation_until_first_write_op.setter
    def deferred_file_creation_until_first_write_op(self, value: bool):
        """Sets whether the serializer must postpone file creation until the first write operation.

        Args:
            value (bool): Postpone file creation until the first write operation.
        """
        if self._serializer:
            self._serializer.set_deferred_file_creation_until_first_write_op(value)

    def __on_layer_changed_event(self) -> None:
        """This is only here to clean-up old clash data dbs from local temp folder."""
        layer_identifiers = list(self._loaded_layers.keys())
        for layer_identifier in layer_identifiers:
            layer = Sdf.Layer.Find(layer_identifier)
            if not layer:  # layer is no longer cached in memory, time to remove the TEMP DB
                self.__layer_remove_assoc_db_from_disk(layer_identifier)
                del self._loaded_layers[layer_identifier]

    def __layer_remove_assoc_db_from_disk(self, layer_identifier) -> bool:
        file_path_name = self._loaded_layers.get(layer_identifier, None)
        if file_path_name:
            # if layer is still loaded in memory, do not delete it
            loaded_layer = ClashDetectLayerHelper.find_clash_detect_layer(layer_identifier)
            if loaded_layer:
                if ExtensionConfig.debug_logging:
                    carb.log_info(
                        f"Layer '{layer_identifier}': not removing '{file_path_name}' because the layer is still present in memory.'"
                    )
                return False
            # if there is another layer among _loaded_layers that references the same DB, do not delete it
            for k, v in self._loaded_layers.items():
                if k != layer_identifier and file_path_name == v:
                    if ExtensionConfig.debug_logging:
                        carb.log_info(
                            f"Layer '{layer_identifier}': not removing '{file_path_name}' because '{k}' also references it.'"
                        )
                    return False
            if ExtensionConfig.debug_logging:
                carb.log_info(f"Layer '{layer_identifier}': removing '{file_path_name}' (if exists)")
            if file_exists(file_path_name):
                return safe_delete_file(file_path_name)
        return False

    def _layer_assoc_db_clean_up(self) -> None:
        """A clean-up of all associated clash data dbs from local temp folder.
           Use with caution, at app exit prefferably.
        """
        removed_layers = []
        for k, v in self._loaded_layers.items():
            if self.__layer_remove_assoc_db_from_disk(k):
                removed_layers.append(k)
        # remove also entries for removed layers from the _loaded_layers dict.
        for k in removed_layers:
            del self._loaded_layers[k]

    @classmethod
    def _compose_target_layer_path_name(cls, usd_file_path: str) -> str:
        """returns target layer path name."""
        if not usd_file_path:
            return ""
        base_path, _ = os.path.splitext(usd_file_path)
        return base_path + cls.CLASH_DATA_LAYER_FILE_EXT

    def _on_serializer_file_modified(self, path_name: str) -> None:
        """this callback is called on each modification of the serializer's target file."""
        # Case 1.a: we have an unnamed stage with no clash data layer as this is the first modification
        # Case 1.b: we have a stage with name with no clash data layer as this is the first modification
        # Case 2.a: we have an unnamed stage with existing unsaved anonymous clash data layer as this is not a first modification
        # Case 2.b: we have a stage with name with existing unsaved anonymous clash data layer as this is not a first modification
        # Case 3: we have a stage with name with existing file based clash data layer as this is not a first modification
        if not self._target_layer:
            # we are always first creating in-memory anonymous layer which will get saved to the file based layer on stage save.
            self._target_layer = ClashDetectLayerHelper.create_new_clash_detect_layer(self.stage, "")
        if self._target_layer and self._loaded_layers is not None:
            self._loaded_layers[self._target_layer.identifier] = path_name  # type: ignore
            metadata = {
                self.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH: path_name,
                self.CLASH_DATA_LAYER_CUSTOM_MODIFIED: "true",
            }
            ClashDetectLayerHelper.set_custom_layer_data(self._target_layer, metadata)
        else:
            carb.log_error("Failed to create clash data layer!")

    def _save_target_layer_as(self, stage: Usd.Stage, target_layer_path_name: str) -> bool:
        """saves target layer to disk under new name."""
        if not self._serializer:
            carb.log_error("Serializer is not set!")
            return False
        if not target_layer_path_name:
            carb.log_error("Target layer must have a name!")
            return False
        if self._target_layer:
            self._old_target_layer_identifier = self._target_layer.identifier  # type: ignore
            self._target_layer = None
            ClashDetectLayerHelper.remove_layer(
                stage.GetRootLayer(), self._old_target_layer_identifier
            )  # removed layer keeps existing in the USD stage cache
        self._target_layer = ClashDetectLayerHelper.create_new_clash_detect_layer(stage, target_layer_path_name)
        if self._target_layer and self._loaded_layers is not None:
            self._loaded_layers[self._target_layer.identifier] = self._serializer.get_file_path()  # type: ignore
            metadata = {
                self.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH: self._serializer.get_file_path(),
                self.CLASH_DATA_LAYER_CUSTOM_MODIFIED: "false",
            }
            ClashDetectLayerHelper.set_custom_layer_data(self._target_layer, metadata)
            # now we need to manually save the newly created layer.
            return self._target_layer.Save(True)
        return False

    def _remove_layer(self, stage: Usd.Stage, layer_identifier: str) -> bool:
        """called when a layer needs to be removed."""
        # We are dealing with 2 options here:
        # 1. the layer is completely missing, but it's referenced by the stage -> remove it from layer references.
        # 2. the layer is corrupted, it failed to load, but it is not present in the filesystem -> delete it from there.
        return ClashDetectLayerHelper.kit_remove_layer(stage, layer_identifier)

    def open(self, stage_id: Optional[int], force_reload_layer: bool = False) -> None:
        """Creates a file or opens an existing one.

        Args:
            stage_id (Optional[int]): Stage ID of the stage to work with.
            force_reload_layer (bool): Force reload target layer to ensure it doesn't come from the stage cache.
        """
        if not self._serializer or not stage_id or self._loaded_layers is None:
            return
        if self._serializer.is_open():
            self._serializer.close()
        self._stage_id = stage_id
        stage = self.stage
        if not stage:
            return
        root_layer = stage.GetRootLayer()
        self._usd_file_path = root_layer.identifier if root_layer.realPath else ""
        file_path_name = get_unique_temp_file_path_name(suffix=self.CLASH_DATA_FILE_EXT)
        # let's try to find an existing clash data layer loaded by normal USD serializer
        target_layer_path_name = self._compose_target_layer_path_name(self._usd_file_path)
        self._target_layer = ClashDetectLayerHelper.find_clash_detect_layer(target_layer_path_name)
        if self._target_layer:
            if force_reload_layer:
                ClashDetectLayerHelper.reload_layer(self._target_layer)
            metadata = ClashDetectLayerHelper.get_custom_layer_data(self._target_layer)
            db_path = metadata.get(self.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH) if metadata else ""
            if db_path:
                file_path_name = db_path
            # If there was another DB path associated with the same target layer identifier,
            # remove the DB from disk.
            # This happens when a layer is reused from a stage cache, not loaded from disk.
            prev_db_path = self._loaded_layers.get(self._target_layer.identifier, None)  # type: ignore
            if prev_db_path and db_path != prev_db_path:
                self.__layer_remove_assoc_db_from_disk(self._target_layer.identifier)
            self._loaded_layers[self._target_layer.identifier] = file_path_name  # type: ignore
        else:
            # When clash data layer is missing but was already referenced by the root layer, then
            # the layer is in read-only state and not even returned by Layer.Find()
            # -> Remove layer using a Kit command so the Layer Widget is aware of add.
            # In case no layer was loaded, then nothing happens
            self._remove_layer(stage, target_layer_path_name)
        if self._usd_file_path:
            ClashTelemetry.log_local_vs_remote_stage(is_local_url(self._usd_file_path))
        self._serializer.open(file_path_name)

    def is_open(self) -> bool:
        """Checks if the serializer is ready.

        Returns:
            bool: True if the serializer is ready.
        """
        return self.stage is not None and self._serializer is not None and self._serializer.is_open()

    def save(self) -> bool:
        """Saves data to the target file.

        Returns:
            bool: True if the save operation was successful.
        """
        if not self.stage or not self._serializer or not self._serializer.is_open():
            return False
        if not self._serializer.save():
            return False
        if self._target_layer:
            # drop the dirty flag
            metadata = {self.CLASH_DATA_LAYER_CUSTOM_MODIFIED: "false"}
            ClashDetectLayerHelper.set_custom_layer_data(self._target_layer, metadata)
            if self._target_layer.anonymous:
                target_layer_path_name = self._compose_target_layer_path_name(self.usd_file_path)
                return self._save_target_layer_as(self.stage, target_layer_path_name)
        return True

    def save_as(self, usd_file_path: str) -> bool:
        """Saves data to a new target file.

        Args:
            usd_file_path (str): The new file path to save to.

        Returns:
            bool: True if the save operation was successful.
        """
        if not self.stage or not usd_file_path or not self._serializer or not self._serializer.is_open():
            return False
        # User is giving new name to the stage.
        # If the _target_layer is anonymous, now we can finally save our target layer from memory to disk
        # If the stage previously had a name, now we have to create new named target layer
        self._serializer.save()
        self._usd_file_path = usd_file_path
        if self._target_layer:
            # Just a double checking, can be removed
            metadata = ClashDetectLayerHelper.get_custom_layer_data(self._target_layer)
            db_path = metadata.get(self.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH, "") if metadata else ""
            if db_path != self._serializer.get_file_path():
                carb.log_error("ClashData: db path name mismatch!")
            target_layer_path_name = self._compose_target_layer_path_name(usd_file_path)
            self._save_target_layer_as(self.stage, target_layer_path_name)
        return True

    def saved(self) -> None:
        """Performs operations after save."""
        # remove the old clash data layer
        if self._old_target_layer_identifier:
            # NOTE: even removed layers can still be cached in memory and can get later reused (without loading).
            # So reloading the layer makes it save the clash data to a new temp file and set it to layer custom data
            old_target_layer = Sdf.Layer.Find(self._old_target_layer_identifier)
            if old_target_layer:
                if not old_target_layer.anonymous:
                    ClashDetectLayerHelper.reload_layer(old_target_layer)
                # update the layer tracker with new clash data DB path
                metadata = ClashDetectLayerHelper.get_custom_layer_data(old_target_layer)
                if metadata and self._loaded_layers is not None:
                    db_path = metadata.get(self.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH, None)
                    self._loaded_layers[self._old_target_layer_identifier] = db_path # type: ignore
                self._old_target_layer_identifier = ""

    def close(self) -> None:
        """Closes the opened file."""
        self._usd_file_path = ""
        self._target_layer = None
        self._stage_id = None
        if self._old_target_layer_identifier:
            # _old_target_layer_identifier not None or '' means that saved() was not called prior close()
            # The only case I found out that this can happen is when 'saving as' an anonymous layer to disk.
            # Because of that, if the associated path with this layer is already used by some other layer, then remove this one.
            db_path = self._loaded_layers.get(self._old_target_layer_identifier, None)
            if db_path:
                for k, v in self._loaded_layers.items():
                    if k != self._old_target_layer_identifier and db_path == v:
                        self._loaded_layers[self._old_target_layer_identifier] = ""
            self._old_target_layer_identifier = ""
        if self._serializer and self._serializer.is_open():
            self._serializer.close()

    def commit(self) -> None:
        """Writes any unwritten data to the file."""
        if self._serializer and self._serializer.is_open():
            self._serializer.commit()

    # Data Structures Migration

    @serializer_data_op
    def migrate_data_structures_to_latest_version(self, file_path_name: str) -> bool:
        """Migrates data structures to the latest versions.

        Args:
            file_path_name (str): Path to the clash data.

        Returns:
            bool: True if migration was successful, False otherwise.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.migrate_data_structures_to_latest_version(file_path_name)
        return False

    # Overlaps (ClashInfo)

    @serializer_data_op
    def insert_overlap(
        self, clash_info: ClashInfo, insert_also_frame_info: bool, update_identifier: bool, commit: bool
    ) -> int:
        """Inserts clash data. If already present, insertion is skipped.

        Args:
            clash_info (ClashInfo): The clash information to insert.
            insert_also_frame_info (bool): Insert frame info as well.
            update_identifier (bool): Update the identifier.
            commit (bool): Commit the changes.

        Returns:
            int: ID of the new record.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.insert_overlap(clash_info, insert_also_frame_info, update_identifier, commit)
        return 0

    @serializer_data_op
    def update_overlap(self, clash_info: ClashInfo, update_also_frame_info: bool, commit: bool) -> int:
        """Updates clash data if present in the database.

        Args:
            clash_info (ClashInfo): The clash information to update.
            update_also_frame_info (bool): Update frame info as well.
            commit (bool): Commit the changes.

        Returns:
            int: Number of affected records.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.update_overlap(clash_info, update_also_frame_info, commit)
        return 0

    @serializer_data_op
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
        if self._serializer and self._serializer.is_open():
            return self._serializer.find_all_overlaps_by_query_id(
                clash_query_id, fetch_also_frame_info, num_frames_to_load, first_frame_offset,
                num_overlaps_to_load, first_overlap_offset
            )
        return dict()

    @serializer_data_op
    def get_overlaps_count_by_query_id(self, clash_query_id: int) -> int:
        """
        Gets the total number of overlaps for a specific query ID.

        Args:
            clash_query_id (int): The ID of the query to count overlaps for.

        Returns:
            int: The total number of overlaps for the query. Returns 0 if no results found.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.get_overlaps_count_by_query_id(clash_query_id)
        return 0

    @serializer_data_op
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
        if self._serializer and self._serializer.is_open():
            return self._serializer.get_overlaps_count_by_query_id_grouped_by_state(clash_query_id)
        return dict()

    @serializer_data_op
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
        if self._serializer and self._serializer.is_open():
            return self._serializer.find_all_overlaps_by_overlap_id(
                overlap_id, fetch_also_frame_info, num_frames_to_load, first_frame_offset
            )
        return dict()

    @serializer_data_op
    def remove_all_overlaps_by_query_id(self, clash_query_id: int, commit: bool) -> int:
        """Deletes specified clash data related to query_id.

        Args:
            clash_query_id (int): ID of the clash query.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of deleted rows.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.remove_all_overlaps_by_query_id(clash_query_id, commit)
        return 0

    @serializer_data_op
    def remove_overlap_by_id(self, overlap_id: int, commit: bool) -> int:
        """Deletes specified clash data.

        Args:
            overlap_id (int): ID of the overlap.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of deleted rows.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.remove_overlap_by_id(overlap_id, commit)
        return 0

    # Frames (ClashFrameInfo)

    @serializer_data_op
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
        if self._serializer and self._serializer.is_open():
            return self._serializer.fetch_clash_frame_info_by_clash_info_id(
                clash_info_id, num_frames_to_load, first_frame_offset
            )
        return []

    @serializer_data_op
    def get_clash_frame_info_count_by_clash_info_id(self, clash_info_id: int) -> int:
        """
        Gets the total number of frame info records for a specific clash info ID.

        Args:
            clash_info_id (int): The ID of the clash info to count frame info records for.

        Returns:
            int: The total number of frame info records. Returns 0 if no results found.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.get_clash_frame_info_count_by_clash_info_id(clash_info_id)
        return 0

    @serializer_data_op
    def insert_clash_frame_info_from_clash_info(self, clash_info: ClashInfo, commit: bool) -> int:
        """Inserts clash_frame_info. If already present, insertion is skipped.

        Args:
            clash_info (ClashInfo): Clash info to insert.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of affected records.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.insert_clash_frame_info_from_clash_info(clash_info, commit)
        return 0

    @serializer_data_op
    def insert_clash_frame_info(self, clash_frame_info: ClashFrameInfo, clash_info_id: int, commit: bool) -> int:
        """Inserts clash_frame_info. If already present, insertion is skipped.

        Args:
            clash_frame_info (ClashFrameInfo): Clash frame info to insert.
            clash_info_id (int): ID of the clash info.
            commit (bool): Commit changes to the database.

        Returns:
            int: ID of the new record.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.insert_clash_frame_info(clash_frame_info, clash_info_id, commit)
        return 0

    @serializer_data_op
    def remove_clash_frame_info_by_clash_info_id(self, clash_info_id: int, commit: bool) -> int:
        """Deletes specified clash_frame_info data.

        Args:
            clash_info_id (int): ID of the clash info.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of deleted rows.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.remove_clash_frame_info_by_clash_info_id(clash_info_id, commit)
        return 0

    # Queries (ClashQuery)

    @serializer_data_op
    def fetch_all_queries(self) -> Dict[int, ClashQuery]:
        """Returns all clash queries.

        Returns:
            Dict[int, ClashQuery]: Dictionary of clash queries. Key is query identifier, value is ClashQuery object.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.fetch_all_queries()
        return dict()

    @serializer_data_op
    def insert_query(self, clash_query: ClashQuery, update_identifier: bool = True, commit: bool = True) -> int:
        """Inserts clash query. If already present, insertion is skipped.

        Args:
            clash_query (ClashQuery): Clash query to insert.
            update_identifier (bool): Update identifier if True.
            commit (bool): Commit changes to the database.

        Returns:
            int: ID of the new record.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.insert_query(clash_query, update_identifier, commit)
        return 0

    @serializer_data_op
    def find_query(self, clash_query_id: int) -> Optional[ClashQuery]:
        """Returns specified clash query.

        Args:
            clash_query_id (int): ID of the clash query.

        Returns:
            Optional[ClashQuery]: The clash query or None if not present.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.find_query(clash_query_id)
        return None

    @serializer_data_op
    def update_query(self, clash_query: ClashQuery, commit: bool = True) -> int:
        """Updates clash query if present in the DB.

        Args:
            clash_query (ClashQuery): Clash query to update.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of affected records.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.update_query(clash_query, commit)
        return 0

    @serializer_data_op
    def remove_query_by_id(self, query_id: int, commit: bool = True) -> int:
        """Deletes specified clash data.

        Args:
            query_id (int): ID of the query.
            commit (bool): Commit changes to the database.

        Returns:
            int: Number of deleted rows.
        """
        if self._serializer and self._serializer.is_open():
            return self._serializer.remove_query_by_id(query_id, commit)
        return 0
