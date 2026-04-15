# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pxr import Sdf, UsdGeom, UsdShade, Usd
import numpy as np
import numpy.typing as npt

from .bake_materials import ClashMaterialsPaths
from .bake_options import ClashBakeOptions
from .bake_utilities import CodeTimer, ClashBakeUtils
from .bake_globals import ClashBakeGlobals
from .bake_info import ClashBakeInfo
from .bake_meshes_stage_holes import ClashBakeMeshesStageHoles
from .bake_meshes_stage_opacity import ClashBakeMeshesStageOpacity
from .bake_generator_stage_inline import ClashBakeGeneratorStageInline


class ClashBakeGeneratorStageScopes:
    """
    Generate overlay clash meshes and outlines in a dedicated USD Scope, outside of the source mesh hierarchy.
    """

    def __init__(
        self,
        bake_info: ClashBakeInfo,
        stage: Usd.Stage,
        materials: ClashMaterialsPaths,
        options: ClashBakeOptions = ClashBakeOptions(),
    ):
        self._bake_info = bake_info
        self._clash_info = bake_info.clash_info
        self._stage = stage
        self._materials = materials
        self._options = options

    def generate(self):
        if self._options.generate_clash_meshes:
            self._generate_meshes_scopes(self._clash_info.object_a_path, self._clash_info.object_b_path, True)
            self._generate_meshes_scopes(self._clash_info.object_b_path, self._clash_info.object_a_path, False)
        if self._options.generate_outlines:
            with CodeTimer("generate_outlines", self._options):
                ClashBakeGeneratorStageInline.generate_outlines(
                    self._stage, self._clash_info, f"/Outlines/Outline_{self._clash_info.identifier}", self._options
                )

    def _generate_meshes_scopes(self, src_path: str, other_path: str, first: bool):
        paths = ClashBakeGlobals.get_meshes_path_scopes(src_path, other_path)

        UsdGeom.Scope.Define(self._stage, ClashBakeGlobals.CLASHES_ROOT)
        UsdGeom.Scope.Define(self._stage, paths.clash_scope)
        merged_scope = UsdGeom.Scope.Define(self._stage, paths.merged_scope)
        sub_scope = UsdGeom.Scope.Define(self._stage, paths.sub_scope)

        with CodeTimer("bake_no_clash MERGED", self._options):
            self._bake_no_clash(src_path=src_path, dst_path=paths.no_merged, reference=True, first=first, faces=False)
        with CodeTimer("bake_no_clash NO_CLASH", self._options):
            self._bake_no_clash(
                src_path=paths.no_merged, dst_path=paths.no_clash, reference=True, first=first, transforms=False
            )

        if self._options.generate_clash_polygons:
            if self._options._use_display_opacity:
                with CodeTimer("bake_inverse_mesh_opacity", self._options):
                    ClashBakeMeshesStageOpacity.bake_inverse_mesh_opacity(
                        stage=self._stage,
                        options=self._options,
                        src_path=paths.no_clash,
                        dst_path=paths.do_clash,
                        first=first,
                    )
            else:
                with CodeTimer("bake_inverse_mesh_holes", self._options):
                    ClashBakeMeshesStageHoles.bake_inverse_mesh_holes(
                        stage=self._stage,
                        options=self._options,
                        src_path=paths.no_clash,
                        dst_path=paths.do_clash,
                        first=first,
                    )

        if self._options.generate_wireframe:
            with CodeTimer("create_wireframe_mesh", self._options):
                ClashBakeGeneratorStageInline.create_wireframe_mesh(
                    stage=self._stage, src_path=paths.do_clash, dst_path=paths.do_wire, first=first
                )

        # Hide Merged scope and show currently updated single mesh scope
        ClashBakeUtils.set_scope_visibility(merged_scope, False)
        ClashBakeUtils.set_scope_visibility(sub_scope, True)

    def _bake_no_clash(self, src_path: str, dst_path: str, reference: bool, first: bool, faces=True, transforms=True):
        index = 0 if first else 1
        if self._bake_info.is_instance_proxy[index]:
            reference = True
        if reference:
            no_clash_mesh = UsdGeom.Mesh.Define(self._stage, dst_path)
            no_clash_prim = no_clash_mesh.GetPrim()
            no_clash_prim.GetReferences().AddReference("", src_path)
            root_prim_path = self._stage.GetPrimAtPath(self._bake_info.root_prim_path[index])
            # NOTE: Hiding the source prim doesn't work when there are animation cuves because they override
            # visibility directly session layer (or Fabric).
            # For this reason we also set the root of the instance proxy to use an invisible material
            binding = UsdShade.MaterialBindingAPI.Apply(root_prim_path)
            rel = binding.GetPrim().CreateRelationship("material:binding", False)
            rel.SetTargets([Sdf.Path("/ClashMaterials/Invisible")])
            # TODO: Hiding is causing some issues in non instanced meshes case, must investigate
            # ClashBakeUtils.set_scope_visibility(root_prim_path, False)
        else:
            no_clash_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(self._stage, src_path)

        with Sdf.ChangeBlock():
            if faces:
                if self._options._use_display_opacity:
                    ClashBakeMeshesStageOpacity.hide_clashing_faces_opacity(
                        self._stage, self._options, self._clash_info, no_clash_mesh, first
                    )
                else:
                    ClashBakeMeshesStageHoles.hide_clashing_faces_holes(
                        self._stage, self._options, self._clash_info, no_clash_mesh, first
                    )
            else:
                # Clear normals to avoid "corrupted data in primvar 'normal': buffer size..." warning
                no_clash_mesh.GetNormalsAttr().Set([])
                UsdGeom.PrimvarsAPI(no_clash_mesh.GetPrim()).RemovePrimvar("normals")
                binding = UsdShade.MaterialBindingAPI.Apply(no_clash_mesh.GetPrim())
                rel = binding.GetPrim().CreateRelationship("material:binding", False)
                if self._options._use_display_opacity:
                    rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectPerFaceSolid{index}")])
                else:
                    rel.SetTargets([Sdf.Path(f"/ClashMaterials/ObjectSolid{index}")])

            if reference and transforms:
                self._write_transforms(no_clash_mesh.GetPrim(), first)

    def _write_transforms(self, prim: Usd.Prim, first: bool):
        if not self._clash_info.clash_frame_info_items:
            return
        dest_xformable = UsdGeom.Xformable(prim)
        transform_ops = dest_xformable.GetOrderedXformOps()
        tcps = self._stage.GetTimeCodesPerSecond()
        for cfi in self._clash_info.clash_frame_info_items:
            timecode = ClashBakeUtils.get_frame_time_code(time=cfi.timecode, fps=tcps)
            # A. Flattern instanced transform
            # self._xform_cache.SetTime(timecode)
            # ClashBakeUtils.flattern_as_matrix(self._xform_cache, src_prim, dest_xformable, timecode)

            # B. Read transforms directly from the CFI
            matrix = cfi.object_0_matrix if first else cfi.object_1_matrix
            ClashBakeUtils.set_matrix_transform_for_ops(matrix=matrix, transform_ops=transform_ops, timecode=timecode)


