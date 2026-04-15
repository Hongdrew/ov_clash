# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import sys
import time
import traceback
from typing import Any, Dict

import carb
import carb.settings
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdUtils

import omni.kit.app
import omni.ui as ui
import omni.usd
import warp as wp
import asyncio
import math

from omni.kit.viewport.utility import create_viewport_window, get_active_viewport
from omni.kit.widget.viewport.api import ViewportAPI
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashDetectionViewportTelemetry, ClashTelemetry

from .clash_viewport_materials import ClashViewportMaterialPaths
from .clash_viewport_meshes import ClashViewportMeshes, ClashViewportMeshPaths
from .clash_viewport_settings import ClashViewportSettingValues
from .clash_viewport_toolbar import ClashDetectionViewportToolbar
from .clash_viewport_utility import ClashViewportCamera, CodeTimer, get_context_stage, remove_all_prim_specs
from .clash_viewport_highlight import ClashViewportHighlight

__all__ = []


SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE = "/rtx/wireframe/wireframeThicknessWorldSpace"
SETTING_RTX_WIREFRAME_THICKNESS = "/rtx/wireframe/wireframeThickness"
SETTING_USDRT_FAST_DIFFING = "/app/usdrt/population/utils/enableFastDiffing"


class ClashDetectionViewport:
    def __init__(self, title: str, usd_context_name: str, clash_viewport_highlight: ClashViewportHighlight):
        """ClashDetectionViewport contructor
        Args:
            title (str): The name of the Window.
            usd_context_name (str): The name of a UsdContext this Viewport will be viewing.
        """
        # Last
        self._last_clash_timecode = 0
        self._last_clash_info_items = {}

        # Additional Window / Additional USD Context
        self._warning_message = None
        self._window_title = title
        self._usd_context_name = usd_context_name
        self._viewport_toolbar = ClashDetectionViewportToolbar(self)
        self._clash_viewport_highlight = clash_viewport_highlight
        self._selection_group_prims = list[str]()

        # Clash Detection window selection hooks
        self._clash_viewport_path = "/ClashDetectionViewport"

        # Stage / Session Layer
        self._create_stage()
        self._create_lights()

        # Settings
        self._settings = carb.settings.get_settings()
        self._settings_subs = None
        self._settings_tracked = False
        self._setting_original_rtx_wireframe_worldspace = False
        self._setting_original_rtx_wireframe_thickness = 0.0
        self._setting_original_usdrt_fast_diffing = True

        # Telemetry
        self._telemetry_inited_at = time.time()
        self._telemetry_visible_at = None
        self._telemetry_focused_at = None

        self._telemetry = ClashDetectionViewportTelemetry()

    def create_dedicated_clash_viewport_window(self):
        """Creates the dedicated usd context and dedicated viewport window"""

        # Change the following settings just once before new usd context and new viewport creation to avoid that the
        # main viewport could see some of its render settings changed or reset.
        # Failing to do this causes for example the default light in the main viewport to become "switched off" or
        # the viewport to cause visual artifacts due to UJITSO geometry streaming not being properly supported on two
        # different USD contexts (both systems overwrite each others' memory budget requests)
        rs_settings = {
            "/app/omni.usd/loadRenderSettingsFromUsdStage": None,
            "/app/omni.usd/resetRenderSettingsInUsdStage": None,
        }

        for k in rs_settings.keys():
            val = self._settings.get(k)
            if val is not None:
                rs_settings[k] = val  # type: ignore
                self._settings.set(k, False)

        try:
            self._create_usd_context(self._usd_context_name, self._stage_id)

            viewport_window = create_viewport_window(
                name=self._window_title,
                usd_context_name=self._usd_context_name,
                width=256,
                height=256,
                visible=True,
            )
        finally:
            # Restoring the changed settings once the clash viewport and the custom usd context have been created
            for k, val in rs_settings.items():
                if val is not None:
                    self._settings.set(k, val)

        # Create widgets
        assert viewport_window
        self._viewport_window = viewport_window
        overlay_frame = self._viewport_window.get_frame("overlay_info")
        with overlay_frame:
            with ui.ZStack():
                self._warning_message = ui.Label(
                    "WARNING_MESSAGE",
                    style={"margin": 5, "color": ui.color.yellow},
                    alignment=ui.Alignment.BOTTOM,
                )
        self._warning_message.visible = False

        # Save Viewport API
        self.on_visibility_changed(True)  # First on visibility event is not launched
        viewport_api = self._viewport_window.viewport_api
        assert isinstance(viewport_api, ViewportAPI)
        self._viewport_api = viewport_api

        # Force refresh settings
        self._clear_settings_sub()
        self._set_settings_sub()

    @property
    def window(self):
        try:
            return self._viewport_window
        except:
            return None

    def destroy(self):  # pragma: no cover

        if len(self._selection_group_prims) > 0:
            self._clash_viewport_highlight.remove_prims_from_highlight(self._selection_group_prims)
            self._selection_group_prims.clear()

        # Telemetry
        del self._telemetry

        # Settings
        self._clear_settings_sub()
        del self._settings

        # Stage / Session Layer
        # self._stage is removed at the very end of this function
        self._remove_session_layer(remove_materials=True)
        if self._stage:
            self._stage.RemovePrim(f"{self._clash_viewport_path}/Clashes")

        del self._main_viewport_overrides
        if self._clash_viewport_root:
            del self._clash_viewport_root
            del self._clash_viewport_shared
            del self._clash_viewport_only
            del self._clash_viewport_environment
            del self._clash_viewport_materials

        # Additional Window / Additional USD Context
        if hasattr(self, "_viewport_api"):
            del self._viewport_api

        if self._viewport_toolbar:
            self._viewport_toolbar.destroy()
            del self._viewport_toolbar
        if hasattr(self, "_viewport_window"):
            self._viewport_window.destroy()
            del self._viewport_window
        del self._warning_message

        if hasattr(self, "_usd_context"):
            self._usd_context.close_stage()
        cache = UsdUtils.StageCache.Get()
        cache.Erase(Usd.StageCache.Id.FromLongInt(self._stage_id))
        del self._stage

        # Removing hydra and destroying context will degrade with leaks over time with hot reloads
        # self._usd_context.remove_all_hydra_engines()  # this makes successive attach stage very slow
        # omni.usd.destroy_context(self._usd_context_name)
        if hasattr(self, "_usd_context"):
            del self._usd_context

        # Last
        del self._last_clash_timecode
        del self._last_clash_info_items

    @property
    def telemetry(self) -> ClashDetectionViewportTelemetry | None:
        return self._telemetry

    def on_visibility_changed(self, visible: bool):
        self.update_telemetry_counters()
        if visible:
            self._telemetry_visible_at = time.time()
        else:
            self._telemetry_visible_at = None

    def on_focus_changed(self, focused: bool):
        self.update_telemetry_counters()
        if focused:
            self._telemetry_focused_at = time.time()
        else:
            self._telemetry_focused_at = None

    def setting_changed_forced_redraw(self):
        self.display_clashes(self._last_clash_timecode, self._last_clash_info_items)

    def update_telemetry_counters(self):
        now_time = time.time()
        if self._telemetry:
            self._telemetry.inited_seconds = now_time - self._telemetry_inited_at
            if self._telemetry_visible_at:
                self._telemetry.visible_seconds += now_time - self._telemetry_visible_at
            if self._telemetry_focused_at:
                self._telemetry.focused_seconds += now_time - self._telemetry_focused_at

    def _create_materials(self):
        assert self._stage
        materials_root = f"{self._clash_viewport_path}/Looks"
        try:
            self._stage.SetEditTarget(self._clash_viewport_materials)
            UsdGeom.Scope.Define(self._stage, materials_root)
            self._stage.GetPrimAtPath(self._clash_viewport_path).SetMetadata("hide_in_stage_window", True)

            # Materials for clash viewport
            self._material_paths = ClashViewportMaterialPaths()
            self._material_paths.fill_standard_materials(self._stage, materials_root)

            # Materials for main viewport
            self._diffuse_materials = self._material_paths.no_clash_diffuse_materials
        finally:
            self._stage.SetEditTarget(self._stage.GetRootLayer())

    def _set_settings_sub(self):
        if self._settings_tracked:
            return
        self._settings_tracked = True
        # this rtx setting gets reset at every new stage
        self._settings_subs = []
        self._setting_original_rtx_wireframe_worldspace = self._settings.get_as_bool(
            SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE
        )
        self._setting_original_rtx_wireframe_thickness = self._settings.get_as_float(SETTING_RTX_WIREFRAME_THICKNESS)
        if self._setting_original_rtx_wireframe_worldspace:
            self._settings.set_bool(SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE, False)
            if self._setting_original_rtx_wireframe_thickness < ClashViewportSettingValues.CLASH_WIREFRAME_THICKNESS:
                self._settings.set_float(
                    SETTING_RTX_WIREFRAME_THICKNESS,
                    ClashViewportSettingValues.CLASH_WIREFRAME_THICKNESS,
                )
            self._settings_subs.append(
                omni.kit.app.SettingChangeSubscription(
                    SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE,
                    self._setting_rtx_wireframe_thickness_changed,
                )
            )
            self._settings_subs.append(
                omni.kit.app.SettingChangeSubscription(
                    SETTING_RTX_WIREFRAME_THICKNESS,
                    self._setting_rtx_wireframe_thickness_changed,
                )
            )
        self._setting_original_usdrt_fast_diffing = self._settings.get_as_bool(SETTING_USDRT_FAST_DIFFING)
        if self._setting_original_usdrt_fast_diffing:
            self._settings.set_bool(SETTING_USDRT_FAST_DIFFING, False)
            self._settings_subs.append(
                omni.kit.app.SettingChangeSubscription(
                    SETTING_USDRT_FAST_DIFFING,
                    self._setting_usdrt_fast_diffing_changed,
                )
            )

    def _clear_settings_sub(self):
        self._settings_subs = None
        if not self._settings_tracked:
            return
        self._settings_tracked = False
        # If we've modified global rtx setting, then we'll restore it to its original value
        if self._setting_original_rtx_wireframe_worldspace:
            if not self._settings.get_as_bool(SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE):
                self._settings.set_bool(SETTING_RTX_WIREFRAME_THICKNESS_WORLD_SPACE, True)
                self._settings.set_float(
                    SETTING_RTX_WIREFRAME_THICKNESS,
                    self._setting_original_rtx_wireframe_thickness,
                )
        if self._setting_original_usdrt_fast_diffing:
            self._settings.set_bool(SETTING_USDRT_FAST_DIFFING, self._setting_original_usdrt_fast_diffing)

    def on_stage_event(self, event_type: omni.usd.StageEventType):
        """To be called when a stage event happens"""
        if event_type == omni.usd.StageEventType.CLOSING:
            self.update_telemetry_counters()
            ClashTelemetry.log_viewport_telemetry(self._telemetry)
            self._remove_session_layer()
            if self._stage:
                self._stage.RemovePrim(f"{self._clash_viewport_path}/Clashes")
            self._clear_settings_sub()
        elif event_type == omni.usd.StageEventType.OPENED:
            self._settings_tracked = False
            source_stage = get_context_stage(omni.usd.get_context())
            if source_stage:
                self._stage.SetEditTarget(self._clash_viewport_root)
                UsdGeom.SetStageUpAxis(self._stage, UsdGeom.GetStageUpAxis(source_stage))
                UsdGeom.SetStageMetersPerUnit(self._stage, UsdGeom.GetStageMetersPerUnit(source_stage))
                self._stage.SetTimeCodesPerSecond(source_stage.GetTimeCodesPerSecond())
                self._stage.SetStartTimeCode(source_stage.GetStartTimeCode())
                self._stage.SetEndTimeCode(source_stage.GetEndTimeCode())

    def _setting_rtx_wireframe_thickness_changed(self, _, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            # If user manually changed it, we will not restore it
            self._setting_original_rtx_wireframe_worldspace = False

    def _setting_usdrt_fast_diffing_changed(self, _, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            # If user manually changed it, we will not restore it
            self._setting_original_usdrt_fast_diffing = False
            if self._settings.get_as_bool(SETTING_USDRT_FAST_DIFFING):
                error_message = f'"{SETTING_USDRT_FAST_DIFFING}" == True causes visual artifacts in clash overlays'
                carb.log_error(error_message)
                self.display_warning(error_message)

    def _create_stage(self):
        # The stage is being organized in multiple layers to allow sharing only some elements in main viewport.
        #
        # - clash_viewport_root         : Clash viewport root layer. Holds all clash_viewport_* layers.
        # - clash_viewport_shared       : Shared layer (main / clash) holding clash meshes
        # - clash_viewport_only         : Clash viewport specific layer (holding no-clash meshes for example)
        # - clash_viewport_environment  : Clash viewport lights (we don't want them in the main viewport)
        # - clash_viewport_materials    : Shared layer (main / clash) holding materials
        # - main_viewport_overrides     : Main viewport specific overrides (different material for source_meshes etc)
        self._clash_viewport_root: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_root")  # type: ignore
        self._clash_viewport_shared: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_shared")  # type: ignore
        self._clash_viewport_only: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_only")  # type: ignore
        self._clash_viewport_environment: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_environment")  # type: ignore
        self._clash_viewport_materials: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_materials")  # type: ignore
        self._main_viewport_overrides: Sdf.Layer = Sdf.Layer.CreateAnonymous("clash_viewport_overrides")  # type: ignore

        # Compose all clash_viewport* layers in the deidcated clash_viewport_root
        stage: Usd.Stage = Usd.Stage.Open(self._clash_viewport_root)  # type: ignore
        Sdf.ListProxy_SdfSubLayerTypePolicy
        self._clash_viewport_root.subLayerPaths.append(self._clash_viewport_shared.identifier)  # type: ignore
        self._clash_viewport_root.subLayerPaths.append(self._clash_viewport_only.identifier)  # type: ignore
        self._clash_viewport_root.subLayerPaths.append(self._clash_viewport_environment.identifier)  # type: ignore
        self._clash_viewport_root.subLayerPaths.append(self._clash_viewport_materials.identifier)  # type: ignore
        stage.RemovePrim(f"{self._clash_viewport_path}/Clashes")
        stage.RemovePrim(f"{self._clash_viewport_path}_Environment")
        self._stage = stage

        # Cannot insert the layer in main stage as main stage may be null here.
        # We insert it lazily in the first _on_clash_selection_changed

        cache: UsdUtils.StageCache = UsdUtils.StageCache.Get()
        cache.Insert(self._stage)
        self._stage_id: int = cache.GetId(self._stage).ToLongInt()

    def _remove_session_layer(self, remove_materials: bool = False):
        if self._clash_viewport_root:
            source_stage = get_context_stage(omni.usd.get_context())
            if source_stage:
                root_layer: Sdf.Layer = source_stage.GetSessionLayer()
                has_layer = self._main_viewport_overrides.identifier in root_layer.subLayerPaths  # type: ignore
                # Removing prim specs before removing the sublayer avoids a full stage resync
                if has_layer:
                    remove_all_prim_specs(self._main_viewport_overrides)
                    remove_all_prim_specs(self._clash_viewport_shared)
                if remove_materials:
                    remove_all_prim_specs(self._clash_viewport_materials)
                    if hasattr(self, "_diffuse_materials"):
                        del self._diffuse_materials
                        self._clash_viewport_materials.Clear()

                if has_layer:
                    root_layer.subLayerPaths.remove(self._main_viewport_overrides.identifier)  # type: ignore
                    root_layer.subLayerPaths.remove(self._clash_viewport_shared.identifier)  # type: ignore
                if remove_materials:
                    root_layer.subLayerPaths.remove(self._clash_viewport_materials.identifier)  # type: ignore

    def _add_session_layer(self):
        context = omni.usd.get_context()
        source_stage = get_context_stage(context)
        if self._clash_viewport_root and source_stage:
            session_layer = source_stage.GetSessionLayer()
            if self._clash_viewport_shared.identifier not in session_layer.subLayerPaths:
                if hasattr(self, "_diffuse_materials"):
                    del self._diffuse_materials
                    self._clash_viewport_materials.Clear()
                session_layer.subLayerPaths.append(self._main_viewport_overrides.identifier)
                session_layer.subLayerPaths.append(self._clash_viewport_shared.identifier)
                if not self._clash_viewport_materials.identifier in session_layer.subLayerPaths:  # type: ignore
                    session_layer.subLayerPaths.append(self._clash_viewport_materials.identifier)

    def _create_usd_context(self, usd_context_name: str, stage_id: int):
        # We may be given an already valid context, or we'll be creating and managing it ourselves
        usd_context = omni.usd.get_context(usd_context_name)
        if not usd_context:
            self._usd_context = omni.usd.create_context(usd_context_name)
        else:
            self._usd_context = usd_context
        self._usd_context.attach_stage_with_callback(stage_id)

    def _create_lights(self):
        self._stage.SetEditTarget(self._clash_viewport_environment)
        UsdGeom.Scope.Define(self._stage, f"{self._clash_viewport_path}_Environment")
        domeLight = UsdLux.DomeLight.Define(self._stage, Sdf.Path(f"{self._clash_viewport_path}_Environment/domeLight"))
        domeLight.CreateIntensityAttr(30)
        domeLight.CreateSpecularAttr().Set(0.0)
        defaultLight: UsdLux.DistantLight = UsdLux.DistantLight.Define(
            self._stage,
            Sdf.Path(f"{self._clash_viewport_path}_Environment/defaultLight"),
        )
        defaultLight.CreateIntensityAttr(3000)  # type: ignore
        defaultLight.CreateAngleAttr(1.0)  # type: ignore
        defaultLight.ClearXformOpOrder()
        defaultLight.AddRotateXYZOp().Set(Gf.Vec3d(315, 0, 0))  # type: ignore
        self._stage.SetEditTarget(self._stage.GetRootLayer())

    def _on_clash_timecode_change(self):
        pass

    @staticmethod
    def _can_use_outlines_for_centering(stage: Usd.Stage, clash_paths: ClashViewportMeshPaths) -> bool:
        # With hard clash, we often have outlines, even if there are a few cases where there are no outlines.
        # Outlines are always the main interest zone under any circumstances and they exist both when using
        # selection groups and when not using them, both in the main viewport and in the dedicated clash viewport.
        # We need however to check that the ABB geometric diagonal is not smaller than clash min scale to avoid
        # centering on too small outlines that would "zoom" in too much on the clash.
        if clash_paths.outlines_path and stage.GetPrimAtPath(clash_paths.outlines_path):
            bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
            bbox = bbox_cache.ComputeWorldBound(stage.GetPrimAtPath(clash_paths.outlines_path)).ComputeAlignedRange()
            diagonal = math.sqrt(
                (bbox.GetMax()[0] - bbox.GetMin()[0]) ** 2
                + (bbox.GetMax()[1] - bbox.GetMin()[1]) ** 2
                + (bbox.GetMax()[2] - bbox.GetMin()[2]) ** 2
            )
            if diagonal < ClashViewportSettingValues.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING:
                return False
            return True
        return False

    @staticmethod
    def _get_centering_paths(stage: Usd.Stage, clash_paths: ClashViewportMeshPaths, p1: str, p2: str):
        if ClashDetectionViewport._can_use_outlines_for_centering(stage, clash_paths):
            selected_paths = [clash_paths.outlines_path]
        else:
            if clash_paths.do_clash_paths_solid:
                prim1 = stage.GetPrimAtPath(clash_paths.do_clash_paths_solid[0])
                prim2 = stage.GetPrimAtPath(clash_paths.do_clash_paths_solid[1])
                if prim1 or prim2:
                    p1 = clash_paths.do_clash_paths_solid[0]
                    p2 = clash_paths.do_clash_paths_solid[1]
            elif clash_paths.no_clash_paths_solid:
                prim1 = stage.GetPrimAtPath(clash_paths.no_clash_paths_solid[0])
                prim2 = stage.GetPrimAtPath(clash_paths.no_clash_paths_solid[1])
                if prim1 or prim2:
                    p1 = clash_paths.no_clash_paths_solid[0]
                    p2 = clash_paths.no_clash_paths_solid[1]
            selected_paths = ClashViewportCamera.choose_smallest_prim(stage, p1, p2)
        selected_paths = [item for item in selected_paths if item is not None]
        return selected_paths

    def _center_main_viewport(self, stage: Usd.Stage, selected_paths: list[str], fine_tuning: bool):
        if len(selected_paths) == 0:
            return

        active_viewport = get_active_viewport()
        assert isinstance(active_viewport, ViewportAPI)
        selection = active_viewport.usd_context.get_selection()
        old_paths = selection.get_selected_prim_paths()

        # Center main viewport on the outlines
        if fine_tuning:
            ClashViewportCamera.center_preserving_user_camera_fine_tuning(active_viewport, stage, selected_paths)
        else:
            ClashViewportCamera.center_selection(
                selection,
                selected_paths,
                active_viewport,
            )

        selection.set_selected_prim_paths(old_paths, False)

    def _center_clash_viewport(self, selected_paths: list[str], fine_tuning: bool):
        if len(selected_paths) == 0:
            return
        # Note: We only focus the first one in case multiple are selected
        if hasattr(self, "_usd_context"):
            # Center clash viewport on the outlines
            if fine_tuning:
                ClashViewportCamera.center_preserving_user_camera_fine_tuning(
                    self._viewport_api, get_context_stage(self._usd_context), selected_paths
                )
            else:
                ClashViewportCamera.center_selection(
                    self._viewport_api.usd_context.get_selection(),
                    selected_paths,
                    self._viewport_api,
                )

    def display_clashes(self, clash_timecode: float, clash_info_items: Dict[str, Any]):
        display_clash_in_main_viewport = (
            ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES
            or ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES
        )
        display_clash_in_clash_viewport = ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES
        center_main_viewport_on_clash = ClashViewportSettingValues.MAIN_VIEWPORT_CENTER_CAMERA
        center_clash_viewport_on_clash = ClashViewportSettingValues.CLASH_VIEWPORT_CENTER_CAMERA
        center_main_viewport_fine_tuning = ClashViewportSettingValues.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE
        center_clash_viewport_fine_tuning = ClashViewportSettingValues.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE
        source_stage = get_context_stage(omni.usd.get_context())

        self._last_clash_timecode = clash_timecode
        self._last_clash_info_items = clash_info_items

        # Empty the layers so that clash overlays will disappear from both main viewport and clash viewport
        self._main_viewport_overrides.Clear()  # Remove main viewport specific overrides
        self._clash_viewport_only.Clear()  # Remove clash viewport no-clash meshes
        self._clash_viewport_shared.Clear()  # Remove shared clash meshes
        self._stage.RemovePrim("/ClashDetectionViewport")  # Remove transforms left by manipulator
        if len(self._selection_group_prims) > 0:
            self._clash_viewport_highlight.remove_prims_from_highlight(self._selection_group_prims)
            self._selection_group_prims.clear()

        if self._warning_message:
            self._warning_message.visible = False

        # Build the meshes
        if clash_info_items is None or (not display_clash_in_main_viewport and not display_clash_in_clash_viewport):
            return

        all_clash_paths = []
        if len(clash_info_items):
            # Materials must be added AFTER materials sublayer is added to root stage
            # THis avoids a full stage resync, a real performance disaster for large stages
            if not hasattr(self, "_diffuse_materials"):
                self._create_materials()

            # TODO: Support only showing main viewport with no clash viewport
            if source_stage:
                UsdGeom.SetStageUpAxis(self._stage, UsdGeom.GetStageUpAxis(source_stage))
                UsdGeom.SetStageMetersPerUnit(self._stage, UsdGeom.GetStageMetersPerUnit(source_stage))
            source_edit_target = source_stage.GetEditTarget()
            with CodeTimer("build_clash_meshes"):
                try:
                    self._stage.SetEditTarget(self._clash_viewport_shared)
                    UsdGeom.Scope.Define(self._stage, f"{self._clash_viewport_path}/Clashes")
                    all_clash_paths = self._build_clash_meshes(
                        clash_info_items=clash_info_items,
                        clash_viewport_path=self._clash_viewport_path,
                        material_paths=self._material_paths,
                        timecode=clash_timecode,
                        source_stage=source_stage,
                    )
                finally:
                    self._stage.SetEditTarget(self._stage.GetRootLayer())
                    source_stage.SetEditTarget(source_edit_target)

        # Center camera / Fix RTX Wireframe settings
        self._setup_main_viewport_visualization(
            source_stage,
            self._stage,
            all_clash_paths,
            clash_info_items,
            display_clash_in_main_viewport,
        )

        if len(all_clash_paths):
            self._set_settings_sub()
            accumulated_main_viewport_paths = []
            accumulated_clash_viewport_paths = []

            for clash_path in all_clash_paths:
                p1 = clash_info_items[clash_path.overlap_id].object_a_path
                p2 = clash_info_items[clash_path.overlap_id].object_b_path

                if display_clash_in_clash_viewport and center_clash_viewport_on_clash:
                    paths = ClashDetectionViewport._get_centering_paths(self._stage, clash_path, p1, p2)
                    accumulated_clash_viewport_paths.extend(paths)

                if display_clash_in_main_viewport and center_main_viewport_on_clash:
                    paths = ClashDetectionViewport._get_centering_paths(source_stage, clash_path, p1, p2)
                    accumulated_main_viewport_paths.extend(paths)

            self._center_clash_viewport(accumulated_clash_viewport_paths, center_clash_viewport_fine_tuning)
            self._center_main_viewport(source_stage, accumulated_main_viewport_paths, center_main_viewport_fine_tuning)

            if ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS:
                if ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES:
                    if display_clash_in_main_viewport:
                        self._update_selection_groups(all_clash_paths, clash_info_items)
        else:
            # Needs to be delayed for the enableFastDiffing to be applied
            asyncio.ensure_future(self._async_clear_settings_sub())

    def _update_selection_groups(self, all_clash_paths: list[ClashViewportMeshPaths], clash_info_items: Dict[str, Any]):
        object_a_group_name = self._clash_viewport_highlight.get_object_a_group_name()
        object_b_group_name = self._clash_viewport_highlight.get_object_b_group_name()
        outlines_group_name = self._clash_viewport_highlight.get_outlines_group_name()
        duplicate_group_name = self._clash_viewport_highlight.get_duplicate_group_name()
        for item in all_clash_paths:
            clash_info = clash_info_items[item.overlap_id]
            p1 = clash_info.object_a_path
            p2 = clash_info.object_b_path
            # Using the "manual" add_prims_to_highlight because:
            # 1. It avoids any potential long USD resync on very large stages (we need to be really careful here)
            # 2. It works also for instance proxies. We can't "un-instance" the prims like clash bake does as per 1.
            if clash_info.is_duplicate:
                # Just one mesh
                self._clash_viewport_highlight.add_prims_to_highlight([p1, p2], duplicate_group_name)
                self._selection_group_prims.extend([p1, p2])
            else:
                # Both meshes
                self._clash_viewport_highlight.add_prims_to_highlight([p1], object_a_group_name)
                self._clash_viewport_highlight.add_prims_to_highlight([p2], object_b_group_name)
                self._clash_viewport_highlight.add_prims_to_highlight([item.outlines_path], outlines_group_name)
                self._selection_group_prims.extend([p1, p2, item.outlines_path])

    async def _async_clear_settings_sub(self):
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        self._clear_settings_sub()

    def _setup_main_viewport_visualization(
        self,
        source_stage: Usd.Stage,
        destination_stage: Usd.Stage,
        all_clash_paths: list[ClashViewportMeshPaths],
        clash_info_items: Dict[str, Any],
        display_clash_in_main_viewport: bool,
    ):
        needs_session_layer = ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES or (
            ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES
            and not ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS
        )
        if display_clash_in_main_viewport and needs_session_layer:
            self._add_session_layer()
        else:
            self._remove_session_layer()
            return

        if len(all_clash_paths) == 0:
            return

        # If the user has disabled clash meshes in the main viewport, we don't need to do anything
        if not ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES:
            return

        # Apply overrides for main viewport
        old_edit_target = source_stage.GetEditTarget()
        try:
            source_stage.SetEditTarget(self._main_viewport_overrides)

            # This can happen when not displaying clash main viewport (because attach will clear materials)
            if not hasattr(self, "_diffuse_materials"):
                self._create_materials()

            diffuse_material0 = UsdShade.Material.Get(destination_stage, self._diffuse_materials[0])
            diffuse_material1 = UsdShade.Material.Get(destination_stage, self._diffuse_materials[1])

            for item in all_clash_paths:
                clash_info = clash_info_items[item.overlap_id]
                if not clash_info.present:
                    self._hide_if_exists(source_stage, item.do_clash_paths_solid[0])
                    self._hide_if_exists(source_stage, item.do_clash_paths_solid[1])
                    self._hide_if_exists(source_stage, item.do_clash_paths_wireframe[0])
                    self._hide_if_exists(source_stage, item.do_clash_paths_wireframe[1])
                    self._hide_if_exists(source_stage, item.outlines_path)

                    if clash_info.is_duplicate:
                        self.display_warning("Showing a duplicate mesh that may not match last clash detection run")
                    else:
                        self.display_warning(
                            "Showing clashing polygons and outlines that may not match last clash detection run"
                        )

                if item.outlines_hidden:
                    self._hide_if_exists(destination_stage, item.outlines_path)
                if item.no_clash_paths_solid:
                    self._change_prim_material_or_hide_parent(
                        source_stage,
                        clash_info.object_a_path,
                        clash_info.present,
                        diffuse_material0,
                        item.no_clash_paths_solid[0],
                    )
                    self._change_prim_material_or_hide_parent(
                        source_stage,
                        clash_info.object_b_path,
                        clash_info.present,
                        diffuse_material1,
                        item.no_clash_paths_solid[1],
                    )

                if clash_info.is_duplicate and not ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS:
                    self._hide_if_exists(source_stage, clash_info.object_a_path)
                    self._hide_if_exists(source_stage, clash_info.object_b_path)

        except Exception as e:
            carb.log_error(e)
            carb.log_error(self._format_exception(e))
        finally:
            source_stage.SetEditTarget(old_edit_target)

    def _hide_with_invisible_material(self, prim_to_hide: Usd.Prim):
        # NOTE: Hiding the source prim doesn't work when there are animation cuves because they override
        # visibility directly session layer (or Fabric).
        # For this reason we also set the root of the instance proxy to use an invisible material
        binding = UsdShade.MaterialBindingAPI.Apply(prim_to_hide)
        rel = binding.GetPrim().CreateRelationship("material:binding", False)
        rel.SetTargets([Sdf.Path(self._material_paths.invisible_material)])
        # prim_to_hide.GetAttribute("visibility").Set("hidden")

    def _hide_if_exists(self, stage, prim_path):
        if not prim_path:
            return
        prim = stage.GetPrimAtPath(prim_path)
        if prim:
            if prim.IsInstanceProxy():
                # Cannot modify visibility of this prim because it's part of an instancing proxy
                parent_prim = prim
                # Let's try to find its instancing root parent
                while parent_prim.IsValid() and parent_prim.IsInstanceProxy():
                    parent_prim = parent_prim.GetParent()
                if parent_prim and parent_prim.IsValid() and not parent_prim.IsPseudoRoot():
                    # Best we can do hide is hiding the parent prim entirely, as we can't hide only some sub children
                    self._hide_with_invisible_material(parent_prim)  # Instance proxy
                else:
                    carb.log_error(f'Failed to find parent prim of instancing proxy at "{prim_path}" to hide')
            else:
                self._hide_with_invisible_material(prim)  # Not Instance proxy

    def _change_prim_material_or_hide_parent(
        self,
        source_stage: Usd.Stage,
        path: str,
        clash_present: bool,
        diffuse_material: UsdShade.Material,
        no_clash_path_solid: str,
    ):
        if ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS:
            return
        source = source_stage.GetPrimAtPath(path)
        if not source:
            return
        if source.IsInstanceProxy():
            # We cannot modify materials of this prim because it's part of an instancing proxy
            self._hide_if_exists(source_stage, source.GetPath())
            mesh = None
            # Using source stage here because we want to override the translucent material only in main viewport
            if no_clash_path_solid:
                no_clash = source_stage.GetPrimAtPath(no_clash_path_solid)
                binding = UsdShade.MaterialBindingAPI.Apply(no_clash)
                binding.Bind(diffuse_material, UsdShade.Tokens.weakerThanDescendants)
                mesh = UsdGeom.Mesh(no_clash)
        else:
            # Change the material used in the main viewport to a generic diffuse material with standard "clash" colors
            binding = UsdShade.MaterialBindingAPI.Apply(source)
            binding.Bind(diffuse_material, UsdShade.Tokens.weakerThanDescendants)
            mesh = UsdGeom.Mesh(source)
            # Modify source mesh hole indices so that it becomes equivalent to the no_clash mesh, without needing to overlay it
            if clash_present and no_clash_path_solid:
                no_clash = source_stage.GetPrimAtPath(no_clash_path_solid)
                mesh.GetHoleIndicesAttr().Set(UsdGeom.Mesh(no_clash).GetHoleIndicesAttr().Get())
        # Change normals interpolation
        if mesh:
            mesh.GetNormalsAttr().Set([])  # Avoids the warning "corrupted data in primvar 'normal': buffer size..."
            mesh.SetNormalsInterpolation("uniform")

    def display_warning(self, text: str):
        if self._warning_message:
            self._warning_message.text = text
            self._warning_message.visible = True

    def _build_clash_meshes(
        self,
        clash_info_items: Dict[str, Any],
        clash_viewport_path: str,
        material_paths: ClashViewportMaterialPaths,
        timecode: float,
        source_stage: Usd.Stage,
    ) -> list[ClashViewportMeshPaths]:
        """Takes a list of clash_info_items and builds clash USD meshes and clash outlines for them"""
        all_clash_paths: list[ClashViewportMeshPaths] = []
        usd_timecode = Usd.TimeCode(omni.usd.get_frame_time_code(timecode, self._stage.GetTimeCodesPerSecond()))

        # This is needed to induct a proper recomposition when "clearing" the clash over layers
        xform = UsdGeom.Xform.Define(self._stage, clash_viewport_path)
        self._stage.SetDefaultPrim(xform.GetPrim())

        # Force not to create wireframes for no-clash meshes
        material_paths.no_clash_wireframe_materials = ("", "")
        display_limit = ClashViewportSettingValues.CLASH_MESHES_DISPLAY_LIMIT
        err_message = None
        if len(clash_info_items) > 1 and display_limit > 1:
            if (
                ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS == False
                and ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES
            ):
                # Safety break for the "material changing" mode that can cause huge performance issues on large stages
                display_limit = 1
                err_message = "Displaying only one clash mesh because '/physics/clashDetectionViewport/mainViewport/useSelectionGroups' is False"

        if len(clash_info_items) > display_limit:
            if err_message is None:
                err_message = f"Displaying the first {display_limit} clashes of the {len(clash_info_items)} requested (/physics/clashDetectionViewport/clashMeshesDisplayLimit: {display_limit})"
            carb.log_warn(err_message)
            self.display_warning(err_message)

            clash_info_items = {
                k: v for k, v in clash_info_items.items() if k in list(clash_info_items.keys())[:display_limit]
            }

        for index, clash_info in enumerate(clash_info_items.values()):
            source_prim_0: Usd.Prim | None = source_stage.GetPrimAtPath(clash_info.object_a_path)
            source_prim_1: Usd.Prim | None = source_stage.GetPrimAtPath(clash_info.object_b_path)
            base_clash_path = f"{clash_viewport_path}/Clashes/Clash{index}"

            try:
                if clash_info.clash_frame_info_items is None:
                    carb.log_error(
                        f"Clash info for {clash_info.object_a_path} / {clash_info.object_b_path} has no frame info"
                    )
                    continue
                frame_info_index = clash_info.get_frame_info_index_by_timecode(timecode)
                clash_info_paths = self._add_clash_frame(
                    source_stage=source_stage,
                    frame_info_index=frame_info_index,
                    clash_info=clash_info,
                    usd_timecode=usd_timecode,
                    source_prim_0=source_prim_0,
                    source_prim_1=source_prim_1,
                    material_paths=material_paths,
                    base_clash_path=base_clash_path,
                )
                if clash_info_paths is None:
                    continue
                all_clash_paths.append(clash_info_paths)
            except Exception as e:
                carb.log_error(e)
                carb.log_error(self._format_exception(e))
        return all_clash_paths

    def _add_clash_frame(
        self,
        source_stage: Usd.Stage,
        frame_info_index: int,
        clash_info: Any,
        usd_timecode: Usd.TimeCode,
        source_prim_0: Usd.Prim | None,
        source_prim_1: Usd.Prim | None,
        material_paths: ClashViewportMaterialPaths,
        base_clash_path: str,
    ) -> ClashViewportMeshPaths | None:
        if clash_info.check_object_a_matrix_changed(source_stage, frame_info_index):
            self.display_warning(
                f'Clash Mesh A is at a different location compared to last clash detection run\n("{clash_info.object_a_path}")'
            )
        if clash_info.check_object_b_matrix_changed(source_stage, frame_info_index):
            self.display_warning(
                f'Clash Mesh B is at a different location compared to last clash detection run\n("{clash_info.object_b_path}")'
            )
        usd_faces_0: wp.array | None = None  # type: ignore
        usd_faces_1: wp.array | None = None  # type: ignore
        collision_outline = wp.array([], dtype=wp.uint32)  # type: ignore
        if clash_info.is_duplicate:
            if not source_prim_0 and not source_prim_1:
                self.display_warning("Both source prims for this duplicate are missing")
                return None
            frame_info = None
            if source_prim_1 and source_prim_0:
                source_prim_1 = None
        else:
            if self._warning_message:
                if not source_prim_0 and not source_prim_1:
                    self.display_warning(
                        f'Missing prims at "{clash_info.object_a_path} and "{clash_info.object_b_path}"'
                    )
                    return None
                elif not source_prim_0:
                    self.display_warning(f'Missing prim at "{clash_info.object_a_path}"')
                elif not source_prim_1:
                    self.display_warning(f'Missing prim at "{clash_info.object_b_path}"')

            frame_info = clash_info.clash_frame_info_items[frame_info_index]
            usd_faces_0 = frame_info.usd_faces_0
            usd_faces_1 = frame_info.usd_faces_1
            collision_outline: wp.array = frame_info.collision_outline  # type: ignore

            # If current frame has no outline (it's possible with soft clashes) this generates the collision
            # outline for first next (or previous) frame info that has some outline.
            # This outline will not be visible and it's just used to center the camera in the viewport

            # Search Forward
            if len(collision_outline) == 0:
                for next_frame_info in clash_info.clash_frame_info_items[frame_info_index:]:
                    if len(next_frame_info.collision_outline) > 0:
                        collision_outline = next_frame_info.collision_outline
                        break

            # Search Backward
            if len(collision_outline) == 0:
                for next_frame_info in clash_info.clash_frame_info_items[:frame_info_index]:
                    if len(next_frame_info.collision_outline) > 0:
                        collision_outline = next_frame_info.collision_outline
                        break

        UsdGeom.Xform.Define(self._stage, base_clash_path)

        # This closure activates the correct destination layer where a specific mesh must be created
        def activate_destination_layer_shared(usd_path: str) -> Usd.Stage:
            # Display the no_clash meshes only on clash viewport, if their source prim is not an instance proxy
            # Everything else goes in the shared layer that is displayed both on main and clash viewport
            if usd_path.endswith("no_clash_0"):
                if source_prim_0 and source_prim_0.IsInstanceProxy():
                    self._stage.SetEditTarget(self._clash_viewport_shared)
                else:
                    self._stage.SetEditTarget(self._clash_viewport_only)
            elif usd_path.endswith("no_clash_1"):
                if source_prim_1 and source_prim_1.IsInstanceProxy():
                    self._stage.SetEditTarget(self._clash_viewport_shared)
                else:
                    self._stage.SetEditTarget(self._clash_viewport_only)
            else:
                self._stage.SetEditTarget(self._clash_viewport_shared)
            return self._stage

        def activate_destination_layer_dest(_: str) -> Usd.Stage:
            return self._stage

        def activate_destination_layer_source(_: str) -> Usd.Stage:
            return source_stage

        # Somewhat convoluted logic but with current setup there's no easier way
        if ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES:
            if ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS:
                if ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES:
                    activate_destination_layer = activate_destination_layer_dest
                    self._stage.SetEditTarget(self._clash_viewport_only)
                else:
                    activate_destination_layer = None
            else:
                if ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES:
                    activate_destination_layer = activate_destination_layer_shared
                else:
                    try:
                        activate_destination_layer = activate_destination_layer_source
                        source_stage.SetEditTarget(self._main_viewport_overrides)
                    except:
                        carb.log_warn("Main viewport overrides is not bound yet")
                        activate_destination_layer = None
        else:
            if ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES:
                activate_destination_layer = activate_destination_layer_dest
                self._stage.SetEditTarget(self._clash_viewport_only)
            else:
                activate_destination_layer = None

        if activate_destination_layer is None:
            clash_info_paths = ClashViewportMeshPaths()
        else:
            clash_info_paths = ClashViewportMeshes.create_clash_pairs(
                source_prim_0,
                source_prim_1,
                usd_faces_0,
                usd_faces_1,
                collision_outline,
                usd_timecode,
                base_clash_path,
                material_paths,
                activate_destination_layer,
                ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_WIREFRAMES,
            )

        if ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES:
            outlines_stage = self._stage
            if ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES:
                self._stage.SetEditTarget(self._clash_viewport_shared)
            else:
                self._stage.SetEditTarget(self._clash_viewport_only)
        else:
            if ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES:
                outlines_stage = source_stage
                try:
                    source_stage.SetEditTarget(self._main_viewport_overrides)
                except:
                    carb.log_warn("Main viewport overrides is not bound yet")
                    outlines_stage = None
            else:
                outlines_stage = None

        with CodeTimer("create_outline_curve"):
            clash_info_paths.outlines_path = f"{base_clash_path}/outlines"
            if not outlines_stage or not ClashViewportMeshes.create_outline_curve(
                collision_outline,
                clash_info_paths.outlines_path,
                material_paths.outlines_material,
                outlines_stage,
            ):
                clash_info_paths.outlines_path = ""

        clash_info_paths.overlap_id = clash_info.overlap_id
        if len(collision_outline) > 0 and frame_info:
            clash_info_paths.outlines_hidden = (
                len(collision_outline) != len(frame_info.collision_outline)
                or frame_info.collision_outline.numpy() != collision_outline.numpy()
            )
            if isinstance(clash_info_paths.outlines_hidden, np.ndarray):
                clash_info_paths.outlines_hidden = clash_info_paths.outlines_hidden.any()  # type: ignore
        return clash_info_paths

    def _format_exception(self, e):
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

        exception_str = "Traceback (most recent call last):\n"
        exception_str += "".join(exception_list)
        # Removing the last \n
        exception_str = exception_str[:-1]

        return exception_str
