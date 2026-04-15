# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Tuple, List
from omni.kit.test import AsyncTestCase
from pxr import Usd, Sdf
from omni.physxclashdetectionui.grouping import group, dump_groups
from omni.physxclashdetectionui.utils import find_common_parent_path


class TestGrouping(AsyncTestCase):
    class DummyClashInfo:
        def __init__(self, object_a_path, object_b_path):
            self.object_a_path = object_a_path
            self.object_b_path = object_b_path

    async def test_grouping(self):
        def setup_stage(setup_kinds: bool = True) -> Tuple[Usd.Stage, List[self.DummyClashInfo]]:
            # Create in-memory stage
            stage = Usd.Stage.CreateInMemory()

            def set_kind(prim, kind):
                if setup_kinds:
                    prim.SetMetadata("kind", kind)

            # Build hierarchy:
            # /World (group)
            #   /World/GroupA (group)
            #     /World/GroupA/SubGroupA1 (group)
            #       /World/GroupA/SubGroupA1/CompA1 (component)
            #         /World/GroupA/SubGroupA1/CompA1/SubA1 (subcomponent)
            #           /World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1 (no kind)
            #           /World/GroupA/SubGroupA1/CompA1/SubA1/LeafA2 (no kind)
            #           /World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1/SubLeafA1 (no kind)
            #           /World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1/SubLeafA2 (no kind)
            #           /World/GroupA/SubGroupA1/CompA1/SubA1/LeafA2/SubLeafA3 (no kind)
            #         /World/GroupA/SubGroupA1/CompA1/SubA2 (subcomponent)
            #           /World/GroupA/SubGroupA1/CompA1/SubA2/LeafA3 (no kind)
            #       /World/GroupA/SubGroupA1/CompA2 (component)
            #         /World/GroupA/SubGroupA1/CompA2/SubA3 (subcomponent)
            #           /World/GroupA/SubGroupA1/CompA2/SubA3/LeafA4 (no kind)
            #     /World/GroupA/CompA3 (component)
            #       /World/GroupA/CompA3/SubA4 (subcomponent)
            #         /World/GroupA/CompA3/SubA4/LeafA5 (no kind)
            #   /World/GroupB (group)
            #     /World/GroupB/CompB1 (component)
            #       /World/GroupB/CompB1/SubB1 (subcomponent)
            #         /World/GroupB/CompB1/SubB1/LeafB1 (no kind)
            #         /World/GroupB/CompB1/SubB1/LeafB2 (no kind)
            #       /World/GroupB/CompB1/SubB2 (subcomponent)
            #         /World/GroupB/CompB1/SubB2/LeafB3 (no kind)

            world = stage.DefinePrim("/World")
            set_kind(world, "group")

            group_a = stage.DefinePrim("/World/GroupA")
            set_kind(group_a, "group")
            subgroup_a1 = stage.DefinePrim("/World/GroupA/SubGroupA1")
            set_kind(subgroup_a1, "group")

            comp_a1 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1")
            set_kind(comp_a1, "component")
            sub_a1 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1")
            set_kind(sub_a1, "subcomponent")
            leaf_a1 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1")
            leaf_a2 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1/LeafA2")
            subleaf_a1 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1/SubLeafA1")
            subleaf_a2 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1/LeafA1/SubLeafA2")
            subleaf_a3 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA1/LeafA2/SubLeafA3")
            sub_a2 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA2")
            set_kind(sub_a2, "subcomponent")
            leaf_a3 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA1/SubA2/LeafA3")

            comp_a2 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA2")
            set_kind(comp_a2, "component")
            sub_a3 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA2/SubA3")
            set_kind(sub_a3, "subcomponent")
            leaf_a4 = stage.DefinePrim("/World/GroupA/SubGroupA1/CompA2/SubA3/LeafA4")

            comp_a3 = stage.DefinePrim("/World/GroupA/CompA3")
            set_kind(comp_a3, "component")
            sub_a4 = stage.DefinePrim("/World/GroupA/CompA3/SubA4")
            set_kind(sub_a4, "subcomponent")
            leaf_a5 = stage.DefinePrim("/World/GroupA/CompA3/SubA4/LeafA5")

            group_b = stage.DefinePrim("/World/GroupB")
            set_kind(group_b, "group")
            comp_b1 = stage.DefinePrim("/World/GroupB/CompB1")
            set_kind(comp_b1, "component")
            sub_b1 = stage.DefinePrim("/World/GroupB/CompB1/SubB1")
            set_kind(sub_b1, "subcomponent")
            leaf_b1 = stage.DefinePrim("/World/GroupB/CompB1/SubB1/LeafB1")
            leaf_b2 = stage.DefinePrim("/World/GroupB/CompB1/SubB1/LeafB2")
            sub_b2 = stage.DefinePrim("/World/GroupB/CompB1/SubB2")
            set_kind(sub_b2, "subcomponent")
            leaf_b3 = stage.DefinePrim("/World/GroupB/CompB1/SubB2/LeafB3")

            # Explicitly define clashing pairs using str() of leaf var paths
            clashing_pairs = [
                self.DummyClashInfo(str(leaf_a1.GetPath()), str(leaf_b1.GetPath())),
                self.DummyClashInfo(str(leaf_a2.GetPath()), str(leaf_b2.GetPath())),
                self.DummyClashInfo(str(leaf_a3.GetPath()), str(leaf_b3.GetPath())),
                self.DummyClashInfo(str(leaf_a4.GetPath()), str(leaf_b1.GetPath())),
                self.DummyClashInfo(str(leaf_a5.GetPath()), str(leaf_b2.GetPath())),
                self.DummyClashInfo(str(subleaf_a2.GetPath()), str(leaf_b3.GetPath())),
                self.DummyClashInfo(str(subgroup_a1.GetPath()), str(comp_b1.GetPath())),
            ]

            return stage, clashing_pairs

        def check_group_node(node_dict, group_path, total_clashes):
            node = node_dict.get(group_path)
            self.assertIsNotNone(node, f"Missing group node: {group_path}")
            self.assertEqual(node.group_path, group_path)
            self.assertEqual(node.total_clashes, total_clashes)

        root_prim_path = find_common_parent_path([Sdf.Path("/World/GroupA"), Sdf.Path("/World/GroupB")])
        self.assertEqual(root_prim_path, "/World")

        # group on no kinds
        stage, clashing_pairs = setup_stage(setup_kinds=False)

        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path))
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 7)
        self.assertEqual(len(root_node.children), 0)

        # group on no kinds, remove empty groups
        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path), discard_empty_groups=True)
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 7)
        self.assertEqual(len(root_node.children), 0)

        # group on "group" kind
        stage, clashing_pairs = setup_stage(setup_kinds=True)

        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path), ["group"])
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 14)

        check_group_node(node_dict, Sdf.Path("/World/GroupA"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupB"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1"), 6)

        self.assertGreaterEqual(len(root_node.children), 2)
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupA") for child in root_node.children))
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupB") for child in root_node.children))

        # group on "group" kind, discard empty groups
        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path), ["group"], discard_empty_groups=True)
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 14)

        check_group_node(node_dict, Sdf.Path("/World/GroupA"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupB"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1"), 6)

        self.assertGreaterEqual(len(root_node.children), 2)
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupA") for child in root_node.children))
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupB") for child in root_node.children))

        # group on "group", "component", "subcomponent" kinds
        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path), ["group", "component", "subcomponent"])
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 14)

        check_group_node(node_dict, Sdf.Path("/World/GroupA"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/CompA3"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/CompA3/SubA4"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1"), 6)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA1"), 4)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA1/SubA1"), 3)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA1/SubA2"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA2"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA2/SubA3"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupB"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1/SubB1"), 4)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1/SubB2"), 2)

        self.assertGreaterEqual(len(root_node.children), 2)
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupA") for child in root_node.children))
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupB") for child in root_node.children))

        # group on "group", "component", "subcomponent" kinds, discard empty groups
        node_dict = group(stage, clashing_pairs, Sdf.Path(root_prim_path), ["group", "component", "subcomponent"], discard_empty_groups=True)
        # dump_groups(node_dict, node_dict[Sdf.Path("/World")])  # Optionally, print the group tree for debug

        # Assertions
        self.assertIn(Sdf.Path("/World"), node_dict)
        root_node = node_dict[Sdf.Path("/World")]
        self.assertEqual(root_node.group_path, Sdf.Path("/World"))
        self.assertEqual(root_node.total_clashes, 14)

        check_group_node(node_dict, Sdf.Path("/World/GroupA/CompA3/SubA4"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1"), 6)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA1/SubA1"), 3)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA1/SubA2"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupA/SubGroupA1/CompA2/SubA3"), 1)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1"), 7)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1/SubB1"), 4)
        check_group_node(node_dict, Sdf.Path("/World/GroupB/CompB1/SubB2"), 2)

        self.assertEqual(len(root_node.children), 3)
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupA/CompA3/SubA4") for child in root_node.children))
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupA/SubGroupA1") for child in root_node.children))
        self.assertTrue(any(child.group_path == Sdf.Path("/World/GroupB/CompB1") for child in root_node.children))
