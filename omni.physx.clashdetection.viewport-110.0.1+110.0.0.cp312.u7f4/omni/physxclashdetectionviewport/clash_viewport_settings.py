# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from dataclasses import dataclass


@dataclass
class ClashViewportSettings:
    """
    This class contains settings related to the clash detection viewport in a physics simulation.
    """

    SHOW_CLASH_VIEWPORT_WINDOW = "/physics/clashDetectionViewport/showClashViewport"
    USE_SOURCE_NORMALS = "/physics/clashDetectionViewport/useSourceNormals"
    CAMERA_CENTERING_FAR_TOLERANCE = "/physics/clashDetectionViewport/cameraCenteringFarTolerance"
    CAMERA_CENTERING_NEAR_TOLERANCE = "/physics/clashDetectionViewport/cameraCenteringNearTolerance"
    CLASH_WIREFRAME_THICKNESS = "/physics/clashDetectionViewport/wireframeThickness"
    CLASH_OUTLINE_WIDTH_SIZE = "/physics/clashDetectionViewport/outlineWidthSize"
    CLASH_OUTLINE_WIDTH_SCALE = "/physics/clashDetectionViewport/outlineWidthScale"
    CLASH_OUTLINE_DIAGONAL_MIN_CENTERING = "/physics/clashDetectionViewport/outlineDiagonalMinCentering"
    CLASH_MESHES_DISPLAY_LIMIT = "/physics/clashDetectionViewport/clashMeshesDisplayLimit"
    MAIN_VIEWPORT_USE_SELECTION_GROUPS = "/physics/clashDetectionViewport/mainViewport/useSelectionGroups"
    MAIN_VIEWPORT_SHOW_CLASH_OUTLINES = "/physics/clashDetectionViewport/mainViewport/showClashOutlines"
    MAIN_VIEWPORT_SHOW_CLASH_MESHES = "/physics/clashDetectionViewport/mainViewport/showClashMeshes"
    MAIN_VIEWPORT_CENTER_CAMERA = "/physics/clashDetectionViewport/mainViewport/centerCamera"
    MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE = "/physics/clashDetectionViewport/mainViewport/enableCameraTolerance"
    CLASH_VIEWPORT_SHOW_CLASHES = "/physics/clashDetectionViewport/clashViewport/showClashes"
    CLASH_VIEWPORT_SHOW_WIREFRAMES = "/physics/clashDetectionViewport/clashViewport/showWireframes"
    CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS = "/physics/clashDetectionViewport/clashViewport/useTranslucentMaterials"
    CLASH_HIGHLIGHT_FILLED_MESHES = "/physics/clashDetectionViewport/clashViewport/highlightFilledMeshes"
    CLASH_VIEWPORT_CENTER_CAMERA = "/physics/clashDetectionViewport/clashViewport/centerCamera"
    CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE = "/physics/clashDetectionViewport/clashViewport/enableCameraTolerance"
    # Private
    LOG_PROFILE = "/physics/clashDetectionViewport/logProfile"
    LOG_HIGHLIGHT = "/physics/clashDetectionViewport/logHighlight"


