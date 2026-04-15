# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pxr import Usd, Tf, UsdUtils
import omni.kit.app
import carb.eventdispatcher
import omni.usd
import usdrt
import usdrt.Usd
import carb.settings
from carb.eventdispatcher import get_eventdispatcher
from .clash_viewport_utility import CodeTimer
from .clash_viewport_settings import ClashViewportSettingValues


class ClashViewportHighlight:
    """
    Handles the highlight of clash meshes in the viewport, listening to USD Changes about ClashViewportHighlightAPI.
    """

    def __init__(self, usd_context: omni.usd.UsdContext):
        self._usd_context = usd_context

        self._kit_update_sub: carb.eventdispatcher.Observer | None = None
        self._usd_notice_listener: Tf.Notice.Listener | None = None
        self._selected_paths: list[str] = self._usd_context.get_selection().get_selected_prim_paths()
        self._prev_selected_paths: list[str] = self._usd_context.get_selection().get_selected_prim_paths()
        self._highlighted_paths_from_usd: set[str] = set()
        self._highlighted_paths_manual: dict[str, str] = {}

        self._register_clash_selection_groups()
        self._register_stage_events()
        self._open_stage()

    def destroy(self):
        self._unregister_stage_events()
        self._close_stage()
        self._clear_highlighted_prims()

    ####################################################################################################################
    ## Public API
    ####################################################################################################################
    def add_prims_to_highlight(self, prims: list[str], group_name: str):
        """Manually highlights prims with the given selection group name even if they miss the ClashViewportHighlightAPI"""
        if group_name not in self._selection_groups:
            carb.log_error(f"Group name {group_name} not found in selection groups")
            return
        if ClashViewportSettingValues.LOG_HIGHLIGHT:
            print(f"Adding prims to highlight: {prims} with group name {group_name}")
        with CodeTimer("add_prims_to_highlight"):
            group_id = self._selection_groups[group_name]
            for path in prims:
                self._usd_context.set_selection_group(group_id, path)
            for prim in prims:
                self._highlighted_paths_manual[prim] = group_name

    def remove_prims_from_highlight(self, prims: list[str]):
        """Remove highlighting for the given prims setting them the default selection group (0)"""
        for path in prims:
            self._usd_context.set_selection_group(0, path)
        for prim in prims:
            self._highlighted_paths_manual.pop(prim, None)

    def get_object_a_group_name(self) -> str:
        """Get the selection group name for object A"""
        return "ClashDetection:ObjectA"

    def get_object_b_group_name(self) -> str:
        """Get the selection group name for object B"""
        return "ClashDetection:ObjectB"

    def get_outlines_group_name(self) -> str:
        """Get the selection group name for outlines"""
        return "ClashDetection:Outlines"

    def get_duplicate_group_name(self) -> str:
        """Get the selection group name for duplicates"""
        return "ClashDetection:Duplicate"

    def changed_settings(self):
        """Force a redraw of the highlighted prims"""
        self._set_selection_group_colors()

    ####################################################################################################################
    ## Clash selection groups
    ####################################################################################################################
    def _register_clash_selection_groups(self):
        self._selection_groups = {
            self.get_object_a_group_name(): self._usd_context.register_selection_group(),
            self.get_object_b_group_name(): self._usd_context.register_selection_group(),
            self.get_outlines_group_name(): self._usd_context.register_selection_group(),
            self.get_duplicate_group_name(): self._usd_context.register_selection_group(),
        }
        self._set_selection_group_colors()

    def _set_selection_group_colors(self):
        """Set the selection group colors"""
        # Object A
        TRANSPARENT = 0.0  # Transparent value
        OPAQUE = 0.7  # Opaque value
        group_a = self._selection_groups[self.get_object_a_group_name()]
        if ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES:
            self._usd_context.set_selection_group_shade_color(group_a, carb.Float4(0.051, 0.467, 0.706, OPAQUE))
            self._usd_context.set_selection_group_outline_color(group_a, carb.Float4(0.051, 0.467, 0.706, 1.0))
        else:
            self._usd_context.set_selection_group_shade_color(group_a, carb.Float4(0.051, 0.467, 0.706, TRANSPARENT))
            self._usd_context.set_selection_group_outline_color(group_a, carb.Float4(0.051, 0.467, 0.706, 1.0))

        # Object B
        group_b = self._selection_groups[self.get_object_b_group_name()]
        if ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES:
            self._usd_context.set_selection_group_shade_color(group_b, carb.Float4(1, 0.478, 0, OPAQUE))
            self._usd_context.set_selection_group_outline_color(group_b, carb.Float4(0.0, 1.0, 0.0, 1.0))
        else:
            self._usd_context.set_selection_group_shade_color(group_b, carb.Float4(1, 0.478, 0, TRANSPARENT))
            self._usd_context.set_selection_group_outline_color(group_b, carb.Float4(1, 0.478, 0, 1.0))

        # Outlines
        group_outlines = self._selection_groups[self.get_outlines_group_name()]
        if ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES:
            self._usd_context.set_selection_group_shade_color(group_outlines, carb.Float4(1.0, 0.0, 1.0, OPAQUE))
            self._usd_context.set_selection_group_outline_color(group_outlines, carb.Float4(1.0, 0.0, 1.0, 1.0))
        else:
            self._usd_context.set_selection_group_shade_color(group_outlines, carb.Float4(1.0, 0.0, 1.0, TRANSPARENT))
            self._usd_context.set_selection_group_outline_color(group_outlines, carb.Float4(1.0, 0.0, 1.0, 1.0))

        # Duplicate
        group_duplicate = self._selection_groups[self.get_duplicate_group_name()]
        if ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES:
            self._usd_context.set_selection_group_shade_color(group_duplicate, carb.Float4(1.0, 0, 0, OPAQUE))
            self._usd_context.set_selection_group_outline_color(group_duplicate, carb.Float4(1.0, 0, 0, 1.0))
        else:
            self._usd_context.set_selection_group_shade_color(group_duplicate, carb.Float4(1.0, 0, 0, TRANSPARENT))
            self._usd_context.set_selection_group_outline_color(group_duplicate, carb.Float4(1.0, 0, 0, 1.0))

    def _clear_highlighted_prims(self):
        """Clear the highlighted prims, resetting the selection groups to the default selection group (0)"""
        for path in self._highlighted_paths_from_usd:
            self._usd_context.set_selection_group(0, path)
        for path in self._highlighted_paths_manual.keys():
            self._usd_context.set_selection_group(0, path)
        self._highlighted_paths_from_usd.clear()

    def _clear_specific_highlighted_prims(self, paths_to_clear: set[str]):
        """Clear specific highlighted prims, resetting their selection groups to the default selection group (0)"""
        for path in paths_to_clear:
            if path in self._highlighted_paths_from_usd:
                self._usd_context.set_selection_group(0, path)
                self._highlighted_paths_from_usd.discard(path)

    def _highlight_single_prim(self, usdrt_path: usdrt.Usd.Sdf.Path):
        """Highlight a single prim that has the ClashViewportHighlightAPI applied."""
        if not self._usdrt_stage:
            carb.log_error("Cannot highlight prim if USDRT Stage not available")
            return False

        prim = self._usdrt_stage.GetPrimAtPath(usdrt_path)
        path = str(usdrt_path)
        if not prim:
            return False

        attribute = prim.GetAttribute("omni:clashViewportHighlight:groupName")
        default_group_name = self.get_object_a_group_name()
        group_name = default_group_name
        if attribute:
            group_name = attribute.Get()
        if not group_name:
            group_name = default_group_name

        if group_name in self._selection_groups:
            self._highlighted_paths_from_usd.add(path)
            if self._can_set_selection_group(path):
                if ClashViewportSettingValues.LOG_HIGHLIGHT:
                    print(f"Setting selection group '{group_name}' for path '{path}'")
                self._usd_context.set_selection_group(self._selection_groups[group_name], path)
                return True
        else:
            carb.log_error(f"Group name {group_name} not found in selection groups")
        return False

    def _can_set_selection_group(self, path: str) -> bool:
        """Check if the path does not start with any of the previous selected prim paths"""
        in_selected = False
        in_prev_selected = False
        for prev_path in self._selected_paths:
            if path.startswith(prev_path):
                in_selected = True
                break
        for prev_path in self._prev_selected_paths:
            if path.startswith(prev_path):
                in_prev_selected = True
                break
        return (in_prev_selected and not in_selected) or not in_selected

    def _find_and_highlight_prims(self, usdrt_query: list[usdrt.Usd.Sdf.Path] | None = None):
        """Find and highlight the prims that have the ClashViewportHighlightAPI applied."""
        if not self._usdrt_stage:
            carb.log_error("Cannot find and highlight prims if USDRT Stage not available")
            return
        # This is needed so that clicking "in the void" doesn't trigger clearing all custom selection grups
        carb.settings.get_settings().set_bool("/app/viewport/multiUserOutlineMode", True)
        if not usdrt_query:
            usdrt_query = self._usdrt_stage.GetPrimsWithAppliedAPIName("ClashViewportHighlightAPI")

        for usdrt_path in usdrt_query:
            self._highlight_single_prim(usdrt_path)

    def _highlight_prims_from_manual(self):
        """Highlight the prims from the manual selection"""
        for path, group_name in self._highlighted_paths_manual.items():
            if self._can_set_selection_group(path):
                if ClashViewportSettingValues.LOG_HIGHLIGHT:
                    print(f"Setting manual selection group '{group_name}' for path '{path}'")
                self._usd_context.set_selection_group(self._selection_groups[group_name], path)

    def _request_rebuild(self):
        """Request a rebuild of the highlighted prims that will be done on the next kit update"""
        if self._kit_update_sub:
            return  # Update already requested

        def kit_update_fn(_):
            with CodeTimer("rebuild_highlighted_prims"):
                self._rebuild_highlighted_prims_if_needed()
            self._kit_update_sub = None

        self._kit_update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=kit_update_fn,
            observer_name="omni.physx.clashdetection.viewport:ClashViewportHighlight",
        )

    ####################################################################################################################
    ## Stage events
    ####################################################################################################################
    def _register_stage_events(self):
        """Register the stage events."""
        name = "omni.physx.clashdetection.viewport:ClashViewportHighlight"
        events_to_subscribe = [
            omni.usd.StageEventType.OPENED,
            omni.usd.StageEventType.CLOSED,
            omni.usd.StageEventType.SELECTION_CHANGED,
        ]
        self._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name=name,
                event_name=omni.usd.get_context().stage_event_name(event_type),
                on_event=self._on_stage_event,
            )
            for event_type in events_to_subscribe
        ]

    def _unregister_stage_events(self):
        """Unregister the stage events."""
        self._stage_event_subs = []

    def _on_stage_event(self, event):
        event_type = omni.usd.get_context().stage_event_type(event.event_name)
        match event_type:
            case omni.usd.StageEventType.OPENED:
                with CodeTimer("open_stage"):
                    self._open_stage()
            case omni.usd.StageEventType.CLOSED:
                with CodeTimer("close_stage"):
                    self._close_stage()
            case omni.usd.StageEventType.SELECTION_CHANGED:
                with CodeTimer("selection_changed"):
                    self._selection_changed()
            case _:
                pass

    def _open_stage(self):
        """Opens USDRT Stage and finds the prims that have the ClashViewportHighlightAPI applied when stage is opened"""
        self._stage: Usd.Stage | None = self._usd_context.get_stage()  # type: ignore
        if self._stage:
            self._usd_notice_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, self._stage)
            stage_id = UsdUtils.StageCache.Get().GetId(self._stage).ToLongInt()
            if stage_id == -1:
                stage_id = UsdUtils.StageCache.Get().Insert(self._stage).ToLongInt()
            self._usdrt_stage: usdrt.Usd.Stage | None = usdrt.Usd.Stage.Attach(stage_id)
            self._find_and_highlight_prims()
        else:
            self._usdrt_stage = None

    def _close_stage(self):
        """Closes USDRT Stage and clears the highlighted prims"""
        self._clear_highlighted_prims()

        if self._usd_notice_listener is not None:
            self._usd_notice_listener.Revoke()
            self._usd_notice_listener = None

        self._stage = None
        self._usdrt_stage = None
        self._kit_update_sub = None

    def _selection_changed(self):
        """Refreshes the highlighted prims when selection is changed because it resets the selection groups"""
        selection = self._usd_context.get_selection()
        selection_paths = selection.get_selected_prim_paths()
        if selection_paths != self._selected_paths:
            self._prev_selected_paths = self._selected_paths
            self._selected_paths = selection_paths

            should_skip_clear = True
            for path in self._highlighted_paths_from_usd | self._highlighted_paths_manual.keys():
                for prev_path in self._prev_selected_paths:
                    if path.startswith(prev_path):
                        should_skip_clear = False
                        break
                for new_path in self._selected_paths:
                    if path.startswith(new_path):
                        should_skip_clear = False
                        break

            if should_skip_clear:
                if ClashViewportSettingValues.LOG_HIGHLIGHT:
                    print("Selection changed (SKIPPED)")
                return
            else:
                if ClashViewportSettingValues.LOG_HIGHLIGHT:
                    print("Selection changed")
            self._clear_highlighted_prims()
            self._find_and_highlight_prims()
            self._highlight_prims_from_manual()

    ####################################################################################################################
    ## USD Notice
    ####################################################################################################################
    def _on_usd_changed(self, notice: Usd.Notice.ObjectsChanged, _: Usd.Stage):
        if self._kit_update_sub:
            return  # Update already requested
        for path in notice.GetResyncedPaths():
            if not path.IsPropertyPath():
                self._request_rebuild()
                break

    def _rebuild_highlighted_prims_if_needed(self):
        """Processes the USD notices and rebuilds the highlighted prims if needed"""
        if not self._stage:
            carb.log_warn("Cannot rebuild highlighted prims if stage not available")
            return
        if not self._usdrt_stage:
            carb.log_warn("Cannot rebuild highlighted prims if USDRT Stage not available")
            return

        with CodeTimer("rebuild_highlighed_usdrt"):
            usdrt_query = self._usdrt_stage.GetPrimsWithAppliedAPIName("ClashViewportHighlightAPI")
            new_paths: set[str] = set()
            for usdrt_path in usdrt_query:
                new_paths.add(str(usdrt_path))

            # Calculate the differences
            paths_to_remove = self._highlighted_paths_from_usd - new_paths
            paths_to_add = new_paths - self._highlighted_paths_from_usd

        with CodeTimer("rebuild_highlighed_clear_prims"):
            # Clear prims that are no longer in the new set
            if paths_to_remove:
                self._clear_specific_highlighted_prims(paths_to_remove)

        with CodeTimer("rebuild_highlighed_highlight_prims"):
            # Add and highlight new prims
            if paths_to_add:
                for path in paths_to_add:
                    self._highlight_single_prim(usdrt.Usd.Sdf.Path(path))
