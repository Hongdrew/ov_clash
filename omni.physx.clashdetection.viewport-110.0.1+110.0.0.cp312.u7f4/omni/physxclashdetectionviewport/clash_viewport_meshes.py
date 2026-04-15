# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import math
from dataclasses import dataclass
from typing import Callable, Sequence, Optional

import numpy as np
import warp as wp
import carb
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt

from .clash_viewport_materials import ClashViewportMaterialPaths
from .clash_viewport_settings import ClashViewportSettingValues
from .clash_viewport_utility import CodeTimer
from .clash_viewport_wireframes import ClashViewportWireframes

__all__ = []


@dataclass
class ClashViewportMeshPaths:
    """Holds usd paths where Clash meshes are created.

    Attributes:
    - overlap_id (str): Overlap ID for this clash
    - do_clash_paths_solid (tuple[str, str]): Paths of meshes representing clashing faces (A/B)
    - no_clash_paths_solid (tuple[str, str]): Paths of meshes representing non-clashing faces (A/B)
    - do_clash_paths_xform (tuple[str, str]): Paths of xform containing solid and wireframe clashing meshes
    - no_clash_paths_xform (tuple[str, str]): Paths of xform containing solid and wireframe non-clashing meshes
    - do_clash_paths_wireframe (tuple[str, str]): Paths of meshes representing clashing faces in wireframe (A/B)
    - no_clash_paths_wireframe (tuple[str, str]): Paths of meshes representing clashing faces in wireframe (A/B)
    - outlines_path (str): Path of the intersection outline curve

    """

    overlap_id: str = ""
    do_clash_paths_solid: tuple[str, str] = ("", "")
    no_clash_paths_solid: tuple[str, str] = ("", "")
    do_clash_paths_xform: tuple[str, str] = ("", "")
    no_clash_paths_xform: tuple[str, str] = ("", "")
    do_clash_paths_wireframe: tuple[str, str] = ("", "")
    no_clash_paths_wireframe: tuple[str, str] = ("", "")
    outlines_path: str = ""
    outlines_hidden: bool = False


@dataclass(init=False)
class ClashViewportMeshesPair:
    clash_xform: tuple[UsdGeom.Xform, UsdGeom.Xform]
    clash_solid: tuple[UsdGeom.Mesh, UsdGeom.Mesh]
    clash_wireframe: tuple[UsdGeom.Mesh, UsdGeom.Mesh]


