# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
from typing import Any, Dict, Optional

import carb
import carb.settings
from carb.events import ISubscription
from carb.eventdispatcher import get_eventdispatcher

import omni.ext
import omni.kit
import omni.kit.app
import carb.events
import omni.usd
import omni.ui as ui

from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry
from omni.physxclashdetectionviewportcommon.windowmenuitem import MenuItem

from .clash_viewport import ClashDetectionViewport
from .clash_viewport_settings import ClashViewportSettings, ClashViewportSettingValues
from .clash_viewport_highlight import ClashViewportHighlight

__all__ = [
    "ClashDetectionViewportExtension",
    "ClashDetectionViewportAPI",
    "get_api_instance",
    "ClashViewportSettings",
]

try:
    from omni.physx.scripts.utils import safe_import_tests

    safe_import_tests("omni.physxclashdetectionviewport.tests", ["tests"])
except:
    pass


class ClashDetectionViewportAPI:
    """A class to manage and control the clash detection viewport.

    This class provides functionality to display and manage clash meshes in both the main viewport and a dedicated clash detection viewport.

    Args:
        clash_viewport (ClashDetectionViewport): An instance of ClashDetectionViewport to manage clashes.
    """

    def __init__(self, clash_viewport: ClashDetectionViewport):
        """Initializes the ClashDetectionViewportAPI instance."""
        self._clash_detection_viewport = clash_viewport

    def hide_all_clash_meshes(self):
        """Removes all clash meshes from main viewport or clash viewport."""
        self._clash_detection_viewport.display_clashes(0, dict())

    @carb.deprecated("Use display_clashes")
    def display_clashes_at_timecode(
        self,
        clash_timecode: float,
        clash_info_items: Dict[str, Any],
        display_clash_in_main_viewport: bool = True,
        display_clash_in_clash_viewport: bool = True,
        center_main_viewport_on_clash: bool = True,
        center_clash_viewport_on_clash: bool = True,
        center_main_viewport_fine_tuning: bool = True,
        center_clash_viewport_fine_tuning: bool = True,
    ):
        """DEPRECATED: Use display_clashes instead.
        Displays a set of clashes at a specific timecode in main and/or dedicated clash viewport.

        Args:
            clash_timecode (float): Timecode at which the clash meshes should be displayed.
            clash_info_items (Dict[str, Any]): Dictionary of ClashInfo to be displayed.
            display_clash_in_main_viewport (bool): If True, displays clash meshes in the main viewport.
            display_clash_in_clash_viewport (bool): If True, displays clash meshes in the dedicated clash viewport.
            center_main_viewport_on_clash (bool): If True, centers active camera on the clashes in the main viewport.
            center_clash_viewport_on_clash (bool): If True, centers active camera on the clashes in the clash viewport.
            center_main_viewport_fine_tuning (bool): If True, avoids recentering the camera in main viewport for small movements.
            center_clash_viewport_fine_tuning (bool): If True, avoids recentering the camera in clash viewport for small movements.
        """
        settings = carb.settings.get_settings()
        # Save previous settings
        previous_main_viewport_show_clashes = settings.get_as_bool(
            ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES
        )
        previous_clash_viewport_show_clashes = settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES)
        previous_main_viewport_center_camera = settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA)
        previous_clash_viewport_center_camera = settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA)
        previous_main_viewport_enable_camera_tolerance = settings.get_as_bool(
            ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE
        )
        previous_clash_viewport_enable_camera_tolerance = settings.get_as_bool(
            ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE
        )
        # Set new settings
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, display_clash_in_main_viewport)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, display_clash_in_clash_viewport)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, center_main_viewport_on_clash)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, center_clash_viewport_on_clash)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE, center_main_viewport_fine_tuning)
        settings.set_bool(
            ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE, center_clash_viewport_fine_tuning
        )
        try:
            self._clash_detection_viewport.display_clashes(clash_timecode, clash_info_items)
        finally:
            # Restore previous settings
            settings.set_bool(
                ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, previous_main_viewport_show_clashes
            )
            settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, previous_clash_viewport_show_clashes)
            settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, previous_main_viewport_center_camera)
            settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, previous_clash_viewport_center_camera)
            settings.set_bool(
                ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE,
                previous_main_viewport_enable_camera_tolerance,
            )
            settings.set_bool(
                ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE,
                previous_clash_viewport_enable_camera_tolerance,
            )

    def display_clashes(
        self,
        clash_timecode: float,
        clash_info_items: Dict[str, Any],
    ):
        """Displays a set of clashes at a specific timecode in main and/or dedicated clash viewport.

        Args:
            clash_timecode (float): Timecode at which the clash meshes should be displayed.
            clash_info_items (Dict[str, Any]): Dictionary of ClashInfo to be displayed.
        """
        self._clash_detection_viewport.display_clashes(
            clash_timecode,
            clash_info_items,
        )

    @property
    def clash_viewport_window(self):
        """Gets the ViewportWindow handle to dedicated Clash Detection Viewport.

        Returns:
            ViewportWindow | None: The handle to the dedicated Clash Detection Viewport window.
        """
        return self._clash_detection_viewport.window


