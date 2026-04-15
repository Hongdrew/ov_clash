# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.app
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from .clash_detect_bench_test_case import ClashDetectionBenchmarkTestCase, ClashBakeBenchmarkParameters, ClashViewportBenchmarkParameters


class ClashDetectionBenchmarkBase(ClashDetectionBenchmarkTestCase):

    async def benchmark_clash_detection_collection(self):
        await self._run_perf_benchmark(
            stage_name="time_sampled.usda",
            expected_num_results=11,
            expected_total_frames=3922,
            expected_total_overlapping_tris=6170043,
            object_a_path="/Root/Utils.collection:StationCollection /Root/Xform_Primitives/Plane",
            object_b_path="/Root/Xform_Primitives /Root/STATION_TIME_SAMPLED/STATION/SKID/lnk/Mesh2",
            dynamic=True,
            start_time=0.0,
            end_time=0.0,
            tolerance=3.0,
            compute_max_local_depth=True,
            max_local_depth_mode=2,
            max_local_depth_epsilon=1.1,
            purge_permanent_static_overlaps=False,
            perform_bake=ClashBakeBenchmarkParameters(),
            perform_viewport=ClashViewportBenchmarkParameters(), # Sweep all clashes
        )

    async def benchmark_clash_detection_curve_anim(self):
        await self._run_perf_benchmark(
            stage_name="clash_perf.usda",
            expected_num_results=21,
            expected_total_frames=36207,
            expected_total_overlapping_tris=843373,
            object_a_path="",
            object_b_path="",
            dynamic=True,
            start_time=0.0,
            end_time=0.0,
            tolerance=0.0,
            purge_permanent_static_overlaps=False,
            perform_bake=ClashBakeBenchmarkParameters(
                measure_runtime=True,
                measure_runtime_start=0.0,
                measure_runtime_end=10.0,
            ),
            perform_viewport=ClashViewportBenchmarkParameters(), # Sweep all clashes
        )

    async def test_benchmark_clash_detection_collection(self):
        await self.benchmark_clash_detection_collection()

    async def test_benchmark_clash_detection_curve_anim(self):
        await self.benchmark_clash_detection_curve_anim()