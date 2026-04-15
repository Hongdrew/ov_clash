# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb


class ClashBakeOptions:
    """Options for the clash bake.

    Args:
        generate_wireframe (bool): Whether to generate a wireframe mesh.
        generate_clash_polygons (bool): Whether to generate time samples for clashing polygons (resource intensive).
        generate_outlines (bool): Whether to generate outlines for the meshes.
        generate_clash_meshes (bool): Whether to generate clash meshes. (Layer mode only). This is useful to highlight the meshes from clash start to end.
        use_selection_groups (bool): Whether to use selection groups. (Layer mode only).
        wireframe_offset_epsilon (float): Offset distance along normals to avoid z-fighting for wireframes (default: 0.001).
        outline_width_size (float): Size of the outline in world space units (default: 0.5).
        outline_width_scale (float): Scale factor for the outline width (default: 1.0).
        group_name_clash_a (str): The name of the selection group for object A.
        group_name_clash_b (str): The name of the selection group for object B.
        group_name_outlines (str): The name of the selection group for outlines.
        group_name_duplicate (str): The name of the selection group for duplicate meshes.
    """

    def __init__(self):
        # public options
        self.generate_wireframe = False  # Not useful with selection groups
        self.generate_clash_meshes = True  # Layer mode only
        self.generate_clash_polygons = False  # Not useful with selection groups
        self.generate_outlines = True
        self.wireframe_offset_epsilon = 0.001  # Offset distance along normals to avoid z-fighting
        self.use_selection_groups = True  # Layer mode only

        # outline width options
        self.outline_width_size = 0.5  # Size of the outline in world space units
        self.outline_width_scale = 1.0  # Scale factor for the outline width

        # selection groups options (layer mode only)
        self.group_name_clash_a = "ClashDetection:ObjectA"
        self.group_name_clash_b = "ClashDetection:ObjectB"
        self.group_name_outlines = "ClashDetection:Outlines"
        self.group_name_duplicate = "ClashDetection:Duplicate"

        # private options
        self._use_display_opacity = True  # Stage mode only
        self._inline_mode = True  # Stage mode only
        self._debug_mode = False
        self._debug_max_level = 1

    def validate(self, layer_mode: bool):
        """Validates the options.

        Args:
            layer_mode (bool): Whether the options are being used in layer mode.
        """
        pass
