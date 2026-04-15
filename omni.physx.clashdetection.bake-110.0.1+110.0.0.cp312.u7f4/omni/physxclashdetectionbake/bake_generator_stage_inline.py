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

from .bake_outlines_stage import ClashOutlinesStage
from .bake_materials import ClashMaterialsPaths
from .bake_options import ClashBakeOptions
from .bake_utilities import CodeTimer, ClashBakeUtils
from .bake_globals import ClashBakeGlobals, ClashInfo
from .bake_info import ClashBakeInfo
from .bake_meshes_stage_holes import ClashBakeMeshesStageHoles
from .bake_meshes_stage_opacity import ClashBakeMeshesStageOpacity


class ClashBakeGeneratorStageInline:
    """
    Generates overlay clash meshes and outlines side by side with the original meshes.
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
            self._generate_meshes_inline(self._clash_info.object_a_path, True)
            self._generate_meshes_inline(self._clash_info.object_b_path, False)
        if self._options.generate_outlines:
            with CodeTimer("generate_outlines", self._options):
                self.generate_outlines(
                    self._stage, self._clash_info, f"/Outlines/Outline_{self._clash_info.identifier}", self._options
                )

    def _generate_meshes_inline(self, src_path: str, first: bool):
        index = 0 if first else 1
        src_root_path = self._bake_info.root_prim_path[index]
        paths = ClashBakeGlobals.get_meshes_path_inline(src_path=src_path, src_root_path=src_root_path)
        # NOTE: Hiding the source prim doesn't work when there are animation cuves because they override
        # visibility directly session layer (or Fabric).
        # For this reason we also set the root of the instance proxy to use an invisible material
        src_root_prim = self._stage.GetPrimAtPath(src_root_path)
        binding = UsdShade.MaterialBindingAPI.Apply(src_root_prim)
        rel = binding.GetPrim().CreateRelationship("material:binding", False)
        rel.SetTargets([Sdf.Path("/ClashMaterials/Invisible")])

        reference_path = paths.reference

        # reference_prim = self._stage.DefinePrim(reference_path) # This doesn't work
        reference_prim = self._bake_info.root_prim_type[index].Define(self._stage, reference_path).GetPrim()
        reference_prim.GetReferences().AddReference("", src_root_path)
        # Important: Remove the inherited instanceable flag so that this reference prims can be modified
        if reference_prim.IsInstanceable():
            reference_prim.SetInstanceable(False)
        binding = UsdShade.MaterialBindingAPI.Apply(reference_prim)
        rel = binding.GetPrim().CreateRelationship("material:binding", False)
        rel.SetTargets([])

        # NO CLASH MESH

        # Find the relative path of the target mesh (src_path) inside the "cloned" reference_path
        # In other words reference_path and src_root_path are "parallel", and src_path is inside src_root_path.
        # We want to find the path inside reference_path that is "corresponding" to src_path.
        no_clash_path = paths.no_clash

        with CodeTimer("bake_no_clash", self._options):
            no_clash_prim = self._stage.GetPrimAtPath(no_clash_path)
            if not no_clash_prim:
                raise Exception(f"Invalid prim at '{no_clash_path}'")
            no_clash_mesh = UsdGeom.Mesh(self._stage.GetPrimAtPath(no_clash_path))

            with Sdf.ChangeBlock():
                if self._options._use_display_opacity:
                    ClashBakeMeshesStageOpacity.hide_clashing_faces_opacity(
                        self._stage, self._options, self._clash_info, no_clash_mesh, first
                    )
                else:
                    ClashBakeMeshesStageHoles.hide_clashing_faces_holes(
                        self._stage, self._options, self._clash_info, no_clash_mesh, first
                    )

        # DO CLASH MESH
        do_clash_path = paths.do_clash
        with CodeTimer("bake_inverse_mesh_holes", self._options):
            if not self._options._use_display_opacity and self._options.generate_clash_polygons:
                ClashBakeMeshesStageHoles.bake_inverse_mesh_holes(
                    stage=self._stage,
                    options=self._options,
                    src_path=no_clash_path,
                    dst_path=do_clash_path,
                    first=first,
                )

        # WIREFRAME Mesh (on DO_CLASH)
        if self._options.generate_wireframe:
            wire_clash_path = paths.do_wire
            with CodeTimer("create_wireframe_mesh", self._options):
                if self._options._use_display_opacity:
                    material_prefix = (
                        "/ClashMaterials/ObjectPerFaceWireframe"
                        if self._options.generate_clash_polygons
                        else "/ClashMaterials/ObjectPerFaceWireframeAlways"
                    )
                    self.create_wireframe_mesh(
                        stage=self._stage,
                        src_path=no_clash_path,
                        dst_path=wire_clash_path,
                        first=first,
                        material_prefix=material_prefix,
                    )
                else:
                    wire_src_path = do_clash_path if self._options.generate_clash_polygons else no_clash_path
                    self.create_wireframe_mesh(
                        stage=self._stage, src_path=wire_src_path, dst_path=wire_clash_path, first=first
                    )

    @staticmethod
    def create_wireframe_mesh(
        stage: Usd.Stage,
        src_path: str,
        dst_path: str,
        first: bool,
        material_prefix: str = "/ClashMaterials/ObjectWireframe",
    ):
        index = "0" if first else "1"

        clash_wire: UsdGeom.Mesh = UsdGeom.Mesh.Define(stage, dst_path)
        prim: Usd.Prim = clash_wire.GetPrim()
        prim.GetReferences().AddReference("", src_path)

        with Sdf.ChangeBlock():
            prim.CreateAttribute("primvars:wireframe", Sdf.ValueTypeNames.Bool).Set(True)  # type: ignore
            prim.SetMetadata("always_pick_model", True)
            index = "0" if first else "1"
            wireframe_material_path = f"{material_prefix}{index}"
            material: UsdShade.Material = UsdShade.Material.Get(stage, wireframe_material_path)
            binding: UsdShade.MaterialBindingAPI = UsdShade.MaterialBindingAPI.Apply(prim)
            binding.Bind(material, UsdShade.Tokens.weakerThanDescendants)  # type: ignore

    @staticmethod
    def generate_outlines(stage: Usd.Stage, clash_info: ClashInfo, outlines_path: str, options: ClashBakeOptions):
        frame_infos = clash_info.clash_frame_info_items
        if not frame_infos:
            return
        UsdGeom.Scope.Define(stage, "/Outlines")
        outline_material_path = "/ClashMaterials/ObjectEmissiveOutlines"
        curve: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Define(stage, outlines_path)
        if not curve:
            return
        material = UsdShade.Material.Get(stage, outline_material_path)
        binding = UsdShade.MaterialBindingAPI.Apply(curve.GetPrim())
        binding.Bind(material, UsdShade.Tokens.weakerThanDescendants)
        clash_outlines = ClashOutlinesStage(curve)
        # TODO: figure out a way to hide the outlines before the firsh clash hit frame and after it's done
        # clash_outlines.build(outline=np.empty(1), timecode=Usd.TimeCode(0))
        timecodes = stage.GetTimeCodesPerSecond()
        with Sdf.ChangeBlock():
            for cfi in frame_infos:
                if cfi.collision_outline is None:
                    continue
                timecode = ClashBakeUtils.get_frame_time_code(cfi.timecode, timecodes)
                clash_outlines.build(
                    outline=cfi.collision_outline.numpy(),
                    timecode=timecode,
                    outline_width_size=options.outline_width_size,
                    outline_width_scale=options.outline_width_scale,
                )
