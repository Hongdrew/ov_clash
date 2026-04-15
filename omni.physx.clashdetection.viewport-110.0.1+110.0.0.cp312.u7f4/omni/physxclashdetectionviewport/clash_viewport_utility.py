# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import time

import carb
import carb.profiler
from pxr import Gf, Sdf, Usd, UsdGeom

import omni.kit
import omni.usd
from omni.kit.viewport.utility import frame_viewport_selection
from omni.kit.widget.viewport.api import ViewportAPI

__all__ = []

from .clash_viewport_settings import ClashViewportSettingValues


def get_context_stage(context: omni.usd.UsdContext) -> Usd.Stage:
    return context.get_stage()  # type: ignore


async def close_stage_async(context: omni.usd.UsdContext) -> Usd.Stage:
    return await context.close_stage_async()  # type: ignore


@staticmethod
def remove_all_prim_specs(layer: Sdf.Layer):

    def remove_prim_spec(prim_spec: Sdf.PrimSpec):
        """Removes prim spec from layer."""
        if prim_spec.nameParent:
            name_parent = prim_spec.nameParent
        else:
            name_parent = layer.pseudoRoot

        if not name_parent:
            return False

        name = prim_spec.name
        if name in name_parent.nameChildren:
            del name_parent.nameChildren[name]

    def on_prim_spec_path(prim_spec_path):
        if prim_spec_path.IsPropertyPath() or prim_spec_path == Sdf.Path.absoluteRootPath:
            return
        prim_spec = layer.GetPrimAtPath(prim_spec_path)
        if prim_spec:
            remove_prim_spec(prim_spec)

    layer.Traverse(Sdf.Path.absoluteRootPath, on_prim_spec_path)


class CodeTimer:
    """Creates profiler zones with a given name"""

    nesting_level = 0

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start_time = time.time()
        self.__class__.nesting_level += 1
        carb.profiler.begin(1, self.name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        if ClashViewportSettingValues.LOG_PROFILE:
            elapsed_time = (self.end_time - self.start_time) * 1000  # in milliseconds
            indentation = "  " * (self.__class__.nesting_level - 1)
            execution_string = f"{indentation}Execution time: {elapsed_time:.2f} ms [[{self.name}]]"
            print(execution_string)
        carb.profiler.end(1)
        self.__class__.nesting_level -= 1


class ClashViewportCamera:
    """Center camera on a usd object"""

    @staticmethod
    def choose_smallest_prim(stage: Usd.Stage, p1: str, p2: str, score_hysteresis: float = 3.0) -> list[str]:
        # Choose which prim to center the camera on based on bounding box analysis.
        # The goal is to select the prim that will appear smaller in screen space when viewed.
        #
        # We use the sum of squared bounding box dimensions as a heuristic for screen space size.
        # This works better than volume because:
        # - A flat plane has zero volume but can have large bounding box extents
        # - A thin object (like a small pillar) might have small volume but still appear large in screen space
        # - The sum of squared dimensions better correlates with how objects appear when projected to screen
        #
        # If the difference between scores is less than the hysteresis factor, we center on both prims.
        if not p1 or not p2:
            return [p1, p2]
        try:
            prim1 = stage.GetPrimAtPath(p1)
            prim2 = stage.GetPrimAtPath(p2)
            if not prim1 or not prim2:
                return [p1, p2]
            bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
            bbox1 = bbox_cache.ComputeWorldBound(prim1).ComputeAlignedRange()
            bbox2 = bbox_cache.ComputeWorldBound(prim2).ComputeAlignedRange()
            score1 = (
                (bbox1.GetMax()[0] - bbox1.GetMin()[0]) ** 2
                + (bbox1.GetMax()[1] - bbox1.GetMin()[1]) ** 2
                + (bbox1.GetMax()[2] - bbox1.GetMin()[2]) ** 2
            )
            score2 = (
                (bbox2.GetMax()[0] - bbox2.GetMin()[0]) ** 2
                + (bbox2.GetMax()[1] - bbox2.GetMin()[1]) ** 2
                + (bbox2.GetMax()[2] - bbox2.GetMin()[2]) ** 2
            )
            if (score1 * score_hysteresis) < score2:
                selected_paths = [p1]
            elif (score2 * score_hysteresis) < score1:
                selected_paths = [p2]
            else:
                selected_paths = [p1, p2]
        except Exception as e:
            carb.log_error(f"Error computing bounding boxes for prims at paths {p1} and {p2}: {e}")
            selected_paths = [p1, p2]
        return selected_paths

    @staticmethod
    def center_selection(
        selection: omni.usd.Selection,
        selection_paths: list[str],
        viewport_api: ViewportAPI,
    ):
        """Centers viewport camera on a given selection of paths"""
        selection.set_selected_prim_paths(selection_paths, False)
        if viewport_api:
            frame_viewport_selection(viewport_api)
        selection.clear_selected_prim_paths()

    @staticmethod
    def center_preserving_user_camera_fine_tuning(
        active_viewport: ViewportAPI, source_stage: Usd.Stage, selection: list[str]
    ):
        """Centers viewport camera on a given selection of paths only if outside some threshold"""
        cam_path = active_viewport.camera_path
        camera_translation = None
        camera = UsdGeom.Camera(source_stage.GetPrimAtPath(cam_path))
        xformMatrix = camera.GetLocalTransformation()
        camera_local_z = xformMatrix.TransformDir(Gf.Vec3d(0, 0, -1))
        camera_translation = xformMatrix.ExtractTranslation()
        ClashViewportCamera.center_selection(active_viewport.usd_context.get_selection(), selection, active_viewport)
        if camera_translation and len(selection):
            camera_new_translation = camera.GetLocalTransformation().ExtractTranslation()
            translation_difference: Gf.Vec3d = camera_new_translation - camera_translation
            translation_difference_length = translation_difference.GetLength()
            translation_difference.Normalize()
            dot_along_camera_z = translation_difference.GetDot(camera_local_z)
            prim = source_stage.GetPrimAtPath(selection[0])
            try:
                extents = UsdGeom.Boundable(prim).GetExtentAttr().Get()
                positive_reference = max(extents[1] - extents[0])
                negative_reference = (min(extents[1] - extents[0]) + max(extents[1] - extents[0])) / 2
                # If only translating around camera Z axis and less than CLASH_CAMERA_CENTERING_FAR_TOLERANCE
                # We discard the camera centering, because we want to preserve user camera "zoom" fine tuning
                zoom_positive = +ClashViewportSettingValues.CAMERA_CENTERING_FAR_TOLERANCE
                zoom_negative = -ClashViewportSettingValues.CAMERA_CENTERING_NEAR_TOLERANCE
                positive_orientation_change_is_small = dot_along_camera_z > 0 and +dot_along_camera_z >= 0.99
                positive_translation_change_is_small = (
                    translation_difference_length < positive_reference * zoom_positive
                )
                negative_orientation_change_is_small = dot_along_camera_z < 0 and -dot_along_camera_z >= 0.99
                negative_translation_change_is_small = (
                    translation_difference_length < negative_reference * zoom_negative
                )
                if (positive_orientation_change_is_small and positive_translation_change_is_small) or (
                    negative_orientation_change_is_small and negative_translation_change_is_small
                ):
                    omni.kit.undo.undo()  # type: ignore
            except Exception:
                pass