class ClashBakeMergerStageScopes:
    def __init__(self, stage: Usd.Stage, options: ClashBakeOptions):
        self._stage = stage
        self._options = options

    def generate_merged(self, paths: list[tuple[str, str]] | None):
        if not self._options.generate_clash_meshes:
            return
        clashes_root: Usd.Prim = self._stage.GetPrimAtPath(ClashBakeGlobals.CLASHES_ROOT)
        if paths:
            # Only recompute merged meshes for paths list
            for mesh_a, mesh_b in paths:
                scope_a = ClashBakeGlobals.get_clash_scope_for(mesh_a)
                scope_b = ClashBakeGlobals.get_clash_scope_for(mesh_b)
                self._generate_merged_mesh(self._stage.GetPrimAtPath(scope_a))
                self._generate_merged_mesh(self._stage.GetPrimAtPath(scope_b))
        else:
            # Enumerate all child UsdGeom.Scope of clashes_root
            for child in clashes_root.GetChildren():
                if not child.IsA(UsdGeom.Scope):
                    continue
                self._generate_merged_mesh(child)

    def _generate_merged_mesh(self, prim: Usd.Prim):
        prims = prim.GetChildren()
        if len(prims) == 2:
            pass  # TODO: Simple case, merged can be copied from the only other sub mesh
        merged = prim.GetChild("Merged")
        children = [child for child in prim.GetChildren() if child.GetName() != "Merged"]

        accumulated_no_clash = {}
        merged_no_clash_mesh = UsdGeom.Mesh(merged.GetChild("NO_CLASH"))
        merged_holes: Usd.Attribute = merged_no_clash_mesh.GetHoleIndicesAttr()
        for child in children:
            mesh: UsdGeom.Mesh = UsdGeom.Mesh(child.GetChild("NO_CLASH"))
            # Get all timesamples for holeIndices attribute in mesh
            hole_attribute = mesh.GetHoleIndicesAttr()
            timesamples = hole_attribute.GetTimeSamples()
            for timesample in timesamples:
                holes = hole_attribute.Get(timesample)
                # if accumulated_no_clash has already an exiting array at timesample, merge holes array with them
                if timesample in accumulated_no_clash:
                    existing = accumulated_no_clash[timesample]
                    accumulated_no_clash[timesample] = np.concatenate((existing, np.array(holes)))
                else:
                    accumulated_no_clash[timesample] = np.array(holes)

        with Sdf.ChangeBlock():
            for child in children:
                ClashBakeUtils.set_scope_visibility(child, False)
            merged_holes.Clear()
            number_of_faces = len(merged_no_clash_mesh.GetFaceVertexCountsAttr().Get())
            some_holes_set = False
            for timesample, holes in accumulated_no_clash.items():
                # let's sort and remove duplicates from holes (unique returns sorted array)
                holes = np.unique(holes)
                if len(holes) < number_of_faces:
                    some_holes_set = True
                    merged_holes.Set(holes, Usd.TimeCode(timesample))

        no_clash_path = merged.GetPath().AppendChild("NO_CLASH")
        do_clash_path = merged.GetPath().AppendChild("DO_CLASH_MERGED")
        wire_path = merged.GetPath().AppendChild("WIREFRAME_MERGED")
        if some_holes_set:
            ClashBakeMeshesStageHoles.bake_inverse_mesh_holes(
                stage=self._stage, options=self._options, src_path=no_clash_path, dst_path=do_clash_path, first=True
            )
            if self._options.generate_wireframe:
                ClashBakeGeneratorStageInline.create_wireframe_mesh(self._stage, do_clash_path, wire_path, True)
        else:
            # Empty array case
            do_clash_prim = self._stage.GetPrimAtPath(do_clash_path)
            if do_clash_prim:
                self._stage.RemovePrim(do_clash_path)
            wire_prim = self._stage.GetPrimAtPath(wire_path)
            if wire_prim:
                self._stage.RemovePrim(wire_path)
        ClashBakeUtils.set_scope_visibility(merged, True)
