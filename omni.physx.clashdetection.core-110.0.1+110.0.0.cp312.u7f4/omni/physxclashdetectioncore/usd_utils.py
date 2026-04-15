# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
from typing import List, Optional, Callable
from pxr import Usd, Sdf, Gf, UsdGeom
from .utils import from_json_str_safe, to_json_str_safe


def get_prim_children_paths(
    prim: Usd.Prim,
    exclude_invisible: bool = True,
    prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None
) -> List[Sdf.Path]:
    """Returns paths of all children of the given prim, optionally filtered by a custom predicate and visibility.

    This function traverses the prim hierarchy starting from the given prim and returns paths to all child prims
    that match the specified filtering criteria. The traversal also handles instance proxies.

    Inactive prims are always excluded from the results. If exclude_invisible is True, prims with visibility=invisible
    and all their descendants will be excluded.

    Args:
        prim (Usd.Prim): The root prim to start traversal from.
        exclude_invisible (bool): If True, excludes prims with visibility=invisible and their descendants.
            If False, includes all prims regardless of visibility. Defaults to True.
        prim_accept_fn (Optional[Callable[[Usd.Prim], bool]]): Optional predicate function that takes a Usd.Prim
            and returns True if the prim should be included. If None, all active prims are accepted. Defaults to None.

    Returns:
        List[Sdf.Path]: List of paths to child prims that match the filtering criteria. The paths are returned
            as Sdf.Path objects.
    """
    paths = []
    traversal = iter(Usd.PrimRange(prim, Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)))
    for p in traversal:
        if p.IsActive():
            if exclude_invisible and p.GetAttribute('visibility').Get() == UsdGeom.Tokens.invisible:
                traversal.PruneChildren()  # Skip invisible prims and their children
                continue
            if prim_accept_fn is None or prim_accept_fn(p):
                paths.append(p.GetPath())
    return paths


def get_list_of_prim_paths(
    stage: Usd.Stage,
    prim_str_path: str,
    add_prim_children: bool = False,
    prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None
) -> List[Sdf.Path]:
    """Returns list of prim paths for a given prim or collection.

    Can optionally include child prims but not for collections.

    Args:
        stage (Usd.Stage): The stage containing the prims.
        prim_str_path (str): The path to the prim or collection.
        add_prim_children (bool): If True, includes paths of all child prims that match prim_accept_fn.
            If False, only returns the path of the specified prim. Defaults to False.
        prim_accept_fn (Optional[Callable[[Usd.Prim], bool]]): Optional predicate function that takes a Usd.Prim
            and returns True if the prim should be included. Only used when add_prim_children is True.
            If None, all active and visible prims are accepted. Defaults to None.

    Returns:
        List[Sdf.Path]: List of prim paths. For a prim input, returns either just the prim path or paths of all
            matching child prims based on add_prim_children. For a collection input, returns paths of all prims
            in the collection (add_prim_children is ignored). Returns empty list if prim/collection not found or on error.
    """
    from .config import ExtensionConfig

    prim_paths: List[Sdf.Path] = []

    if not stage:
        carb.log_error("Invalid stage supplied!")
        return prim_paths

    if not prim_str_path:
        if ExtensionConfig.debug_logging:
            carb.log_info(f"Empty prim path '{prim_str_path}' supplied. Was it intentional?")
        return prim_paths

    if not Sdf.Path.IsValidPathString(prim_str_path):
        carb.log_error(f"Invalid prim path '{prim_str_path}' supplied!")
        return prim_paths

    prim_path = Sdf.Path(prim_str_path)
    prim = stage.GetPrimAtPath(prim_path)

    if prim:
        prim_paths = get_prim_children_paths(prim, True, prim_accept_fn) if add_prim_children else [prim_path]
    else:
        # check if it's a collection
        try:
            collection_api = Usd.CollectionAPI.GetCollection(stage, prim_path)
        except Exception as e:
            carb.log_error(f"No prim or collection on path '{prim_str_path}'. Exception: {e.args[0]}")
            return []
        if collection_api:
            try:
                prim_paths = Usd.CollectionAPI.ComputeIncludedPaths(
                    collection_api.ComputeMembershipQuery(), stage, Usd.TraverseInstanceProxies()
                )
            except Exception as e:
                carb.log_error(f"ComputeIncludedPaths on collection {prim_str_path} failed. Exception: {e.args[0]}")
                return []

    if ExtensionConfig.debug_logging:
        carb.log_info(f"set_scope prims: {prim_paths}")

    return prim_paths


