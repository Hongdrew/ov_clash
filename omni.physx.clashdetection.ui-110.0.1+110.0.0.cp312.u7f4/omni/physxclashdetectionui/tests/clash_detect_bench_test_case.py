# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, Optional, Tuple, Callable
import dataclasses
import os
import asyncio
import time
from datetime import datetime
from pathlib import Path
import gc
import shutil
import carb
import carb.settings
import omni.usd
import omni.client
import omni.kit.app
from omni.kit.test import BenchmarkTestCase, get_test_output_path
import omni.kit.ui_test as ui_test
from omni.kit.viewport.utility import get_active_viewport_window
import omni.ui as ui
import omni.timeline
import numpy as np
from pxr import Usd, UsdGeom, UsdUtils, Sdf
from omni.physxclashdetectioncore.clash_info import ClashInfo
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.usd_utils import matrix_to_list
from omni.physxclashdetectioncore.clash_detect_export import export_to_json, export_to_html, ExportColumnDef
from omni.physxclashdetectioncore.utils import (
    OptimizedProgressUpdate, safe_copy_file, get_unique_temp_file_path_name, get_random_word
)
from ..utils import get_datetime_str
from ..settings import ExtensionSettings
from .utils import CodeTimer, get_used_mem


@dataclasses.dataclass
class ClashBakeBenchmarkParameters:
    measure_runtime_start: float | None = None
    measure_runtime_end: float | None = None
    measure_runtime: bool = False


@dataclasses.dataclass
class ClashViewportBenchmarkParameters:
    clashes_range: tuple[int, int] | None = None
    use_selection_groups = True


