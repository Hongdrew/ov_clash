# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Optional, Union

import numpy as np
import numpy.typing as npt
import carb

from .bake_utilities import CodeTimer
from .bake_options import ClashBakeOptions

__all__ = ["ClashBakeOffsetMesh"]


class ClashBakeOffsetMesh:
    """Helper class for computing offset vertices for meshes to avoid z-fighting."""

    @staticmethod
    def compute_offset_points(
        points: np.ndarray,
        face_vertex_indices: np.ndarray,
        face_vertex_counts: np.ndarray,
        epsilon: float = 0.001,
        visible_face_indices: Optional[np.ndarray] = None,
        options: ClashBakeOptions = ClashBakeOptions(),
    ) -> np.ndarray:
        """Compute offset points along vertex normals to avoid z-fighting.

        This method computes vertex normals and offsets all vertices along their normals by a small epsilon value.
        If normals are not available, they will be computed as vertex normals from face normals.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_vertex_indices (np.ndarray): Indices into points array for each face
        - face_vertex_counts (np.ndarray): Number of vertices per face
        - epsilon (float): The offset distance along normals to avoid z-fighting (default: 0.001)
        - visible_face_indices (Optional[np.ndarray]): Optional array of face indices that will be visible
                                                        (used to optimize normal computation)
        - options (ClashBakeOptions): Options for the bake (for timing/profiling)

        Returns:
        - np.ndarray: Array of offset vertex positions (N x 3)
        """
        # Compute vertex normals
        with CodeTimer("compute_vertex_normals", options):
            normals = ClashBakeOffsetMesh._compute_vertex_normals_optimized(
                points, face_vertex_indices, face_vertex_counts, visible_face_indices, options
            )

        # Offset points along normals
        offset_points = points + normals * epsilon

        return offset_points

    @staticmethod
    def _compute_vertex_normals_optimized(
        points: np.ndarray,
        face_vertex_indices: Union[np.ndarray, npt.NDArray],
        face_vertex_counts: Union[np.ndarray, npt.NDArray],
        visible_face_indices: Optional[np.ndarray] = None,
        options: ClashBakeOptions = ClashBakeOptions(),
    ) -> np.ndarray:
        """Compute per-vertex normals from mesh geometry using optimized vectorized operations.

        This computes normals by averaging face normals for all faces that share a vertex.
        If visible_face_indices is provided, only those faces are considered for normal computation.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_vertex_indices (Sequence[int]): Indices into points array for each face
        - face_vertex_counts (Sequence[int]): Number of vertices per face
        - visible_face_indices (Optional[np.ndarray]): Optional array of face indices to process (optimization)
        - options (ClashBakeOptions): Options for the bake (for timing/profiling)

        Returns:
        - np.ndarray: Array of vertex normals (N x 3)
        """
        num_points = len(points)
        vertex_normals = np.zeros((num_points, 3), dtype=np.float32)

        # Convert to numpy arrays
        face_indices_array = np.array(face_vertex_indices, dtype=np.int32)
        face_counts_array = np.array(face_vertex_counts, dtype=np.int32)

        # Build a mask or set of faces to process
        if visible_face_indices is not None and len(visible_face_indices) > 0:
            total_face_count = len(face_counts_array)
            if options._debug_mode:
                carb.log_info(
                    f"Optimizing normal computation: processing {len(visible_face_indices)} of {total_face_count} faces "
                    f"({100.0 * len(visible_face_indices) / total_face_count:.1f}%)"
                )
            # Create a boolean mask for fast lookup
            faces_mask = np.zeros(total_face_count, dtype=bool)
            faces_mask[visible_face_indices] = True
        else:
            faces_mask = np.ones(len(face_counts_array), dtype=bool)

        # Compute cumulative offsets for each face's starting index
        face_offsets = np.concatenate(([0], np.cumsum(face_counts_array[:-1])))

        # Process triangles in batch (most common case) - fully vectorized!
        triangle_mask = (face_counts_array == 3) & faces_mask
        if np.any(triangle_mask):
            with CodeTimer("_compute_normals_triangles_vectorized", options):
                ClashBakeOffsetMesh._process_triangles_vectorized(
                    points, face_indices_array, face_offsets, triangle_mask, vertex_normals
                )

        # Process quads in batch (also common) - fully vectorized!
        quad_mask = (face_counts_array == 4) & faces_mask
        if np.any(quad_mask):
            with CodeTimer("_compute_normals_quads_vectorized", options):
                ClashBakeOffsetMesh._process_quads_vectorized(
                    points, face_indices_array, face_offsets, quad_mask, vertex_normals
                )

        # Process general polygons with a loop (less common)
        polygon_mask = (face_counts_array > 4) & faces_mask
        if np.any(polygon_mask):
            with CodeTimer("_compute_normals_polygons", options):
                ClashBakeOffsetMesh._process_polygons(
                    points, face_indices_array, face_counts_array, face_offsets, polygon_mask, vertex_normals
                )

        # Normalize all vertex normals at once (vectorized)
        lengths = np.linalg.norm(vertex_normals, axis=1, keepdims=True)
        # Avoid division by zero
        lengths = np.where(lengths > 1e-10, lengths, 1.0)
        vertex_normals = vertex_normals / lengths

        # Set default normal for vertices with zero normal (isolated or degenerate)
        zero_mask = np.linalg.norm(vertex_normals, axis=1) < 1e-10
        vertex_normals[zero_mask] = np.array([0, 1, 0], dtype=np.float32)

        return vertex_normals

    @staticmethod
    def _process_triangles_vectorized(
        points: np.ndarray,
        face_indices_array: np.ndarray,
        face_offsets: np.ndarray,
        triangle_mask: np.ndarray,
        vertex_normals: np.ndarray,
    ) -> None:
        """Process all triangles at once using fully vectorized numpy operations.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_indices_array (np.ndarray): Flat array of all face vertex indices
        - face_offsets (np.ndarray): Starting index in face_indices_array for each face
        - triangle_mask (np.ndarray): Boolean mask indicating which faces are triangles to process
        - vertex_normals (np.ndarray): Output array to accumulate normals into (modified in place)
        """
        # Get the starting offsets for all triangles
        tri_offsets = face_offsets[triangle_mask]
        num_triangles = len(tri_offsets)

        # Build arrays of vertex indices for all triangles at once
        # Shape: (num_triangles, 3)
        tri_idx0 = face_indices_array[tri_offsets]
        tri_idx1 = face_indices_array[tri_offsets + 1]
        tri_idx2 = face_indices_array[tri_offsets + 2]

        # Get all triangle vertices at once
        # Shape: (num_triangles, 3, 3) where last dimension is xyz
        v0 = points[tri_idx0]  # (num_triangles, 3)
        v1 = points[tri_idx1]  # (num_triangles, 3)
        v2 = points[tri_idx2]  # (num_triangles, 3)

        # Compute all edge vectors at once
        edge1 = v1 - v0  # (num_triangles, 3)
        edge2 = v2 - v0  # (num_triangles, 3)

        # Compute all face normals at once using vectorized cross product
        face_normals = np.cross(edge1, edge2)  # (num_triangles, 3)

        # Normalize all face normals at once
        lengths = np.linalg.norm(face_normals, axis=1, keepdims=True)  # (num_triangles, 1)
        valid_mask = lengths[:, 0] > 1e-10
        face_normals[valid_mask] = face_normals[valid_mask] / lengths[valid_mask]

        # Accumulate normals to vertices using np.add.at (handles duplicate indices correctly)
        # This adds each face normal to all three vertices of that triangle
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) > 0:
            # Stack all vertex indices that need updating (3 per valid triangle)
            all_vertex_indices = np.column_stack(
                [tri_idx0[valid_indices], tri_idx1[valid_indices], tri_idx2[valid_indices]]
            ).ravel()  # Flatten to 1D array

            # Repeat each face normal 3 times (once for each vertex)
            all_normals = np.repeat(face_normals[valid_indices], 3, axis=0)

            # Accumulate to vertex normals (np.add.at handles duplicate indices correctly)
            np.add.at(vertex_normals, all_vertex_indices, all_normals)

    @staticmethod
    def _process_quads_vectorized(
        points: np.ndarray,
        face_indices_array: np.ndarray,
        face_offsets: np.ndarray,
        quad_mask: np.ndarray,
        vertex_normals: np.ndarray,
    ) -> None:
        """Process all quads at once using fully vectorized numpy operations.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_indices_array (np.ndarray): Flat array of all face vertex indices
        - face_offsets (np.ndarray): Starting index in face_indices_array for each face
        - quad_mask (np.ndarray): Boolean mask indicating which faces are quads to process
        - vertex_normals (np.ndarray): Output array to accumulate normals into (modified in place)
        """
        # Get the starting offsets for all quads
        quad_offsets = face_offsets[quad_mask]
        num_quads = len(quad_offsets)

        # Build arrays of vertex indices for all quads at once
        # Shape: (num_quads, 4)
        quad_idx0 = face_indices_array[quad_offsets]
        quad_idx1 = face_indices_array[quad_offsets + 1]
        quad_idx2 = face_indices_array[quad_offsets + 2]
        quad_idx3 = face_indices_array[quad_offsets + 3]

        # Get all quad vertices at once
        # Shape: (num_quads, 3) where last dimension is xyz
        v0 = points[quad_idx0]
        v1 = points[quad_idx1]
        v2 = points[quad_idx2]
        v3 = points[quad_idx3]

        # Compute quad normal using two triangles: (v0,v1,v2) and (v0,v2,v3)
        edge1 = v1 - v0  # (num_quads, 3)
        edge2 = v2 - v0  # (num_quads, 3)
        edge3 = v3 - v0  # (num_quads, 3)

        # Compute normals for both triangles
        n1 = np.cross(edge1, edge2)  # Triangle (v0,v1,v2)
        n2 = np.cross(edge2, edge3)  # Triangle (v0,v2,v3)

        # Average the two triangle normals (sum them, normalize later)
        face_normals = n1 + n2  # (num_quads, 3)

        # Normalize all face normals at once
        lengths = np.linalg.norm(face_normals, axis=1, keepdims=True)  # (num_quads, 1)
        valid_mask = lengths[:, 0] > 1e-10
        face_normals[valid_mask] = face_normals[valid_mask] / lengths[valid_mask]

        # Accumulate normals to vertices using np.add.at
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) > 0:
            # Stack all vertex indices that need updating (4 per valid quad)
            all_vertex_indices = np.column_stack(
                [quad_idx0[valid_indices], quad_idx1[valid_indices], quad_idx2[valid_indices], quad_idx3[valid_indices]]
            ).ravel()  # Flatten to 1D array

            # Repeat each face normal 4 times (once for each vertex)
            all_normals = np.repeat(face_normals[valid_indices], 4, axis=0)

            # Accumulate to vertex normals (np.add.at handles duplicate indices correctly)
            np.add.at(vertex_normals, all_vertex_indices, all_normals)

    @staticmethod
    def _process_polygons(
        points: np.ndarray,
        face_indices_array: np.ndarray,
        face_counts_array: np.ndarray,
        face_offsets: np.ndarray,
        polygon_mask: np.ndarray,
        vertex_normals: np.ndarray,
    ) -> None:
        """Process general polygons (5+ vertices) using Newell's method.

        Args:
        - points (np.ndarray): Array of vertex positions (N x 3)
        - face_indices_array (np.ndarray): Flat array of all face vertex indices
        - face_counts_array (np.ndarray): Number of vertices per face
        - face_offsets (np.ndarray): Starting index in face_indices_array for each face
        - polygon_mask (np.ndarray): Boolean mask indicating which polygon faces to process
        - vertex_normals (np.ndarray): Output array to accumulate normals into (modified in place)
        """
        # Get indices of faces to process
        face_indices_to_process = np.where(polygon_mask)[0]

        for face_idx in face_indices_to_process:
            face_count = face_counts_array[face_idx]
            face_start_idx = face_offsets[face_idx]

            # Get vertex indices for this face
            face_verts = face_indices_array[face_start_idx : face_start_idx + face_count]

            # General polygon - use Newell's method (vectorized)
            verts = points[face_verts]
            verts_rolled = np.roll(verts, -1, axis=0)
            face_normal = np.sum(np.cross(verts, verts_rolled), axis=0)

            # Normalize face normal
            length = np.linalg.norm(face_normal)
            if length > 1e-10:
                face_normal = face_normal / length
                # Add to all vertices of this face
                vertex_normals[face_verts] += face_normal