def matrix_to_list(matrix: Gf.Matrix4d) -> List[float]:
    """
    Converts a Gf.Matrix4d to a flat list of 16 floats in row-major order.

    Args:
        matrix (Gf.Matrix4d): The 4x4 matrix to convert.

    Returns:
        List[float]: The matrix elements as a flat list in row-major order.
    """
    return [matrix[i, j] for i in range(4) for j in range(4)]


def list_to_matrix(lst: List[float]) -> Optional[Gf.Matrix4d]:
    """
    Converts a flat list of 16 floats in row-major order to a Gf.Matrix4d.

    Args:
        lst (List[float]): The list of 16 floats to convert.

    Returns:
        Optional[Gf.Matrix4d]: The resulting Gf.Matrix4d or None if input is invalid.
    """
    if lst is None or len(lst) != 16:
        return None

    return Gf.Matrix4d(
        lst[0], lst[1], lst[2], lst[3],
        lst[4], lst[5], lst[6], lst[7],
        lst[8], lst[9], lst[10], lst[11],
        lst[12], lst[13], lst[14], lst[15]
    )


def serialize_matrix_to_json(matrix: Gf.Matrix4d) -> str:
    """Creates json string out of matrix.

    Args:
        matrix (Gf.Matrix4d): The matrix to serialize into a JSON string.

    Returns:
        str: The JSON string representation of the matrix.
    """
    if not matrix:
        return "[]"
    vals = [[matrix[i, j] for j in range(4)] for i in range(4)]
    return to_json_str_safe(vals)


def deserialize_matrix_from_json(json_string: str) -> Optional[Gf.Matrix4d]:
    """Creates matrix out of json string. Returns None in case of failure.

    Args:
        json_string (str): The JSON string to deserialize into a matrix.

    Returns:
        Optional[Gf.Matrix4d]: The deserialized matrix or None if failed.
    """
    if json_string:
        lst = from_json_str_safe(json_string)
        if not lst or len(lst) == 0:
            return None
        try:
            return Gf.Matrix4d(lst)
        except Exception as e:
            carb.log_error(f"Failed to deserialize matrix from JSON string. Exception: {e}")
            return None
    return None


def get_prim_matrix(stage: Usd.Stage, prim_path: str, time: Optional[float] = None) -> Optional[Gf.Matrix4d]:
    """Returns world transformation of a prim on 'prim_path' or None in case of failure.
    If 'time' is None then Usd.TimeCode.Default() is used.

    Args:
        stage (Usd.Stage): The stage containing the prim.
        prim_path (str): The path to the prim.
        time (float, optional): The time of the transformation in seconds. Defaults to Usd.TimeCode.Default().

    Returns:
        Optional[Gf.Matrix4d]: The world transformation matrix or None if failed.
    """
    prim = stage.GetPrimAtPath(prim_path)
    if prim and prim.IsA(UsdGeom.Xformable):
        xform = UsdGeom.Xformable(prim)
        fps = stage.GetTimeCodesPerSecond()
        if fps <= 0.0:
            return None  # FPS is not set, cannot determine TimeCode
        tc = Usd.TimeCode(time * fps) if time is not None else Usd.TimeCode.Default()
        return xform.ComputeLocalToWorldTransform(tc)
    return None
