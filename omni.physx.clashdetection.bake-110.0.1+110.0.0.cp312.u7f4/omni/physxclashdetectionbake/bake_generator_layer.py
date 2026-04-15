# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pxr import Sdf, Usd, UsdGeom, Vt, Gf
import numpy as np
from typing import Optional

from .bake_materials import ClashMaterialsPaths
from .bake_options import ClashBakeOptions
from .bake_utilities import ClashBakeUtils
from .bake_info import ClashBakeInfo
from .bake_globals import ClashBakeGlobals, ClashBakePaths
from .bake_outlines_layer import ClashOutlinesLayer
from .bake_utilities import CodeTimer
from .bake_meshes_layer_opacity import ClashBakeMeshesLayerOpacity
from .bake_offset_mesh import ClashBakeOffsetMesh


class ClashBakeGeneratorLayer:
    """
    Generates clash meshes and outlines in a layer, using the Sdf API.
    """

    def __init__(
        self,
        bake_info: ClashBakeInfo,
        layer: Sdf.Layer,
        materials: ClashMaterialsPaths | None,
        options: ClashBakeOptions = ClashBakeOptions(),
    ):
        self._bake_info = bake_info
        self._clash_info = bake_info.clash_info
        self._layer = layer
        self._tcps = self._layer.timeCodesPerSecond
        self._materials = materials
        self._options = options

    def generate(self):
        bi = self._bake_info
        ci = self._clash_info

        if ci.is_duplicate:
            self._generate_duplicate_clash(bi, ci)
        else:
            self._generate_regular_clash(bi, ci)

    def _generate_regular_clash(self, bi: ClashBakeInfo, ci):
        paths = (
            ClashBakeGlobals.get_meshes_path_inline(src_path=ci.object_a_path, src_root_path=bi.root_prim_path[0]),
            ClashBakeGlobals.get_meshes_path_inline(src_path=ci.object_b_path, src_root_path=bi.root_prim_path[1]),
        )

        if self._options.generate_clash_meshes:
            self._clone_clash_meshes(paths, bi, ci)

            if self._options.use_selection_groups:
                self._prepend_viewport_highlight_api(paths[0].no_clash, group_name=self._options.group_name_clash_a)
                self._prepend_viewport_highlight_api(paths[1].no_clash, group_name=self._options.group_name_clash_b)
            else:
                with CodeTimer("animate_clash_mesh_faces_and_material A", self._options):
                    number_of_faces = self._bake_info.number_of_faces[0]
                    self._animate_clash_mesh_faces_and_material(paths[0], number_of_faces=number_of_faces, first=True)
                with CodeTimer("animate_clash_mesh_faces_and_material B", self._options):
                    number_of_faces = self._bake_info.number_of_faces[1]
                    self._animate_clash_mesh_faces_and_material(paths[1], number_of_faces=number_of_faces, first=False)

                # Can only generate wireframe if dedicated meshes are generated
                if self._options.generate_wireframe:
                    with CodeTimer("generate_wireframe A", self._options):
                        self._generate_wireframe(paths[0], bi, first=True)
                    with CodeTimer("generate_wireframe B", self._options):
                        self._generate_wireframe(paths[1], bi, first=False)

        if self._options.generate_outlines:
            with CodeTimer("generate_outlines", self._options):
                self._generate_outlines(paths[0], ci.object_b_path)

    def _generate_duplicate_clash(self, bi: ClashBakeInfo, ci):
        if self._options.generate_clash_meshes and self._options.use_selection_groups:
            paths = (
                ClashBakeGlobals.get_meshes_path_inline(src_path=ci.object_a_path, src_root_path=bi.root_prim_path[0]),
                ClashBakeGlobals.get_meshes_path_inline(src_path=ci.object_b_path, src_root_path=bi.root_prim_path[1]),
            )

            if bi.is_instance_proxy[0] == False and len(bi.instanceable_paths[0]) == 0:
                self._prepend_viewport_highlight_api(ci.object_a_path, group_name=self._options.group_name_duplicate)
            elif bi.is_instance_proxy[1] == False and len(bi.instanceable_paths[1]) == 0:
                self._prepend_viewport_highlight_api(ci.object_b_path, group_name=self._options.group_name_duplicate)
            else:
                # Both meshes are instanceable we need to clone one, remove instanceable flag and create a reference
                # Choosing the first one as either one will do
                self._clone_clash_mesh(paths, bi, ci, 0)
                self._prepend_viewport_highlight_api(paths[0].no_clash, group_name=self._options.group_name_duplicate)

    def _prepend_viewport_highlight_api(self, path: str, group_name: str):
        """Prepend the ClashViewportHighlightAPI to the prim at the given path with the given group name"""
        # Note: this works also for instance proxies because the reference to the original instance has the instanceable
        # flag set to False, allowing to manipulate visibility and apply the API to sub-prims of such reference.
        prim_spec = Sdf.CreatePrimInLayer(self._layer, path)
        existing_apis = prim_spec.GetInfo("apiSchemas")
        prepended = [p for p in existing_apis.prependedItems if p != "ClashViewportHighlightAPI"]
        prepended.append("ClashViewportHighlightAPI")
        prim_spec.SetInfo("apiSchemas", Sdf.TokenListOp.Create(prependedItems=prepended))
        group_name_attribute = "omni:clashViewportHighlight:groupName"
        if group_name_attribute in prim_spec.attributes:
            group_name_spec = prim_spec.attributes[group_name_attribute]
        else:
            group_name_spec = Sdf.AttributeSpec(prim_spec, group_name_attribute, Sdf.ValueTypeNames.String)
        group_name_spec.default = group_name  # type: ignore

    def _clone_clash_mesh(self, paths: tuple[ClashBakePaths, ClashBakePaths], bi: ClashBakeInfo, ci, index: int):
        # Set the instanceable flag to False for all paths from source to root_prim to allow applying APIs to sub-prims
        ClashBakeUtils.set_instanceable_paths(self._layer, bi.instanceable_paths[index])

        # Create a reference to original source prims
        ClashBakeUtils.create_reference_to(
            self._layer, bi.root_prim_path[index], paths[index].reference, bi.root_prim_type[index]
        )

        # Hide the original source prims during the time range of the clash
        ClashBakeUtils.merge_visibility_range(False, self._layer, bi.root_prim_path[index], ci.start_time, ci.end_time)

        # Show the "cloned" (reference prims) only during the time range of the clash
        ClashBakeUtils.merge_visibility_range(True, self._layer, paths[index].reference, ci.start_time, ci.end_time)

    def _clone_clash_meshes(self, paths: tuple[ClashBakePaths, ClashBakePaths], bi: ClashBakeInfo, ci):
        self._clone_clash_mesh(paths, bi, ci, 0)
        self._clone_clash_mesh(paths, bi, ci, 1)

    def _animate_clash_mesh_faces_and_material(self, paths: ClashBakePaths, number_of_faces: int, first: bool):
        if self._materials is None:
            return
        cfii = None
        if not self._options.generate_clash_polygons:
            cfii = self._clash_info.clash_frame_info_items
            self._clash_info.clash_frame_info_items = None

        ClashBakeMeshesLayerOpacity.hide_clashing_faces_opacity(
            layer=self._layer,
            options=self._options,
            clash_info=self._clash_info,
            number_of_faces=number_of_faces,
            prim_path=paths.no_clash,
            materials=self._materials,
            first=first,
        )

        if not self._options.generate_clash_polygons:
            self._clash_info.clash_frame_info_items = cfii

    def _generate_wireframe(self, paths: ClashBakePaths, bi: ClashBakeInfo, first: bool):
        index = 0 if first else 1
        if self._materials is None:
            return

        ci = self._clash_info

        # Check if wireframe already exists (from a previous clash using the same mesh)
        wireframe_already_exists = self._layer.GetPrimAtPath(paths.wireframe) is not None

        if not wireframe_already_exists:
            ClashBakeUtils.create_reference_to(self._layer, paths.no_clash, paths.wireframe, UsdGeom.Mesh)

        wireframe_spec = self._layer.GetPrimAtPath(paths.wireframe)

        # Check if we have mesh geometry data
        if bi.mesh_points[index] is not None:
            # Create wireframe mesh with offset vertices

            # Get mesh geometry (already checked for None above)
            points = bi.mesh_points[index]
            face_vertex_indices = bi.mesh_face_vertex_indices[index]
            face_vertex_counts = bi.mesh_face_vertex_counts[index]

            # These should never be None at this point due to the earlier check
            assert points is not None
            assert face_vertex_indices is not None
            assert face_vertex_counts is not None

            # Determine which faces to optimize for (current clash)
            current_clash_faces = self._compute_visible_face_indices(ci, first)

            # If wireframe already exists, merge with previously affected faces
            visible_face_indices = current_clash_faces
            if wireframe_already_exists and current_clash_faces is not None:
                # Read previously stored affected faces
                affected_faces_attr_name = "primvars:clashAffectedFaces"
                if affected_faces_attr_name in wireframe_spec.attributes:
                    affected_faces_spec = wireframe_spec.attributes[affected_faces_attr_name]
                    previous_faces = np.array(affected_faces_spec.default, dtype=np.int32)
                    # Merge with current clash faces
                    visible_face_indices = np.unique(np.concatenate((current_clash_faces, previous_faces)))

                    # Check if merged set exceeds threshold
                    total_faces = bi.number_of_faces[index]
                    affected_ratio = len(visible_face_indices) / total_faces if total_faces > 0 else 1.0
                    if affected_ratio > 0.4:
                        # Too many faces now, process all instead
                        if self._options._debug_mode:
                            import carb

                            carb.log_info(
                                f"Merged affected faces exceed threshold: {len(visible_face_indices)} of {total_faces} "
                                f"({affected_ratio*100:.1f}% > 40%), processing all vertices"
                            )
                        visible_face_indices = None

            # Compute offset points
            with CodeTimer("compute_offset_points", self._options):
                offset_points = ClashBakeOffsetMesh.compute_offset_points(
                    points=points,
                    face_vertex_indices=face_vertex_indices,
                    face_vertex_counts=face_vertex_counts,
                    epsilon=self._options.wireframe_offset_epsilon,
                    visible_face_indices=visible_face_indices,
                    options=self._options,
                )

            # Store the affected faces for future merging (if optimization was used)
            if visible_face_indices is not None:
                affected_faces_attr_name = "primvars:clashAffectedFaces"
                if affected_faces_attr_name in wireframe_spec.attributes:
                    affected_faces_spec = wireframe_spec.attributes[affected_faces_attr_name]
                else:
                    affected_faces_spec = Sdf.AttributeSpec(
                        wireframe_spec, affected_faces_attr_name, Sdf.ValueTypeNames.IntArray
                    )
                    affected_faces_spec.custom = True  # type: ignore
                affected_faces_spec.default = Vt.IntArray.FromNumpy(visible_face_indices)  # type: ignore

            # Write offset points as default (not time-sampled, since offset is static)
            # The animation comes from the reference to the original mesh
            if "points" in wireframe_spec.attributes:
                points_spec = wireframe_spec.attributes["points"]
            else:
                points_spec = Sdf.AttributeSpec(wireframe_spec, "points", Sdf.ValueTypeNames.Point3fArray)

            points_spec.default = Vt.Vec3fArray.FromNumpy(offset_points.astype(np.float32))  # type: ignore

            # Copy extent (expanded slightly for the offset)
            # Not really necessary but it shouldn't cost much to compute
            extent_min = np.min(offset_points, axis=0) - self._options.wireframe_offset_epsilon
            extent_max = np.max(offset_points, axis=0) + self._options.wireframe_offset_epsilon

            # Get or create extent attribute spec
            if "extent" in wireframe_spec.attributes:
                extent_spec = wireframe_spec.attributes["extent"]
            else:
                extent_spec = Sdf.AttributeSpec(wireframe_spec, "extent", Sdf.ValueTypeNames.Float3Array)

            # Convert numpy float32 to Python float for Gf.Vec3f compatibility
            extent_min = Gf.Vec3f(float(extent_min[0]), float(extent_min[1]), float(extent_min[2]))
            extent_max = Gf.Vec3f(float(extent_max[0]), float(extent_max[1]), float(extent_max[2]))
            extent_spec.default = Vt.Vec3fArray([extent_min, extent_max])  # type: ignore

        # Disable allowing click this wireframe mesh
        wireframe_spec.SetInfo("always_pick_model", True)

        # Add the wireframe primvar
        if "primvars:wireframe" not in wireframe_spec.attributes:
            wireframe_primvar_spec = Sdf.AttributeSpec(wireframe_spec, "primvars:wireframe", Sdf.ValueTypeNames.Bool)
            wireframe_primvar_spec.custom = True  # type: ignore
            wireframe_primvar_spec.default = True  # type: ignore

        # Set wireframe material
        if wireframe_spec.relationships.get("material:binding") is None:
            material_bind_rel_spec = Sdf.RelationshipSpec(wireframe_spec, "material:binding")
        else:
            material_bind_rel_spec = wireframe_spec.relationships["material:binding"]
        if self._options.generate_clash_polygons:
            material = [Sdf.Path(self._materials.do_clash_wireframe_per_face_materials[index])]
        else:
            material = [Sdf.Path(self._materials.all_wireframe_per_face_materials[index])]
        material_bind_rel_spec.targetPathList.explicitItems = material  # type: ignore

    def _compute_visible_face_indices(self, ci, first: bool) -> Optional[np.ndarray]:
        """Compute the union of all visible (clashing) face indices across all frames.

        This is used to optimize normal computation by only processing vertices of clashing faces.
        If more than 40% of faces are affected, returns None to process all faces instead.

        Args:
        - ci: ClashInfo object with clash_frame_info_items
        - first (bool): True for object A, False for object B

        Returns:
        - Optional[np.ndarray]: Array of unique face indices, or None if optimization should be skipped
        """
        if not ci.clash_frame_info_items:
            return None

        # Collect all affected face indices across all frames
        all_face_indices = []
        for cfi in ci.clash_frame_info_items:
            faces = cfi.usd_faces_0 if first else cfi.usd_faces_1
            if faces is not None:
                all_face_indices.append(faces.numpy())

        if not all_face_indices:
            return None

        # Compute union of all face indices
        unique_faces = np.unique(np.concatenate(all_face_indices))

        # Check if optimization is worth it (threshold: 40%)
        index = 0 if first else 1
        total_faces = self._bake_info.number_of_faces[index]
        affected_ratio = len(unique_faces) / total_faces if total_faces > 0 else 1.0

        if affected_ratio > 0.4:
            # Too many faces affected, process all instead
            if self._options._debug_mode:
                import carb

                carb.log_info(
                    f"Skipping face optimization: {len(unique_faces)} of {total_faces} faces "
                    f"affected ({affected_ratio*100:.1f}% > 40%)"
                )
            return None

        return unique_faces

    def _generate_outlines(self, paths: ClashBakePaths, other_path: str):
        ci = self._clash_info
        frame_infos = ci.clash_frame_info_items
        if not frame_infos:
            return
        timecodes = self._tcps

        # Create the root scope
        root_scope_spec = Sdf.CreatePrimInLayer(self._layer, ClashBakeGlobals.OUTLINES_SCOPE)
        root_scope_spec.specifier = Sdf.SpecifierDef
        root_scope_spec.typeName = "Scope"

        # Create scope of outlines that have object a equal to this path
        child_scope_spec = Sdf.CreatePrimInLayer(self._layer, paths.outlines_scope)
        child_scope_spec.specifier = Sdf.SpecifierDef
        child_scope_spec.typeName = "Scope"

        # Create the outline prim for clash of object a with object b
        clash_outlines_path = paths.get_outlines_path_for_clash_with(other_path)
        clash_outlines = ClashOutlinesLayer(self._layer, Sdf.Path(clash_outlines_path))

        # Apply material to outlines
        if self._options.use_selection_groups:
            self._prepend_viewport_highlight_api(clash_outlines_path, group_name=self._options.group_name_outlines)
        else:
            if self._materials is not None:
                clash_outlines.apply_material(self._materials.outlines_material)

        # Create all frames of the animated outline
        for cfi in frame_infos:
            if cfi.collision_outline is None:
                continue
            timecode = ClashBakeUtils.get_frame_time_code(cfi.timecode, timecodes)
            clash_outlines.build(
                outline=cfi.collision_outline.numpy(),
                timecode=timecode,
                outline_width_size=self._options.outline_width_size,
                outline_width_scale=self._options.outline_width_scale,
            )

        # Show the outlines only during the time range of the clash
        ClashBakeUtils.merge_visibility_range(True, self._layer, clash_outlines_path, ci.start_time, ci.end_time)


