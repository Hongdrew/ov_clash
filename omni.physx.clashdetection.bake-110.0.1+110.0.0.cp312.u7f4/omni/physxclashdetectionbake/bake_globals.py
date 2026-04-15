# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import ctypes
from dataclasses import dataclass
from typing import Any


# Keeping this here for now, it may be useful when developing or debugging
# from omni.physxclashdetectioncore.clash_info import ClashInfo
ClashInfo = Any


@dataclass
class ClashBakePaths:
    # Common
    no_clash: str = ""
    do_clash: str = ""
    do_wire: str = ""
    wireframe: str = ""
    outlines_scope: str = ""

    # Inline mode specific
    reference: str = ""

    # Scoped mode specific
    no_merged: str = ""
    clash_scope: str = ""
    merged_scope: str = ""
    sub_scope: str = ""

    def get_outlines_path_for_clash_with(self, other_path: str) -> str:
        identifier = ClashBakeGlobals._get_positive_hash_for(other_path)
        return f"{self.outlines_scope}/{ClashBakeGlobals.OUTLINES_PREFIX}{identifier}"


class ClashBakeGlobals:
    NO_CLASH = "NO_CLASH"
    DO_CLASH = "DO_CLASH"
    DO_WIREFRAME = "DO_WIREFRAME"
    WIREFRAME = "WIREFRAME"
    OUTLINES_SCOPE = "/ClashOutlines"
    CLASHES_ROOT = "/Clashes"
    OUTLINES_PREFIX = "Outline_"
    MESH_PREFIX = "Mesh_"
    SUB_MESH_PREFIX = "Sub_"
    MERGED_MESH = "Merged"

    @staticmethod
    def _get_positive_hash_for(path: str) -> int:
        # Using ctypes to avoid negative hashes that can't be used as prim names
        return ctypes.c_size_t(hash(path)).value

    @staticmethod
    def _get_clash_sub_scope_for(upper_scope: str, lower_scope: str) -> str:
        return f"{ClashBakeGlobals.get_clash_scope_for(upper_scope)}/{ClashBakeGlobals.SUB_MESH_PREFIX}{ClashBakeGlobals._get_positive_hash_for(lower_scope)}"

    @staticmethod
    def _get_clash_merged_scope_for(upper_scope: str) -> str:
        return f"{ClashBakeGlobals.get_clash_scope_for(upper_scope)}/{ClashBakeGlobals.MERGED_MESH}"

    @staticmethod
    def get_clash_scope_for(path: str) -> str:
        return f"{ClashBakeGlobals.CLASHES_ROOT}/{ClashBakeGlobals.MESH_PREFIX}{ClashBakeGlobals._get_positive_hash_for(path)}"

    @staticmethod
    def get_meshes_path_scopes(src_path: str, other_path: str) -> ClashBakePaths:
        paths = ClashBakePaths()
        paths.clash_scope = ClashBakeGlobals.get_clash_scope_for(src_path)
        paths.sub_scope = ClashBakeGlobals._get_clash_sub_scope_for(src_path, other_path)
        paths.merged_scope = ClashBakeGlobals._get_clash_merged_scope_for(src_path)

        paths.no_clash = f"{paths.sub_scope}/{ClashBakeGlobals.NO_CLASH}"
        paths.do_clash = f"{paths.sub_scope}/{ClashBakeGlobals.DO_CLASH}"
        paths.do_wire = f"{paths.sub_scope}/{ClashBakeGlobals.DO_WIREFRAME}"
        paths.no_merged = f"{paths.merged_scope}/{ClashBakeGlobals.NO_CLASH}"
        identifier = ClashBakeGlobals._get_positive_hash_for(src_path)
        paths.outlines_scope = f"{ClashBakeGlobals.OUTLINES_SCOPE}/{ClashBakeGlobals.OUTLINES_PREFIX}{identifier}"

        return paths

    @staticmethod
    def get_meshes_path_inline(src_path: str, src_root_path: str) -> ClashBakePaths:
        paths = ClashBakePaths()
        paths.reference = f"{src_root_path}_CLASH"

        # Find the relative path of the target mesh (src_path) inside the "cloned" reference_path
        # In other words reference_path and src_root_path are "parallel", and src_path is inside src_root_path.
        # We want to find the path inside reference_path that is "corresponding" to src_path.
        # If src_path is == src_root_path then no_clash is equal to paths.reference
        paths.no_clash = f"{paths.reference}{src_path.removeprefix(str(src_root_path))}"
        paths.do_clash = f"{paths.no_clash}_{ClashBakeGlobals.DO_CLASH}"
        paths.do_wire = f"{paths.no_clash}_{ClashBakeGlobals.DO_WIREFRAME}"
        paths.wireframe = f"{paths.no_clash}_{ClashBakeGlobals.WIREFRAME}"
        identifier = ClashBakeGlobals._get_positive_hash_for(src_path)
        paths.outlines_scope = f"{ClashBakeGlobals.OUTLINES_SCOPE}/{ClashBakeGlobals.OUTLINES_PREFIX}{identifier}"

        return paths
