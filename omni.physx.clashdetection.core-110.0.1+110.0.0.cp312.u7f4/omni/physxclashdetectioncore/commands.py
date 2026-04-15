# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.commands
import omni.client
from pxr import Usd, UsdUtils
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_data_serializer_sqlite import ClashDataSerializerSqlite
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_detect_export import export_to_html, export_to_json, ExportColumnDef
from omni.physxclashdetectioncore.utils import OptimizedProgressUpdate

# internal ref to the registered commands, so they can be
# unregistered when the extension is unloaded
_cmds = None


class OpenStageForClashDetectionCommand(omni.kit.commands.Command):
    """A command to open a USD stage for clash detection.

    This command facilitates opening a USD stage and preparing it for clash detection processes. It ensures that the stage path is standardized and that the stage is correctly loaded into the cache.

    Keyword Args:
        path (str): The path to the USD stage.
        stage_path (str): An alternative key for the path to the USD stage.
    """

    def __init__(
        self,
        **kwargs,
    ):
        """Initializes the OpenStageForClashDetectionCommand class."""
        super().__init__()

        # pull out the stage name to process from the entry
        # check for a couple different forms
        self._stage_path = None
        for key in ["path", "stage_path"]:
            if key in kwargs:
                self._stage_path = kwargs[key]
                break

        # standardize the path separator character
        self._stage_path = self._stage_path.replace("\\", "/") if self._stage_path else None

    def do(self) -> int:
        """Opens the stage for clash detection.

        Returns:
            int: The ID of the loaded stage.
        """
        if not self._stage_path:
            print("Stage name to process was not provided.")
            return 0

        # close existing stages
        stage_cache = UsdUtils.StageCache.Get()

        print(f"Opening stage '{self._stage_path}'...")
        stage = Usd.Stage.Open(self._stage_path)
        if not stage:
            print(f"Failed to open stage '{self._stage_path}'")
            return 0

        # add the new stage to the cache
        self._stage_id = stage_cache.Insert(stage).ToLongInt()
        print(f"...loaded stage ID: {self._stage_id}")

        return self._stage_id

    def undo(self) -> None:
        """Undoes the clash detection stage opening."""
        if hasattr(self, "_stage_id"):
            stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
            UsdUtils.StageCache.Get().Erase(stage_id)


class SaveClashDetectionCommand(omni.kit.commands.Command):
    """A command to save the results of a clash detection process.

    This class provides the functionality to save the clash detection results for a given stage ID to a persistent storage.

    Args:
        stage_id (int): The ID of the stage for which the clash detection results are to be saved.
    """

    def __init__(self, stage_id):
        """Initializes the SaveClashDetectionCommand."""
        super().__init__()

        self._stage_id = stage_id

    def do(self) -> int:
        """Executes the command to save clash detection results.

        Returns:
            int: The stage ID if successful, otherwise 0.
        """
        print(f"Saving stage '{self._stage_id}'...")

        stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
        stage = UsdUtils.StageCache.Get().Find(stage_id)
        if not stage:
            print(f"Failed to find stage associated with {self._stage_id}")
            return 0

        clash_data = ClashData(ClashDataSerializerSqlite())
        if not clash_data:
            print("Failed to create connection for clash detection results.")
            return 0

        clash_data.open(self._stage_id, True)
        if not clash_data.is_open() or not clash_data.save():
            print("Failed to save clash detection results.")
            return 0

        # TODO: this should go through Core API to persist changes to the stage
        Usd.Stage.Save(stage)

        clash_data.saved()
        print("... save succeeded")

        return self._stage_id


class CloseStageForClashDetectionCommand(omni.kit.commands.Command):
    """A command to close a stage used for clash detection.

    This command handles the process of closing a stage by erasing it from the stage cache and destroying any associated clash data.

    Args:
        stage_id (int): The identifier of the stage to be closed.
    """

    def __init__(self, stage_id):
        """Initializes the CloseStageForClashDetectionCommand."""
        super().__init__()

        self._stage_id = stage_id

    def do(self) -> bool:
        """Closes the stage and cleans up clash detection data.

        Returns:
            bool: True if the stage was successfully closed, otherwise False.
        """
        print(f"Closing stage '{self._stage_id}'...")

        clash_data = ClashData(ClashDataSerializerSqlite())
        if not clash_data:
            print("Failed to create connection for clash detection results.")
            return False

        clash_data.open(self._stage_id, True)
        if not clash_data.is_open():
            print("Failed to load clash detection results.")
            return False

        # convert back to full ID class form from the long int that is passed to commands
        stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
        UsdUtils.StageCache.Get().Erase(stage_id)

        clash_data.close()
        clash_data.destroy()

        print("... close succeeded")

        return True


