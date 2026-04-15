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
from typing import List, Optional, Tuple
from pxr import Sdf, Usd, UsdUtils


__all__ = []


def omni_get_current_stage() -> Optional[Usd.Stage]:
    """Returns the current omni.usd stage.

    Returns:
        Optional[Usd.Stage]: The current stage or None in case of failure.
    """
    import omni.usd

    context = omni.usd.get_context()
    if not context:
        carb.log_error("Failed to get omni context!")
        return None
    stage = context.get_stage()  # type: ignore
    return stage


def omni_get_current_stage_id() -> int:
    """Returns the id of the current omni.usd stage.

    Returns:
        int: The id of the current stage or 0 in case of failure.
    """
    stage = omni_get_current_stage()
    if not stage:
        carb.log_error("Failed to get omni stage!")
        return 0
    stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
    return stage_id


def omni_get_path_name_of_current_stage() -> str:
    """Returns the file name of the currently opened stage.

    Returns:
        str: The file name, or an empty string in case of error or if the stage is unnamed.
    """
    stage = omni_get_current_stage()
    if not stage:
        carb.log_error("Failed to get omni stage!")
        return ""
    root_layer = stage.GetRootLayer()
    usd_path = root_layer.realPath
    return usd_path


def debug_print_descendants(prim: Usd.Prim, depth: int = 0) -> None:
    """Prints prim hierarchy out to the console.

    Args:
        prim (Usd.Prim): The prim whose descendants are to be printed.
        depth (int): The current depth in the hierarchy.
    """
    print(f"{'  ' * depth} {prim.GetPath()} ({prim.GetTypeName()})")
    for child in prim.GetChildren():
        debug_print_descendants(child, depth + 1)


def get_prim_kind(prim: Usd.Prim) -> str:
    """Return the 'kind' metadata of a prim, or an empty string if not set.

    Args:
        prim (Usd.Prim): The prim to query.

    Returns:
        str: The kind metadata as a string, or an empty string if not set.
    """
    if not prim or not prim.IsValid():
        return ""
    kind = prim.GetKind() if hasattr(prim, "GetKind") else None
    if kind is not None:
        return str(kind)
    if prim.HasMetadata("kind"):
        return prim.GetMetadata("kind")
    return ""


def find_nearest_group(stage: Usd.Stage, prim_path: Sdf.Path, kinds: List[str], root_prim_path: Sdf.Path) -> Tuple[Sdf.Path, str]:
    """
    Walks up the USD hierarchy from prim_path, returning the path of the first ancestor prim whose kind is in `kinds`.
    If no such ancestor is found before reaching root_prim_path, returns root_prim_path.

    Args:
        stage (Usd.Stage): USD stage to query.
        prim_path (Sdf.Path): Path to start search from.
        kinds (List[str]): List of kind strings to match (e.g. ["component", "group"]).
        root_prim_path (Sdf.Path): Path to stop at and return if no match is found.

    Returns:
        Tuple[Sdf.Path, str]: Path of the nearest ancestor prim with a matching kind, or root_prim_path if none found.
    """
    while prim_path:
        if prim_path == root_prim_path:
            return root_prim_path, ""
        prim = stage.GetPrimAtPath(prim_path)
        prim_kind = get_prim_kind(prim)
        if prim and prim_kind in kinds:
            return prim_path, prim_kind
        prim_path = prim_path.GetParentPath()
    return root_prim_path, ""  # fallback, should not be hit