_viewport_api_instance: ClashDetectionViewportAPI


def get_api_instance() -> ClashDetectionViewportAPI:
    """Retrieve the singleton instance of ClashDetectionViewportAPI.

    Returns:
        ClashDetectionViewportAPI: The singleton instance of the ClashDetectionViewportAPI.
    """
    global _viewport_api_instance
    return _viewport_api_instance


class ClashDetectionViewportExtension(omni.ext.IExt):
    """An extension for managing the Clash Detection Viewport in the NVIDIA Omniverse Kit.

    This extension integrates with the NVIDIA Omniverse Kit to provide a dedicated viewport for clash detection. It includes settings management, viewport window management, and telemetry event handling.

    The extension interacts with various Omniverse components such as the main viewport, settings, and the application lifecycle to ensure seamless integration and functionality. It also provides a menu item for toggling the visibility of the clash detection viewport and handles various settings changes to update the viewport configuration.
    """

    MENU_ITEM_VIEWPORT_NAME = "Clash Detection Viewport"

    def __init__(self):
        """Initializes the ClashDetectionViewportExtension."""
        super().__init__()
        self._menu_viewport = None
        self._settings_subs = None
        self._settings = carb.settings.get_settings()
        self._stage_event_sub = None
        self._clash_viewport = None
        self._clash_viewport_highlight = ClashViewportHighlight(omni.usd.get_context())
        self._shutdown_subscription = None

    # Fastshutdown might prevent us from flushing telemetry events out. This is a workaround.
    def __on_shutdown_event(self, e: carb.events.IEvent):
        if self._clash_viewport and self._clash_viewport.telemetry:
            self._clash_viewport.update_telemetry_counters()
            ClashTelemetry.log_viewport_telemetry(self._clash_viewport.telemetry)

    def __setting_viewport_globals(self, value, event_type):
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return
        # fmt: off
        ClashViewportSettingValues.USE_SOURCE_NORMALS = self._settings.get_as_bool(ClashViewportSettings.USE_SOURCE_NORMALS)
        ClashViewportSettingValues.LOG_PROFILE = self._settings.get_as_bool(ClashViewportSettings.LOG_PROFILE)
        ClashViewportSettingValues.LOG_HIGHLIGHT = self._settings.get_as_bool(ClashViewportSettings.LOG_HIGHLIGHT)
        ClashViewportSettingValues.CLASH_WIREFRAME_THICKNESS = self._settings.get_as_float(ClashViewportSettings.CLASH_WIREFRAME_THICKNESS)
        ClashViewportSettingValues.CAMERA_CENTERING_FAR_TOLERANCE = self._settings.get_as_float(ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE)
        ClashViewportSettingValues.CAMERA_CENTERING_NEAR_TOLERANCE = self._settings.get_as_float(ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE)
        ClashViewportSettingValues.MAIN_VIEWPORT_CENTER_CAMERA = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA)
        ClashViewportSettingValues.CLASH_VIEWPORT_CENTER_CAMERA = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA)
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SIZE = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE)
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SCALE = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE)
        ClashViewportSettingValues.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING)
        ClashViewportSettingValues.CLASH_MESHES_DISPLAY_LIMIT = self._settings.get_as_int(ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT)
        ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS)
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES)
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES)
        ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES)
        ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_WIREFRAMES = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_WIREFRAMES)
        ClashViewportSettingValues.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS)
        ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES = self._settings.get_as_bool(ClashViewportSettings.CLASH_HIGHLIGHT_FILLED_MESHES)
        # fmt: on

    def on_startup(self, _):
        """Handles the startup event.

        Args:
            _ (Any): Placeholder argument for event data.
        """
        # fmt: off
        self._settings_subs = (
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, self.__setting_changed),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.USE_SOURCE_NORMALS,self.__setting_viewport_globals,),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.USE_SOURCE_NORMALS, self.__setting_redraw),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.LOG_PROFILE, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.LOG_HIGHLIGHT, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_WIREFRAME_THICKNESS, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, self.__setting_redraw),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS, self.__setting_redraw),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_SHOW_WIREFRAMES, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_VIEWPORT_SHOW_WIREFRAMES, self.__setting_redraw),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_HIGHLIGHT_FILLED_MESHES, self.__setting_viewport_globals),
            omni.kit.app.SettingChangeSubscription(ClashViewportSettings.CLASH_HIGHLIGHT_FILLED_MESHES, self.__setting_redraw_highlight),
        )
        # fmt: on

        # Telemetry events need to be sent, if telemetry is enabled, when stage is closing. If fastShutdown is enabled
        # these will not fire. This subscription ensures that we properly flush those events at application shutdown.
        self._shutdown_subscription = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_POST_QUIT,
            on_event=self.__on_shutdown_event,
            observer_name="physx.clashdetection.telemetry shutdown hook",
            order=0,
        )

        # fmt: off
        ClashViewportSettingValues.LOG_PROFILE = self._settings.get_as_bool(ClashViewportSettings.LOG_PROFILE)
        ClashViewportSettingValues.LOG_HIGHLIGHT = self._settings.get_as_bool(ClashViewportSettings.LOG_HIGHLIGHT)
        ClashViewportSettingValues.CLASH_WIREFRAME_THICKNESS = self._settings.get_as_float(ClashViewportSettings.CLASH_WIREFRAME_THICKNESS)
        ClashViewportSettingValues.USE_SOURCE_NORMALS = self._settings.get_as_bool(ClashViewportSettings.USE_SOURCE_NORMALS)
        ClashViewportSettingValues.CAMERA_CENTERING_FAR_TOLERANCE = self._settings.get_as_float(ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE)
        ClashViewportSettingValues.CAMERA_CENTERING_NEAR_TOLERANCE = self._settings.get_as_float(ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE)
        ClashViewportSettingValues.MAIN_VIEWPORT_CENTER_CAMERA = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA)
        ClashViewportSettingValues.CLASH_VIEWPORT_CENTER_CAMERA = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA)
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SIZE = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE)
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SCALE = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE)
        ClashViewportSettingValues.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING = self._settings.get_as_float(ClashViewportSettings.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING)
        ClashViewportSettingValues.CLASH_MESHES_DISPLAY_LIMIT = self._settings.get_as_int(ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT)
        ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS)
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES)
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES = self._settings.get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES)
        ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES)
        ClashViewportSettingValues.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS = self._settings.get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS)
        # fmt: on

        self._menu_viewport = MenuItem(
            f"Physics/{ClashDetectionViewportExtension.MENU_ITEM_VIEWPORT_NAME}",
            "Window",
            self.main_menu_click,
            lambda: (
                self._clash_viewport.window.visible if self._clash_viewport and self._clash_viewport.window else False
            ),
        )

        self._stage_event_sub = [
            get_eventdispatcher().observe_event(
                observer_name="omni.physx.clashdetection.viewport:ClashDetectionViewportExtension",
                event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType(i)),
                on_event=self.__on_stage_event,
            )
            for i in range(int(omni.usd.StageEventType.COUNT))
        ]

        ui.Workspace.set_show_window_fn(
            ClashDetectionViewportExtension.MENU_ITEM_VIEWPORT_NAME,
            self.__show_clash_viewport,
        )

        self._clash_viewport = ClashDetectionViewport(
            usd_context_name="Clash Detection Window",
            title=ClashDetectionViewportExtension.MENU_ITEM_VIEWPORT_NAME,
            clash_viewport_highlight=self._clash_viewport_highlight,
        )
        global _viewport_api_instance
        _viewport_api_instance = ClashDetectionViewportAPI(self._clash_viewport)

        should_be_visible = self._settings.get_as_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
        if should_be_visible:
            # We delay initialization because Viewport / additional usd context creation takes a lot less
            # (300ms vs 3000ms) if it's being done after first rendered frame
            asyncio.ensure_future(self.__delayed_initialization())

    def main_menu_click(self):
        val = self._settings.get_as_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
        self._settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, not val)

    def on_shutdown(self):  # pragma: no cover
        global _viewport_api_instance
        del _viewport_api_instance

        def empty(_):
            pass

        ui.Workspace.set_show_window_fn(ClashDetectionViewportExtension.MENU_ITEM_VIEWPORT_NAME, empty)
        self._settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, False)
        if self._menu_viewport:
            import omni.kit.actions.core

            # WindowMenuItemAction_PhysicsClashDetectionViewport
            self._menu_viewport.remove()
            self._menu_viewport = None
            ext_id = "omni.physxclashdetectionviewportcommon.windowmenuitem"  # self.__class__.__module__
            omni.kit.actions.core.get_action_registry().deregister_all_actions_for_extension(ext_id)

        self._stage_event_sub = None
        self._settings_subs = None
        del self._settings

        self._clash_viewport_highlight.destroy()

        if self._clash_viewport:
            self._clash_viewport.destroy()
            self._clash_viewport = None
        self._shutdown_subscription = None

    async def __delayed_initialization(self):
        for _ in range(1):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        if self._clash_viewport:
            self._clash_viewport.create_dedicated_clash_viewport_window()
        await self.__dock_clash_detection_window()

    async def __dock_clash_detection_window(self):
        if self._clash_viewport and self._clash_viewport.window:
            self._clash_viewport.window.deferred_dock_in("Property", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def __on_stage_event(self, event):
        event_type = omni.usd.get_context().stage_event_type(event.event_name)
        if self._clash_viewport:
            self._clash_viewport.on_stage_event(event_type)

    def __setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            enabled = self._settings.get_as_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
            self.__show_clash_viewport(show=enabled)

    def __setting_redraw(self, item, event_type):
        async def redraw_later():
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            if self._clash_viewport:
                self._clash_viewport.setting_changed_forced_redraw()

        if event_type == carb.settings.ChangeEventType.CHANGED:
            asyncio.ensure_future(redraw_later())

    def __setting_redraw_highlight(self, item, event_type):
        async def redraw_later():
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            if self._clash_viewport_highlight:
                self._clash_viewport_highlight.changed_settings()

        if event_type == carb.settings.ChangeEventType.CHANGED:
            asyncio.ensure_future(redraw_later())

    def __show_clash_viewport(self, show: bool):
        if self._clash_viewport:
            if show:
                window = self._clash_viewport.window
                if window:
                    window.visible = True
                else:
                    self._clash_viewport.create_dedicated_clash_viewport_window()  # Already visible when created
                    window = self._clash_viewport.window
                    if window:
                        window.set_visibility_changed_fn(self.__viewport_visibility_changed_fn)
                        window.set_focused_changed_fn(self.__viewport_focus_changed_fn)
                        asyncio.ensure_future(self.__dock_clash_detection_window())
            else:
                if self._clash_viewport.window:
                    self._clash_viewport.window.visible = False

    def __viewport_visibility_changed_fn(self, visible):
        if self._clash_viewport:
            self._clash_viewport.on_visibility_changed(visible)
        # handle the case when user closes the window by the top right cross
        if not visible:
            window_enabled = self._settings.get_as_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW)
            if window_enabled:
                self._settings.set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, False)
        if self._menu_viewport:
            self._menu_viewport.refresh()

    def __viewport_focus_changed_fn(self, focused):
        if self._clash_viewport:
            self._clash_viewport.on_focus_changed(focused)