class ClashDetectionBenchmarkTestCase(BenchmarkTestCase):
    CLASH_WND_NAME = "Clash Detection"
    PROGRESS_WINDOW_NAME = "Clash Detection Progress"
    PROGRESS_UPDATE_RATE = 3.0
    PROGRESS_FORCE_UPDATE_RATE = 3.0

    def __init__(self, tests=()):
        """Initialize the ClashDetectionBenchmarkTestCase test case."""
        super().__init__(tests=tests)
        if hasattr(self, "CUSTOM_TEST_DATA_DIR") and getattr(self, "CUSTOM_TEST_DATA_DIR"):
            self._test_data_dir = getattr(self, "CUSTOM_TEST_DATA_DIR")
        else:
            test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
            self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'
        self._clash_data = ExtensionSettings.clash_data
        self._clash_detect = ClashDetection()
        self._perform_normal_benchmarks = True
        self._perform_ui_benchmarks = True
        self._tmp_paths_to_remove = []
        # overridden settings
        self._clash_detect_wnd_bak = None
        self._show_full_clash_paths_bak = None
        self._show_prompts_bak = None
        self._ui_no_timestamps = None
        self._development_mode_bak = None

    # Before running each test
    async def setUp(self): # type: ignore
        """Set up the test environment before each test."""
        settings = carb.settings.get_settings()

        self._clash_detect_wnd_bak = settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW)
        settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, True)

        self._show_full_clash_paths_bak = ExtensionSettings.show_full_clash_paths
        ExtensionSettings.show_full_clash_paths = False

        self._show_prompts_bak = ExtensionSettings.show_prompts
        ExtensionSettings.show_prompts = False

        self._ui_no_timestamps = ExtensionSettings.ui_no_timestamps
        ExtensionSettings.ui_no_timestamps = True

        self._ui_no_locale_formatting = ExtensionSettings.ui_no_locale_formatting
        ExtensionSettings.ui_no_locale_formatting = True

        self._development_mode_bak = ExtensionSettings.development_mode
        ExtensionSettings.development_mode = False

        await self.wait(5)

        clash_window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(clash_window)
        await clash_window.bring_to_front()
        clash_window.widget.position_x = 0 # type: ignore
        clash_window.widget.position_y = 0 # type: ignore

    async def tearDown(self): # type: ignore
        """Restore the test environment after each test."""
        await self.wait_for_events_processed()

        if self._clash_detect:
            self._clash_detect.reset()

        # remove temporary files and folders
        for path in self._tmp_paths_to_remove:
            if path.endswith('/'):
                print(f"Removing temp folder w/subfolders '{path}'...")
                shutil.rmtree(path)
            else:
                print(f"Removing temp file '{path}'...")
                os.remove(path)
        self._tmp_paths_to_remove = []

        settings = carb.settings.get_settings()

        if self._show_full_clash_paths_bak is not None:
            ExtensionSettings.show_full_clash_paths = self._show_full_clash_paths_bak
        if self._show_prompts_bak is not None:
            ExtensionSettings.show_prompts = self._show_prompts_bak
        if self._ui_no_timestamps is not None:
            ExtensionSettings.ui_no_timestamps = self._ui_no_timestamps
        if self._ui_no_locale_formatting is not None:
            ExtensionSettings.ui_no_locale_formatting = self._ui_no_locale_formatting
        if self._clash_detect_wnd_bak is not None:
            settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, self._clash_detect_wnd_bak)
        if self._development_mode_bak is not None:
            ExtensionSettings.development_mode = self._development_mode_bak

        gc.collect()

    @staticmethod
    async def wait(frames: int = 1):
        """Wait for a specified number of frames by yielding to the async event loop."""
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async() # type: ignore

    @classmethod
    async def wait_for_events_processed(cls):
        """Wait for pending UI/events to be processed."""
        await cls.wait(2)

    async def wait_for_update(self, usd_context=None, wait_frames=10):
        """
        Wait for a specified number of frames or until the USD stage is done loading.

        Args:
            usd_context: The USD context to check loading status on. If None, uses the default context.
            wait_frames: Maximum number of frames to wait.

        """
        # NOTE: get_stage_loading_status doesn't return assets loading info
        if usd_context is None:
            usd_context = omni.usd.get_context(ExtensionSettings.usd_context_name)
        max_loops = 0
        while max_loops < wait_frames:
            _, files_loaded, total_files = usd_context.get_stage_loading_status()
            await omni.kit.app.get_app().next_update_async() # type: ignore
            if files_loaded or total_files:
                continue
            max_loops = max_loops + 1

    async def wait_for_streaming(self, usd_context=None, wait_frames=10):
        """
        Wait for USD stage streaming to finish, or until a timeout is reached.

        Args:
            usd_context: The USD context to check streaming status on. If None, uses the default context.
            wait_frames: Maximum number of frames to wait for streaming to finish.

        Returns:
            bool: True if streaming finished before timeout, False otherwise.
        """
        # NOTE: get_stage_loading_status doesn't return assets loading info
        if usd_context is None:
            usd_context = omni.usd.get_context(ExtensionSettings.usd_context_name)
        max_loops = 0
        while max_loops < wait_frames:
            _, files_loaded, total_files = usd_context.get_stage_loading_status()
            await omni.kit.app.get_app().next_update_async() # type: ignore
            if files_loaded or total_files:
                continue
            max_loops = max_loops + 1

        wait_success = True
        while True:
            isBusy = usd_context.get_stage_streaming_status()
            if isBusy:
                await omni.kit.app.get_app().next_update_async() # type: ignore
                max_loops -= 1
                if max_loops == 0:
                    carb.log_warn(f"Waiting for stage streaming timeout")
                    wait_success = False
                    break
                continue
            break

        usd_context.reset_renderer_accumulation()

        return wait_success

    def _record_curve_anims(
        self,
        stage: Usd.Stage,
        clash_query: Optional[ClashQuery],
        anim_file_name_base: str,
        ct: CodeTimer
    ) -> None:
        """
        Record curve animations for the given USD stage and clash query.

        This method uses the AnimRecorder to convert curve animations to time samples
        for the specified prims in the stage, based on the clash query. It tracks progress
        and memory usage using the provided CodeTimer.

        Args:
            stage (Usd.Stage): The USD stage to record animations from.
            clash_query (Optional[ClashQuery]): Optional clash query containing paths and settings.
            anim_file_name_base (str): Base name for the animation file to save.
            ct (CodeTimer): Timer object used to track memory usage during recording.
        """
        anim_recorder = None
        try:
            from omni.physxclashdetectionanim.scripts.anim_recorder import AnimRecorder
            if not anim_recorder:
                anim_recorder = AnimRecorder()
        except Exception as e:
            anim_recorder = None
            print(
                "For curve anim support please enable physx.clashdetection.anim extension.\n"
                f"Import FAILED with exception: {e}"
            )
            return

        fps = stage.GetTimeCodesPerSecond()
        self.assertTrue(fps is not None and fps > 0, "Invalid stage FPS value")

        def is_xform(prim: Usd.Prim) -> bool:
            return prim.IsA(UsdGeom.Xformable)

        if clash_query and (clash_query.object_a_path or clash_query.object_b_path):
            prim_paths_a, int_paths_a = ClashDetection.get_list_of_prims_int_paths(stage, clash_query.object_a_path, True, is_xform)
            prim_paths_b, int_paths_b = ClashDetection.get_list_of_prims_int_paths(stage, clash_query.object_b_path, True, is_xform)
        else:
            # A special case - obj A and obj B paths empty means processing of the whole stage
            prim_paths_a, int_paths_a = ClashDetection.get_list_of_prims_int_paths(stage, "/", True, is_xform)
            int_paths_b = []

        self.assertTrue(stage.GetStartTimeCode() is not None, "Invalid stage start time")
        self.assertTrue(stage.GetEndTimeCode() is not None, "Invalid stage end time")

        start_time : float = stage.GetStartTimeCode() / fps
        end_time : float = stage.GetEndTimeCode() / fps

        self.assertTrue(start_time >= 0.0, "Invalid stage start time")
        self.assertTrue(end_time >= 0.0, "Invalid stage end time")

        if clash_query:
            setting_start_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_START_TIME.name, 0.0)
            if setting_start_time > start_time:
                start_time = setting_start_time
            setting_end_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_END_TIME.name, 0.0)
            if setting_end_time != 0.0 and setting_end_time < end_time:
                end_time = setting_end_time

        time_length = abs(end_time - start_time)
        if time_length <= 0.0:
            print("No time range to record. Skipping animation recording...")
            return

        print(f"Recording from time {start_time}sec to {end_time}sec...")
        progress_update = OptimizedProgressUpdate(update_rate=self.PROGRESS_UPDATE_RATE, force_update_rate=self.PROGRESS_FORCE_UPDATE_RATE)
        for current_timecode in anim_recorder.run(
            stage,
            int_paths_a + int_paths_b,
            start_time,
            end_time,
            fps
        ):
            ct.check_mem()
            if current_timecode < start_time:  # this can happen as user specified time might not match timeline
                start_time = current_timecode
                time_length = abs(end_time - start_time)
            progress_value = (current_timecode - start_time) / time_length
            if progress_update.update(progress_value):
                print(f"{progress_value*100:.2f}% - timecode {current_timecode}. Used process memory: {get_used_mem() / 1024 ** 2} MB.")
        print("Finished.")
        recording_session_layer_name = anim_recorder.get_recording_session_layer_name()
        print(f"Recorded to '{recording_session_layer_name}'.")
        self.assertTrue(recording_session_layer_name is not None and recording_session_layer_name != "")
        # save anim layer to file
        if anim_file_name_base:
            output_path = Path(get_test_output_path())
            output_file_name = get_random_word(8) + "_" + anim_file_name_base
            output_path_name = str(output_path.joinpath(output_file_name))
            recording_layer = Sdf.Layer.Find(recording_session_layer_name)
            self.assertIsNotNone(recording_layer)
            ret = recording_layer.Export(output_path_name)
            self.assertTrue(ret)
            print(f"Saved anim layer to '{output_path_name}'.")

    async def _run_clash_detection_async_ui(self, ct: CodeTimer) -> None:
        """
        Run clash detection asynchronously using the UI.

        This method simulates clicking the "Run Clash Detection" button in the UI,
        waits for the process to complete, and tracks progress and memory usage.

        Args:
            ct (CodeTimer): Timer object used to track memory usage during execution.
        """
        run_clash_detection_button = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].text=='Run Clash Detection'")
        self.assertIsNotNone(run_clash_detection_button)
        self.assertTrue(run_clash_detection_button.widget.enabled)
        progress_update = OptimizedProgressUpdate(update_rate=self.PROGRESS_UPDATE_RATE, force_update_rate=self.PROGRESS_FORCE_UPDATE_RATE)
        use_async_clash_pipeline_bak = ExtensionSettings.use_async_clash_pipeline
        ExtensionSettings.use_async_clash_pipeline = True
        print("Running clash detection engine using UI...")
        await run_clash_detection_button.click()  # run clash detection with the selected query
        await self.wait(10)
        clash_detection_progress_label = ui_test.find(f"{self.PROGRESS_WINDOW_NAME}//Frame/**/Label[0]")
        clash_detection_progress_bar = ui_test.find(f"{self.PROGRESS_WINDOW_NAME}//Frame/**/ProgressBar[0]")
        self.assertIsNotNone(clash_detection_progress_label)
        self.assertIsNotNone(clash_detection_progress_bar)

        viewport_window = get_active_viewport_window()
        self.assertIsNotNone(viewport_window)
        viewport_api = viewport_window.viewport_api # type: ignore
        self.assertIsNotNone(viewport_api)
        while not run_clash_detection_button.widget.enabled:
            await self.wait_for_events_processed()
            if progress_update.update(0):
                try:
                    progress_text = clash_detection_progress_label.widget.text  # type: ignore
                    progress_value = clash_detection_progress_bar.widget.model.as_string  # type: ignore
                except:
                    progress_text = "?"
                    progress_value = "?"
                try:
                    fps = f"{viewport_api.fps:.2f}"
                except:
                    fps = "?"
                print(f"[UI] {progress_value} - {progress_text}. {fps} FPS. Used process memory: {get_used_mem() / 1024 ** 2} MB.")
            ct.check_mem()
        print("Finished.")
        ExtensionSettings.use_async_clash_pipeline = use_async_clash_pipeline_bak

    def _run_clash_detection(self, ct: CodeTimer) -> None:
        """
        Run the clash detection pipeline and update progress.

        This method resets the clash detector, creates the pipeline, and executes each pipeline step,
        tracking progress and memory usage.

        Args:
            ct (CodeTimer): Timer object used to track memory usage during execution.
        """
        print("Running clash detection engine...")
        self._clash_detect.reset()
        num_steps = self._clash_detect.create_pipeline()
        progress_update = OptimizedProgressUpdate(update_rate=self.PROGRESS_UPDATE_RATE, force_update_rate=self.PROGRESS_FORCE_UPDATE_RATE)
        for i in range(num_steps):
            step_data = self._clash_detect.get_pipeline_step_data(i)
            if progress_update.update(step_data.progress) or i == num_steps - 1:
                print(f"{step_data.progress*100:.2f}% - [{i}/{num_steps - 1} steps] - {step_data.name}. Used process memory: {get_used_mem() / 1024 ** 2} MB.")
            self._clash_detect.run_pipeline_step(i)
            ct.check_mem()
        print("Finished.")

    def _get_num_results(self, clash_query: ClashQuery) -> int:
        """
        Get the number of results found by the clash detection engine.
        """
        setting_find_duplicates = clash_query.clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, False)
        num_dups = self._clash_detect.get_nb_duplicates()
        num_overlaps = self._clash_detect.get_nb_overlaps()
        return num_dups if setting_find_duplicates else num_overlaps

    def _fetch_results(
        self, stage: Usd.Stage,
        clash_query: ClashQuery,
        save_results: bool,
        fetch_results_cb_fn: Optional[Callable[[int, int, int], bool]],
        ct: CodeTimer,
    ) -> Tuple[List[ClashInfo], int, int, int, int]:
        """
        Retrieve and process clash detection results (overlaps or duplicates), optionally collecting new results.

        This method iterates over all detected clashes or duplicate mesh records, as specified by the clash query
        settings, and processes each one. Optionally, it collects new (previously unseen) results in a returned list.
        Progress and memory usage statistics are logged periodically.

        Args:
            stage (Usd.Stage): The USD stage containing the scene data.
            clash_query (ClashQuery): Settings and identifiers for the current clash detection query.
            save_results (bool): If True, only new (identifier == -1) records are collected and returned.
            fetch_results_cb_fn (Optional[Callable[[int, int, int], bool]]):
                Callback function to decide if the current clash info should be fetched.
                The callback receives three arguments:
                  - idx (int): The index of the current clash info in the results iteration.
                  - total_clashes (int): The total number of clashes found so far.
                  - total_frames (int): The total number of frames processed so far.
                The function should return True if the current result should be fetched, or False to skip it.
            ct (CodeTimer): Timer/context object for monitoring memory usage during the operation.

        Returns:
            Tuple[List[ClashInfo], int, int, int, int]:
                - List[ClashInfo]: New clash or duplicate records (empty if save_results is False).
                - int: Total number of clashes/duplicates processed.
                - int: Total frame count summed from all results.
                - int: Total number of clashes/duplicates skipped.
                - int: Total number of overlapping triangles processed.
        """
        existing_clash_info_items = dict()
        new_clash_info_items = []
        total_clashes = 0
        total_clashes_skipped = 0
        total_frames = 0
        total_overlapping_tris = 0
        progress_update = OptimizedProgressUpdate(update_rate=self.PROGRESS_UPDATE_RATE, force_update_rate=self.PROGRESS_FORCE_UPDATE_RATE)
        setting_find_duplicates = clash_query.clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, False)
        start_time = time.time()
        if setting_find_duplicates:
            count = self._clash_detect.get_nb_duplicates()
            print(f"Fetching {count} duplicates...")
            for idx in range(count):
                if fetch_results_cb_fn and not fetch_results_cb_fn(idx, total_clashes, total_frames):
                    total_clashes_skipped += 1
                    continue  # skip current clash info
                p = float(idx + 1) / float(count)
                if progress_update.update(p) or idx == count - 1:
                    elapsed_time = time.time() - start_time
                    eta = (elapsed_time / p) - elapsed_time if p > 0 else 0
                    eta_str = f"ETA: {int(eta//3600)}h {int((eta%3600)//60)}m" if eta > 60 else "ETA: less than a minute"
                    print(f"{p*100:.2f}% [{idx + 1}/{count} records]. {eta_str}. Used process memory: {get_used_mem() / 1024 ** 2} MB.")
                clash_info = self._clash_detect.process_duplicate(
                    stage,
                    idx,
                    existing_clash_info_items,
                    clash_query.identifier,
                )
                if save_results and clash_info and clash_info.identifier == -1:  # identifier -1 means new clash, otherwise existing
                    new_clash_info_items.append(clash_info)
                total_frames += clash_info.num_records
                assert clash_info.clash_frame_info_items is not None
                total_overlapping_tris += sum(cfi.overlap_tris for cfi in clash_info.clash_frame_info_items)
                total_clashes += 1
                ct.check_mem()
        else:
            setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0)
            setting_depth_epsilon = clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0)
            count = self._clash_detect.get_nb_overlaps()
            print(f"Fetching {count} clashes...")
            for idx in range(count):
                if fetch_results_cb_fn and not fetch_results_cb_fn(idx, total_clashes, total_frames):
                    total_clashes_skipped += 1
                    continue  # skip current clash info
                p = float(idx + 1) / float(count)
                if progress_update.update(p) or idx == count - 1:
                    elapsed_time = time.time() - start_time
                    eta = (elapsed_time / p) - elapsed_time if p > 0 else 0
                    eta_str = f"ETA: {int(eta//3600)}h {int((eta%3600)//60)}m" if eta > 60 else "ETA: less than a minute"
                    print(f"{p*100:.2f}% [{idx + 1}/{count} records]. {eta_str}. Used process memory: {get_used_mem() / 1024 ** 2} MB.")
                clash_info = self._clash_detect.process_overlap(
                    stage,
                    idx,
                    existing_clash_info_items,
                    clash_query.identifier,
                    setting_tolerance,
                    setting_depth_epsilon
                )
                if save_results and clash_info and clash_info.identifier == -1:  # identifier -1 means new clash, otherwise existing
                    new_clash_info_items.append(clash_info)
                total_frames += clash_info.num_records
                assert clash_info.clash_frame_info_items is not None
                total_overlapping_tris += sum(cfi.overlap_tris for cfi in clash_info.clash_frame_info_items)
                total_clashes += 1
                ct.check_mem()
        print("Finished.")
        return new_clash_info_items, total_clashes, total_frames, total_clashes_skipped, total_overlapping_tris

    async def _export_results(self, overlaps: List[ClashInfo], file_name_base: str, clash_query: ClashQuery) -> None:
        def dump_query_info(clash_query: ClashQuery) -> str:
            query_info = f"Query Name: {clash_query.query_name}"
            query_info += f" ({clash_query.comment}). " if clash_query.comment else ". "
            query_info += f"Object A: {clash_query.object_a_path}. "
            query_info += f"Object B: {clash_query.object_b_path}. "
            query_info += f"Clash Detection Engine Settings: "
            query_info += ", ".join(
                f"{setting_name}: {clash_query.clash_detect_settings[setting_name]}"
                for setting_name in clash_query.clash_detect_settings.keys()
            ) + "."
            return query_info.strip()

        def write_to_csv(path_name: str, column_defs: List["ExportColumnDef"], rows: List[List[str]]) -> bool:
            try:
                with open(path_name, "w") as f:
                    header = "\t".join([col.name for col in column_defs]) + "\n"
                    f.write(header)
                    for row in rows:
                        row_str = "\t".join(cell for cell in row) + "\n"
                        f.write(row_str)
                return True
            except Exception as e:
                print(f"Failed to write to CSV: {e}")
                return False

        output_path = Path(get_test_output_path())
        file_name_prefix = get_random_word(8) + "_" + file_name_base
        file_name_prefix = str(output_path.joinpath(file_name_prefix))

        column_defs = [
            ExportColumnDef(0, "Clash ID"),
            ExportColumnDef(1, "Min Distance", True),
            ExportColumnDef(2, "Tolerance", True),
            ExportColumnDef(3, "Max Depth", True),
            ExportColumnDef(4, "Depth Epsilon", True),
            ExportColumnDef(5, "PX +X", True),
            ExportColumnDef(6, "PX -X", True),
            ExportColumnDef(7, "PY +Y", True),
            ExportColumnDef(8, "PY -Y", True),
            ExportColumnDef(9, "PZ +Z", True),
            ExportColumnDef(10, "PZ -Z", True),
            ExportColumnDef(11, "Triangles", True),
            ExportColumnDef(12, "Clash Start"),
            ExportColumnDef(13, "Clash End"),
            ExportColumnDef(14, "Records", True),
            ExportColumnDef(15, "Object A"),
            ExportColumnDef(16, "Object B"),
            ExportColumnDef(17, "Comment"),
        ]

        print("Generating export rows...")
        rows = []
        with CodeTimer(f"Export Rows Generation"):
            for clash_info in overlaps:
                row = [
                    clash_info.overlap_id,
                    f"{clash_info.min_distance:.3f}",
                    f"{clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0):.3f}",
                    f"{clash_info.max_local_depth:.3f}",
                    f"{clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0):.3f}",
                    f"{clash_info.penetration_depth_px:.3f}",
                    f"{clash_info.penetration_depth_nx:.3f}",
                    f"{clash_info.penetration_depth_py:.3f}",
                    f"{clash_info.penetration_depth_ny:.3f}",
                    f"{clash_info.penetration_depth_pz:.3f}",
                    f"{clash_info.penetration_depth_nz:.3f}",
                    str(clash_info.overlap_tris),
                    f"{clash_info.start_time:.3f}",
                    f"{clash_info.end_time:.3f}",
                    str(clash_info.num_records),
                    clash_info.object_a_path,
                    clash_info.object_b_path,
                    clash_info.comment,
                ]
                rows.append(row)
                assert clash_info.clash_frame_info_items is not None
                for idx, cfi in enumerate(clash_info.clash_frame_info_items):
                    assert cfi is not None
                    row = [
                        f"{clash_info.overlap_id}.{idx + 1}",
                        f"{cfi.min_distance:.3f}",
                        f"{clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0):.3f}",
                        f"{cfi.max_local_depth:.3f}",
                        f"{clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0):.3f}",
                        f"{cfi.penetration_depth_px:.3f}",
                        f"{cfi.penetration_depth_nx:.3f}",
                        f"{cfi.penetration_depth_py:.3f}",
                        f"{cfi.penetration_depth_ny:.3f}",
                        f"{cfi.penetration_depth_pz:.3f}",
                        f"{cfi.penetration_depth_nz:.3f}",
                        f"{cfi.overlap_tris}",
                        f"{cfi.timecode:.3f}",
                        f"{cfi.timecode:.3f}",
                        "1",
                        str(matrix_to_list(cfi.object_0_matrix)),
                        str(matrix_to_list(cfi.object_1_matrix)),
                        f"Clashing frame #{idx + 1}, usd_faces_0 len: {len(cfi.usd_faces_0)}, #usd_faces_1 len: {len(cfi.usd_faces_1)}, collision_outline len: {len(cfi.collision_outline)}",
                    ]
                    rows.append(row)
        print(f"Done. {len(rows)} rows generated.")

        additional_info = {
            "Author": "Performance Benchmark",
            "Date": get_datetime_str(datetime.now()),
            "Engine": "NVIDIA Omniverse Clash Detection",
            "Company": "NVIDIA",
            "Company Website": "https://www.nvidia.com",
            "Additional Info": dump_query_info(clash_query),
        }

        path_name = file_name_prefix + ".csv"
        print(f"Exporting to CSV file '{path_name}'...")
        with CodeTimer(f"Export to CSV"):
            write_to_csv(path_name, column_defs, rows)
        print("Done!")

        path_name = file_name_prefix + ".json"
        print(f"Exporting to JSON file '{path_name}'...")
        with CodeTimer(f"Export to JSON"):
            json_bytes = export_to_json(column_defs, rows, additional_info)
        self.assertTrue(len(json_bytes) > 0)
        self.assertTrue(omni.client.write_file(path_name, json_bytes) == omni.client.Result.OK)
        print("Done!")

        path_name = file_name_prefix + ".html"
        print(f"Exporting to HTML file '{path_name}'...")
        with CodeTimer(f"Export to HTML"):
            html_bytes = export_to_html("Clash Detection Results", file_name_base, column_defs, rows, additional_info)
        self.assertTrue(len(html_bytes) > 0)
        self.assertTrue(omni.client.write_file(path_name, html_bytes) == omni.client.Result.OK)
        print("Done!")

    async def _run_perf_benchmark(
        self,
        stage_name: str,
        expected_num_results: int,
        expected_total_frames: int = -1,
        expected_total_overlapping_tris: int = -1,
        object_a_path: str = "",
        object_b_path: str = "",
        dynamic: bool = True,
        start_time: float = 0.0,
        end_time: float = 0.0,
        tolerance: float = 0.0,
        compute_max_local_depth: bool = False,
        max_local_depth_epsilon: float = -1.0,
        max_local_depth_mode: int = 1,
        convert_curve_anim: bool = True,
        convert_curve_anim_whole_timeline: bool = True,
        purge_permanent_static_overlaps: bool = True,
        additional_query_settings: dict = {},
        fetch_results: bool = True,
        fetch_results_cb_fn: Optional[Callable[[int, int, int], bool]] = None,
        serialize_results: bool = True,
        deserialize_results: bool = True,
        export_results: bool = True,
        perform_bake: ClashBakeBenchmarkParameters | None = None,
        perform_viewport: ClashViewportBenchmarkParameters | None = None,
    ) -> None:
        """
        Executes a full performance benchmark for the clash detection pipeline, covering file I/O, query
        configuration, clash computation, result processing, and cleanup stages. Performance metrics such as
        timing and memory usage are recorded for each step using CodeTimer.

        This method supports extensive customization via parameters to facilitate a range of benchmarking scenarios,
        including static and dynamic detection, curve animation handling, result serialization, and more.

        Args:
            stage_name (str): Relative path to the USD stage file (can include subdirectory) to use for the test.
            expected_num_results (int): Number of expected result entries for assertion and validation.
            expected_total_frames (int, optional): Total number of expected frames in all processed records. Defaults to -1 (no expected value).
            expected_total_overlapping_tris (int, optional): Total number of expected overlapping triangles in all processed records. Defaults to -1 (no expected value).
            object_a_path (str, optional): USD path to the first object for clash detection (empty = all). Defaults to "".
            object_b_path (str, optional): USD path to the second object for clash detection (empty = all). Defaults to "".
            dynamic (bool, optional): If True, performs dynamic (animated) clash checks; otherwise static. Defaults to True.
            start_time (float, optional): Timecode to begin clash detection (for animations). Defaults to 0.0.
            end_time (float, optional): Timecode to end clash detection. Defaults to 0.0.
            tolerance (float, optional): Tolerance value for minimum distance to be considered a clash. Defaults to 0.0.
            compute_max_local_depth (bool, optional): If True, computes max local depth for the query. Defaults to False.
            max_local_depth_epsilon (float, optional): Threshold for comparing max local depths. Defaults to -1.0.
            max_local_depth_mode (int, optional): Mode for max local depth computation. 0 = Legacy (fastest), 1 = Medium (medium accuracy), 2 = High (highest accuracy). Defaults to 1.
            convert_curve_anim (bool, optional): If True, converts all curve-animated properties to time samples (non-UI only). Defaults to True.
            convert_curve_anim_whole_timeline (bool, optional): If True, converts for the whole animation timeline (non-UI). Defaults to True.
            purge_permanent_static_overlaps (bool, optional): If True, purges non-dynamic clashes from database. Defaults to True.
            additional_query_settings (dict, optional): Dictionary of extra settings to merge into the query. Defaults to {}.
            fetch_results (bool, optional): If True, retrieves results after detection (non-UI only). Defaults to True.
            fetch_results_cb_fn (Optional[Callable[[int, int, int], bool]], optional):
                Callback function to decide if the current clash info should be fetched.
                The callback receives three arguments:
                  - idx (int): The index of the current clash info in the results iteration.
                  - total_clashes (int): The total number of clashes found so far.
                  - total_frames (int): The total number of frames processed so far.
                The function should return True if the current result should be fetched, or False to skip it.
                Defaults to None.
            serialize_results (bool, optional): If True, serializes results to storage (non-UI only). Defaults to True.
            deserialize_results (bool, optional): If True, deserializes prior results (non-UI only). Defaults to True.
            export_results (bool, optional): If True, exports results to a file (non-UI only). Defaults to True.
            perform_bake (ClashBakeBenchmarkParameters, optional): Parameters for the bake benchmark. Defaults to None (that skips the bake benchmark entirely).
            perform_viewport (ClashViewportBenchmarkParameters, optional): Parameters for the viewport benchmark. Defaults to None (that skips the viewport benchmark entirely).
        """
        self.assertIsNotNone(self._clash_data, "Clash data is not initialized")
        if not self._clash_data:
            return

        print(f"*** Performance Benchmark Initiated ***")
        CodeTimer.clear_records()

        print("Resetting clash detection engine...")
        self._clash_detect.reset()

        usd_context = omni.usd.get_context(ExtensionSettings.usd_context_name)
        print("Creating an empty stage...")
        (result, err) = await usd_context.new_stage_async() # type: ignore

        stage_name = stage_name.replace("\\", "/")

        def extract_first_path_component(path: str) -> str:
            return path.split("/", 1)[0] if "/" in path else ""

        stage_subdir_name = extract_first_path_component(stage_name)
        stage_file_name = os.path.basename(stage_name)

        if stage_subdir_name:
            stage_dir_name_src = self._test_data_dir + stage_subdir_name
            stage_dir_name = get_unique_temp_file_path_name("_" + stage_subdir_name)
            stage_path_name = os.path.join(stage_dir_name, stage_file_name).replace("\\", "/")
            print(f"Copying folder w/subfolders '{stage_dir_name_src}' to '{stage_dir_name}'...")
            shutil.copytree(stage_dir_name_src, stage_dir_name, dirs_exist_ok=True)
            self._tmp_paths_to_remove.append(stage_dir_name + '/')
        else:
            stage_path_name_src = self._test_data_dir + stage_name
            stage_path_name = get_unique_temp_file_path_name("_" + stage_name)
            print(f"Copying '{stage_path_name_src}' to '{stage_path_name}'...")
            self.assertTrue(safe_copy_file(stage_path_name_src, stage_path_name))
            self._tmp_paths_to_remove.append(stage_path_name)

        print(f"Opening stage '{stage_path_name}'...")
        with CodeTimer(f"Stage Open ({stage_name.replace("/", ": ")})"):
            (result, err) = await usd_context.open_stage_async(stage_path_name) # type: ignore
            print("Waiting for stage to finish streaming...")
            streaming_result = await self.wait_for_streaming(usd_context, 1000)
            print(f"Wait for the stage streaming finished with result {result}.")

        self.assertTrue(result)
        stage = usd_context.get_stage() # type: ignore
        self.assertIsNotNone(stage)
        await self.wait_for_events_processed()

        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), True)

        print("Setting up new clash detection query...")
        my_query = ClashQuery(
            query_name="Benchmark Query",
            object_a_path=object_a_path,
            object_b_path=object_b_path,
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_STATIC_TIME.name: 0.0,
                SettingId.SETTING_DUP_MESHES.name: False,
                SettingId.SETTING_DYNAMIC.name: dynamic,
                SettingId.SETTING_DYNAMIC_START_TIME.name: start_time,
                SettingId.SETTING_DYNAMIC_END_TIME.name: end_time,
                SettingId.SETTING_TOLERANCE.name: tolerance,
                SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS.name: purge_permanent_static_overlaps,
                SettingId.SETTING_PURGE_PERMANENT_OVERLAPS.name: False,
                SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS.name: False,
                SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name: compute_max_local_depth,
                SettingId.SETTING_MAX_LOCAL_DEPTH_MODE.name: max_local_depth_mode,
                SettingId.SETTING_DEPTH_EPSILON.name: max_local_depth_epsilon,
                SettingId.SETTING_CONTACT_CUTOFF.name: -1.0,
                SettingId.SETTING_USE_USDRT.name: False,
                SettingId.SETTING_IGNORE_INVISIBLE_PRIMS.name: True,
                SettingId.SETTING_NEW_TASK_MANAGER.name: True,
                SettingId.SETTING_NB_TASKS.name: 128,
                SettingId.SETTING_SINGLE_THREADED.name: False,
                SettingId.SETTING_POSE_EPSILON.name: 1.0e-06,
                SettingId.SETTING_AREA_EPSILON.name: 1.0e-06,
                SettingId.SETTING_BOUNDS_EPSILON.name: 0.01,
                SettingId.SETTING_TIGHT_BOUNDS.name: True,
                SettingId.SETTING_COPLANAR.name: True,
                SettingId.SETTING_ANY_HIT.name: False,
                SettingId.SETTING_QUANTIZED.name: False,
                SettingId.SETTING_TRIS_PER_LEAF.name: 15,
                SettingId.SETTING_TRIANGLE_LIMIT.name: 0,
                SettingId.SETTING_DISCARD_TOUCHING_CONTACTS.name: False,
                SettingId.SETTING_OVERLAP_CODE.name: 3,
                SettingId.SETTING_FILTER_TEST.name: False,
            },
        )
        my_query.clash_detect_settings.update(additional_query_settings)
        print(f"Query settings:")
        print(f" * Object A path: {my_query.object_a_path}")
        print(f" * Object B path: {my_query.object_b_path}")
        print(f" * Clash Detection Engine Settings:")
        for setting_name in my_query.clash_detect_settings.keys():
            print(f"    * {setting_name}: {my_query.clash_detect_settings[setting_name]}")

        query_id = -1
        with CodeTimer(f"Insert New Query"):
            query_id = self._clash_data.insert_query(my_query, True, True)
        self.assertTrue(query_id and query_id == 1)

        if self._perform_normal_benchmarks:
            print("Performing normal benchmark...")
            if convert_curve_anim:
                print("Converting curve anims to time samples...")
                # convert curve anims to time samples for the whole stage from the beginning to the end
                with CodeTimer(f"Curve Anim Conversion") as ct:
                    self._record_curve_anims(
                        stage,
                        my_query if not convert_curve_anim_whole_timeline else None,
                        "anim_" + stage_name.replace("/", "-"),
                        ct
                    )

            print("Setting up clash detection engine...")
            with CodeTimer(f"Set Scope"):
                self.assertTrue(self._clash_detect.set_scope(stage, my_query.object_a_path, my_query.object_b_path))
            with CodeTimer(f"Set Settings"):
                self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

            with CodeTimer(f"Clash Detection Engine") as ct:
                self._run_clash_detection(ct)

            print(f"Found {self._get_num_results(my_query)} records, expected {expected_num_results}.")
            self.assertEqual(self._get_num_results(my_query), expected_num_results)

            if fetch_results:
                overlaps = None
                with CodeTimer(f"Clash Results Fetch") as ct:
                    (
                        overlaps, total_clashes, total_frames, total_clashes_skipped, total_overlapping_tris
                    ) = self._fetch_results(stage, my_query, serialize_results, fetch_results_cb_fn, ct)
                if serialize_results:
                    print(f"Fetched {len(overlaps)} overlaps, skipped {total_clashes_skipped}, expected total {expected_num_results}.")
                else:
                    print(f"Fetched but not stored {total_clashes} overlaps, skipped {total_clashes_skipped}, expected total {expected_num_results}.")

                print(f"Total sum of all frames in all processed records: {total_frames}, expected {expected_total_frames}.")
                print(f"Total sum of all overlapping triangles in all processed records: {total_overlapping_tris}, expected {expected_total_overlapping_tris}.")
                if expected_total_frames != -1:
                    self.assertEqual(total_frames, expected_total_frames)
                if expected_total_overlapping_tris != -1:
                    self.assertEqual(total_overlapping_tris, expected_total_overlapping_tris)

                # sanity check if all hashes (overlap_ids) are unique
                all_hashes = [ci.overlap_id for ci in overlaps]
                self.assertEqual(len(all_hashes), len(set(all_hashes)), "All hashes (overlap_ids) should be unique.")
                print(f"All hashes (overlap_ids) are unique.")

                clash_info_num_records_dict = dict()
                if serialize_results:
                    print("Serializing clash detection results...")

                    with CodeTimer(f"Clash Results Serialization") as ct:
                        for clash_info in overlaps:
                            new_id = self._clash_data.insert_overlap(clash_info, True, True, False)
                            self.assertTrue(new_id is not None and new_id > 0)
                            clash_info_num_records_dict[clash_info.identifier] = clash_info.num_records
                            ct.check_mem()
                        self._clash_data.commit()
                else:
                    print("Skipped serialization of clash detection results.")

                if export_results:
                    print("Sorting clash detection results by overlap id...")
                    with CodeTimer("Clash Results Sort") as ct:
                        overlaps.sort(key=lambda x: x.overlap_id)
                        ct.check_mem()
                    await self._export_results(overlaps, stage_name.replace("/", "-"), my_query)
                else:
                    print("Skipped export of clash detection results.")

                del overlaps

                clash_db_size_mb = os.path.getsize(self._clash_data.serializer_path) / 1024 ** 2
                print(f"Clash database size: {clash_db_size_mb} MB at \"{self._clash_data.serializer_path}\".")

                if deserialize_results:
                    print("Deserializing clash detection results...")
                    with CodeTimer(f"Clash Results Deserialization") as ct:
                        for clash_info_id in clash_info_num_records_dict.keys():
                            clash_info_dict_loaded = self._clash_data.find_all_overlaps_by_overlap_id(
                                [clash_info_id], True
                            )
                            self.assertEqual(len(clash_info_dict_loaded.keys()), 1)
                            self.assertEqual(
                                clash_info_dict_loaded.popitem()[1].num_records,
                                clash_info_num_records_dict[clash_info_id]
                            )
                            ct.check_mem()
                            del clash_info_dict_loaded
                    del clash_info_num_records_dict
                else:
                    print("Skipped deserialization of clash detection results.")

                # test query selection in the UI
                print(f"Selecting query using dropdown in the UI...")
                settings = carb.settings.get_settings()
                clash_query_combobox = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'")
                self.assertIsNotNone(clash_query_combobox)
                self.assertTrue(clash_query_combobox.widget.enabled)
                clash_query_combobox.widget.model.select_item_index(-1) # type: ignore
                settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
                await self.wait_for_events_processed()
                with CodeTimer(f"Select Query"):
                    clash_query_combobox.widget.model.select_item_index(0) # type: ignore

                # create summary timer entry summing together:
                labels = [
                    f"Curve Anim Conversion",
                    f"Set Scope",
                    f"Set Settings",
                    f"Clash Detection Engine",
                    f"Clash Results Fetch",
                    f"Clash Results Serialization",
                    f"Select Query",
                ]
                total_time = 0.0
                peak_ram = 0
                for label in labels:
                    rec = CodeTimer.find_record(label)
                    if rec:
                        time, ram, units = rec
                        total_time += time
                        if ram > peak_ram:
                            peak_ram = ram
                CodeTimer.add_record(f"Clash Detection Engine Sum (non-UI)", total_time, peak_ram)

                if serialize_results:
                    print("Deleting clash detection results from the clash database...")
                    with CodeTimer(f"Delete Clash Detection Results"):
                        num_deleted_records = self._clash_data.remove_all_overlaps_by_query_id(query_id, True)
                        print(f"Deleted {num_deleted_records} records, expected {total_clashes}.")
                        self.assertEqual(num_deleted_records, total_clashes)
                else:
                    print("Skipped deletion of clash detection results because serialization is disabled.")
            else:
                print("Skipped fetching clash detection results, therefore serialization, deserialization and deletion also skipped.")
        else:
            print("Normal benchmark skipped.")

        if self._perform_ui_benchmarks:
            print("Performing UI benchmark...")
            print(f"Selecting query using dropdown in the UI...")
            settings = carb.settings.get_settings()
            settings.set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
            await self.wait_for_events_processed()
            clash_query_combobox = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'")
            self.assertIsNotNone(clash_query_combobox)
            self.assertTrue(clash_query_combobox.widget.enabled)
            self.assertEqual(len(clash_query_combobox.widget.model.items), 1) # type: ignore
            clash_query_combobox.widget.model.select_item_index(0) # type: ignore
            await self.wait_for_events_processed()

            with CodeTimer(f"Clash Detection Engine (Async UI)") as ct:
                await self._run_clash_detection_async_ui(ct)
            # check the number of clashes detected
            num_of_records_saved = self._clash_data.get_overlaps_count_by_query_id(query_id)
            print(f"Saved {num_of_records_saved} records, expected {expected_num_results}.")
            self.assertEqual(num_of_records_saved, expected_num_results)
            if perform_viewport:
                await self._run_viewport_benchmark(perform_viewport, expected_num_results)
            if perform_bake:
                await self._run_bake_benchmark(perform_bake, expected_num_results)

        else:
            print("UI benchmark skipped.")

        print(f"Saving stage '{stage_path_name}'...")
        with CodeTimer(f"Stage Save"):
            await usd_context.save_stage_async() # type: ignore

        print("Resetting clash detection engine, free up used memory...")
        self._clash_detect.reset()  # reset the clash detection engine, free up used memory

        print(f"Closing stage '{stage_path_name}'...")
        with CodeTimer(f"Stage Close"):
            await usd_context.close_stage_async() # type: ignore
            await self.wait_for_events_processed()

        print(f"Performance Benchmark Summary")
        CodeTimer.dump_records()
        CodeTimer.process_records_cb(lambda label, val, unit: self.set_metric_sample(name=label, value=val, unit=unit))
        CodeTimer.clear_records()

    async def _run_bake_benchmark(self, bake_parameters: ClashBakeBenchmarkParameters, expected_num_results: int):
        fps_units = ("fps", "fps", "FPS")
        if bake_parameters.measure_runtime:
            print(f"Measuring timeline median FPS WITHOUT bake layer enabled...")
            median_fps_without_bake = await self._measure_timeline_median_fps(bake_parameters)
            CodeTimer.add_record("Clash Bake - Median FPS Without Bake Layer", median_fps_without_bake, 0, fps_units)
            await self.wait(50)
            gc.collect()
            await self.wait(100)
            gc.collect()
        print("Performing bake benchmark...")
        old_debug_logging = ExtensionSettings.debug_logging
        try:
            ExtensionSettings.debug_logging = True
            await self._run_bake_generation_benchmark(expected_num_results)
        finally:
            ExtensionSettings.debug_logging = old_debug_logging
        if bake_parameters.measure_runtime:
            print(f"Measuring timeline median FPS WITH bake layer enabled...")
            median_fps_with_bake = await self._measure_timeline_median_fps(bake_parameters)
            CodeTimer.add_record("Clash Bake - Median FPS With Bake Layer", median_fps_with_bake, 0, fps_units)
        
        # Disable clash bake layer to ensure clean state for subsequent tests
        await self._toggle_clash_bake_layer_ui(enable=False)

    def _get_results_tree(self):
        return ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/TreeView[*].name=='clash_results'")

    def _get_query_combobox(self):
        return ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/ComboBox[*].name=='clash_query_combo'")

    def _ensure_query_selected(self):
        clash_query_combobox = self._get_query_combobox()
        if clash_query_combobox.widget.model.selected_query_id() == -1: # type: ignore
            print(f"Selecting the first query in the UI...")
            time_selection_start = time.time()
            clash_query_combobox.widget.model.select_item_index(0)  # type: ignore
            time_selection_end = time.time()
            print(f"Finished selecting the first query in the UI in {time_selection_end - time_selection_start:.2f} seconds...")
        window = ui_test.find(self.CLASH_WND_NAME)
        if not window:
            self.assertIsNotNone(window)

    async def _toggle_clash_bake_layer_ui(self, enable: bool):
        """Toggle the clash bake layer through UI interaction.
        
        Args:
            enable: True to enable the bake layer, False to disable it
        """
        # Click the button to open it
        btn_bake = ui_test.find(f"{self.CLASH_WND_NAME}//Frame/**/Button[*].name=='bake'")
        self.assertIsNotNone(btn_bake, "Could not find bake button")
        await btn_bake.click()
        await self.wait(5)
        assert ExtensionSettings.clash_bake_view is not None
        
        # Find the settings window again
        bake_settings_window = ui_test.find("Bake Layer Settings###ClashBake")
  
        self.assertIsNotNone(bake_settings_window, "Could not find bake settings window after button click and direct show")
        self.assertTrue(bake_settings_window.widget.visible, "Bake settings window exists but is not visible")

        # Find the "Enable Clash Bake Layer" checkbox
        enable_checkbox = ui_test.find("Bake Layer Settings###ClashBake//Frame/**/CheckBox[*].identifier=='enable_clash_bake_layer_checkbox'")
        self.assertIsNotNone(enable_checkbox, "Could not find 'Enable Clash Bake Layer' checkbox")
        
        # Click the checkbox if its state doesn't match the desired state
        current_state = enable_checkbox.widget.model.as_bool # type: ignore
        if current_state != enable:
            await enable_checkbox.click()
            await self.wait(10)
        
        # Close the settings window
        bake_settings_window.widget.visible = False
        await self.wait(5)

    async def _run_bake_generation_benchmark(self, expected_num_results: int):
        self._ensure_query_selected()  # select the first query
        
        # Enable clash bake layer through UI
        await self._toggle_clash_bake_layer_ui(enable=True)
        
        clash_results_tree = self._get_results_tree()
        clash_results_tree.widget.selection = clash_results_tree.widget.model.filtered_children  # type: ignore
        await self.wait(5)

        # Clear the process complete event before triggering the bake
        bake_view = ExtensionSettings.clash_bake_view
        self.assertIsNotNone(bake_view)
        assert bake_view is not None  # type assertion for linter
        complete_event = bake_view.get_process_complete_event()
        complete_event.clear()

        window = ui_test.find(self.CLASH_WND_NAME)
        self.assertIsNotNone(window)
        p1 = ui_test.Vec2(window.widget.position_x + 100, window.widget.position_y + 140) # type: ignore
        # p1 = ui_test.Vec2(clash_results_tree.position.x + 5, clash_results_tree.position.y + 30) # Not reliable
        # print(f"window.widget.position {window.widget.position_x}, {window.widget.position_y}") # type: ignore
        # print(f"clash_results_tree.position: {clash_results_tree.position}")
        await ui_test.emulate_mouse_move_and_click(p1, right_click=True)
        self.assertIsNotNone(ui.Menu.get_current())
        # Save current RAM usage
        current_ram = get_used_mem()
        await ui_test.select_context_menu("Generate Clash Meshes")

        # Wait for the bake process to complete or await for 1 second and loop to print status
        start_time = time.time()
        while not complete_event.is_set():
            status = bake_view.get_status()
            elapsed_time = time.time() - start_time
            used_memory_mb = status.memory_total / 1024**2
            print(
                f"Clash Bake - Progress: {status.progress*100:.2f}%... time elapsed: {elapsed_time:.2f} seconds, used memory: {used_memory_mb:.2f} MB"
            )
            # Wait for the earliest that happens between the event being set or 1 second elapsed
            # To obtain more precise peak memory before rtx allocates its stuff
            time_to_wait = 1 if status.progress < 0.9 else 0.3
            _, _ = await asyncio.wait(
                [asyncio.create_task(complete_event.wait()), asyncio.create_task(asyncio.sleep(time_to_wait))],
                return_when=asyncio.FIRST_COMPLETED,
            )
        status = bake_view.get_status()

        # Save final RAM usage
        self.assertEqual(status.progress, 1.0)
        self.assertIsNotNone(status.info_message)
        self.assertIsNone(status.error_message)
        self.assertEqual(status.infos_total, status.infos_processed)

        CodeTimer.add_record(f"Clash Bake - Remove Overs", status.time_remove_overs, status.memory_remove_overs)

        # All these 3 phases are done interleaved in batches so memory tracking may not be very accurate
        CodeTimer.add_record(f"Clash Bake - Prepare Clashes", status.time_prepare, status.memory_prepare)
        CodeTimer.add_record(f"Clash Bake - Load Database", status.time_database_load, status.memory_database_load)
        CodeTimer.add_record(f"Clash Bake - Bake Clashes", status.time_bake, status.memory_bake)

        CodeTimer.add_record(f"Clash Bake - Finalize Clashes", status.time_finalize, status.memory_finalize)
        CodeTimer.add_record(f"Clash Bake - Update Layer", status.time_update_layer, status.memory_update_layer)
        CodeTimer.add_record(f"Clash Bake - Kit Updates", status.time_kit_app_updates, status.memory_kit_app_updates)

        CodeTimer.add_record(f"Clash Bake - Total Time and Memory", status.time_total, status.memory_total)

    async def _measure_timeline_median_fps(self, parameters: ClashBakeBenchmarkParameters):
        # This test measures the FPS of playing the timeline with the bake layer enabled

        from omni.kit.viewport.utility import get_active_viewport_window

        viewport_window = get_active_viewport_window()
        assert viewport_window is not None
        viewport_api = viewport_window.viewport_api
        baseline_fps = []
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_looping(False)
        old_start_time = timeline.get_start_time()
        old_end_time = timeline.get_end_time()

        if parameters.measure_runtime_start is not None:
            timeline.set_start_time(parameters.measure_runtime_start)
            timeline.set_current_time(parameters.measure_runtime_start)
        else:
            timeline.set_current_time(old_start_time)
        if parameters.measure_runtime_end is not None:
            timeline.set_end_time(parameters.measure_runtime_end)

        timeline.play()
        await asyncio.sleep(1)  # Wait for the timeline to start playing
        while timeline.is_playing():
            print(f"[{timeline.get_current_time():.2f}]: {viewport_api.fps:.2f} FPS")
            baseline_fps.append(viewport_api.fps)
            await asyncio.sleep(1)
        median_fps = np.median(baseline_fps)
        print(f"Median FPS: {median_fps:.2f} FPS")
        print(f"Max    FPS: {np.max(baseline_fps):.2f} FPS")
        print(f"Min    FPS: {np.min(baseline_fps):.2f} FPS")

        if parameters.measure_runtime_start is not None:
            timeline.set_start_time(old_start_time)
        if parameters.measure_runtime_end is not None:
            timeline.set_end_time(old_end_time)

        return float(median_fps)

    async def _run_viewport_benchmark(self, perform_viewport: ClashViewportBenchmarkParameters, expected_num_results: int):
        print(f"Measuring Clash Viewport Benchmark...")
        self._ensure_query_selected()  # select the first query
        clash_results_tree = self._get_results_tree()
        range_start = perform_viewport.clashes_range[0] if perform_viewport.clashes_range is not None else 0
        range_end = perform_viewport.clashes_range[1] if perform_viewport.clashes_range is not None else expected_num_results  # type: ignore
        if range_end > expected_num_results:  # type: ignore
            range_end = expected_num_results  # type: ignore
        start_time = time.time()
        start_mem = get_used_mem()
        total_clashes = range_end - range_start
        print(f"Testing clash results viewport switching with {total_clashes} clashes...")
        for idx in range(range_start, range_end):
            start_clash_time = time.time()
            clash_info = clash_results_tree.widget.model.filtered_children[idx]  # type: ignore
            clash_results_tree.widget.selection = [clash_info]  # type: ignore
            await self.wait(1)
            end_clash_time = time.time()
            clash_time = end_clash_time - start_clash_time
            current_mem = get_used_mem()
            delta_mem_mb = (current_mem - start_mem) / 1024**2
            print(f"Switch clash {idx} of {total_clashes} took {clash_time:.3f} secs. Memory: {delta_mem_mb:.2f} MB")
        clash_results_tree.widget.selection = []  # type: ignore
        await self.wait(1)
        end_time = time.time()
        end_mem = get_used_mem()
        total_time = end_time - start_time
        total_mem = end_mem - start_mem
        total_mem_mb = total_mem / 1024**2
        print(f"Switched through {total_clashes} clashes in {total_time:.2f} secs. Memory delta: {total_mem_mb:.2f} MB")
        CodeTimer.add_record(f"Clash Viewport - Switch results", total_time, total_mem)
