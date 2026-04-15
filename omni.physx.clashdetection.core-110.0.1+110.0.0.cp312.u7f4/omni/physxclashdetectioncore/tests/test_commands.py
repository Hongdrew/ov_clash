# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import os
import omni.kit.commands
from omni.kit.test import AsyncTestCase
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry
from pxr import UsdUtils
from omni.physxtests import utils as test_utils


class CommandsTest(AsyncTestCase):

    def __init__(self, tests=()):
        super().__init__(tests)
        test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
        self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'

    # Before running each test
    def setUp(self):
        super().setUp()
        self._clash_telemetry_logging_orig_val = ClashTelemetry.debug_logging
        ClashTelemetry.debug_logging = True

    def tearDown(self):
        ClashTelemetry.debug_logging = self._clash_telemetry_logging_orig_val
        super().tearDown()

    def test_run_clash_detection_cmd(self):
        stage_path_name = test_utils.TmpFileFromSrc(
            src_directory=self._test_data_dir,
            src_filename="time_sampled.usda",
            tmp_filename="_time_sampled.usda",
            random_prefix=True
        ).get_path()

        export_path_name = test_utils.TmpFile(
            tmp_filename="_test_run_clash_detection_cmd",
        ).get_path()

        open_cmd_name = "OpenStageForClashDetectionCommand"
        cmd_res, stage_id = omni.kit.commands.execute(
            open_cmd_name,
            path=stage_path_name,
        )
        self.assertTrue(cmd_res)
        self.assertNotEqual(stage_id, 0)

        run_cmd_name = "RunClashDetectionCommand"
        print(f"Executing '{run_cmd_name}'...")
        cmd_res, out_stage_id = omni.kit.commands.execute(
            run_cmd_name,
            stage_id=stage_id,
            object_a_path="/Root/STATION_TIME_SAMPLED",
            object_b_path="/Root/Xform_Primitives",
            tolerance=5,
            dynamic=True,
            start_time=5,
            end_time=10,
            logging=False,
            html_path_name=f"{export_path_name}.html",
            json_path_name=f"{export_path_name}.json",
            query_name="My RunClashDetectionCommand Query",
            comment="My RunClashDetectionCommand comment"
        )
        self.assertTrue(cmd_res)
        self.assertEqual(stage_id, out_stage_id)

        print(f"Executing '{run_cmd_name}' undo...")
        omni.kit.undo.undo()

        print(f"Executing '{run_cmd_name}' redo...")
        omni.kit.undo.redo()

        print(f"Executing '{run_cmd_name}' undo...")
        omni.kit.undo.undo()

        # undo the stage open command
        print(f"Executing '{open_cmd_name}' undo...")
        omni.kit.undo.undo()

        # make sure the stage that was opened is now closed after undoing the command
        stage_cache = UsdUtils.StageCache.Get()
        stages = stage_cache.GetAllStages()
        for stage in stages:
            found_stage_id = stage_cache.GetId(stage).ToLongInt()
            self.assertNotEqual(found_stage_id, stage_id)

        open_cmd_name = "OpenStageForClashDetectionCommand"
        cmd_res, stage_id = omni.kit.commands.execute(
            open_cmd_name,
            path=stage_path_name,
        )
        self.assertTrue(cmd_res)
        self.assertNotEqual(stage_id, 0)

        save_cmd_name = "SaveClashDetectionCommand"
        cmd_res, stage_id = omni.kit.commands.execute(
            save_cmd_name,
            stage_id=stage_id
        )
        self.assertTrue(cmd_res)
        self.assertNotEqual(stage_id, 0)

        close_cmd_name = "CloseStageForClashDetectionCommand"
        cmd_res, closed = omni.kit.commands.execute(
            close_cmd_name,
            stage_id=stage_id
        )
        self.assertTrue(cmd_res)
        self.assertEqual(closed, True)
