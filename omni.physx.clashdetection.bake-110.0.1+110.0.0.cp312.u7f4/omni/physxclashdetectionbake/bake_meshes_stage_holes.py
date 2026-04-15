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


class ClashBakeMeshesStageHoles:
    """
    This class is used to hide the clashing faces of the no-clash mesh.
    It uses the hole indices primvar to hide the clashing faces.
    It also generates the inverse mesh for the do-clash mesh.
    """

    @staticmethod
    def hide_clashing_faces_holes(
        stage: Usd.Stage, options: ClashBakeOptions, clash_info: ClashInfo, no_clash_mesh: UsdGeom.Mesh, first: bool
    ):
        index = 0 if first else 1
        prim = no_clash_mesh.GetPrim()

        # Flat shaded look
        no_clash_mesh.CreateSubdivisionSchemeAttr("bilinear")

        binding = UsdShade.MaterialBindingAPI.Apply(prim)
        rel = binding.GetPrim().CreateRelationship("material:binding", False)
        rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectSolid{index}")])

        if not clash_info.clash_frame_info_items:
            return
        if not options.generate_clash_polygons:
            return
        tcps = stage.GetTimeCodesPerSecond()
        number_of_faces = len(no_clash_mesh.GetFaceVertexCountsAttr().Get())
        no_clash_holes = no_clash_mesh.CreateHoleIndicesAttr()  # type: ignore

        collected_faces: list[tuple[Usd.TimeCode, npt.NDArray]] = []

        # Collect and merge all faces
        first_timecode = ClashBakeUtils.get_frame_time_code(time=0, fps=tcps)
        last_frame = clash_info.clash_frame_info_items[-1]
        last_timecode = ClashBakeUtils.get_frame_time_code(time=last_frame.timecode + 0.1, fps=tcps)
        first_timecode_written = False
        last_timecode_written = False
        static_clash = len(clash_info.clash_frame_info_items) == 1
        np_existing_holes_prev = np.array([])
        np_usd_faces_prev = np.array([])

        for cfi in clash_info.clash_frame_info_items:
            timecode = ClashBakeUtils.get_frame_time_code(time=cfi.timecode, fps=tcps)
            faces = cfi.usd_faces_0 if first else cfi.usd_faces_1

            np_usd_faces = faces.numpy()
            np_existing_holes = np.array(no_clash_holes.Get(timecode))

            # Skip this timesample if its content are the same as previous one
            if len(np_usd_faces) == len(np_usd_faces_prev) and len(np_existing_holes) == len(np_existing_holes_prev):
                if (np_usd_faces == np_usd_faces_prev).all() and (np_existing_holes == np_existing_holes_prev).all():
                    continue
            # Remember previous faces to check if we can skip some of the next timesamples
            np_usd_faces_prev = np_usd_faces
            np_existing_holes_prev = np_existing_holes

            if len(np_existing_holes):
                # If we have existing holes, we concatenate with the clash faces to keep them hidden
                # We have to get unique faces (that are sorted) as well because otherwise renderer
                # will not pick them up properly (RTX bug or USD Spec?)
                np_faces_to_hide = np.unique(np.concatenate((np_usd_faces, np_existing_holes)))
            else:
                np_faces_to_hide = np_usd_faces

            collected_faces.append((timecode, np_faces_to_hide))

        # Write all faces
        for timecode, np_faces_to_hide in collected_faces:
            if timecode == first_timecode:
                first_timecode_written = True
            if timecode == last_timecode:
                last_timecode_written = True
            if len(np_faces_to_hide) < number_of_faces:
                if static_clash:
                    no_clash_holes.Set(np_faces_to_hide)
                else:
                    no_clash_holes.Set(np_faces_to_hide, timecode)

        if not static_clash:
            # Write first frame to reset
            if not first_timecode_written:
                no_clash_holes.Set([], first_timecode)

            # Write last frame to reset
            if not last_timecode_written:
                no_clash_holes.Set([], last_timecode)

    @staticmethod
    def bake_inverse_mesh_holes(stage: Usd.Stage, options: ClashBakeOptions, src_path: str, dst_path: str, first: bool):
        index = "0" if first else "1"
        inverted_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(stage, dst_path)
        prim: Usd.Prim = inverted_mesh.GetPrim()
        prim.GetReferences().AddReference("", src_path)
        src_mesh = UsdGeom.Mesh(stage.GetPrimAtPath(src_path))
        src_holes: Usd.Attribute = src_mesh.GetHoleIndicesAttr()
        with Sdf.ChangeBlock():
            prim = inverted_mesh.GetPrim()
            binding = UsdShade.MaterialBindingAPI.Apply(prim)
            rel = binding.GetPrim().CreateRelationship("material:binding", False)
            rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectEmissiveTwoSided{index}")])
            if not options.generate_clash_polygons:
                return

            number_of_faces = len(inverted_mesh.GetFaceVertexCountsAttr().Get())
            all_numbers = np.arange(number_of_faces)
            all_numbers_minus_one = np.arange(number_of_faces - 1)

            inverted_holes: Usd.Attribute = inverted_mesh.GetHoleIndicesAttr()
            timesamples = src_holes.GetTimeSamples()  # type: ignore
            at_least_some_holes = False
            if len(timesamples) > 0:
                # Dynamic Clash
                prev_src_holes_np = np.array([])
                for timecode in timesamples:
                    src_holes_np = np.array(src_holes.Get(timecode))  # type: ignore
                    if len(src_holes_np) == 0:
                        # We display one triangle instead of marking it as hole as we can't generate an only holes mesh
                        # TODO: Figure out a way to hide the prim during this timecode...
                        inverted_holes.Set(all_numbers_minus_one, timecode)  # Cannot set all faces as holes
                        prev_src_holes_np = np.array([])
                    else:
                        at_least_some_holes = True
                        if len(prev_src_holes_np) == len(src_holes_np) and (prev_src_holes_np == src_holes_np).all():
                            continue
                        prev_src_holes_np = src_holes_np
                        inverted_np = np.setdiff1d(all_numbers, src_holes_np)
                        inverted_holes.Set(inverted_np, timecode)
            else:
                # Static Clash
                src_holes_np = np.array(src_holes.Get())  # type: ignore
                if len(src_holes_np) == 0:
                    # We display one triangle instead of marking it as hole as we can't generate an only holes mesh
                    # TODO: Best option here would be to hide or delete the prim
                    inverted_holes.Set(all_numbers_minus_one)  # type: ignore # Cannot set all faces as holes
                else:
                    at_least_some_holes = True
                    inverted_np = np.setdiff1d(all_numbers, src_holes_np)
                    inverted_holes.Set(inverted_np)  # type: ignore
            if not at_least_some_holes:
                rel.SetTargets([Sdf.Path(f"/ClashMaterials/Invisible")])