class ClashBakeOptimizeLayer:
    """
    Optimizes the clash meshes in a layer, using the Sdf API.
    """

    def __init__(self, layer: Sdf.Layer, options: ClashBakeOptions = ClashBakeOptions()):
        self._layer = layer
        self._tcps = self._layer.timeCodesPerSecond

    def optimize(self, bake_infos: list[ClashBakeInfo]):
        for bi in bake_infos:
            paths = (
                ClashBakeGlobals.get_meshes_path_inline(
                    src_path=bi.clash_info.object_a_path, src_root_path=bi.root_prim_path[0]
                ),
                ClashBakeGlobals.get_meshes_path_inline(
                    src_path=bi.clash_info.object_b_path, src_root_path=bi.root_prim_path[1]
                ),
            )

            ClashBakeMeshesLayerOpacity.remove_duplicated_time_samples(self._layer, paths[0].no_clash)
            ClashBakeMeshesLayerOpacity.remove_duplicated_time_samples(self._layer, paths[1].no_clash)

            # Remove temporary metadata used during wireframe generation
            self._remove_temporary_wireframe_metadata(paths[0].wireframe)
            self._remove_temporary_wireframe_metadata(paths[1].wireframe)

    def _remove_temporary_wireframe_metadata(self, wireframe_path: str):
        """Remove temporary attributes used during wireframe generation process."""
        wireframe_spec = self._layer.GetPrimAtPath(wireframe_path)
        if wireframe_spec is None:
            return

        # Remove the clashAffectedFaces attribute if it exists
        affected_faces_attr_name = "primvars:clashAffectedFaces"
        if affected_faces_attr_name in wireframe_spec.attributes:
            wireframe_spec.RemoveProperty(wireframe_spec.attributes[affected_faces_attr_name])