class ClashViewportMeshes:

    @staticmethod
    def create_clash_pairs(
        source_prim_0: Usd.Prim | None,
        source_prim_1: Usd.Prim | None,
        usd_faces_0: wp.array | None,
        usd_faces_1: wp.array | None,
        collision_outline: wp.array,
        usd_timecode: Usd.TimeCode,
        base_clash_path: str,
        material_paths: ClashViewportMaterialPaths,
        destination_stage: Callable[[str], Usd.Stage],
        create_wireframe: bool,
    ) -> ClashViewportMeshPaths:
        """Creates 5 meshes, from the two source prims.
         Two of them are made only of clashing (intersecting) faces from source_prim_0 and source_prim_1.
         Additional two are made of non-clashing faces from source_prim_0 and source_prim_1.
         If provided also the collision_outline will be generated, that is a curve represeting intersection profile.
         Everything will be sampled at given usd_timecode and meshes will be created as children of base_clash_path, on
         the given destination_stage.
         Materials will be used as specified in materials_path.

         Args:
        - source_prim_0 (Usd.Prim | None): The first prim in the pair to generate the clash and no-clash meshes for
        - source_prim_1 (Usd.Prim | None): The second prim in the pair to generate the clash and no-clash meshes for
        - usd_faces_0 (wp.array(dtype=wp.uint32) | None): List of face indices that are clashing in source_prim_0
        - usd_faces_1 (wp.array(dtype=wp.uint32) | None): List of face indices that are clashing in source_prim_1
        - collision_outline (wp.array(dtype=wp.float32)): List of floats that will be interpreted as 3d vectors defining the collision outline
        - usd_timecode (Usd.Timecode): The timecode at which the meshes and transforms will be sampled
        - base_clash_path (str): The root USD path where to create xforms, solid, wireframe and collision outline meshes
        - material_paths (ClashViewportMaterialPaths): USD paths of the materials used for solid, wireframe and outline
        - destination_stage (Callable[[str], Usd.Stage]): Callback to get the stage where a given mesh should be created
        - create_wireframe (bool): If True, wireframes will be created for the clash mesh
        """
        do_clash_paths_solid = ["", ""]
        no_clash_paths_solid = ["", ""]
        do_clash_paths_xform = ["", ""]
        no_clash_paths_xform = ["", ""]
        do_clash_paths_wireframe = ["", ""]
        no_clash_paths_wireframe = ["", ""]
        if source_prim_0:
            pair0 = ClashViewportMeshes.create_single_clash_pair(
                source_prim_0,
                usd_faces_0,
                usd_timecode,
                base_clash_path,
                0,
                material_paths,
                destination_stage,
                create_wireframe,
            )
            if pair0.clash_solid[0]:
                do_clash_paths_xform[0] = str(pair0.clash_xform[0].GetPath())
                do_clash_paths_solid[0] = str(pair0.clash_solid[0].GetPath())
            if pair0.clash_solid[1]:
                no_clash_paths_xform[0] = str(pair0.clash_xform[1].GetPath())
                no_clash_paths_solid[0] = str(pair0.clash_solid[1].GetPath())
            if pair0.clash_wireframe[0]:
                do_clash_paths_wireframe[0] = str(pair0.clash_wireframe[0].GetPath())
            if pair0.clash_wireframe[1]:
                no_clash_paths_wireframe[0] = str(pair0.clash_wireframe[1].GetPath())
        if source_prim_1:
            pair1 = ClashViewportMeshes.create_single_clash_pair(
                source_prim_1,
                usd_faces_1,
                usd_timecode,
                base_clash_path,
                1,
                material_paths,
                destination_stage,
                create_wireframe,
            )
            if pair1.clash_solid[1]:
                do_clash_paths_xform[1] = str(pair1.clash_xform[0].GetPath())
                do_clash_paths_solid[1] = str(pair1.clash_solid[0].GetPath())
            if pair1.clash_solid[1]:
                no_clash_paths_xform[1] = str(pair1.clash_xform[1].GetPath())
                no_clash_paths_solid[1] = str(pair1.clash_solid[1].GetPath())
            if pair1.clash_wireframe[1]:
                do_clash_paths_wireframe[1] = str(pair1.clash_wireframe[0].GetPath())
            if pair1.clash_wireframe[1]:
                no_clash_paths_wireframe[1] = str(pair1.clash_wireframe[1].GetPath())

        clash_info_paths = ClashViewportMeshPaths()
        clash_info_paths.do_clash_paths_xform = (do_clash_paths_xform[0], do_clash_paths_xform[1])
        clash_info_paths.do_clash_paths_solid = (do_clash_paths_solid[0], do_clash_paths_solid[1])
        clash_info_paths.no_clash_paths_xform = (no_clash_paths_xform[0], no_clash_paths_xform[1])
        clash_info_paths.no_clash_paths_solid = (no_clash_paths_solid[0], no_clash_paths_solid[1])
        clash_info_paths.do_clash_paths_wireframe = (do_clash_paths_wireframe[0], do_clash_paths_wireframe[1])
        clash_info_paths.no_clash_paths_wireframe = (no_clash_paths_wireframe[0], no_clash_paths_wireframe[1])
        return clash_info_paths

    @staticmethod
    def create_single_clash_pair(
        source_prim: Usd.Prim,
        usd_faces: wp.array | None,
        usd_timecode: Usd.TimeCode,
        base_clash_path: str,
        index: int,
        material_paths: ClashViewportMaterialPaths,
        destination_stage: Callable[[str], Usd.Stage],
        create_wireframe: bool,
    ) -> ClashViewportMeshesPair:
        """Creates solid and wireframe meshes for a given source prim, putting them under an xform.
         One is made only of clashing (intersecting) faces from source_prim.
         The other is made of non-clashing faces from source_prim.
         Everything will be sampled at given usd_timecode and meshes will be created as children of base_clash_path, on
         the given destination_stage.
         Materials will be used as specified in materials_path, using index to lookup in material paths array.

         Args:
        - source_prim (Usd.Prim): The prim to generate the clash and no-clash meshes for
        - usd_faces (wp.array(dtype=wp.uint32)): List of face indices that are clashing in source_prim
        - usd_timecode (Usd.Timecode): The timecode at which the meshes and transforms will be sampled
        - base_clash_path (str): The root USD path where to create xforms, solid, wireframe and collision outline meshes
        - material_paths (ClashViewportMaterialPaths): USD paths of the materials used for solid, wireframe and outline
        - destination_stage (Callable[[str], Usd.Stage]): Callback to get the stage where a given mesh should be created
        - create_wireframe (bool): If True, wireframes will be created for the clash mesh
        """
        clash_mesh_pair = ClashViewportMeshesPair()
        with CodeTimer("create_clash_xform"):
            UsdGeom.Xform.Define(destination_stage(base_clash_path), base_clash_path)
            xform = ClashViewportMeshes.create_clash_xform(
                source_prim,
                usd_timecode,
                f"{base_clash_path}/do_clash_{index}",
                f"{base_clash_path}/no_clash_{index}",
                destination_stage,
            )
            clash_mesh_pair.clash_xform = xform

        with CodeTimer("create_clash_solid_meshes"):
            if ClashViewportSettingValues.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS:
                m1 = material_paths.do_clash_emissive_materials[index]
                m2 = material_paths.no_clash_translucent_materials[index]
            else:
                m1 = material_paths.do_clash_diffuse_materials[index]
                m2 = material_paths.no_clash_diffuse_materials[index]
            solid = ClashViewportMeshes.create_clash_solid_meshes(
                UsdGeom.Mesh(source_prim),
                usd_faces,
                usd_timecode,
                f"{base_clash_path}/do_clash_{index}/solid",
                f"{base_clash_path}/no_clash_{index}/solid",
                m1,
                m2,
                destination_stage,
            )
            clash_mesh_pair.clash_solid = solid

        with CodeTimer("create_wireframe_mesh"):
            wf0 = None
            wf1 = None
            # Convert usd_faces to numpy array for optimization
            visible_clash_faces = None
            visible_no_clash_faces = None
            total_faces = None
            if create_wireframe and usd_faces is not None and len(usd_faces) > 0:
                # Get the source mesh to determine total face count
                source_mesh = UsdGeom.Mesh(source_prim)
                total_faces = len(source_mesh.GetFaceVertexCountsAttr().Get())

                # For clash mesh, only the clashing faces are visible
                visible_clash_faces = np.array(usd_faces.numpy(), dtype=np.int32)

            if (
                create_wireframe
                and material_paths.do_clash_wireframe_materials[index]
                and clash_mesh_pair.clash_solid[0]
            ):
                wf0 = ClashViewportMeshes.create_wireframe_mesh(
                    clash_mesh_pair.clash_solid[0],
                    usd_timecode,
                    f"{base_clash_path}/do_clash_{index}/wireframe",
                    material_paths.do_clash_wireframe_materials[index],
                    destination_stage,
                    offset_wireframe=True,
                    visible_face_indices=visible_clash_faces,
                )
            if (
                create_wireframe
                and material_paths.no_clash_wireframe_materials[index]
                and clash_mesh_pair.clash_solid[1]
            ):
                if visible_clash_faces is not None and total_faces is not None:
                    # For no-clash mesh, all faces except clashing ones are visible
                    all_faces = np.arange(total_faces, dtype=np.int32)
                    visible_no_clash_faces = np.setdiff1d(all_faces, visible_clash_faces)

                wf1 = ClashViewportMeshes.create_wireframe_mesh(
                    clash_mesh_pair.clash_solid[1],
                    usd_timecode,
                    f"{base_clash_path}/no_clash_{index}/wireframe",
                    material_paths.no_clash_wireframe_materials[index],
                    destination_stage,
                    offset_wireframe=True,
                    visible_face_indices=visible_no_clash_faces,
                )
            # Only create wireframe for clash mesh
            clash_mesh_pair.clash_wireframe = (wf0, wf1)
        return clash_mesh_pair

    @staticmethod
    def create_clash_xform(
        source_prim: Usd.Prim,
        usd_timecode: Usd.TimeCode,
        do_clash_path: str,
        no_clash_path: str,
        destination_stage: Callable[[str], Usd.Stage],
    ) -> tuple[UsdGeom.Xform, UsdGeom.Xform]:
        """Creates an UsdGeom.XForm node for clash and no-clash meshes.
        This also sets Usd.ModelAPI Kind as Kind.Tokens.component and bakes the transformation as matrix from source_prim.

        Args:
        - source_prim (Usd.Prim): The prim to generate the clash and no-clash xform nodes for
        - usd_timecode (Usd.Timecode): The timecode at which the meshes and transforms will be sampled
        - do_clash_path (str): Usd path where to create XForm that will hold clash meshes
        - no_clash_path (str): Usd path where to create XForm that will hold no-clash meshes
        - destination_stage (Callable[[str], Usd.Stage]): Callback to get the stage where a given mesh should be created
        """
        do_xform: UsdGeom.Xform = UsdGeom.Xform.Define(destination_stage(do_clash_path), do_clash_path)
        with Sdf.ChangeBlock():
            Usd.ModelAPI(do_xform).SetKind(Kind.Tokens.component)
            ClashViewportMeshes.flattern_transformation_as_matrix(source_prim, do_xform.GetPrim(), usd_timecode)

        no_xform: UsdGeom.Xform = UsdGeom.Xform.Define(destination_stage(no_clash_path), no_clash_path)
        with Sdf.ChangeBlock():
            Usd.ModelAPI(no_xform).SetKind(Kind.Tokens.component)
            ClashViewportMeshes.flattern_transformation_as_matrix(source_prim, no_xform.GetPrim(), usd_timecode)
        return (do_xform, no_xform)

    @staticmethod
    def create_clash_solid_meshes(
        source_mesh: UsdGeom.Mesh,
        usd_faces: wp.array | None,
        usd_timecode: Usd.TimeCode,
        do_clash_path: str,
        no_clash_path: str,
        do_clash_material: str,
        no_clash_material: str,
        destination_stage: Callable[[str], Usd.Stage],
    ) -> tuple[UsdGeom.Mesh, UsdGeom.Mesh]:
        """Creates the clash and no-clash solid meshes from a given source_mesh.
            Meshes will also be marked to `always_pick_model` so that their top level xform  is selected.

        Args:
        - source_mesh (UsdGeom.Mesh): The mesh to generate the clash and no-clash meshes for
        - usd_faces (wp.array(dtype=wp.uint32)): List of face indices that are clashing in source_mesh
        - usd_timecode (Usd.Timecode): The timecode at which the meshes and transforms will be sampled
        - do_clash_path (str): Usd path where to create clash mesh
        - no_clash_path (str): Usd path where to create no-clash mesh
        - do_clash_material (str): Usd path of material to be used for clash mesh
        - no_clash_material (str): Usd path of material to be used for no-clash mesh
        - destination_stage (Callable[[str], Usd.Stage]): Callback to get the stage where a given mesh should be created
        """
        with CodeTimer("define_mesh"):
            no_clash_mesh: UsdGeom.Mesh | None = UsdGeom.Mesh.Define(destination_stage(no_clash_path), no_clash_path)
            assert no_clash_mesh
            do_clash_mesh: UsdGeom.Mesh | None = UsdGeom.Mesh.Define(destination_stage(do_clash_path), do_clash_path)
            assert do_clash_mesh
            do_clash_mesh.GetPrim().SetMetadata("always_pick_model", True)
            no_clash_mesh.GetPrim().SetMetadata("always_pick_model", True)

        with CodeTimer(f"split_mesh_along_faces ({do_clash_path})"):
            clash_mesh_normals = ClashViewportSettingValues.USE_SOURCE_NORMALS
            with Sdf.ChangeBlock():
                ClashViewportMeshes.split_mesh_along_faces(
                    source_mesh,
                    do_clash_mesh,
                    no_clash_mesh,
                    usd_faces,
                    usd_timecode,
                    clash_mesh_normals,
                )
            if no_clash_mesh.GetFaceCount() == 0:
                no_clash_mesh = None
            if do_clash_mesh.GetFaceCount() == 0:
                do_clash_mesh = None

        with CodeTimer("set_materials"):
            if do_clash_mesh:
                material0 = UsdShade.Material.Get(destination_stage(do_clash_material), do_clash_material)
                binding = UsdShade.MaterialBindingAPI.Apply(do_clash_mesh.GetPrim())
                binding.Bind(material0, UsdShade.Tokens.weakerThanDescendants)
            if no_clash_mesh:
                material0 = UsdShade.Material.Get(destination_stage(no_clash_material), no_clash_material)
                binding = UsdShade.MaterialBindingAPI.Apply(no_clash_mesh.GetPrim())
                binding.Bind(material0, UsdShade.Tokens.weakerThanDescendants)

        return (do_clash_mesh, no_clash_mesh)

    @staticmethod
    def create_wireframe_mesh(
        source_mesh: UsdGeom.Mesh,
        usd_timecode: Usd.TimeCode,
        wireframe_path: str,
        wireframe_material_path: str,
        destination_stage: Callable[[str], Usd.Stage],
        offset_wireframe: bool = True,
        visible_face_indices: Optional[np.ndarray] = None,
    ) -> UsdGeom.Mesh:
        """Create a wireframe mesh from a given source mesh.

        Args:
        - source_mesh (UsdGeom.Mesh): The mesh to generate the wireframe for
        - usd_timecode (Usd.Timecode): The timecode at which the mesh will be sampled
        - wireframe_path (str): Usd path where to create wireframe mesh
        - wireframe_material_path (str): Usd path of material to be used for wireframe mesh
        - destination_stage (Callable[[str], Usd.Stage]): Callback to get the stage where a given mesh should be created
        - offset_wireframe (bool): If True, the wireframe will be offset by a small amount to avoid z-fighting
        - visible_face_indices (Optional[np.ndarray]): Optional array of visible face indices for optimization
        """
        wireframe_material = UsdShade.Material.Get(destination_stage(wireframe_material_path), wireframe_material_path)
        destination_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(destination_stage(wireframe_path), wireframe_path)
        if offset_wireframe:
            ClashViewportWireframes.clone_mesh_with_offset(
                source_mesh, destination_mesh, usd_timecode, visible_face_indices=visible_face_indices
            )
        else:
            ClashViewportMeshes.clone_mesh(source_mesh, destination_mesh, usd_timecode, False)
        prim0: Usd.Prim = destination_mesh.GetPrim()
        prim0.CreateAttribute("primvars:wireframe", Sdf.ValueTypeNames.Bool).Set(True)
        prim0.SetMetadata("always_pick_model", True)
        binding = UsdShade.MaterialBindingAPI.Apply(prim0)
        binding.Bind(wireframe_material, UsdShade.Tokens.weakerThanDescendants)
        return destination_mesh

    @staticmethod
    def create_outline_curve(
        collision_outline: wp.array,
        outlines_path: str,
        outline_material_path: str,
        destination_stage: Usd.Stage,
    ) -> bool:
        """Create an outline curve UsdGeom.BasisCurves from a sequence of floats.

        Args:
        - collision_outline (wp.array): List of floats that will be interpreted as 3d vectors defining the collision outline
        - outlines_path (str): Usd path of where outlines will be created as UsdGeom.BasisCurves
        - outline_material_path (str): Usd path of Material to be used for the generated UsdGeom.BasisCurves
        - destination_stage (Usd.Stage): Stage where a given mesh should be created
        """
        curve: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Define(destination_stage, outlines_path)
        with Sdf.ChangeBlock():
            if ClashViewportMeshes.build_outlines_curve(curve, collision_outline):
                material = UsdShade.Material.Get(destination_stage, outline_material_path)
                binding = UsdShade.MaterialBindingAPI.Apply(curve.GetPrim())
                binding.Bind(material, UsdShade.Tokens.weakerThanDescendants)
                return True
        destination_stage.RemovePrim(outlines_path)
        return False

    @staticmethod
    def clone_mesh(
        source_mesh: UsdGeom.Mesh,
        destination_mesh: UsdGeom.Mesh,
        usd_timecode: Usd.TimeCode,
        enable_normals: bool,
    ) -> None:
        """Clone a source UsdGeom.Mesh into a destination UsdGeom.Mesh at given timecode.

        Attributes copied are: Points, FaceVertexIndices, FaceVertexCounts, Extent, SubdivisionScheme, HoleIndices.
        Optionally can copy normals too.

        Args:
        - source_mesh (UsdGeom.Mesh): A mesh to be cloned
        - destination_mesh (UsdGeom.Mesh): A mesh that will receive clone of source_mesh
        - usd_timecode (Usd.Timecode): A timecode where the mesh to be cloned will be sampled at
        - enable_normals (bool): If True it will also copy normals (Normals / NormalsInterpolation)
        """
        # Mandatory attributes
        destination_mesh.GetPointsAttr().Set(source_mesh.GetPointsAttr().Get(usd_timecode))
        destination_mesh.GetFaceVertexIndicesAttr().Set(source_mesh.GetFaceVertexIndicesAttr().Get(usd_timecode))
        destination_mesh.GetFaceVertexCountsAttr().Set(source_mesh.GetFaceVertexCountsAttr().Get(usd_timecode))

        # Optional attributes
        try:
            destination_mesh.GetExtentAttr().Set(source_mesh.GetExtentAttr().Get(usd_timecode))
        except Exception:
            pass
        try:
            destination_mesh.GetSubdivisionSchemeAttr().Set(source_mesh.GetSubdivisionSchemeAttr().Get(usd_timecode))
        except Exception:
            pass
        try:
            destination_mesh.GetHoleIndicesAttr().Set(source_mesh.GetHoleIndicesAttr().Get(usd_timecode))
        except Exception:
            pass
        try:
            if enable_normals:
                destination_mesh.GetNormalsAttr().Set(source_mesh.GetNormalsAttr().Get(usd_timecode))
                destination_mesh.SetNormalsInterpolation(source_mesh.GetNormalsInterpolation())
        except Exception:
            pass

    @staticmethod
    def _compute_vertex_normals(
        points: np.ndarray,
        face_vertex_indices: Sequence[int],
        face_vertex_counts: Sequence[int],
    ) -> np.ndarray:
        """Compute per-vertex normals from mesh geometry.

        This computes normals by averaging face normals for all faces that share a vertex.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_vertex_indices (Sequence[int]): Indices into points array for each face
        - face_vertex_counts (Sequence[int]): Number of vertices per face

        Returns:
        - np.ndarray: Array of vertex normals (N x 3)
        """
        num_points = len(points)
        vertex_normals = np.zeros((num_points, 3), dtype=np.float32)
        vertex_counts = np.zeros(num_points, dtype=np.int32)

        # Convert to numpy arrays for easier indexing
        face_indices_array = np.array(face_vertex_indices)
        face_counts_array = np.array(face_vertex_counts)

        # Process each face
        idx = 0
        for face_count in face_counts_array:
            if face_count < 3:
                idx += face_count
                continue

            # Get vertices for this face
            face_indices = face_indices_array[idx : idx + face_count]

            # Compute face normal using Newell's method for robustness
            face_normal = np.zeros(3, dtype=np.float32)
            for i in range(face_count):
                v0 = points[face_indices[i]]
                v1 = points[face_indices[(i + 1) % face_count]]
                face_normal += np.cross(v0, v1)

            # Normalize face normal
            length = np.linalg.norm(face_normal)
            if length > 1e-10:
                face_normal /= length

                # Add face normal to all vertices of this face
                for vertex_idx in face_indices:
                    vertex_normals[vertex_idx] += face_normal
                    vertex_counts[vertex_idx] += 1

            idx += face_count

        # Normalize vertex normals
        for i in range(num_points):
            if vertex_counts[i] > 0:
                length = np.linalg.norm(vertex_normals[i])
                if length > 1e-10:
                    vertex_normals[i] /= length
                else:
                    # Default to up vector if normal is degenerate
                    vertex_normals[i] = np.array([0, 1, 0], dtype=np.float32)
            else:
                # Default to up vector for isolated vertices
                vertex_normals[i] = np.array([0, 1, 0], dtype=np.float32)

        return vertex_normals

    @staticmethod
    def split_mesh_along_faces(
        source_mesh: UsdGeom.Mesh,
        do_clash_mesh: UsdGeom.Mesh,
        no_clash_mesh: UsdGeom.Mesh,
        usd_faces: wp.array | None,
        usd_timecode: Usd.TimeCode,
        enable_normals: bool,
    ) -> None:
        """Creates two meshes splitting source_mesh along a list of usd_faces at a given timecode.

        Args:
        - source_mesh (UsdGeom.Mesh): A mesh to be split
        - do_clash_mesh (UsdGeom.Mesh): A mesh that will have only faces as specified in usd_faces
        - no_clash_mesh (UsdGeom.Mesh): A mesh that will have only faces not specified in usd_faces
        - usd_faces (wp.array(dtype=wp.uint32)): List of face indices that are used to split the source_mesh in *_clash_mesh
        - usd_timecode (Usd.Timecode): The timecode at which the mesh will be sampled
        - enable_normals (bool): If True it will also copy normals (Normals / NormalsInterpolation)
        """
        if not source_mesh or not do_clash_mesh:
            return
        number_of_faces = len(source_mesh.GetFaceVertexCountsAttr().Get())

        usd_faces_len = len(usd_faces) if usd_faces is not None else number_of_faces

        # Clone both meshes
        if usd_faces_len > 0:
            with CodeTimer("clone_mesh do_clash_mesh"):
                ClashViewportMeshes.clone_mesh(source_mesh, do_clash_mesh, usd_timecode, enable_normals)

        # If we're asked to split the entire mesh we just avoid doing any useless work
        if number_of_faces == usd_faces_len:
            return

        if no_clash_mesh:
            with CodeTimer("clone_mesh no_clash_mesh"):
                ClashViewportMeshes.clone_mesh(source_mesh, no_clash_mesh, usd_timecode, enable_normals)

        if usd_faces_len == 0 or usd_faces is None:
            return

        if not isinstance(usd_faces, wp.array):
            raise Exception("usd_faces must be a warp.array(dtype=warp.uint32)")

        # For clash mesh, hide all faces in the source mesh that are not in the 'clashing' list
        # For no clash mesh, hide all faces NOT in the 'clashing' list plus potential existing holes

        with CodeTimer(f"create_holes no_clash_mesh ({no_clash_mesh.GetPrim().GetPath()})"):
            # TODO: Figure out if it's feasible recomputing extents for clash meshes without excessive slowdown
            # Note: Hole Indices MUST be sorted in order for the renderer to pick them up properly
            np_usd_faces = np.sort(np.array(usd_faces.numpy()))
            np_existing_holes = None
            existing_holes_attribute = source_mesh.GetHoleIndicesAttr()
            if existing_holes_attribute:
                np_existing_holes = np.array(existing_holes_attribute.Get())
            if np_existing_holes is not None and len(np_existing_holes):
                # If we have existing holes, we concatenate with the clash faces to keep them hidden
                # We have to sort as well because otherwise renderer will not pick them up properly
                np_faces_to_hide = np.sort(np.concatenate((np_usd_faces, np_existing_holes)))
            else:
                np_faces_to_hide = np_usd_faces
            hole_indices = no_clash_mesh.CreateHoleIndicesAttr()
            hole_indices.Set(np_faces_to_hide)

        with CodeTimer(f"create_holes do_clash_mesh ({do_clash_mesh.GetPrim().GetPath()})"):
            all_numbers = np.arange(number_of_faces)
            result_np = np.setdiff1d(all_numbers, np_usd_faces)
            hole_indices = do_clash_mesh.CreateHoleIndicesAttr()
            hole_indices.Set(result_np)

    @staticmethod
    def build_outlines_curve(curve: UsdGeom.BasisCurves, outline: wp.array) -> bool:
        """Create an UsdGeom.BasisCurve out of the given sequence 3D points representing an outline.

        Args:
        - curve (UsdGeom.BasisCurves): A curve that will be filled with the given collision outline data
        - outline (wp.array(dtype=wp.float32)): List of floats that will be interpreted as 3d vectors defining the collision outline
        """
        if not isinstance(outline, wp.array):
            raise Exception("outline must be a warp.array(dtype=warp.float32)")
        num_outlines = len(outline)
        if num_outlines < 2:
            return False
        num_points = num_outlines // 3
        num_segments = num_points // 2
        counts = Vt.IntArray(num_segments, 2)

        # Reshape the outline data into a NumPy array (note that this is a Float32 array)
        points = np.array(outline.numpy()).reshape(num_points, 3)

        # Find the extents using a more numerically stable approach
        min_coords = np.min(points, axis=0)
        max_coords = np.max(points, axis=0)
        extent = np.array([min_coords, max_coords])

        outline_width = (
            ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SCALE * ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SIZE
        )

        # Center the outline origin in the center of their extents using a more stable approach
        # Instead of adding min and max and dividing by 2, we compute the center as min + (max-min)/2
        extent_center = min_coords + (max_coords - min_coords) * 0.5

        # In case of a simple linear segment, extent will be 0 on some directions, so we give it at least some width
        extent_size = max_coords - min_coords
        if math.fabs(extent_size[0]) < 1e-6:
            extent_size[0] = outline_width * 4
        if math.fabs(extent_size[1]) < 1e-6:
            extent_size[1] = outline_width * 4
        if math.fabs(extent_size[2]) < 1e-6:
            extent_size[2] = outline_width * 4

        # Recenter points using a more stable approach
        # Instead of subtracting the center directly, we subtract min and then subtract half the extent
        points = points - min_coords - (max_coords - min_coords) * 0.5

        # Update extent to be centered around origin
        extent = np.array([-extent_size * 0.5, extent_size * 0.5])

        # Enlarge extent by double its size for better focusing
        extent[0] -= extent_size / 2
        extent[1] += extent_size / 2

        # TODO: As optimization we could probably nest two transforms, setting the root one as component and making the
        # outline force select component, to avoid transforming all the points...but numpy is fast enough for now

        # Update transformation to reflect changed origin
        extent_float64 = tuple(extent_center.astype(np.float64))  # explicit cast to float64 to avoid precision loss
        curve_xformable = UsdGeom.Xformable(curve)
        curve_xformable.ClearXformOpOrder()
        translate_op: UsdGeom.XformOp = curve_xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
        translate_op.Set(extent_float64)

        Usd.ModelAPI(curve).SetKind(Kind.Tokens.component)

        # Fill all attributes from points, extents, widths
        curve.CreateCurveVertexCountsAttr().Set(counts)
        curve.CreateExtentAttr().Set(extent)
        curve.CreatePointsAttr().Set(points)

        widths = np.full(num_points, outline_width, dtype=np.float32)
        curve.CreateWidthsAttr().Set(widths)
        curve.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
        curve.CreateBasisAttr().Set("bspline")
        curve.CreateTypeAttr().Set("linear")
        curve.CreateWrapAttr().Set("nonperiodic")
        return True

    @staticmethod
    def flattern_transformation_as_matrix(source_prim: Usd.Prim, dest_prim: Usd.Prim, usd_timecode: Usd.TimeCode):
        """Sets a matrix transform op in dest_prim as a flatterned transformation of source_prim.

        Args:
        - source_prim (Usd.Prim): Source primitive with some applied XForms
        - dest_prim (Usd.Prim): Destination primitive that will receive the matrix transformation
        - usd_timecode (Usd.TimeCode): Usd timecode where to sample the transformation.
        """
        source_matrix = UsdGeom.XformCache(usd_timecode).GetLocalToWorldTransform(source_prim)
        dest_xformable = UsdGeom.Xformable(dest_prim)
        dest_xformable.ClearXformOpOrder()
        matrix_op = dest_xformable.AddTransformOp()
        matrix_op.Set(Gf.Matrix4d(source_matrix))
