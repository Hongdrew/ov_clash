# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.usd
import tempfile
import pathlib
import shutil
import carb
from datetime import datetime
from pxr import Sdf
from omni.kit.test import AsyncTestCase
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.utils import file_exists, get_random_word
from ..settings import ExtensionSettings


class TestSerialization(AsyncTestCase):
    REMOTE_PATH_SETTING = "/exts/omni.physx.clashdetection.ui/testRemoteUrl"

    def __init__(self, tests=()):
        super().__init__(tests)

    # Before running each test
    def setUp(self):
        super().setUp()
        self._clash_data = ExtensionSettings.clash_data

    def tearDown(self):
        self._clash_data = None
        super().tearDown()

    @staticmethod
    async def wait(frames: int = 1):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    @classmethod
    async def wait_for_events_processed(cls):
        await cls.wait(2)

    def _get_layer_db_path(self, layer: Sdf.Layer):
        self.assertIsNotNone(layer)
        metadata = layer.customLayerData
        self.assertIsNotNone(metadata, f"Layer '{layer.identifier}' has empty customLayerData!")
        self.assertIsNotNone(self._clash_data)
        db_path = metadata.get(self._clash_data.CLASH_DATA_LAYER_CUSTOM_CLASH_DB_PATH)
        self.assertTrue(db_path)
        return db_path

    @staticmethod
    def _replace_file_ext(file_path_name: str, new_extension: str):
        import os
        file_path_name_no_ext, _ = os.path.splitext(file_path_name)
        return file_path_name_no_ext + new_extension

    def _delete_file(self, file_path_name: str):
        print(f"Deleting '{file_path_name}'...")
        oc_res = omni.client.delete(file_path_name)
        self.assertTrue(oc_res == omni.client.Result.OK or oc_res == omni.client.Result.ERROR_NOT_FOUND)

    async def test_stage_serialization(self):

        async def run_tests(save_stage1_path_name: str, save_stage2_path_name: str) -> bool:
            print("Creating new empty stage...")
            query1_comment = get_random_word(10)
            query2_comment = get_random_word(16)
            query3_comment = get_random_word(20)
            db_paths = set()
            usd_context = omni.usd.get_context(ExtensionSettings.usd_context_name)
            (result, err) = await usd_context.new_stage_async()
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)

            print("Creating new query...")
            new_query = ClashQuery(query_name="My Test Query", comment=query1_comment)
            new_id = self._clash_data.insert_query(new_query, True, True)
            self.assertTrue(new_id and new_id == 1)
            await self.wait_for_events_processed()

            # at this point (DB write operation was executed), new anonymous clash detection layer should have been created
            clash_anonymous_layer = self._clash_data._target_layer
            self.assertTrue(clash_anonymous_layer)
            db_path_anon = self._get_layer_db_path(clash_anonymous_layer)
            db_paths.add(db_path_anon)

            # save as
            print(f"Testing Save as #1 to {save_stage1_path_name}...")
            await usd_context.save_as_stage_async(save_stage1_path_name)
            await self.wait_for_events_processed()
            # Save as from perf reasons does not unload, old layer still hangs in memory.
            # New layer should use db previously used by the anonymous layer
            # In this case, CLOSED stage event is fired. Anonymous layer can never be used again because of it's random part of its identifier
            clash_layer1 = self._clash_data._target_layer
            db_path_anon_new = self._get_layer_db_path(clash_anonymous_layer)
            db_path_clash_layer1 = self._get_layer_db_path(clash_layer1)
            del clash_anonymous_layer
            self.assertTrue(db_path_anon == db_path_clash_layer1)
            self.assertTrue(db_path_anon_new == db_path_clash_layer1)  # cannot be reloaded so db path hasn't changed
            db_paths.add(db_path_anon_new)
            db_paths.add(db_path_clash_layer1)
            del db_path_anon
            del db_path_anon_new

            # save as #2 (we need to test save as 2x as now we are not saving anonymous layer but file based layer)
            print(f"Testing Save as #2 to {save_stage2_path_name}...")
            await usd_context.save_as_stage_async(save_stage2_path_name)
            await self.wait_for_events_processed()
            # Save as from perf reasons does not unload, old layer still hangs in memory.
            # New layer should use db previously used by the previous layer
            clash_layer2 = self._clash_data._target_layer
            db_path_clash_layer1_new = self._get_layer_db_path(clash_layer1)
            db_path_clash_layer2 = self._get_layer_db_path(clash_layer2)
            self.assertEqual(db_path_clash_layer1, db_path_clash_layer2)
            db_paths.add(db_path_clash_layer1_new)
            db_paths.add(db_path_clash_layer2)
            del db_path_clash_layer1
            del db_path_clash_layer1_new
            del db_path_clash_layer2

            print("Testing Save...")
            # normal save
            clash_layer1_identifier = clash_layer1.identifier
            clash_layer2_identifier = clash_layer2.identifier
            del clash_layer1
            del clash_layer2
            # add a new query
            new_query = ClashQuery(query_name="My Test Query New", comment=query2_comment)
            new_id = self._clash_data.insert_query(new_query, True, True)
            self.assertTrue(new_id and new_id == 2)
            await self.wait_for_events_processed()
            await usd_context.save_stage_async()
            await self.wait_for_events_processed()

            print("Testing New...")
            # New stage
            (result, err) = await usd_context.new_stage_async()
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)
            await self.wait_for_events_processed()
            # We need to make sure that loaded clash data layers are unloaded. Otherwise they would get re-used (without loading)
            self.assertIsNone(Sdf.Layer.Find(clash_layer1_identifier))
            self.assertIsNone(Sdf.Layer.Find(clash_layer2_identifier))
            # New stage triggers unload of all layers, check if all DBs were also deleted
            for path_name in db_paths:
                self.assertTrue(not file_exists(path_name))

            print(f"Testing Open #1 from {save_stage1_path_name}...")
            # open stage
            (result, err) = await usd_context.open_stage_async(save_stage1_path_name)
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)
            await self.wait_for_events_processed()
            clash_layer = self._clash_data._target_layer
            db_path_clash_layer = self._get_layer_db_path(clash_layer)
            db_paths.add(db_path_clash_layer)
            del clash_layer
            queries = self._clash_data.fetch_all_queries()
            self.assertEqual(len(queries), 1)
            queries = [q for q in queries.values()]
            self.assertEqual(queries[0].comment, query1_comment)  # validate that we loaded data that we expected

            print(f"Testing Open #2 from {save_stage2_path_name}...")
            # open stage
            (result, err) = await usd_context.open_stage_async(save_stage2_path_name)
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)
            await self.wait_for_events_processed()
            clash_layer = self._clash_data._target_layer
            db_path_clash_layer = self._get_layer_db_path(clash_layer)
            db_paths.add(db_path_clash_layer)
            clash_layer_identifier = clash_layer.identifier
            del clash_layer
            queries = self._clash_data.fetch_all_queries()
            self.assertEqual(len(queries), 2)
            queries = [q for q in queries.values()]
            self.assertEqual(queries[0].comment, query1_comment)  # validate that we loaded data that we expected
            self.assertEqual(queries[1].comment, query2_comment)  # validate that we loaded data that we expected

            print(f"Testing Save as #3 with overwrite to {save_stage1_path_name}...")
            # add a new query
            new_query = ClashQuery(query_name="My Final Test Query", comment=query3_comment)
            new_id = self._clash_data.insert_query(new_query, True, True)
            self.assertTrue(new_id and new_id == 3)
            await usd_context.save_as_stage_async(save_stage1_path_name)
            await self.wait_for_events_processed()
            # Save as from perf reasons does not unload, old layer still hangs in memory.
            # New layer should use db previously used by the previous layer
            clash_layer3 = self._clash_data._target_layer
            db_path_clash_layer3 = self._get_layer_db_path(clash_layer3)
            self.assertEqual(db_path_clash_layer, db_path_clash_layer3)
            clash_layer = Sdf.Layer.Find(clash_layer_identifier)
            if clash_layer:
                db_path_clash_layer = self._get_layer_db_path(clash_layer)
                self.assertNotEqual(db_path_clash_layer, db_path_clash_layer3)
                db_paths.add(db_path_clash_layer)
            db_paths.add(db_path_clash_layer3)
            del clash_layer
            del clash_layer3
            del db_path_clash_layer3

            print(f"Testing Open #3 from {save_stage1_path_name}...")
            # open stage
            (result, err) = await usd_context.new_stage_async()  # clear the stage of cached layers
            (result, err) = await usd_context.open_stage_async(save_stage1_path_name)
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)
            await self.wait_for_events_processed()
            clash_layer = self._clash_data._target_layer
            db_path_clash_layer = self._get_layer_db_path(clash_layer)
            db_paths.add(db_path_clash_layer)
            del clash_layer
            queries = self._clash_data.fetch_all_queries()
            self.assertEqual(len(queries), 3)
            queries = [q for q in queries.values()]
            self.assertEqual(queries[0].comment, query1_comment)  # validate that we loaded data that we expected
            self.assertEqual(queries[1].comment, query2_comment)  # validate that we loaded data that we expected
            self.assertEqual(queries[2].comment, query3_comment)  # validate that we loaded data that we expected

            print("Testing Reload...")
            # check the data - clash should contain 3 queries
            (result, err) = await usd_context.reopen_stage_async()
            self.assertTrue(result)
            stage = usd_context.get_stage()
            self.assertIsNotNone(stage)
            await self.wait_for_events_processed()
            queries = self._clash_data.fetch_all_queries()
            self.assertEqual(len(queries), 3)
            queries = [q for q in queries.values()]
            self.assertEqual(queries[0].comment, query1_comment)  # validate that we loaded data that we expected
            self.assertEqual(queries[1].comment, query2_comment)  # validate that we loaded data that we expected
            self.assertEqual(queries[2].comment, query3_comment)  # validate that we loaded data that we expected

            print("Testing Close...")
            await usd_context.close_stage_async()
            (result, err) = await usd_context.new_stage_async()
            await self.wait_for_events_processed()
            # check if all DB temp files were removed
            for path_name in db_paths:
                self.assertTrue(not file_exists(path_name))

            return True

        async def safe_run_tests(path1, path2):
            try:
                self.assertTrue(await run_tests(path1, path2))
            except Exception as e:
                print(f"TEST FAILED: Exception occurred: {e}")
                raise e
            finally:
                # delete usda and clashDetection companion files
                self._delete_file(path1)
                self._delete_file(self._replace_file_ext(path1, self._clash_data.CLASH_DATA_LAYER_FILE_EXT))
                self._delete_file(path2)
                self._delete_file(self._replace_file_ext(path2, self._clash_data.CLASH_DATA_LAYER_FILE_EXT))

        # init
        temp_dir_path = tempfile.TemporaryDirectory().name
        stage1_path = str(pathlib.Path(temp_dir_path).joinpath("test_clash_detect_serialization1.usda"))
        stage2_path = str(pathlib.Path(temp_dir_path).joinpath("test_clash_detect_serialization2.usda"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # RUN LOCAL TESTS
        await safe_run_tests(stage1_path, stage2_path)

        # RUN REMOTE TESTS
        remote_path = carb.settings.get_settings().get_as_string(self.REMOTE_PATH_SETTING)
        if remote_path:
            print(f"Remote test path is set to: '{remote_path}'")
            stage1_remote_path = f"{remote_path}{timestamp}_{get_random_word(4)}_test_clash_detect_serialization1.usda"
            stage2_remote_path = f"{remote_path}{timestamp}_{get_random_word(4)}_test_clash_detect_serialization2.usda"
            await safe_run_tests(stage1_remote_path, stage2_remote_path)  # Nucleus/s3 tests
        else:
            print("Remote test path is not set, skipping remote tests.")

        # cleanup
        print(f"Deleting folder '{temp_dir_path}' with subfolders...")
        shutil.rmtree(temp_dir_path, ignore_errors=True)

    def test_string_interning(self):
        """ Test that most common strings are interned (means reused - saves RAM). """
        from omni.physxclashdetectionui.utils import get_yes_no_str, get_time_delta_str
        from omni.physxclashdetectionui.clash_priority_viewmodel import ClashPriorityStr
        # check that Yes No strings are interned
        yes_id = id(get_yes_no_str(True))
        self.assertEqual(yes_id, id(get_yes_no_str(True)))
        no_id = id(get_yes_no_str(False))
        self.assertEqual(no_id, id(get_yes_no_str(False)))
        self.assertNotEqual(yes_id, no_id)
        # check that time delta strings are interned
        delta_id = id(get_time_delta_str(0))
        self.assertEqual(delta_id, id(get_time_delta_str(0)))
        self.assertNotEqual(delta_id, id(get_time_delta_str(1001)))
        # check that most common clash priority strings are interned
        priority_high_id = id(ClashPriorityStr.get_priority_str(5))
        self.assertEqual(priority_high_id, id(ClashPriorityStr.get_priority_str(5)))
        priority_medium_id = id(ClashPriorityStr.get_priority_str(3))
        self.assertEqual(priority_medium_id, id(ClashPriorityStr.get_priority_str(3)))
        self.assertNotEqual(priority_high_id, priority_medium_id)
        priority_low_id = id(ClashPriorityStr.get_priority_str(1))
        self.assertEqual(priority_low_id, id(ClashPriorityStr.get_priority_str(1)))
        self.assertNotEqual(priority_low_id, priority_medium_id)
        # check that unassigned person full name strings are interned
        self._pic = ExtensionSettings.users.get_person("")
        pic_id = id(self._pic.full_name)
        self.assertEqual(pic_id, id(self._pic.full_name))