class RunClashDetectionCommand(omni.kit.commands.Command):
    """Run the clash detection on a stage.

    Parameters:
        stage_id (int): ID of the stage to be processed.
        object_a_path (str): Absolute stage path or a USD collection to define searchset A.
        object_b_path (str): Absolute stage path or a USD collection to define searchset B.
        tolerance (float): Tolerance distance for overlap queries. Use zero for hard clashes, non-zero for soft (clearance) clashes.
        dynamic (bool): True for dynamic clash detection, False for static.
        start_time (float): Start time in seconds. Only works when dynamic clash detection is enabled.
        end_time (float): End time in seconds. Only works when dynamic clash detection is enabled.
        logging (bool): If True, logs info & performance results to console.
        html_path_name (str): Full path to HTML file if export to HTML is needed. No clash images will be exported.
        json_path_name (str): Full path to JSON file if export to JSON is needed. No clash images will be exported.
        query_name (str): Custom name for the clash detection query which will be generated based on parameters above.
        comment (str): Custom comment for the clash detection query which will be generated based on parameters above.

    Returns:
        bool: True on success, otherwise False
    """

    def __init__(
        self,
        stage_id: int,
        object_a_path: str = "",
        object_b_path: str = "",
        tolerance: float = 0.0,
        dynamic: bool = False,
        start_time: float = 0.0,
        end_time: float = 0.0,
        logging: bool = False,
        html_path_name: str = "",
        json_path_name: str = "",
        query_name: str = "RunClashDetectionCommand Query",
        comment: str = "",
    ):
        """Initializes the RunClashDetectionCommand."""
        super().__init__()

        self._stage_id = stage_id
        self._clash_data = ClashData(ClashDataSerializerSqlite())
        self._html_path_name = html_path_name
        self._json_path_name = json_path_name
        self._query = ClashQuery(
            query_name=query_name,
            object_a_path=object_a_path,
            object_b_path=object_b_path,
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: logging is True,
                SettingId.SETTING_TOLERANCE.name: float(tolerance),
                SettingId.SETTING_DYNAMIC.name: dynamic,
                SettingId.SETTING_DYNAMIC_START_TIME.name: float(start_time),
                SettingId.SETTING_DYNAMIC_END_TIME.name: float(end_time),
                SettingId.SETTING_NEW_TASK_MANAGER.name: True,
                SettingId.SETTING_NB_TASKS.name: 128,
            },
            comment=comment,
        )
        self._new_clash_data_layer_path_name = ""  # path to the new clash data layer if new one was created

    def _export(self, num_overlaps_chk: int) -> bool:
        """Handles export (if needed).
        Returns True on success, False otherwise.
        """
        column_defs = [
            ExportColumnDef(0, "Clash ID"),
            ExportColumnDef(1, "Min Distance", True),
            ExportColumnDef(2, "Tolerance", True),
            ExportColumnDef(3, "Overlap Tris", True),
            ExportColumnDef(4, "Clash Start"),
            ExportColumnDef(5, "Clash End"),
            ExportColumnDef(6, "Records", True),
            ExportColumnDef(7, "Object A"),
            ExportColumnDef(8, "Object B"),
            ExportColumnDef(9, "Comment"),
        ]

        overlaps = self._clash_data.find_all_overlaps_by_query_id(self._query.identifier, False)
        if len(overlaps) != num_overlaps_chk:
            print("Serialization issue detected.")
        rows = [
            [
                o.overlap_id,
                f"{o.min_distance:.3f}",
                f"{o.tolerance:.3f}",
                str(o.overlap_tris),
                f"{o.start_time:.3f}",
                f"{o.end_time:.3f}",
                str(o.num_records),
                o.object_a_path,
                o.object_b_path,
                o.comment,
            ]
            for o in overlaps.values()
        ]

        if self._html_path_name:
            print(f"Exporting to HTML file '{self._html_path_name}'...")
            stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
            stage = UsdUtils.StageCache.Get().Find(stage_id)
            stage_path_name = stage.GetRootLayer().identifier
            html_bytes = export_to_html("Clash Detection Results", stage_path_name, column_defs, rows)
            if not html_bytes or len(html_bytes) == 0:
                print("HTML export failed.")
                return False
            if omni.client.write_file(self._html_path_name, html_bytes) != omni.client.Result.OK:
                print(f"Failed writing HTML file to '{self._html_path_name}'.")
                return False
            html_bytes = None

        if self._json_path_name:
            print(f"Exporting to JSON file '{self._json_path_name}'...")
            json_bytes = export_to_json(column_defs, rows)
            if not json_bytes or len(json_bytes) == 0:
                print("JSON export failed.")
                return False
            if omni.client.write_file(self._json_path_name, json_bytes) != omni.client.Result.OK:
                print(f"Failed writing JSON file to '{self._json_path_name}'.")
                return False
            json_bytes = None

        return True

    def _detect_overlaps(self, stage: Usd.Stage, clash_detect: ClashDetection) -> int:
        """Runs clash detection engine, fetches results and serializes them.
        Returns number of overlaps found.
        """
        print("Running clash detection engine...", end="")
        progress_update = OptimizedProgressUpdate()
        num_steps = clash_detect.create_pipeline()
        for i in range(num_steps):
            step_data = clash_detect.get_pipeline_step_data(i)
            if progress_update.update(step_data.progress):
                print(".", end="")
            clash_detect.run_pipeline_step(i)
        print("Finished.")

        num_overlaps = clash_detect.get_nb_overlaps()
        print(f"Fetching {num_overlaps} overlaps...", end="")
        for p in clash_detect.fetch_and_save_overlaps(stage, self._clash_data, self._query):
            print(".", end="")
        print("Finished.")

        return num_overlaps

    def _clean_overlaps_and_query(self) -> bool:
        print(f"Opening stage '{self._stage_id}'...")
        stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
        stage = UsdUtils.StageCache.Get().Find(stage_id)
        if not stage:
            print(f"Failed to open stage '{self._stage_id}'")
            return False

        self._clash_data.open(self._stage_id, True)

        num_affected_records = self._clash_data.remove_all_overlaps_by_query_id(self._query.identifier, False)
        print(f"{num_affected_records} clash {'record' if num_affected_records == 1 else 'records'} removed.")
        num_affected_records = self._clash_data.remove_query_by_id(self._query.identifier)
        print(f"{num_affected_records} clash {'query' if num_affected_records == 1 else 'queries'} removed.")
        self._query._identifier = 0

        self._clash_data.save()
        Usd.Stage.Save(stage)
        self._clash_data.saved()
        self._clash_data.close()

        return True

    def do(self) -> int:
        """Executes the clash detection command.

        Returns:
            int: ID of the stage processed.
        """
        print("RunClashDetectionCommand.do():")
        stage_id = UsdUtils.StageCache.Get().Id.FromLongInt(self._stage_id)
        stage = UsdUtils.StageCache.Get().Find(stage_id)
        if not stage:
            print(f"Failed to open stage '{self._stage_id}'")
            return 0

        self._clash_data.open(self._stage_id, True)

        print("Creating new query...")
        new_query_id = self._clash_data.insert_query(self._query, True, True)
        if not new_query_id or new_query_id < 1:
            print("Failed to save clash detection query...")
            return 0

        new_clash_data_layer = False
        if self._clash_data._target_layer and self._clash_data._target_layer.anonymous:
            new_clash_data_layer = True

        print("Setting up clash detection engine...")
        clash_detect = ClashDetection()
        if not clash_detect.set_settings(self._query.clash_detect_settings, stage):
            print("Failed to set clash detection settings.")
            return 0
        if not clash_detect.set_scope(
            stage,
            self._query.object_a_path,
            self._query.object_b_path,
            self._query.clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, False)
        ):
            print("Failed to set clash detection scope.")
            return 0

        num_overlaps = self._detect_overlaps(stage, clash_detect)

        if new_clash_data_layer:
            self._new_clash_data_layer_path_name = self._clash_data._target_layer.identifier

        if self._json_path_name or self._html_path_name:
            self._export(num_overlaps)

        return self._stage_id

    def undo(self) -> bool:
        """Undoes the clash detection command.

        Returns:
            bool: True on success, otherwise False.

        """
        print("RunClashDetectionCommand.undo():")
        self._clash_data.close()
        r = True
        if self._json_path_name:
            if omni.client.delete(self._json_path_name) == omni.client.Result.OK:
                print(f"Exported file '{self._json_path_name}' deleted.")
            else:
                r = False
        if self._html_path_name:
            if omni.client.delete(self._html_path_name) == omni.client.Result.OK:
                print(f"Exported file '{self._html_path_name}' deleted.")
            else:
                r = False
        if self._new_clash_data_layer_path_name:
            if omni.client.delete(self._new_clash_data_layer_path_name) == omni.client.Result.OK:
                print(f"Created layer '{self._new_clash_data_layer_path_name}' deleted.")
            else:
                r = False
            self._new_clash_data_layer_path_name = ""
        else:
            if not self._clean_overlaps_and_query():
                r = False
        return r


def register_commands():
    """Register all commands in the current module."""
    global _cmds
    _cmds = omni.kit.commands.register_all_commands_in_module(__name__)


def unregister_commands():
    """Unregister all commands previously registered in the current module."""
    global _cmds
    if _cmds is not None:
        omni.kit.commands.unregister_module_commands(_cmds)
        _cmds = None
