# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List
from collections import namedtuple
import os
from pathlib import Path
import warp as wp
import numpy as np
import omni.client
from pxr import Usd, UsdUtils
from omni.kit.test import AsyncTestCase
from omni.physxclashdetectioncore.clash_info import ClashInfo, ClashFrameInfo, ClashState, OverlapType
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_data_serializer_sqlite import ClashDataSerializerSqlite
from omni.physxclashdetectioncore.clash_detect_export import export_to_html, export_to_json, ExportColumnDef
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.usd_utils import serialize_matrix_to_json, deserialize_matrix_from_json
from omni.physxclashdetectioncore.utils import (
    OptimizedProgressUpdate, make_int128, file_exists, safe_delete_file, get_random_word,
    get_unique_temp_file_path_name, get_current_user_name, measure_execution_time, to_json_str_safe, from_json_str_safe
)
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry


def compare_text_files(file1_name: str, file2_name: str, ignore_order: bool) -> List[str]:
    """ Compares provided text files and returns differences, if empty string if any.
        Is able to find matching lines if they are in different order.
    """
    def remove_matching_line(text_to_remove: str, lines: List[str]):
        """
        Remove the first occurrence of a matching line from the list.
        :param lines: List of strings (lines of text)
        :param text_to_remove: The text to find and remove
        :return: Modified list with the matching line removed
        """
        try:
            index_to_remove = lines.index(text_to_remove)
            del lines[index_to_remove]
            return True
        except ValueError:
            return False

    differences = []
    try:
        with open(file1_name, 'r') as f1, open(file2_name, 'r') as f2:
            file1_lines = f1.readlines()
            file2_lines = f2.readlines()
        if ignore_order:
            for line_num, line in enumerate(file1_lines, start=1):
                if not remove_matching_line(line, file2_lines):
                    differences.append((line_num, "Line not found: ", line.strip()))
            if len(file2_lines) != 0:
                differences.append((0, "Number of unmatched lines: ", len(file2_lines)))
        else:
            for line_num, (line1, line2) in enumerate(zip(file1_lines, file2_lines), start=1):
                if line1 != line2:
                    differences.append((line_num, line1.strip(), line2.strip()))
    except FileNotFoundError as e:
        differences.append(str(e))
    finally:
        return differences