@dataclass
class ClashViewportSettingValues:
    """ClashViewportSettingValues(CLASH_WIREFRAME_THICKNESS: float = 0.5, USE_SOURCE_NORMALS: bool = False, CAMERA_CENTERING_NEAR_TOLERANCE: float = -3, CAMERA_CENTERING_FAR_TOLERANCE: float = 5, CLASH_OUTLINE_WIDTH_SIZE: float = 0.5, CLASH_OUTLINE_WIDTH_SCALE: float = 1.0, CLASH_MESHES_DISPLAY_LIMIT: int = 1)

    This class contains values for various settings related to the clash detection viewport.

    Args:
        CLASH_WIREFRAME_THICKNESS (float): Screen space thickness of overlapping wireframes.
        USE_SOURCE_NORMALS (bool): If to use source normals for clash meshes.
        CAMERA_CENTERING_NEAR_TOLERANCE (float): Positional tolerance above which camera re-centering will happen (Z+).
        CAMERA_CENTERING_FAR_TOLERANCE (float): Positional tolerance above which camera re-centering will happen (Z-).
        CLASH_OUTLINE_WIDTH_SIZE (float): Size of the outline in world space units.
        CLASH_OUTLINE_WIDTH_SCALE (float): Scale factor for the outline width.
        CLASH_OUTLINE_DIAGONAL_MIN_CENTERING (float): Minimum diagonal length for clash outline to be considered for centering.
        CLASH_MESHES_DISPLAY_LIMIT (int): Max number of meshes to display at a given time.
        MAIN_VIEWPORT_CENTER_CAMERA: (bool): If to center camera in main viewport.
        MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE: (bool): If to enable camera tolerance/hysteresis in main viewport.
        MAIN_VIEWPORT_SHOW_CLASH_OUTLINES (bool): If to show clash outlines in main viewport.
        MAIN_VIEWPORT_USE_SELECTION_GROUPS (bool): If to use selection groups to highlight clash meshes in main viewport.
        MAIN_VIEWPORT_SHOW_CLASH_MESHES (bool): If to show clash meshes in main viewport.
        CLASH_VIEWPORT_CENTER_CAMERA: (bool): If to center camera in clash viewport.
        CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE: (bool): If to enable camera tolerance/hysteresis in clash viewport.
        CLASH_VIEWPORT_SHOW_CLASHES (bool): If to display clash meshes in clash viewport.
        CLASH_VIEWPORT_SHOW_WIREFRAMES (bool): If to display wireframes for clash meshes in clash viewport.
        CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS (bool): If to use translucent materials for clash meshes in clash viewport.
        CLASH_HIGHLIGHT_FILLED_MESHES (bool): If to fill clash meshes with a color in highlight.
    """

    CLASH_WIREFRAME_THICKNESS: float = 0.5  # Screen space thickness of overlapping wireframes
    USE_SOURCE_NORMALS: bool = False  # If to use source normals for clash meshes
    CAMERA_CENTERING_NEAR_TOLERANCE: float = -3  # Positional tolerance above which camera re-centering will happen (Z+)
    CAMERA_CENTERING_FAR_TOLERANCE: float = 5  # Positional tolerance above which camera re-centering will happen (Z-)
    CLASH_OUTLINE_WIDTH_SIZE: float = 0.5  # Size of the outline in world space units
    CLASH_OUTLINE_WIDTH_SCALE: float = 1.0  # Scale factor for the outline width
    CLASH_OUTLINE_DIAGONAL_MIN_CENTERING: float = 1.0  # Minimum diagonal for considering clash outline for centering
    CLASH_MESHES_DISPLAY_LIMIT: int = 20  # Max number of meshes to display at a given time
    MAIN_VIEWPORT_CENTER_CAMERA: bool = True  # If to center camera in main viewport
    MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE: bool = True  # If to enable camera tolerance/hysteresis in main viewport
    MAIN_VIEWPORT_SHOW_CLASH_OUTLINES: bool = True  # If to show clash outlines in main viewport
    MAIN_VIEWPORT_USE_SELECTION_GROUPS: bool = True  # If to use selection groups (to see through occluded objects)
    MAIN_VIEWPORT_SHOW_CLASH_MESHES: bool = True  # If to show clash meshes in main viewport
    CLASH_VIEWPORT_CENTER_CAMERA: bool = True  # If to center camera in clash viewport
    CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE: bool = True  # If to enable camera tolerance/hysteresis in clash viewport
    CLASH_VIEWPORT_SHOW_CLASHES: bool = True  # If to display clash meshes in clash viewport
    CLASH_VIEWPORT_SHOW_WIREFRAMES: bool = True  # If to display wireframes for clash meshes in clash viewport
    CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS: bool = True  # If to use translucent materials in clash viewport
    CLASH_HIGHLIGHT_FILLED_MESHES: bool = True  # If to fill clash meshes with a color in highlight
    # private
    LOG_PROFILE: bool = False  # Shows profile timings
    LOG_HIGHLIGHT: bool = False  # Shows logs for highlight process
