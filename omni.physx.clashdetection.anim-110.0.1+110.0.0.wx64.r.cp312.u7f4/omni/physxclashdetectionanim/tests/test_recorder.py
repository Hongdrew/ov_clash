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
import os
import tempfile
import pathlib
import shutil
import inspect
import carb
from pxr import Usd, Sdf, UsdUtils
import omni.usd
from omni.kit.test import AsyncTestCase
from omni.schemaclashdetection.bindings._usdUtils import sdfPathToInt
from omni.physxclashdetectionanim.scripts.anim_recorder import AnimRecorder
from omni.physxclashdetectionanim.scripts.utils import safe_delete_file, measure_execution_time, compare_text_files
from omni.physxclashdetectionanim.scripts.config import ExtensionConfig
from omni.physxclashdetectionanim.bindings._clashDetectionAnim import SETTINGS_LOGGING_ENABLED


class RecorderTest(AsyncTestCase):
    TEST_SCENE_TRANSLATE = "curve_anim_test_scene1.usda"
    TEST_SCENE_TRANSLATE_ROT_SCALE = "curve_anim_test_scene2.usda"
    RECORDED_PREFIX = "curve_anim_recorded_"

    def __init__(self, tests=()):
        super().__init__(tests)
        test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
        self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'
        self._debug_logging_orig_val = ExtensionConfig.debug_logging
        self._settings = carb.settings.get_settings()

    # Before running each test
    def setUp(self):
        super().setUp()
        self._temp_dir_path = tempfile.TemporaryDirectory().name
        self._debug_logging_orig_val = ExtensionConfig.debug_logging
        self._settings.set_bool(SETTINGS_LOGGING_ENABLED, True)
        self._anim_recorder = AnimRecorder()

    def tearDown(self):
        if self._anim_recorder:
            self._anim_recorder.destroy()
            self._anim_recorder = None
        if self._temp_dir_path:
            print(f"Deleting temp folder '{self._temp_dir_path}' with subfolders...")
            shutil.rmtree(self._temp_dir_path, ignore_errors=True)
        self._settings.set_bool(SETTINGS_LOGGING_ENABLED, self._debug_logging_orig_val)
        super().tearDown()

    async def wait(self, frames=1):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    def _sdf_paths_to_int_paths(self, prim_paths: List[Sdf.Path]) -> List[int]:
        return [sdfPathToInt(path) for path in prim_paths]

    async def _open_test_stage(self, stage_name) -> Usd.Stage:
        if not omni.usd.get_context():
            self.fail("omni.usd.get_context() is None")
        stage_path_name = str(pathlib.Path(self._test_data_dir).joinpath(stage_name))
        print(f"Opening stage '{stage_path_name}'...")
        # animation seems to require kit to function so we cannot use plain USD
        # stage = Usd.Stage.Open(stage_path_name)
        # self.assertIsNotNone(stage)
        # UsdUtils.StageCache.Get().Insert(stage)
        await omni.usd.get_context().open_stage_async(stage_path_name)
        return omni.usd.get_context().get_stage()

    async def _close_stage(self, stage):
        # animation seems to require kit to function so we cannot use plain USD
        # UsdUtils.StageCache.Get().Erase(stage)
        if not omni.usd.get_context():
            self.fail("omni.usd.get_context() is None")
        self.assertEqual(omni.usd.get_context().get_stage(), stage)
        await omni.usd.get_context().close_stage_async()

    @measure_execution_time
    def _record_save_compare(
        self,
        target_file_name: str,
        golden_file_name: str,
        stage: Usd.Stage,
        prims_int_path: List[int],
        start_time: float,
        end_time: float,
        codes_per_second: float
    ):
        if not self._anim_recorder:
            self.fail("self._anim_recorder is None")

        target_path = str(pathlib.Path(self._temp_dir_path).joinpath(target_file_name))
        print(f"Recording from time {start_time} to {end_time} into session layer:")

        for _ in self._anim_recorder.run(
            stage,
            prims_int_path,
            start_time,
            end_time,
            codes_per_second
        ):
            print(".", end='')
        print("Done.")

        recording_session_layer_name = self._anim_recorder.get_recording_session_layer_name()
        print(f"Finished recording to '{recording_session_layer_name}'.")
        self.assertTrue(recording_session_layer_name is not None and recording_session_layer_name != "")

        print(f"Exporting session layer '{recording_session_layer_name}' to '{target_path}'...")
        recording_layer = Sdf.Layer.Find(recording_session_layer_name)
        self.assertIsNotNone(recording_layer)
        ret = recording_layer.Export(target_path)
        self.assertTrue(ret is True)

        golden_path = str(pathlib.Path(self._test_data_dir).joinpath(golden_file_name))
        print(f"Comparing '{target_path}' with golden '{golden_path}'...")
        differences = compare_text_files(target_path, golden_path, ignore_order=True)
        print(f"Differences against golden recorded file: {differences}")
        self.assertTrue(len(differences) == 0)

        print(f"Deleting '{target_path}'...")
        safe_delete_file(target_path)

    async def test_basic_entire_timeline(self):
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        fps = stage.GetTimeCodesPerSecond()
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([
                Sdf.Path("/World/fix"), Sdf.Path("/World/fix/Cube"), Sdf.Path("/World/fix/Cube_01"),
                Sdf.Path("/World/fix/Cube_02"), Sdf.Path("/World/animated/Cube")
            ]),
            stage.GetStartTimeCode() / fps,
            stage.GetEndTimeCode() / fps,
            fps
        )
        await self._close_stage(stage)

    async def test_basic_limited_timeline(self):
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([Sdf.Path("/World/fix/Cube_01"), Sdf.Path("/World/animated/Cube")]),
            0.33,
            0.77,
            stage.GetTimeCodesPerSecond()
        )
        await self._close_stage(stage)

    async def test_basic_beyond_timeline(self):
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([Sdf.Path("/World/fix/Cube_01"), Sdf.Path("/World/animated/Cube")]),
            1.5,
            2.0,  # value exceeding the timeline's end
            stage.GetTimeCodesPerSecond()
        )
        await self._close_stage(stage)

    async def test_advanced_entire_timeline(self):
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE_ROT_SCALE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        fps = stage.GetTimeCodesPerSecond()
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([
                Sdf.Path("/World"), Sdf.Path("/World/Cylinder"), Sdf.Path("/World/Cone"), Sdf.Path("/World/Disk"),
                Sdf.Path("/World/PushGraph"),
                Sdf.Path("/World/PushGraph/Cube_01CurveNode"), Sdf.Path("/World/PushGraph/CylinderCurveNode"),
                Sdf.Path("/World/PushGraph/ConeCurveNode"), Sdf.Path("/World/PushGraph/CubeCurveNode"),
                Sdf.Path("/World/Looks"), Sdf.Path("/World/Looks/PreviewSurface"),
                Sdf.Path("/World/Looks/PreviewSurface/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_01"), Sdf.Path("/World/Looks/PreviewSurface_01/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_02"), Sdf.Path("/World/Looks/PreviewSurface_02/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_03"), Sdf.Path("/World/Looks/PreviewSurface_03/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_04"), Sdf.Path("/World/Looks/PreviewSurface_04/Shader"),
                Sdf.Path("/World/Cube_Top"), Sdf.Path("/World/Cube_Side")
            ]),
            stage.GetStartTimeCode() / fps,
            stage.GetEndTimeCode() / fps,
            fps
        )
        await self._close_stage(stage)

    async def test_advanced_limited_timeline(self):
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE_ROT_SCALE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([
                Sdf.Path("/World"), Sdf.Path("/World/Cylinder"), Sdf.Path("/World/Cone"), Sdf.Path("/World/Disk"),
                Sdf.Path("/World/PushGraph"),
                Sdf.Path("/World/PushGraph/Cube_01CurveNode"), Sdf.Path("/World/PushGraph/CylinderCurveNode"),
                Sdf.Path("/World/PushGraph/ConeCurveNode"), Sdf.Path("/World/PushGraph/CubeCurveNode"),
                Sdf.Path("/World/Looks"), Sdf.Path("/World/Looks/PreviewSurface"),
                Sdf.Path("/World/Looks/PreviewSurface/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_01"), Sdf.Path("/World/Looks/PreviewSurface_01/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_02"), Sdf.Path("/World/Looks/PreviewSurface_02/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_03"), Sdf.Path("/World/Looks/PreviewSurface_03/Shader"),
                Sdf.Path("/World/Looks/PreviewSurface_04"), Sdf.Path("/World/Looks/PreviewSurface_04/Shader"),
                Sdf.Path("/World/Cube_Top"), Sdf.Path("/World/Cube_Side")
            ]),
            0.33,
            0.77,
            stage.GetTimeCodesPerSecond()
        )
        await self._close_stage(stage)

    async def test_advanced_limited_timeline_copy_also_unrecorded_attribs(self):
        if not self._anim_recorder:
            self.fail("self._anim_recorder is None")
        copy_attribs_bak = self._anim_recorder.copy_also_unrecorded_usd_attribs_on_save
        self._anim_recorder.copy_also_unrecorded_usd_attribs_on_save = True
        stage = await self._open_test_stage(self.TEST_SCENE_TRANSLATE_ROT_SCALE)
        self.assertIsNotNone(stage)
        recording_name = RecorderTest.RECORDED_PREFIX + inspect.currentframe().f_code.co_name + ".usda"
        self._record_save_compare(
            recording_name,
            recording_name,
            stage,
            self._sdf_paths_to_int_paths([Sdf.Path("/World/Cube_Top"), Sdf.Path("/World/Cube_Side")]),
            0.33,
            1.17,
            stage.GetTimeCodesPerSecond()
        )
        await self._close_stage(stage)
        self._anim_recorder.copy_also_unrecorded_usd_attribs_on_save = copy_attribs_bak
