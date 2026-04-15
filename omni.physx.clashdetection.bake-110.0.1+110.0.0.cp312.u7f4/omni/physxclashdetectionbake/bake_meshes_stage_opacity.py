# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pxr import UsdGeom, UsdShade, Sdf, Usd
import numpy as np
import numpy.typing as npt

from .bake_utilities import ClashBakeUtils
from .bake_options import ClashBakeOptions
from .bake_globals import ClashInfo


class ClashBakeMeshesStageOpacity:
    """
    This class is used to hide the clashing faces of the no-clash mesh.
    It uses the display opacity primvar to hide the clashing faces.
    It also generates the inverse mesh for the do-clash mesh.
    """

    @staticmethod
    def hide_clashing_faces_opacity(
        stage: Usd.Stage, options: ClashBakeOptions, clash_info: ClashInfo, no_clash_mesh: UsdGeom.Mesh, first: bool
    ):
        # This code was originally using indexed primvars but it was causing issues with references to instanced prims
        # very likely due to a bug in USD itself, so it has been changed to write display opacity directly.
        index = 0 if first else 1
        prim = no_clash_mesh.GetPrim()

        # Flat shaded look
        no_clash_mesh.CreateSubdivisionSchemeAttr("bilinear")

        binding = UsdShade.MaterialBindingAPI.Apply(prim)
        rel = binding.GetPrim().CreateRelationship("material:binding", False)
        rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectPerFaceSolid{index}")])

        if not clash_info.clash_frame_info_items:
            return
        if not options.generate_clash_polygons:
            return
        tcps = stage.GetTimeCodesPerSecond()
        number_of_faces = len(no_clash_mesh.GetFaceVertexCountsAttr().Get())
        no_clash_opacities: UsdGeom.Primvar = no_clash_mesh.CreateDisplayOpacityPrimvar(interpolation="uniform")  # type: ignore

        collected_opacities: list[tuple[Usd.TimeCode, npt.NDArray]] = []
        first_timecode = ClashBakeUtils.get_frame_time_code(time=0, fps=tcps)
        last_frame = clash_info.clash_frame_info_items[-1]
        last_timecode = ClashBakeUtils.get_frame_time_code(time=last_frame.timecode + 0.1, fps=tcps)
        first_timecode_written = False
        last_timecode_written = False
        static_clash = len(clash_info.clash_frame_info_items) == 1
        np_usd_faces_prev = np.array([])

        for cfi in clash_info.clash_frame_info_items:
            timecode = ClashBakeUtils.get_frame_time_code(time=cfi.timecode, fps=tcps)
            faces = cfi.usd_faces_0 if first else cfi.usd_faces_1

            np_usd_faces = faces.numpy()

            # Skip this timesample if its content are the same as previous one
            if len(np_usd_faces) == len(np_usd_faces_prev) and (np_usd_faces == np_usd_faces_prev).all():
                continue
            # Remember previous faces to check if we can skip some of the next timesamples
            np_usd_faces_prev = np_usd_faces

            # Create an array of 1.0s (fully opaque) and set clashing faces to 0.0 (fully transparent)
            np_opacities = np.ones(number_of_faces, dtype=float)
            np_opacities[np_usd_faces] = 0.0

            collected_opacities.append((timecode, np_opacities))

        # Write all opacities
        for timecode, np_opacities in collected_opacities:
            if timecode == first_timecode:
                first_timecode_written = True
            if timecode == last_timecode:
                last_timecode_written = True
            if static_clash:
                no_clash_opacities.Set(np_opacities)
            else:
                no_clash_opacities.Set(np_opacities, timecode)

        if not static_clash:
            # Write first frame to reset
            if not first_timecode_written:
                no_clash_opacities.Set(np.ones(number_of_faces, dtype=float), first_timecode)

            # Write last frame to reset
            if not last_timecode_written:
                no_clash_opacities.Set(np.ones(number_of_faces, dtype=float), last_timecode)

    @staticmethod
    def bake_inverse_mesh_opacity(
        stage: Usd.Stage, options: ClashBakeOptions, src_path: str, dst_path: str, first: bool
    ):
        index = "0" if first else "1"
        inverted_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(stage, dst_path)
        prim: Usd.Prim = inverted_mesh.GetPrim()
        prim.GetReferences().AddReference("", src_path)
        src_mesh = UsdGeom.Mesh(stage.GetPrimAtPath(src_path))
        src_indices = src_mesh.GetDisplayOpacityPrimvar().GetIndicesAttr()
        with Sdf.ChangeBlock():
            prim = inverted_mesh.GetPrim()
            binding = UsdShade.MaterialBindingAPI.Apply(prim)
            rel = binding.GetPrim().CreateRelationship("material:binding", False)
            rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectEmissiveTwoSided{index}")])
            if not options.generate_clash_polygons:
                return
            inverted_opacities = inverted_mesh.CreateDisplayOpacityPrimvar(interpolation="uniform")  # type: ignore
            inverted_opacities.Set(value=[0, 1], time=Usd.TimeCode.Default())  # 0 == visible, 1 == invisible
            inverted_indices = inverted_opacities.CreateIndicesAttr()
            timesamples = src_indices.GetTimeSamples()  # type: ignore
            if len(timesamples) > 0:
                # Dynamic Clash
                for timecode in timesamples:
                    inverted_indices.Set(src_indices.Get(timecode), timecode)
            else:
                # Static Clash
                inverted_indices.Set(src_indices.Get(), time=Usd.TimeCode.Default())