class DataStructuresTest(AsyncTestCase):

    def __init__(self, tests=()):
        super().__init__(tests)
        self.maxDiff = None
        self._clash_telemetry_logging_orig_val = ClashTelemetry.debug_logging
        test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
        self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'
        self._ignore_save_load_events = None
        self._clash_data = ClashData(ClashDataSerializerSqlite())
        self._clash_detect = ClashDetection()

    # Before running each test
    def setUp(self):
        super().setUp()
        ClashTelemetry.debug_logging = True
        try:
            # disable the .ui module so stage events, so it is not interfering with the test
            from omni.physxclashdetectionui.settings import ExtensionSettings
            self._ignore_save_load_events = ExtensionSettings.ignore_save_load_events
            ExtensionSettings.ignore_save_load_events = True
        except Exception:
            pass  # import not available, we don't need to care

    def tearDown(self):
        ClashTelemetry.debug_logging = self._clash_telemetry_logging_orig_val
        try:
            from omni.physxclashdetectionui.settings import ExtensionSettings
            if self._ignore_save_load_events is not None:
                ExtensionSettings.ignore_save_load_events = self._ignore_save_load_events
        except Exception:
            pass  # import not available, we don't need to care
        self._stage_cleanup(None, False)
        super().tearDown()

    def _stage_cleanup(self, stage: Usd.Stage, delete_clash_layers=True):
        # clear USD Stage Cache
        in_cache = UsdUtils.StageCache.Get().Contains(stage)
        if in_cache:
            UsdUtils.StageCache.Get().Erase(stage)
        # Clear also clash layers and temp data files
        for k, v in self._clash_data._loaded_layers.items():
            if delete_clash_layers and file_exists(k):
                safe_delete_file(k)
            if file_exists(v):
                safe_delete_file(v)
        # clear the loaded layers dict only if we are deleting the clash layers otherwise keep even deleted temp files
        if delete_clash_layers:
            self._clash_data._loaded_layers.clear()

    def _prop_test(self, inst, prop, val, test_last_modified: bool = False):
        timestamp = None
        if test_last_modified:
            timestamp = inst.last_modified_timestamp
            inst._last_modified_by = ''  # reset the field, so we can check if it was properly set
        prop.fset(inst, val)
        self.assertEqual(prop.fget(inst), val)
        if test_last_modified:
            self.assertTrue(inst.last_modified_timestamp >= timestamp)
            self.assertEqual(inst.last_modified_by, get_current_user_name())

    @measure_execution_time
    def _test_query_ops(self, my_query: ClashQuery) -> None:
        my_retrieved_query = self._clash_data.find_query(my_query.identifier)
        self.assertIsNotNone(my_retrieved_query)
        self.assertEqual(vars(my_query), vars(my_retrieved_query))  # verify they are equal

        my_second_query_id = self._clash_data.insert_query(my_retrieved_query)  # duplicate the query
        self.assertTrue(my_second_query_id and my_second_query_id == 2 and my_second_query_id == my_retrieved_query.identifier)

        my_retrieved_query.object_a_path = "A/B/C"
        my_retrieved_query.object_b_path = "C/B/A/"
        my_retrieved_query.query_name = "My Updated Test Query"
        my_retrieved_query.clash_detect_settings = {SettingId.SETTING_LOGGING.name: True}
        my_retrieved_query.comment = "Updated comment"
        affected_records = self._clash_data.update_query(my_retrieved_query)
        self.assertEqual(affected_records, 1)

        my_retrieved_query2 = self._clash_data.find_query(my_second_query_id)
        self.assertIsNotNone(my_retrieved_query2)
        self.assertEqual(vars(my_retrieved_query), vars(my_retrieved_query2))  # verify they are equal

        all_queries = self._clash_data.fetch_all_queries()
        self.assertEqual(len(all_queries), 2)
        all_queries_list = list(all_queries.values())
        query1 = all_queries_list[0]
        self.assertEqual(vars(query1), vars(my_query))  # verify they are equal
        query2 = all_queries_list[1]
        self.assertEqual(vars(query2), vars(my_retrieved_query))  # verify they are equal

        affected_records = self._clash_data.remove_query_by_id(my_second_query_id)
        self.assertEqual(affected_records, 1)
        deleted_query = self._clash_data.find_query(my_second_query_id)
        self.assertIsNone(deleted_query)

        my_retrieved_query3 = self._clash_data.find_query(my_query.identifier)  # get the original query
        self.assertIsNotNone(my_retrieved_query3)
        self.assertEqual(vars(my_query), vars(my_retrieved_query3))  # verify they are equal

        my_retrieved_empty = self._clash_data.find_query(0)  # try to get non-existent query
        self.assertIsNone(my_retrieved_empty)

    @measure_execution_time
    def _run_clash_detection(self, stage: Usd.Stage) -> None:
        print("Running clash detection engine...", end="")
        self._clash_detect.reset()
        num_steps = self._clash_detect.create_pipeline()
        progress_update = OptimizedProgressUpdate(update_rate=1.0, force_update_rate=1.0)
        for i in range(num_steps):
            step_data = self._clash_detect.get_pipeline_step_data(i)
            if progress_update.update(step_data.progress):
                print(".", end="")
            self._clash_detect.run_pipeline_step(i)
        print("Finished.")

    @measure_execution_time
    def _fetch_overlaps(self, stage: Usd.Stage, clash_query: ClashQuery) -> List[ClashInfo]:
        existing_clash_info_items = dict()
        new_clash_info_items = []
        setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0)
        setting_depth_epsilon = clash_query.clash_detect_settings.get(SettingId.SETTING_DEPTH_EPSILON.name, -1.0)
        count = self._clash_detect.get_nb_overlaps()

        print(f"Fetching {count} overlaps...", end="")
        progress_update = OptimizedProgressUpdate(update_rate=1.0, force_update_rate=1.0)
        for idx in range(count):
            if progress_update.update(float(idx) / float(count)):
                print(".", end="")
            clash_info = self._clash_detect.process_overlap(
                stage,
                idx,
                existing_clash_info_items,
                clash_query.identifier,
                setting_tolerance,
                setting_depth_epsilon
            )
            if clash_info and clash_info.identifier == -1:  # identifier -1 means new clash, otherwise existing
                new_clash_info_items.append(clash_info)
        print("Finished.")
        return new_clash_info_items

    async def _test_depth_query(self, depth_epsilon: float, discard_contacts: bool) -> List[ClashInfo]:
        """Tests contact classification."""
        stage_path_name = self._test_data_dir + "contact_cases.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        print("Creating new query...")
        my_query = ClashQuery(
            query_name="My Depth Query",
            object_a_path="",
            object_b_path="",
            clash_detect_settings={
                SettingId.SETTING_LOGGING.name: False,
                SettingId.SETTING_DYNAMIC.name: False,
                SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name: True,
                SettingId.SETTING_MAX_LOCAL_DEPTH_MODE.name: 0,
                SettingId.SETTING_CONTACT_CUTOFF.name: 1.0,
                SettingId.SETTING_DEPTH_EPSILON.name: depth_epsilon,
                SettingId.SETTING_DISCARD_TOUCHING_CONTACTS.name: discard_contacts,
            },
        )

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                my_query.object_a_path,
                my_query.object_b_path
            )
        )
        self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

        self._run_clash_detection(stage)

        overlaps = self._fetch_overlaps(stage, my_query)

        print("Closing...")
        self._stage_cleanup(stage)

        return overlaps

    def _compare_clash_info(self, ci1: ClashInfo, ci2: ClashInfo):
        """ verify equality value by value """
        # vars() is awesome, but we cannot use it for inner arrays so let's compare them separately
        ci1_fi = ci1.clash_frame_info_items
        ci2_fi = ci2.clash_frame_info_items
        ci1.clash_frame_info_items = None
        ci2.clash_frame_info_items = None
        self.assertEqual(vars(ci1), vars(ci2))
        ci1.clash_frame_info_items = ci1_fi
        ci2.clash_frame_info_items = ci2_fi
        if not ci1_fi:
            self.assertEqual(ci1_fi, ci2_fi)  # if both are None (do not contain any frame info) then we can leave
            return
        self.assertIsNotNone(ci1.clash_frame_info_items)
        self.assertIsNotNone(ci2.clash_frame_info_items)
        if ci1.clash_frame_info_items and ci2.clash_frame_info_items:
            self.assertEqual(len(ci1.clash_frame_info_items), len(ci2.clash_frame_info_items))
            for i in range(len(ci1.clash_frame_info_items)):
                self.assertEqual(ci1.clash_frame_info_items[i], ci2.clash_frame_info_items[i])

    @measure_execution_time
    def _test_overlap_ops(self, clash_info_items: List[ClashInfo], my_query: ClashQuery) -> None:
        custom_time_code = 666.666
        mod_clash_info = clash_info_items[0]

        # save all the clash info
        for ci in clash_info_items:
            ci_identifier = self._clash_data.insert_overlap(ci, True, True, False)
            self.assertTrue(ci_identifier and ci_identifier > 0)
        self._clash_data.commit()

        retrieved_overlaps_count = self._clash_data.get_overlaps_count_by_query_id(my_query.identifier)
        self.assertEqual(retrieved_overlaps_count, len(clash_info_items) - 1)

        retrieved_clash_frame_info_count = self._clash_data.get_clash_frame_info_count_by_clash_info_id(mod_clash_info.identifier)
        self.assertEqual(retrieved_clash_frame_info_count, len(mod_clash_info.clash_frame_info_items))

        ci_identifier = mod_clash_info.identifier

        # retrieve all the clash info data and compare for equality
        retrieved_overlaps = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, True)
        self.assertEqual(len(retrieved_overlaps), len(clash_info_items) - 1)
        retrieved_overlaps2 = self._clash_data.find_all_overlaps_by_query_id(0, True)
        self.assertEqual(len(retrieved_overlaps2), 1)

        # test partial retrieval of clashing frames
        cfi_offset = 2
        retrieved_overlaps_limit = self._clash_data.find_all_overlaps_by_query_id(
            my_query.identifier, True, 3, cfi_offset
        )
        self.assertEqual(len(retrieved_overlaps_limit), len(clash_info_items) - 1)
        # check loaded frames match expectations
        for idx_ci, ci in enumerate(retrieved_overlaps_limit.values()):
            for idx_cfi, cfi in enumerate(ci.clash_frame_info_items):
                self.assertEqual(cfi, clash_info_items[idx_ci].clash_frame_info_items[idx_cfi + cfi_offset])

        retrieved_overlaps.update(retrieved_overlaps2)
        self.assertEqual(len(retrieved_overlaps), len(clash_info_items))
        for ci in clash_info_items:
            retrieved_ci = retrieved_overlaps.get(ci.overlap_id)
            self.assertIsNotNone(retrieved_ci)
            self._compare_clash_info(ci, retrieved_ci)

        # Make a modification to clash info and its clash frame info and update it
        mod_clash_info.comment = "New Comment"
        mod_clash_info.person_in_charge = "username"
        mod_clash_info.priority = 100
        mod_clash_info.state = ClashState.RESOLVED
        mod_clash_info._min_distance = 1.0
        mod_clash_info._max_local_depth = 2.0
        mod_clash_info._depth_epsilon = 3.0
        mod_clash_info._tolerance = 4.0
        mod_clash_info.penetration_depth_nz = 1.0
        mod_clash_info.penetration_depth_px = 2.0
        mod_clash_info.penetration_depth_py = 3.0
        mod_clash_info.penetration_depth_pz = 4.0
        mod_clash_info.penetration_depth_ny = 5.0
        mod_clash_info.penetration_depth_nx = 6.0
        self.assertTrue(len(mod_clash_info.clash_frame_info_items) > 0)
        # Be sure that it will retain last position with custom_time_code (timecode sort happens after fetching cfi)
        mod_clash_info.clash_frame_info_items[-1]._timecode = custom_time_code
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_nz = 1.0
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_px = 2.0
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_py = 3.0
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_pz = 4.0
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_ny = 5.0
        mod_clash_info.clash_frame_info_items[-1]._penetration_depth_nx = 6.0
        affected_records = self._clash_data.update_overlap(mod_clash_info, True, False)
        self.assertEqual(affected_records, 1)
        # read back the modified clash info
        clash_info_dict = self._clash_data.find_all_overlaps_by_overlap_id([ci_identifier], True)
        self.assertEqual(len(clash_info_dict), 1)
        clash_info = next(iter(clash_info_dict.values()))
        self._compare_clash_info(mod_clash_info, clash_info)

        # test partial retrieval of clashing frames
        clash_info_dict_limit = self._clash_data.find_all_overlaps_by_overlap_id([ci_identifier], True, 1, cfi_offset)
        self.assertEqual(len(clash_info_dict_limit), 1)
        self.assertEqual(
            clash_info_dict_limit[mod_clash_info.overlap_id].clash_frame_info_items[0],
            mod_clash_info.clash_frame_info_items[cfi_offset]
        )

        # test fetching clash frame info
        cfi_array = self._clash_data.fetch_clash_frame_info_by_clash_info_id(ci_identifier)
        self.assertEqual(len(mod_clash_info.clash_frame_info_items), len(cfi_array))
        for idx in range(len(mod_clash_info.clash_frame_info_items)):
            self.assertEqual(mod_clash_info.clash_frame_info_items[idx], cfi_array[idx])  # verify they are equal

        last_clash_frame_info = mod_clash_info.clash_frame_info_items[-1]
        # duplicate the clash frame info with some changes
        last_clash_frame_info._timecode = custom_time_code
        affected_records = self._clash_data.remove_clash_frame_info_by_clash_info_id(ci_identifier, True)
        self.assertEqual(affected_records, len(mod_clash_info.clash_frame_info_items))
        new_cfi_id = self._clash_data.insert_clash_frame_info_from_clash_info(mod_clash_info, True)
        self.assertTrue(new_cfi_id and new_cfi_id > 0)
        cfi_array = self._clash_data.fetch_clash_frame_info_by_clash_info_id(ci_identifier)
        self.assertEqual(len(cfi_array), len(mod_clash_info.clash_frame_info_items))
        self.assertEqual(cfi_array[-1], last_clash_frame_info)
        # add a new Clash Frame Info to the mod_clash_info
        new_clash_frame_info = ClashFrameInfo(custom_time_code, 0.1, 12345678)
        new_cfi_id = self._clash_data.insert_clash_frame_info(new_clash_frame_info, ci_identifier, True)
        # read back the modified clash info
        clash_info_dict = self._clash_data.find_all_overlaps_by_overlap_id([ci_identifier], True)
        self.assertEqual(len(clash_info_dict), 1)
        clash_info = next(iter(clash_info_dict.values()))
        self.assertEqual(len(clash_info.clash_frame_info_items), len(mod_clash_info.clash_frame_info_items) + 1)
        self.assertEqual(clash_info.clash_frame_info_items[-1], new_clash_frame_info)  # verify they are equal

        overlaps_count_by_state = self._clash_data.get_overlaps_count_by_query_id_grouped_by_state(my_query.identifier)
        self.assertEqual(len(overlaps_count_by_state), 2)
        self.assertEqual(overlaps_count_by_state[ClashState.NEW], 5)
        self.assertEqual(overlaps_count_by_state[ClashState.RESOLVED], 1)

        # remove clash frame info
        affected_records = self._clash_data.remove_clash_frame_info_by_clash_info_id(ci_identifier, True)
        self.assertEqual(affected_records, len(clash_info.clash_frame_info_items))
        # check that no clash frame info was loaded
        clash_info_dict = self._clash_data.find_all_overlaps_by_overlap_id([ci_identifier], True)
        self.assertEqual(len(clash_info_dict), 1)
        clash_info = next(iter(clash_info_dict.values()))
        self.assertEqual(len(clash_info.clash_frame_info_items), 0)

        # remove one overlap (clash info)
        affected_records = self._clash_data.remove_overlap_by_id(ci_identifier, False)
        self.assertEqual(affected_records, 1)
        retrieved_overlaps2 = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, True)
        self.assertEqual(len(retrieved_overlaps2), len(retrieved_overlaps) - 2)  # -1 for clash info not belonging to this query and -1 for deleted one

        # remove all overlaps by query id
        affected_records = self._clash_data.remove_all_overlaps_by_query_id(my_query.identifier, False)
        self.assertEqual(affected_records, len(retrieved_overlaps2))
        retrieved_overlaps = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, True)
        self.assertEqual(len(retrieved_overlaps), 0)
        retrieved_overlaps = self._clash_data.find_all_overlaps_by_query_id(0, True)  # appended clash info not belonging to my query
        self.assertEqual(len(retrieved_overlaps), 1)

    def _test_frame_timecodes_search(self, my_overlap):
        """ this tests searching for time codes within very specific overlap """
        cfi_index = my_overlap.get_frame_info_index_by_timecode(4.52)
        self.assertTrue(round(my_overlap.clash_frame_info_items[cfi_index].timecode, 2), 4.50)  # @4.52s should give us frame at 4.5s
        cfi_index = my_overlap.get_frame_info_index_by_timecode(1.0)
        self.assertEqual(round(my_overlap.clash_frame_info_items[cfi_index].timecode, 2), 3.62)  # @1.0s should give us frame at start = 3.62s
        cfi_index = my_overlap.get_frame_info_index_by_timecode(100.0)
        self.assertEqual(round(my_overlap.clash_frame_info_items[cfi_index].timecode, 2), 6.04)  # @100.0s should give us frame at end = 6.04s
        cfi_index = my_overlap.get_frame_info_index_by_timecode(6.01)
        self.assertEqual(round(my_overlap.clash_frame_info_items[cfi_index].timecode, 2), 6.00)  # @6.01s should give us frame at end = 6.04s

    def test_query_export_import(self):
        """Test export and import of clash query."""
        my_query = ClashQuery(
            query_name="My Test Export Query",
            object_a_path="/Tomas/Jelinek",
            object_b_path="/NVIDIA",
            clash_detect_settings={
                SettingId.SETTING_DYNAMIC.name: True,
                SettingId.SETTING_DYNAMIC_START_TIME.name: 1.11,
                SettingId.SETTING_DYNAMIC_END_TIME.name: 11.123,
                SettingId.SETTING_TOLERANCE.name: 3.33,
                SettingId.SETTING_DUP_MESHES.name: False,
            },
            comment="<<My comment & notes>>"
        )
        # test query export and import
        print("Testing query export/import...")
        query_export_file_name = get_unique_temp_file_path_name("_clash_query.json")
        print(f"Exporting to '{query_export_file_name}'...")
        json_str = to_json_str_safe([my_query.serialize_to_dict()], indent=4)
        self.assertTrue(len(json_str) > 0)
        json_bytes = json_str.encode("utf-8")
        self.assertTrue(len(json_bytes) > 0)
        self.assertEqual(omni.client.write_file(query_export_file_name, json_bytes), omni.client.Result.OK)
        # import
        print(f"Importing from '{query_export_file_name}'...")
        result, version, content = omni.client.read_file(query_export_file_name)
        self.assertEqual(result, omni.client.Result.OK)
        json_str = memoryview(content).tobytes().decode("utf-8")
        self.assertTrue(len(json_str) > 0)
        loaded_queries = from_json_str_safe(json_str)
        self.assertEqual(len(loaded_queries), 1)
        query_dict = loaded_queries[0]
        deserialized_clash_query = ClashQuery.deserialize_from_dict(query_dict, True)
        self.assertIsNotNone(deserialized_clash_query)
        self.assertEqual(deserialized_clash_query.identifier, -1)
        deserialized_clash_query._identifier = my_query._identifier
        self.assertEqual(vars(deserialized_clash_query), vars(my_query))

        # clean up
        safe_delete_file(query_export_file_name)

        # import of corrupted file
        try:
            from omni.physxtests import utils
            omni_physxtests_utils_available = True
        except:
            omni_physxtests_utils_available = False
        print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")

        corrupted_query_export_file_name = self._test_data_dir + "corrupted_export_query.json"
        print(f"Importing corrupted exported query file from  '{corrupted_query_export_file_name}'...")
        result, version, content = omni.client.read_file(corrupted_query_export_file_name)
        self.assertEqual(result, omni.client.Result.OK)
        json_str = memoryview(content).tobytes().decode("utf-8")
        self.assertTrue(len(json_str) > 0)
        loaded_queries = from_json_str_safe(json_str)
        self.assertEqual(len(loaded_queries), 1)
        query_dict = loaded_queries[0]
        new_query = ClashQuery()
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "Restore attribute error. Exception: 'ClashQuery' object has no attribute '_comment_zzzzz'.",
                    "Restore attribute error. Exception: Invalid isoformat string: '0'.",
                    "Restore attribute error. Exception: 'ClashQuery' object has no attribute '_---_name_---'.",
                ],
            ):
                new_query = ClashQuery.deserialize_from_dict(query_dict)
                self.assertIsNone(new_query)

    async def test_serialization(self):
        """Test serialization of clash detection data structures."""
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        expected_num_clashes = 6
        deferred_file_creation_until_first_write_op_prev_val = self._clash_data.deferred_file_creation_until_first_write_op
        self._clash_data.deferred_file_creation_until_first_write_op = False
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)

        print("Testing ClashQuery...")
        # if number of settings changed, update the dict below, so we test all of them
        self.assertEqual(len(SettingId), 31)
        clash_detect_settings = {
            SettingId.SETTING_TIGHT_BOUNDS.name: True,
            SettingId.SETTING_DYNAMIC.name: True,
            SettingId.SETTING_DYNAMIC_START_TIME.name: 0.0,
            SettingId.SETTING_DYNAMIC_END_TIME.name: 0.0,
            SettingId.SETTING_PURGE_PERMANENT_OVERLAPS.name: False,
            SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS.name: False,  # important to be False to check plane vs cube
            SettingId.SETTING_FILTER_TEST.name: False,
            SettingId.SETTING_NEW_TASK_MANAGER.name: True,
            SettingId.SETTING_NB_TASKS.name: 128,
            SettingId.SETTING_POSE_EPSILON.name: 1e-06,
            SettingId.SETTING_BOUNDS_EPSILON.name: 0.01,
            SettingId.SETTING_AREA_EPSILON.name: 1e-06,
            SettingId.SETTING_COPLANAR.name: True,
            SettingId.SETTING_TOLERANCE.name: 0.0,
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_SINGLE_THREADED.name: False,
            SettingId.SETTING_ANY_HIT.name: False,
            SettingId.SETTING_QUANTIZED.name: False,
            SettingId.SETTING_TRIS_PER_LEAF.name: 15,
            SettingId.SETTING_OVERLAP_CODE.name: 3,
            SettingId.SETTING_DUP_MESHES.name: False,
            SettingId.SETTING_STATIC_TIME.name: 1.33,
            SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name: True,
            SettingId.SETTING_DEPTH_EPSILON.name: -1.0,
            SettingId.SETTING_DISCARD_TOUCHING_CONTACTS.name: True,
            SettingId.SETTING_USE_USDRT.name: False,
            SettingId.SETTING_TRIANGLE_LIMIT.name: 0,
            SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS.name: False,
            SettingId.SETTING_IGNORE_INVISIBLE_PRIMS.name: True,
            SettingId.SETTING_CONTACT_CUTOFF.name: -1.0,
            SettingId.SETTING_MAX_LOCAL_DEPTH_MODE.name: 0,
        }

        my_query = ClashQuery(
            query_name="My Test Query",
            object_a_path="/Root/Utils.collection:StationCollection /Root/Xform_Primitives/Plane",
            object_b_path="/Root/Xform_Primitives/Cube /Root/STATION_TIME_SAMPLED/STATION/SKID/lnk/Mesh2",
            clash_detect_settings=clash_detect_settings,
            comment="My comment"
        )

        settings_str = my_query.get_settings_as_str()
        my_query.load_settings_from_str(settings_str)
        self.assertEqual(clash_detect_settings, my_query.clash_detect_settings)  # verify they are equal

        my_query_id = self._clash_data.insert_query(my_query, True, True)
        self.assertTrue(my_query_id and my_query_id == 1 and my_query_id == my_query.identifier)

        #  NOTE: clash data should all belong to an anonymous layer, no disk based layer should get created
        self.assertTrue(self._clash_data._target_layer.anonymous)

        print("Testing query data ops...")
        self._test_query_ops(my_query)

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                my_query.object_a_path,
                my_query.object_b_path
            )
        )
        self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

        self._run_clash_detection(stage)

        overlaps = self._fetch_overlaps(stage, my_query)
        self.assertEqual(len(overlaps), expected_num_clashes)

        # sort overlaps by order they are retrieved from the database (by clash hash)
        overlaps.sort(key=lambda x: x.overlap_id)

        print("Testing overlap data ops...")
        matching_overlaps = [o for o in overlaps if o.num_records == 59]
        self.assertTrue(len(matching_overlaps) > 0)
        my_overlap = matching_overlaps[0]
        self.assertIsNotNone(my_overlap)
        self._test_frame_timecodes_search(my_overlap)

        overlaps.append(ClashInfo(clash_frame_info_items=[]))  # append empty clash info to also test serialization of just initialized class

        self._test_overlap_ops(overlaps, my_query)

        print("Closing...")
        self._clash_data.close()
        self._clash_data.deferred_file_creation_until_first_write_op = deferred_file_creation_until_first_write_op_prev_val
        self._stage_cleanup(stage)

    async def test_clash_query_props(self):
        """Test clash query properties."""
        from datetime import datetime
        import time

        start_time = datetime.now()
        query = ClashQuery()
        time.sleep(0.1)
        self.assertTrue(query.creation_timestamp >= start_time)
        self.assertTrue(query.creation_timestamp < datetime.now())
        self.assertEqual(query.identifier, -1)

        self._prop_test(query, ClashQuery.query_name, "Test Query Name", True)
        self._prop_test(query, ClashQuery.object_a_path, "test/pathA", True)
        self._prop_test(query, ClashQuery.object_b_path, "test/pathB", True)
        self._prop_test(query, ClashQuery.comment, "A test comment", True)
        self._prop_test(query, ClashQuery.comment, "A test comment", True)
        self._prop_test(query, ClashQuery.clash_detect_settings, {SettingId.SETTING_DYNAMIC.name: True}, True)
        # clash_detect_settings are more tested in serialization test

    async def test_clash_info_props(self):
        """Test clash info properties."""
        from datetime import datetime
        import time
        from pxr import Gf

        start_time = datetime.now()
        matrix0 = Gf.Matrix4d()
        matrix1 = Gf.Matrix4d(10)

        # check matrix serialization
        json_matrix = serialize_matrix_to_json(matrix1)
        matrix1_deserialized = deserialize_matrix_from_json(json_matrix)
        self.assertEqual(matrix1, matrix1_deserialized)

        clash_info = ClashInfo(
            10, 10, "0x0", OverlapType.DUPLICATE, True, 0.0, 0.0, -1.0, 5,
            "/a/path", "0xabc",
            "/b/path", "0xbbc",
            1.1, 9.9, 2, 1000
        )
        clash_info.penetration_depth_px = 1.0
        clash_info.penetration_depth_nx = 2.0
        clash_info.penetration_depth_py = 3.0
        clash_info.penetration_depth_ny = 4.0
        clash_info.penetration_depth_pz = 5.0
        clash_info.penetration_depth_nz = 6.0
        time.sleep(0.1)
        self.assertTrue(clash_info.creation_timestamp >= start_time)
        self.assertTrue(clash_info.creation_timestamp < datetime.now())

        self.assertEqual(clash_info.identifier, 10)
        self.assertEqual(clash_info.query_id, 10)
        self.assertEqual(clash_info.overlap_id, "0x0")
        self.assertEqual(clash_info.present, True)
        self.assertEqual(clash_info.min_distance, 0.0)
        self.assertEqual(clash_info.max_local_depth, 0.0)
        self.assertEqual(clash_info.depth_epsilon, -1.0)
        self.assertEqual(clash_info.tolerance, 5)
        self.assertEqual(clash_info.object_a_path, "/a/path")
        self.assertEqual(clash_info.object_a_mesh_crc, "0xabc")
        self.assertEqual(clash_info.object_b_path, "/b/path")
        self.assertEqual(clash_info.object_b_mesh_crc, "0xbbc")
        self.assertEqual(clash_info.start_time, 1.1)
        self.assertEqual(clash_info.end_time, 9.9)
        self.assertEqual(clash_info.num_records, 2)
        self.assertEqual(clash_info.overlap_tris, 1000)
        self.assertEqual(clash_info.penetration_depth_px, 1.0)
        self.assertEqual(clash_info.penetration_depth_nx, 2.0)
        self.assertEqual(clash_info.penetration_depth_py, 3.0)
        self.assertEqual(clash_info.penetration_depth_ny, 4.0)
        self.assertEqual(clash_info.penetration_depth_pz, 5.0)
        self.assertEqual(clash_info.penetration_depth_nz, 6.0)

        self._prop_test(clash_info, ClashInfo.state, ClashState.RESOLVED, True)
        self._prop_test(clash_info, ClashInfo.priority, 100, True)
        self._prop_test(clash_info, ClashInfo.person_in_charge, "Tomas Jelinek", True)
        self._prop_test(clash_info, ClashInfo.comment, "Just a test!", True)

        usd_faces_0 = wp.array([1, 2, 3], dtype=wp.uint32)
        usd_faces_1 = wp.array([3, 2, 1], dtype=wp.uint32)
        collision_outline = wp.array([0.1, 0.2, 0.22, 0.222], dtype=wp.float32)

        cfi = ClashFrameInfo(
            1.1, 0.0, 0.0, 100,
            wp.clone(usd_faces_0), wp.clone(usd_faces_1), wp.clone(collision_outline),
            matrix0, matrix1
        )
        cfi.penetration_depth_px = 1.0
        cfi.penetration_depth_nx = 2.0
        cfi.penetration_depth_py = 3.0
        cfi.penetration_depth_ny = 4.0
        cfi.penetration_depth_pz = 5.0
        cfi.penetration_depth_nz = 6.0
        self.assertEqual(cfi.timecode, 1.1)
        self.assertEqual(cfi.min_distance, 0.0)
        self.assertEqual(cfi.max_local_depth, 0.0)
        self.assertEqual(cfi.overlap_tris, 100)
        self.assertTrue(np.array_equal(cfi.usd_faces_0.numpy(), usd_faces_0.numpy()))
        self.assertTrue(np.array_equal(cfi.usd_faces_1.numpy(), usd_faces_1.numpy()))
        self.assertTrue(np.array_equal(cfi.collision_outline.numpy(), collision_outline.numpy()))
        self.assertEqual(vars(cfi.object_0_matrix), vars(matrix0))
        self.assertEqual(vars(cfi.object_0_matrix), vars(matrix1))
        self.assertTrue(cfi.check_object_0_matrix_changed(matrix1))  # test matrix changed method
        self.assertTrue(cfi.check_object_1_matrix_changed(matrix0))  # test matrix changed method
        self.assertEqual(cfi.penetration_depth_px, 1.0)
        self.assertEqual(cfi.penetration_depth_nx, 2.0)
        self.assertEqual(cfi.penetration_depth_py, 3.0)
        self.assertEqual(cfi.penetration_depth_ny, 4.0)
        self.assertEqual(cfi.penetration_depth_pz, 5.0)
        self.assertEqual(cfi.penetration_depth_nz, 6.0)
        self._prop_test(clash_info, ClashInfo.clash_frame_info_items, [cfi, cfi], False)
        self.assertEqual(vars(clash_info.get_last_clash_frame_info()), vars(cfi))

        # test serialization to dict and deserialization from dict
        clash_info_dict = clash_info.serialize_to_dict()
        self.assertIsNotNone(clash_info_dict)
        deserialized_clash_info = ClashInfo.deserialize_from_dict(clash_info_dict, True)
        self.assertIsNotNone(deserialized_clash_info)
        deserialized_clash_info._identifier = clash_info._identifier  # set back the id value as it gets reset on purpose
        self._compare_clash_info(deserialized_clash_info, clash_info)

    async def test_serializer_ops_on_invalid_target(self):
        """Test serializer operations on invalid target."""
        def test_data_ops(cd: ClashData):
            self.assertIsNotNone(cd.insert_overlap(None, True, True, False))
            self.assertIsNotNone(cd.insert_overlap(ClashInfo(), True, True, False))
            self.assertIsNotNone(cd.update_overlap(None, True, False))
            self.assertIsNotNone(cd.update_overlap(ClashInfo(), True, False))
            self.assertIsNotNone(cd.find_all_overlaps_by_query_id(0, True))
            self.assertIsNotNone(cd.find_all_overlaps_by_overlap_id(None, True))
            self.assertIsNotNone(cd.find_all_overlaps_by_overlap_id([], True))
            self.assertIsNotNone(cd.find_all_overlaps_by_overlap_id([0], True))
            self.assertIsNotNone(cd.remove_all_overlaps_by_query_id(0, False))
            self.assertIsNotNone(cd.remove_overlap_by_id(0, False))
            self.assertIsNotNone(cd.fetch_clash_frame_info_by_clash_info_id(0))
            self.assertIsNotNone(cd.insert_clash_frame_info_from_clash_info(ClashInfo(), False))
            self.assertIsNotNone(cd.insert_clash_frame_info_from_clash_info(None, False))
            self.assertIsNotNone(cd.insert_clash_frame_info(ClashFrameInfo(), 0, False))
            self.assertIsNotNone(cd.insert_clash_frame_info(None, 0, False))
            self.assertIsNotNone(cd.remove_clash_frame_info_by_clash_info_id(0, False))
            self.assertIsNotNone(cd.fetch_all_queries())
            self.assertIsNotNone(cd.insert_query(ClashQuery()))
            self.assertIsNotNone(cd.insert_query(None))
            self.assertIsNone(cd.find_query(0))
            self.assertIsNotNone(cd.update_query(ClashQuery(), False))
            self.assertIsNotNone(cd.update_query(None, False))
            self.assertIsNotNone(cd.remove_query_by_id(0, False))

        try:
            from omni.physxtests import utils
            omni_physxtests_utils_available = True
        except:
            omni_physxtests_utils_available = False
        print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")

        """ Should-not-crash test. """
        from omni.physxclashdetectioncore.clash_data import Serializer_data_operations
        expected_serializer_data_operations = 19
        self.assertEqual(len(Serializer_data_operations), expected_serializer_data_operations)
        # testing serializer ops on non-existent file
        self._clash_data.open(0)
        self._clash_data._serializer.open("$invalid/path/*&?<")
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(self, "SQLite error 'unable to open database file' occurred."):
                test_data_ops(self._clash_data)
        self.assertIsNone(self._clash_data._target_layer)
        self._clash_data.close()

        # testing serializer ops on corrupted file = won't load, ops will be performed on an anonymous in-memory layer
        stage_path_name = self._test_data_dir + "corrupted_data_file.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)
        test_data_ops(self._clash_data)
        self.assertTrue(self._clash_data._target_layer.anonymous)
        self._clash_data.close()
        self._stage_cleanup(stage, False)

        # testing serializer ops on broken file
        stage_path_name = self._test_data_dir + "broken_data_file.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "_execute_fetch_query: SQLite error 'no such table: version_info' occurred.",
                    "_execute_fetch_query: SQLite error 'no such table: clash_info' occurred.",
                    "_execute_commit_query: SQLite error 'no such table: clash_info' occurred.",
                    "_execute_fetch_query: SQLite error 'no such table: clash_frame_info' occurred.",
                    "_execute_commit_query: SQLite error 'no such table: clash_frame_info' occurred."
                ],
            ):
                test_data_ops(self._clash_data)
        self._clash_data.close()
        self._stage_cleanup(stage, False)

        # testing clash data on uninitialized serializer
        clash_data_no_serializer = ClashData(None)
        clash_data_no_serializer.open(0)
        test_data_ops(clash_data_no_serializer)
        clash_data_no_serializer.close()
        clash_data_no_serializer.destroy()
        del clash_data_no_serializer

    async def test_save_as_to_db(self):
        """Test saving / loading clash detection results to and from database."""
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)

        UsdUtils.StageCache.Get().Insert(stage)

        stage_path_name = get_unique_temp_file_path_name("_test_save_to_db.usda")
        print(f"Saving stage as '{stage_path_name}'...")
        stage.GetRootLayer().identifier = stage_path_name
        stage.GetRootLayer().Save(True)
        Usd.Stage.Save(stage)

        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        expected_num_clashes = 6
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)

        print("Creating new query...")
        clash_detect_settings = {
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_DYNAMIC.name: True,
            SettingId.SETTING_NEW_TASK_MANAGER.name: True,
            SettingId.SETTING_NB_TASKS.name: 128,
        }

        my_query = ClashQuery(
            query_name="My Test Query",
            object_a_path="/Root/STATION_TIME_SAMPLED",
            object_b_path="/Root/Xform_Primitives",
            clash_detect_settings=clash_detect_settings,
            comment="My comment"
        )
        new_id = self._clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                my_query.object_a_path,
                my_query.object_b_path
            )
        )
        self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

        self._run_clash_detection(stage)

        num_overlaps = self._clash_detect.get_nb_overlaps()
        self.assertEqual(num_overlaps, expected_num_clashes)

        print(f"Fetching {num_overlaps} overlaps...", end="")
        for _ in self._clash_detect.fetch_and_save_overlaps(stage, self._clash_data, my_query):
            print(".", end="")
        print("Finished.")

        print(f"Re-fetching {num_overlaps} overlaps to test clash data updating...", end="")
        for _ in self._clash_detect.fetch_and_save_overlaps(stage, self._clash_data, my_query):
            print(".", end="")
        print("Finished.")

        saved_overlaps = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, False)
        self.assertEqual(len(saved_overlaps), num_overlaps)

        print(f"Saving stage '{stage_path_name}'...")
        self._clash_data.save()
        Usd.Stage.Save(stage)
        self._clash_data.saved()

        print(f"Closing stage '{stage_path_name}'...")
        # We want to make sure that nothing got cached -> that clash data layer was loaded from disk, not re-used from memory.
        # Each time clash data file is extracted from the clash layer, it receives a unique random file name in the temp dir.
        self._clash_data.close()
        self._stage_cleanup(stage, False)
        del stage

        print(f"Re-opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), True)

        print("Verifying saved data...")
        queries = self._clash_data.fetch_all_queries()
        self.assertEqual(len(queries), 1)
        query = next(iter(queries.values()))
        self.assertEqual(vars(query), vars(my_query))

        print("Closing...")
        self._clash_data.close()
        self._stage_cleanup(stage)
        if file_exists(stage_path_name):
            safe_delete_file(stage_path_name)

    async def test_on_fly_export(self):
        """ This test does not use ClashData at all. """
        stage_name = "time_sampled.usda"
        stage_path_name = self._test_data_dir + stage_name
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        expected_num_clashes = 6

        print("Creating new query...")
        clash_detect_settings = {
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_DYNAMIC.name: True,
            SettingId.SETTING_TOLERANCE.name: 0.7,
            SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH.name: True,
            SettingId.SETTING_MAX_LOCAL_DEPTH_MODE.name: 1,
        }

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                "/Root/STATION_TIME_SAMPLED",
                "/Root/Xform_Primitives"
            )
        )
        self.assertTrue(self._clash_detect.set_settings(clash_detect_settings, stage))

        self._run_clash_detection(stage)

        num_overlaps = self._clash_detect.get_nb_overlaps()
        self.assertEqual(num_overlaps, expected_num_clashes)
        print(f"Fetching {num_overlaps} overlaps...", end="")
        overlaps = []
        ClashInfoReportData = namedtuple("ClashInfoReportData", "overlap_id clash_info end_time")
        for idx in range(num_overlaps):
            clash_info = self._clash_detect.get_overlap_data(idx, 0)
            overlap_id = str(hex(make_int128(clash_info.clash_hash[0], clash_info.clash_hash[1])))
            end_time = self._clash_detect.get_overlap_data(idx, clash_info.nb_records - 1).time
            overlaps.append(ClashInfoReportData(overlap_id, clash_info, end_time))
        self.assertEqual(len(overlaps), expected_num_clashes)

        # sort overlaps by clash hash
        overlaps.sort(key=lambda x: x.overlap_id)

        print(f"Generating {len(overlaps)} rows...", end="")
        rows = []
        progress_update = OptimizedProgressUpdate()
        for idx, clash_info in enumerate(overlaps):
            row = [
                clash_info.overlap_id,
                f"{clash_info.clash_info.min_distance:.3f}",
                f"{clash_info.clash_info.max_local_depth:.3f}",
                f"{clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, 0.0):.3f}",
                str(clash_info.clash_info.nb_tris),
                f"{clash_info.clash_info.time:.3f}",
                f"{clash_info.end_time:.3f}",
                str(clash_info.clash_info.nb_records),
                clash_info.clash_info.name0,
                clash_info.clash_info.name1,
                f"My custom comment #{idx + 1}"
            ]
            rows.append(row)
            if progress_update.update(float(idx) / float(num_overlaps)):
                print(".", end="")
        self.assertEqual(len(rows), expected_num_clashes)
        print("Finished.")

        del overlaps

        column_defs = [
            ExportColumnDef(0, "Clash ID"),
            ExportColumnDef(1, "Min Distance", True),
            ExportColumnDef(2, "Max Local Depth", True),
            ExportColumnDef(3, "Tolerance", True),
            ExportColumnDef(4, "Overlap Tris", True),
            ExportColumnDef(5, "Clash Start"),
            ExportColumnDef(6, "Clash End"),
            ExportColumnDef(7, "Records", True),
            ExportColumnDef(8, "Object A"),
            ExportColumnDef(9, "Object B"),
            ExportColumnDef(10, "Comment"),
        ]

        output_path = Path(omni.kit.test.get_test_output_path())
        file_name_prefix = get_random_word(8) + "_clash_data"
        file_name_prefix = str(output_path.joinpath(file_name_prefix))

        path_name = file_name_prefix + ".json"
        print(f"Exporting to JSON file '{path_name}'...")
        additional_info = {
            "Author": "Tomas Jelinek",
            "Date": "2025-01-01",
            "Engine": "NVIDIA Omniverse Clash Detection",
            "Company": "NVIDIA",
            "Company Website": "https://www.nvidia.com",
            "Additional Info": "This is a test - this is a test - this is a test - this is a test - this is a test..."
        }
        json_bytes = export_to_json(column_defs, rows, additional_info)
        self.assertTrue(len(json_bytes) > 0)
        self.assertTrue(omni.client.write_file(path_name, json_bytes) == omni.client.Result.OK)
        print("Done!")
        golden_path = self._test_data_dir + "export_clash_data.json"
        print(f"Comparing '{path_name}' with golden '{golden_path}'...")
        differences = compare_text_files(path_name, golden_path, ignore_order=False)
        print(f"Differences against golden file: {differences}")
        self.assertTrue(len(differences) == 0)

        path_name = file_name_prefix + ".html"
        print(f"Exporting to HTML file '{path_name}'...")
        html_bytes = export_to_html("Clash Detection Results", stage_name, column_defs, rows, additional_info)
        self.assertTrue(len(html_bytes) > 0)
        self.assertTrue(omni.client.write_file(path_name, html_bytes) == omni.client.Result.OK)
        print("Done!")
        golden_path = self._test_data_dir + "export_clash_data.html"
        print(f"Comparing '{path_name}' with golden '{golden_path}'...")
        differences = compare_text_files(path_name, golden_path, ignore_order=False)
        print(f"Differences against golden file: {differences}")
        self.assertTrue(len(differences) == 0)

        print("Closing...")

    async def test_dup_query_direct(self):
        """Tests duplicate mesh clash detection using direct API calls."""
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        expected_num_clashes = 1

        print("Creating new query...")
        clash_detect_settings = {
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_DYNAMIC.name: False,
            SettingId.SETTING_DUP_MESHES.name: True,
            SettingId.SETTING_STATIC_TIME.name: 1.111,
            SettingId.SETTING_NEW_TASK_MANAGER.name: True,
            SettingId.SETTING_NB_TASKS.name: 128,
        }

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                "/Root/STATION_TIME_SAMPLED",
                "/Root/Xform_Primitives",
                True  # merge scopes into a single scope so we detect duplicates also 'inside' scopes
            )
        )
        self.assertTrue(self._clash_detect.set_settings(clash_detect_settings, stage))

        self._run_clash_detection(stage)

        dups_count = self._clash_detect.get_nb_duplicates()
        self.assertEqual(dups_count, expected_num_clashes)

        dup_clash_info = self._clash_detect.process_duplicate(stage, 0, dict(), 0)
        self.assertEqual(dup_clash_info.query_id, 0)
        self.assertEqual(dup_clash_info.object_a_path, "/Root/Xform_Primitives/Cube_Dup1")
        self.assertEqual(dup_clash_info.object_b_path, "/Root/Xform_Primitives/Cube_Dup2")
        self.assertEqual(dup_clash_info.overlap_tris, 12)
        self.assertEqual(dup_clash_info.min_distance, 0.0)
        self.assertEqual(dup_clash_info.num_records, 1)
        self.assertEqual(dup_clash_info.max_local_depth, -1.0)

        print("Closing...")
        self._stage_cleanup(stage)

    async def test_dup_query_save_to_db(self):
        """Tests saving duplicate mesh clash detection results to a database."""
        stage_path_name = self._test_data_dir + "time_sampled.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)

        time_codes_per_second = stage.GetTimeCodesPerSecond()
        self.assertTrue(time_codes_per_second > 0)

        expected_num_dups = 1
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)

        print("Creating new query...")
        clash_detect_settings = {
            SettingId.SETTING_LOGGING.name: False,
            SettingId.SETTING_DYNAMIC.name: False,
            SettingId.SETTING_DUP_MESHES.name: True,
            SettingId.SETTING_STATIC_TIME.name: 1.111,
            SettingId.SETTING_NEW_TASK_MANAGER.name: True,
            SettingId.SETTING_NB_TASKS.name: 128,
        }

        my_query = ClashQuery(
            query_name="My Test Dup Query",
            object_a_path="/Root/STATION_TIME_SAMPLED",
            object_b_path="/Root/Xform_Primitives",
            clash_detect_settings=clash_detect_settings,
            comment="My comment"
        )
        new_id = self._clash_data.insert_query(my_query, True, True)
        self.assertTrue(new_id and new_id == 1)

        print("Setting up clash detection engine...")
        self.assertTrue(
            self._clash_detect.set_scope(
                stage,
                my_query.object_a_path,
                my_query.object_b_path,
                True
            )
        )
        self.assertTrue(self._clash_detect.set_settings(my_query.clash_detect_settings, stage))

        self._run_clash_detection(stage)

        print("Fetching...", end="")
        for _ in self._clash_detect.fetch_and_save_overlaps(stage, self._clash_data, my_query):
            print(".", end="")
        print("Finished.")

        saved_overlaps = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, False)
        print(f"Number of saved overlaps: {len(saved_overlaps)}")
        self.assertEqual(len(saved_overlaps), expected_num_dups)

        print("Re-fetching to test clash data updating...", end="")
        for _ in self._clash_detect.fetch_and_save_overlaps(stage, self._clash_data, my_query):
            print(".", end="")
        print("Finished.")

        saved_overlaps = self._clash_data.find_all_overlaps_by_query_id(my_query.identifier, False)
        print(f"Number of re-saved overlaps: {len(saved_overlaps)}")
        self.assertEqual(len(saved_overlaps), expected_num_dups)

        dup_clash_info = next(iter(saved_overlaps.values()))
        self.assertEqual(dup_clash_info.query_id, new_id)
        self.assertEqual(dup_clash_info.object_a_path, "/Root/Xform_Primitives/Cube_Dup1")
        self.assertEqual(dup_clash_info.object_b_path, "/Root/Xform_Primitives/Cube_Dup2")
        self.assertEqual(dup_clash_info.overlap_tris, 12)
        self.assertEqual(dup_clash_info.min_distance, 0.0)
        self.assertEqual(dup_clash_info.num_records, 1)
        self.assertEqual(dup_clash_info.max_local_depth, -1.0)

        print("Closing...")
        self._clash_data.close()
        self._stage_cleanup(stage)

    async def test_depth_queries(self):

        def check_hard_clash_depth(ci: ClashInfo):
            import math
            return ci.is_hard_clash and math.isclose(ci.max_local_depth, 0.3278431892395)

        results = await self._test_depth_query(0.05, False)
        self.assertEqual(len(results), 4)
        contact_count = sum(1 for result in results if result.is_contact)
        self.assertEqual(contact_count, 3)
        hard_count = sum(1 for result in results if check_hard_clash_depth(result))
        self.assertEqual(hard_count, 1)

        results = await self._test_depth_query(0.05, True)
        self.assertEqual(len(results), 1)
        contact_count = sum(1 for result in results if result.is_contact)
        self.assertEqual(contact_count, 0)
        hard_count = sum(1 for result in results if check_hard_clash_depth(result))
        self.assertEqual(hard_count, 1)

        results = await self._test_depth_query(-1, False)
        self.assertEqual(len(results), 4)
        contact_count = sum(1 for result in results if result.is_contact and result.max_local_depth == 0.0)
        self.assertEqual(contact_count, 1)
        hard_count = sum(1 for result in results if result.is_hard_clash)
        self.assertEqual(hard_count, 3)

    async def test_migration_to_latest(self):
        try:
            from omni.physxtests import utils
            omni_physxtests_utils_available = True
        except:
            omni_physxtests_utils_available = False
        print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")

        # open stage
        stage_path_name = self._test_data_dir + "static_clash_version_3-15-5.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)
        clash_data_path = self._clash_data.serializer_path
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "SqliteSerializer: Incompatible DB table",
                    "SQL Serializer Fatal Error: some or all tables are not compatible with current version of extension.",
                ],
                partial_string_match=True,
                expect_all=True,  # expect all of the above messages
            ):
                _ = self._clash_data.find_query(0)  # force clash data read access by calling this harmless query
        # check compatibility and possibility of migration
        self.assertFalse(self._clash_data.data_structures_compatible)
        self.assertTrue(self._clash_data.data_structures_migration_to_latest_version_possible)
        # migrate data structures to the latest version
        self._clash_data._serializer.open(clash_data_path)
        self.assertTrue(self._clash_data.migrate_data_structures_to_latest_version(clash_data_path))
        # save the migrated clash data
        self._clash_data._serializer.save()
        self._clash_data._serializer.close()

        self._clash_data._serializer.open(clash_data_path)
        self.assertTrue(self._clash_data.data_structures_compatible)
        # read some data and check some values
        queries = self._clash_data.fetch_all_queries()
        self.assertEqual(len(queries), 1)
        query = next(iter(queries.values()))
        overlaps = self._clash_data.find_all_overlaps_by_query_id(query.identifier, True)
        self.assertEqual(len(overlaps), 1)
        overlap = next(iter(overlaps.values()))
        self.assertEqual(overlap.object_a_path, "/World/Cube")
        self.assertEqual(overlap.object_b_path, "/World/Sphere")
        self.assertEqual(overlap.overlap_tris, 112)
        self.assertEqual(overlap.num_records, 1)
        self.assertEqual(overlap.min_distance, 0.0)
        self.assertEqual(overlap.max_local_depth, -1.0)
        self.assertEqual(overlap.penetration_depth_px, -1.0)
        self.assertEqual(overlap.penetration_depth_nx, -1.0)
        self.assertEqual(overlap.penetration_depth_py, -1.0)
        self.assertEqual(overlap.penetration_depth_ny, -1.0)
        self.assertEqual(overlap.penetration_depth_pz, -1.0)
        self.assertEqual(overlap.penetration_depth_nz, -1.0)
        # check also frame info
        frame_info = overlap.get_clash_frame_info(0)
        self.assertIsNotNone(frame_info)
        self.assertEqual(frame_info.timecode, 0)
        self.assertEqual(frame_info.min_distance, 0.0)
        self.assertEqual(frame_info.max_local_depth, -1)
        self.assertEqual(frame_info.overlap_tris, 112)
        self.assertEqual(frame_info.penetration_depth_px, -1.0)
        self.assertEqual(frame_info.penetration_depth_nx, -1.0)
        self.assertEqual(frame_info.penetration_depth_py, -1.0)
        self.assertEqual(frame_info.penetration_depth_ny, -1.0)
        self.assertEqual(frame_info.penetration_depth_pz, -1.0)
        self.assertEqual(frame_info.penetration_depth_nz, -1.0)
        # close clash data and stage
        self._clash_data.close()
        self._stage_cleanup(stage, False)

    async def test_migration_impossible(self):
        try:
            from omni.physxtests import utils
            omni_physxtests_utils_available = True
        except:
            omni_physxtests_utils_available = False
        print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")

        # open stage
        stage_path_name = self._test_data_dir + "unsupported_newer_data_version.usda"
        print(f"Opening stage '{stage_path_name}'...")
        stage = Usd.Stage.Open(stage_path_name)
        self.assertIsNotNone(stage)
        UsdUtils.StageCache.Get().Insert(stage)
        self._clash_data.open(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), False)
        clash_data_path = self._clash_data.serializer_path
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "SqliteSerializer: Incompatible DB table",
                    "SQL Serializer Fatal Error: some or all tables are not compatible with current version of extension.",
                    "SQL Serializer Fatal Error: migration of some or all tables to the latest version is not possible.",
                    "No migration path for table",
                ],
                partial_string_match=True,
                expect_all=True,  # expect all of the above messages
            ):
                _ = self._clash_data.find_query(0)  # force clash data read access by calling this harmless query
        # check compatibility and possibility of migration
        self.assertFalse(self._clash_data.data_structures_compatible)
        self.assertFalse(self._clash_data.data_structures_migration_to_latest_version_possible)
        # migrate data structures to the latest version
        self._clash_data._serializer.open(clash_data_path)
        self.assertFalse(self._clash_data.migrate_data_structures_to_latest_version(clash_data_path))
        # close clash data and stage
        self._clash_data.close()
        self._stage_cleanup(stage, False)
