# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, Dict, Optional
from pxr import Sdf, Usd
from .clash_detect_viewmodel import ClashDetectTableRowItem
from .usd_utils import find_nearest_group


class GroupNode:
    """
    Hierarchical node for grouping clash results by USD prim path and kind.

    Each GroupNode represents a USD prim (group_path, group_kind) and contains:
      - clashing_pairs: Set of ClashDetectTableRowItem instances directly associated with this node.
      - children: Set of child GroupNode objects (sub-groups).
      - total_clashes: Total number of clashes in this group and all descendants.

    Attributes:
        group_path (Sdf.Path): The USD prim path for this group node.
        group_kind (str): The USD kind metadata for this group node.
        children (set[GroupNode]): Child group nodes.
        clashing_pairs (set[ClashDetectTableRowItem]): Clash items grouped at this node.
        total_clashes (int): Total number of clashes in this group and all subgroups.
    """
    def __init__(self, group_path: Sdf.Path, group_kind: str = ""):
        self._group_path = group_path
        self._group_kind = group_kind
        self._clashing_pairs = set()
        self._children = set()
        self._total_clashes = 0

    @property
    def group_path(self):
        return self._group_path

    @property
    def group_kind(self):
        return self._group_kind

    @property
    def children(self):
        return self._children

    @property
    def clashing_pairs(self):
        return self._clashing_pairs

    @property
    def total_clashes(self):
        return self._total_clashes

    @total_clashes.setter
    def total_clashes(self, total_clashes: int):
        self._total_clashes = total_clashes

    def add_clashing_pair(self, row_item: ClashDetectTableRowItem):
        """Add a ClashDetectTableRowItem to this group node."""
        self._clashing_pairs.add(row_item)

    def add_child(self, child: "GroupNode"):
        """Add a child GroupNode to this group node."""
        self._children.add(child)


def group(
    stage: Usd.Stage,
    clashing_pairs_list: List[ClashDetectTableRowItem],
    root_prim_path: Optional[Sdf.Path] = None,
    kinds: Optional[List[str]] = None,
    discard_empty_groups: bool = False,
) -> Dict[Optional[Sdf.Path], GroupNode]:
    """
    Build a tree of GroupNode objects, grouping each clash row item by the nearest ancestor prim of a given kind.

    For each ClashDetectTableRowItem in clashing_pairs_list, both object_a_path and object_b_path are walked up the USD hierarchy.
    The closest ancestor prim whose kind matches any in `kinds` is used as the group node. If no such ancestor is found,
    the root_prim_path is used. Each group node collects all row items assigned to it, and the tree structure is built by
    recursively linking child group nodes to their parents.

    Args:
        stage (Usd.Stage): The USD stage to operate on.
        clashing_pairs_list (List[ClashDetectTableRowItem]): List of clash row items to group.
        root_prim_path (Optional[Sdf.Path]): The root group node path. If None, uses the stage's pseudo-root.
        kinds (Optional[List[str]]): List of prim kinds to use as grouping boundaries. Defaults to ["component", "subcomponent", "group"].
        discard_empty_groups (bool): If True, remove groups with no clashing pairs from the hierarchy.

    Returns:
        Dict[Optional[Sdf.Path], GroupNode]: Mapping from prim path to GroupNode. The root node is always included and accessible via node_dict[root_prim_path].
                                            node_dict[None] is also set to the root node for convenience.
    """

    def add_to_nearest_group(
        node_dict: Dict[Optional[Sdf.Path], GroupNode],
        group_node: Optional[GroupNode],
        stage: Usd.Stage,
        prim_path: Sdf.Path,
        clashing_pair: Optional[ClashDetectTableRowItem],
        kinds: List[str],
    ) -> None:
        """
        Attach a clashing pair or a GroupNode to the nearest ancestor group node (by kind) in the hierarchy.

        If clashing_pair is provided, it is added to the group node for the nearest ancestor prim of the specified kind.
        If group_node is provided, it is added as a child to the nearest ancestor group node.
        If the group node for the ancestor prim does not exist, it is created and added to node_dict.
        Recursively ensures all parent group nodes are created and linked up to the root.
        """
        group_path, group_kind = find_nearest_group(stage, Sdf.Path(prim_path), kinds, root_prim_path)
        if group_path:
            existing_group_node = node_dict.get(group_path, None)
            if existing_group_node:
                if clashing_pair:
                    existing_group_node.add_clashing_pair(clashing_pair)
                if group_node is not None:
                    existing_group_node.add_child(group_node)
            else:
                new_group_node = GroupNode(group_path, group_kind)
                if clashing_pair:
                    new_group_node.add_clashing_pair(clashing_pair)
                if group_node is not None:
                    new_group_node.add_child(group_node)
                node_dict[group_path] = new_group_node
                if group_path != root_prim_path:
                    add_to_nearest_group(node_dict, new_group_node, stage, group_path.GetParentPath(), None, kinds)

    def remove_empty_groups(node_dict: Dict[Optional[Sdf.Path], GroupNode], group_node: GroupNode) -> None:
        """
        Recursively remove children of group_node that have no clashing pairs, both from the group_node hierarchy and from node_dict.
        If a child is empty, its non-empty children are promoted up one level.
        """
        to_remove = set()
        to_add = set()
        for child in list(group_node.children):
            remove_empty_groups(node_dict, child)
            if len(child.clashing_pairs) == 0:
                if child.group_path in node_dict:
                    del node_dict[child.group_path]
                to_remove.add(child)
                for grandchild in child.children:
                    if len(grandchild.clashing_pairs) > 0 or len(grandchild.children) > 0:
                        to_add.add(grandchild)
        group_node.children.difference_update(to_remove)
        group_node.children.update(to_add)

    def update_total_clashes(group_node: GroupNode) -> None:
        """
        Recursively compute and update the total number of clashes for the given group node,
        including all direct clashing pairs and those in all descendant sub-groups.
        """
        total_clashes = len(group_node.clashing_pairs)
        for child in group_node.children:
            update_total_clashes(child)
            total_clashes += child.total_clashes
        group_node.total_clashes = total_clashes

    if not stage:
        return {}

    if kinds is None:
        kinds = ["component", "subcomponent", "group"]

    if not root_prim_path:
        root_prim_path = stage.GetPseudoRoot().GetPath()

    root_group_node = GroupNode(root_prim_path, "")
    node_dict = {
        root_prim_path: root_group_node,
        None: root_group_node  # helper to find the root group node easily
    }

    for clashing_pair in clashing_pairs_list:
        add_to_nearest_group(node_dict, None, stage, Sdf.Path(clashing_pair.object_a_path), clashing_pair, kinds)
        add_to_nearest_group(node_dict, None, stage, Sdf.Path(clashing_pair.object_b_path), clashing_pair, kinds)

    if discard_empty_groups:
        remove_empty_groups(node_dict, root_group_node)

    update_total_clashes(root_group_node)

    return node_dict


