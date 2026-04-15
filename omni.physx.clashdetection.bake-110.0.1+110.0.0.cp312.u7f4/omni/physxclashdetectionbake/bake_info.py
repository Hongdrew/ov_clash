# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pxr import Usd, UsdGeom, Sdf
import numpy as np
import numpy.typing as npt
from typing import Optional

from .bake_globals import ClashBakeGlobals, ClashInfo
from .bake_options import ClashBakeOptions
from .bake_utilities import ClashBakeUtils


class ClashBakeInfo:

    def __init__(self, clash_info: ClashInfo):
        self.clash_info = clash_info
        if not clash_info.identifier >= 0:
            raise Exception("Clash Info identifier must be a strictly positive number")
        self.root_prim_path = ["", ""]
        # Paths from target to root_prim path where the instanceable flag must be set
        self.instanceable_paths = [[], []]
        self.root_prim_type = [UsdGeom.Xform, UsdGeom.Xform]
        self.is_instance_proxy = [False, False]
        self.number_of_faces = [0, 0]

        # Mesh geometry data for wireframe generation (only populated if needed)
        self.mesh_points: list[Optional[npt.NDArray]] = [None, None]
        self.mesh_face_vertex_indices: list[Optional[npt.NDArray]] = [None, None]
        self.mesh_face_vertex_counts: list[Optional[npt.NDArray]] = [None, None]

    @staticmethod
    def _remove_baked_meshes(
        stage: Usd.Stage, layer: Sdf.Layer, src_path: str, options: ClashBakeOptions = ClashBakeOptions()
    ) -> bool:
        if options._inline_mode:
            # src_root_path is stored in ClashBakeInfo but we don't have it here, so let's recompute it
            root_prim_path = ClashBakeUtils.get_instance_root_path(src_path, stage)
            if not root_prim_path:
                return False
            if root_prim_path != src_path:
                src_prim = stage.GetPrimAtPath(src_path)
                src_root_prim = stage.GetPrimAtPath(root_prim_path)
                instanceable_paths = ClashBakeInfo._compute_instanceable_paths(src_prim, src_root_prim)
            else:
                instanceable_paths = []

            paths = ClashBakeGlobals.get_meshes_path_inline(src_path=src_path, src_root_path=root_prim_path)
            # This is important to avoid merging previous results
            ClashBakeUtils.remove_prim_spec(layer, paths.do_wire)
            ClashBakeUtils.remove_prim_spec(layer, paths.wireframe)
            ClashBakeUtils.remove_prim_spec(layer, paths.do_clash)
            ClashBakeUtils.remove_prim_spec(layer, paths.no_clash)
            ClashBakeUtils.remove_prim_spec(layer, paths.outlines_scope)

            ClashBakeInfo._remove_if_not_in_use(
                layer=layer,
                reference_path=paths.reference,
                src_path=src_path,
                root_prim_path=root_prim_path,
                instanceable_paths=instanceable_paths,
            )
        else:
            pass  # TODO: Implement for Scoped mode
        return True

    @staticmethod
    def _remove_if_not_in_use(
        layer: Sdf.Layer, reference_path: str, src_path: str, root_prim_path: str, instanceable_paths: list[str]
    ):
        # The reason to have the code below is a little bit convoluted and deserves some explanation.
        # It can happen for multiple unrelated clashes to have been "highlighted" under the same instancing root
        # in order to know if the reference can be removed, and if the original root instance prim visibility restored.
        # We first need to "try" making the reference prim inert (that means clearing its references, typename,
        # instanceable status and removing visibility for it an any of the "instanceable paths" where instancing has
        # been disabled because it wouldn't allow for modification of any of its children).
        # After making it inert calling Sdf.Layer.RemoveInertSceneDescription() will attempt to "garbage collect" it.
        # At this point if the original reference_spec doesn't exist anymore it means that no other clashes exist below
        # this instancing root that would require for it to still be valid.
        # If reference_spec still exist however, it means the other clashes DO need it to stay as it it is and so there
        # is need to "undo" all changes done by this function that have "dirtied" refrence_spec to try making it inert.
        # That's why the code below is doing a backup copy, that will be copied back to reference_path if needed.

        reference_spec: Sdf.PrimSpec = layer.GetPrimAtPath(reference_path)
        if reference_spec:
            # Make a backup copy of reference_spec
            backup_path: Sdf.Path = reference_spec.path.GetParentPath().AppendPath("_____ClashBakeBackup")  # type: ignore
            backup_spec = Sdf.CreatePrimInLayer(layer, backup_path)  # type: ignore
            Sdf.CopySpec(layer, reference_spec.path, layer, backup_spec.path)

            # Try making reference_spec 'inert'
            reference_spec.ClearInstanceable()
            reference_spec.ClearReferenceList()
            reference_spec.ClearInfo("typeName")
            if "visibility" in reference_spec.attributes.keys():  # type: ignore
                reference_spec.RemoveProperty(reference_spec.attributes["visibility"])  # type: ignore

            # We must clear instanceable flag also here
            for path in instanceable_paths:
                instaceable_spec: Sdf.PrimSpec = layer.GetPrimAtPath(path)
                if instaceable_spec:
                    instaceable_spec.ClearInstanceable()
            reference_spec.specifier = Sdf.SpecifierOver  # type: ignore

            # Garbage Collect unused prims specs
            layer.RemoveInertSceneDescription()

            # Check if reference_spec has been removed because inert
            reference_spec = layer.GetPrimAtPath(reference_path)
            if reference_spec:
                # Other clashes are still using this reference_path
                ClashBakeUtils.remove_prim_spec(layer, reference_path)
                reference_spec = Sdf.CreatePrimInLayer(layer, reference_path)  # type: ignore
                Sdf.CopySpec(layer, backup_spec.path, layer, reference_path)
                ClashBakeUtils.remove_prim_spec(layer, str(backup_spec.path))
            else:
                # No other clash is using this reference_path
                ClashBakeUtils.remove_prim_spec(layer, str(backup_spec.path))
                ClashBakeUtils.remove_prim_spec(layer, src_path)
                ClashBakeUtils.remove_prim_spec(layer, root_prim_path)
        else:
            # No reference path exists, there is probably no opinion both in src_path and in root_prim_path but remove
            # any spurious prim spec anyway from them just in case
            ClashBakeUtils.remove_prim_spec(layer, src_path)
            ClashBakeUtils.remove_prim_spec(layer, root_prim_path)

    @staticmethod
    def _compute_instanceable_paths(src_prim: Usd.Prim, src_root_prim: Usd.Prim):
        # Find all paths from src_path to root_prim_path where the instanceable flag must be set to False
        instanceable_paths: list[str] = []
        prim = src_prim
        while prim != src_root_prim:
            if prim.IsInstanceable():
                instanceable_paths.append(str(prim.GetPath()))
            prim = prim.GetParent()
        # Reverse the list
        instanceable_paths.reverse()
        return instanceable_paths

    def _prepare_bake(self, stage: Usd.Stage, first: bool, options: ClashBakeOptions = ClashBakeOptions()) -> bool:
        index = 0 if first else 1
        src_path = self.clash_info.object_a_path if first else self.clash_info.object_b_path
        root_prim_path = ClashBakeUtils.get_instance_root_path(src_path, stage)
        if not root_prim_path:
            return False
        self.root_prim_path[index] = root_prim_path
        src_prim: Usd.Prim = stage.GetPrimAtPath(src_path)
        src_root_prim: Usd.Prim = stage.GetPrimAtPath(self.root_prim_path[index])

        self.instanceable_paths[index] = self._compute_instanceable_paths(src_prim, src_root_prim)

        self.is_instance_proxy[index] = src_prim.IsInstanceProxy()

        if src_root_prim.IsA(UsdGeom.Xform):
            self.root_prim_type[index] = UsdGeom.Xform
        elif src_root_prim.IsA(UsdGeom.Mesh):
            self.root_prim_type[index] = UsdGeom.Mesh
        else:
            raise Exception(
                f"Unexpected type {src_prim.GetTypeName()} for src_root_prim='{self.root_prim_path[index]}'"
            )

        mesh = UsdGeom.Mesh(src_prim)
        self.number_of_faces[index] = len(mesh.GetFaceVertexCountsAttr().Get())

        # Read and store mesh geometry if wireframe generation is enabled
        if options.generate_wireframe:
            self.mesh_points[index] = np.array(mesh.GetPointsAttr().Get())
            self.mesh_face_vertex_indices[index] = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int32)
            self.mesh_face_vertex_counts[index] = np.array(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int32)
        return True