def dump_groups(node_dict: Dict[Optional[Sdf.Path], GroupNode], node: GroupNode, indent: int = 0):
    """
    Recursively print sorted group hierarchy and clashing pairs for a given group node.

    Args:
        node_dict (Dict[Optional[Sdf.Path], GroupNode]): Mapping from Sdf.Path to GroupNode for all groups.
        node (GroupNode): The current group node to print.
        indent (int, optional): Indentation level for pretty-printing. Defaults to 0.

    Prints:
        The group path, total number of clashes, number of children, and all clashing pairs for each group,
        recursively traversing the group tree.

    Notes:
        Clashing pairs are sorted by object_a_path (as string).
        Children are sorted by group_path (as string).
    """
    counts = f"({node.total_clashes} total clashes, {len(node.children)} children):"
    print(f"{' ' * indent}Group [{node.group_kind} {node.group_path}] {counts}")
    for clashing_pair in sorted(node.clashing_pairs, key=lambda c: str(c.object_a_path)):
        print(f"{' ' * (indent + 2)}Clashing pair [{clashing_pair.object_a_path}] [{clashing_pair.object_b_path}]")
    for child in sorted(node.children, key=lambda c: str(c.group_path)):
        dump_groups(node_dict, child, indent + 2)


def dump_groups_to_json(node_dict: Dict[Optional[Sdf.Path], GroupNode], node: GroupNode, indent: int = 0):
    """
    Recursively serialize the group hierarchy and clashing pairs to JSON and print.

    Args:
        node_dict (Dict[Optional[Sdf.Path], GroupNode]): Mapping from Sdf.Path to GroupNode for all groups.
        node (GroupNode): The root group node to serialize.
        indent (int, optional): Indentation level for pretty-printing the JSON output. Defaults to 0.

    Output:
        Prints a JSON string representing the group tree, including:
            - group_path (str)
            - group_kind (str)
            - total_clashes (int)
            - children (list of groups, sorted by group_path)
            - clashing_pairs (list of dicts, sorted by object_a_path)
    """
    import json

    def group_node_to_dict(node: GroupNode):
        return {
            "group_path": str(node.group_path),
            "group_kind": node.group_kind,
            "total_clashes": node.total_clashes,
            "children": [group_node_to_dict(child) for child in sorted(node.children, key=lambda c: str(c.group_path))],
            "clashing_pairs": [
                {
                    "object_a_path": str(pair.object_a_path),
                    "object_b_path": str(pair.object_b_path)
                }
                for pair in sorted(node.clashing_pairs, key=lambda c: str(c.object_a_path))
            ]
        }

    group_json = group_node_to_dict(node)
    print(json.dumps(group_json, indent=2))
