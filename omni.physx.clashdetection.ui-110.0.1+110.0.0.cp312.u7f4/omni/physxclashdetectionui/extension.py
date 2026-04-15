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
import carb
import carb.events
import carb.settings
from carb.eventdispatcher import get_eventdispatcher
import omni.ext
import omni.kit
import omni.kit.app
import omni.usd
import omni.kit.ui
import omni.ui as ui
import omni.client
import omni.kit.actions.core
from omni.kit.hotkeys.core import get_hotkey_registry
from .clash_detect_window import ClashDetectionWindow
from .clash_bake_view import ClashBakeView
from .clash_data_ui import ClashDataUI
from omni.physxclashdetectioncore.clash_data_serializer_sqlite import ClashDataSerializerSqlite
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from .pic_test_data import PersonsInChargeTestData
from .selection.clash_selection import ClashSelection
from .clash_viewport_bridge import ClashViewportBridge
from .utils import show_notification, clean_path
from .usd_utils import omni_get_current_stage
from .settings import ExtensionSettings
from omni.physxclashdetectioncore.config import ExtensionConfig
from omni.physxclashdetectiontelemetry.clash_telemetry import ClashTelemetry
from omni.physxclashdetectionuicommon.windowmenuitem import MenuItem

try:
    from omni.physx.scripts.utils import safe_import_tests

    safe_import_tests("omni.physxclashdetectionui.tests")
except:
    pass


class ClashDetectionUiExtension(omni.ext.IExt):
    """A class for managing the Clash Detection UI extension.

    This class handles the initialization, configuration, and shutdown of the Clash Detection UI extension.
    It interacts with various components such as settings, UI elements, and event subscriptions to enable the functionality of the extension.
    """

    MENU_ITEM_NAME = "Clash Detection"

    def __init__(self):
        """Initializes the ClashDetectionUiExtension instance."""
        super().__init__()

        if not ExtensionSettings.development_mode:
            ExtensionSettings.development_mode = carb.settings.get_settings().get_as_bool("/physics/developmentMode")

        self._clash_detect = None
        self._menu = None
        self._settings_subs = None
        self._stage_event_sub = None
        self._clash_window = None

        # These two function allow decoupling ClashBakeAsync from kit and from clash core
        async def copy_support_files(src, dest):
            await omni.client.copy_async(src, dest, omni.client.CopyBehavior.OVERWRITE)  # type: ignore

        async def load_data_from_database(clash_infos):
            # This function has been made async in case we want to use async IO in the future
            if ExtensionSettings.clash_data:
                for ci in clash_infos:
                    ci.clash_frame_info_items = (
                        ExtensionSettings.clash_data.fetch_clash_frame_info_by_clash_info_id(ci.identifier)
                    )
        from omni.physxclashdetectionbake.private import ClashBakeAsync
        self._clash_bake_async = ClashBakeAsync(copy_support_files, load_data_from_database)
        self._clash_bake_view = ClashBakeView(self._clash_bake_async)
        ExtensionSettings.clash_bake_view = self._clash_bake_view
        self._clash_data = None
        self._clash_query = None
        self._clash_selection = None
        self._users = None

    def on_startup(self, ext_id):
        """Initializes the extension components on startup.

        Args:
            ext_id (str): The extension identifier.
        """
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        ExtensionSettings.extension_path = ext_path

        self._clash_detect = ClashDetection()
        self._clash_data = ClashDataUI(ClashDataSerializerSqlite())
        ExtensionSettings.clash_data = self._clash_data
        self._clash_selection = ClashSelection()
        ExtensionSettings.clash_selection = self._clash_selection
        ExtensionSettings.clash_viewport = ClashViewportBridge(self._clash_data, self._clash_selection)

        self._users = PersonsInChargeTestData()
        pic_file_path = ExtensionSettings.pic_file_path
        if not pic_file_path:
            pic_file_path = f"{ext_path}/omni/physxclashdetectionui/pic.json"
        self._users.fetch(pic_file_path)
        ExtensionSettings.users = self._users

        ExtensionSettings.clash_query = None

        # Add a hotkey Ctrl+Shift+Alt+C to open clash detection window
        action_ext_id = __name__
        action_name = "open_clash_detection_window"
        self._open_clash_detection_window_action = omni.kit.actions.core.get_action_registry().register_action(
            action_ext_id,
            action_name,
            lambda: carb.settings.get_settings().set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, True),
            display_name="Open Clash Detection Window",
            tag="Clash Detection UI",
        )
        # Register the hotkey: Ctrl+Shift+Alt+C
        self._open_clash_detection_window_hotkey = get_hotkey_registry().register_hotkey(
            action_ext_id,
            "Ctrl+Shift+Alt+C",
            action_ext_id,
            action_name,
        )

        settings = carb.settings.get_settings()
        if settings:
            def set_default_bool(setting, value):
                settings.set_default_bool(ExtensionSettings.DEFAULT_SETTING_PREFIX + setting, value)
                settings.set_default_bool(setting, value)

            set_default_bool(
                ExtensionSettings.SETTING_SHOW_FULL_PATHS,
                ExtensionSettings.show_full_clash_paths
            )
            set_default_bool(
                ExtensionSettings.SETTING_USE_ASYNC_CLASH_PIPELINE,
                ExtensionSettings.use_async_clash_pipeline
            )
            set_default_bool(
                ExtensionSettings.SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE,
                ExtensionSettings.clash_timeline_slider_immediate_update
            )
            set_default_bool(
                ExtensionSettings.SETTING_DEBUG_LOGGING,
                ExtensionSettings.debug_logging and ExtensionConfig.debug_logging
            )
        self._settings_subs = (
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW,
                self._show_clash_window_setting_changed
            ),
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_SHOW_FULL_PATHS,
                self._show_full_paths_setting_changed
            ),
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_USE_ASYNC_CLASH_PIPELINE,
                self._use_async_clash_pipeline_setting_changed
            ),
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE,
                self._clash_timeline_slider_immediate_update_setting_changed
            ),
            omni.kit.app.SettingChangeSubscription(
                ExtensionSettings.SETTING_DEBUG_LOGGING,
                self._debug_logging_setting_changed
            ),
        )

        def on_app_quit_event(e: carb.events.IEvent):
            # shutdown on app quit event - perform clean up
            if self._clash_data:
                self._clash_data.close()
                self._clash_data._layer_assoc_db_clean_up()

        self._shutdown_subs = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_POST_QUIT,
            on_event=on_app_quit_event, observer_name="clash detection core shutdown hook", order=0
        )

        # fetch current values from settings
        self._show_full_paths_setting_changed(None, carb.settings.ChangeEventType.CHANGED)
        self._use_async_clash_pipeline_setting_changed(None, carb.settings.ChangeEventType.CHANGED)
        self._clash_timeline_slider_immediate_update_setting_changed(None, carb.settings.ChangeEventType.CHANGED)
        self._debug_logging_setting_changed(None, carb.settings.ChangeEventType.CHANGED)

        def main_menu_click():
            settings = carb.settings.get_settings()
            val = settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW)
            settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, not val)

        self._menu = MenuItem(
            f"Physics/{ClashDetectionUiExtension.MENU_ITEM_NAME}",
            "Window",
            main_menu_click,
            lambda: self._clash_window.window.visible if self._clash_window and self._clash_window.window else False,
        )

        usd_context = omni.usd.get_context(ExtensionSettings.usd_context_name)
        self._stage_event_sub = [
            get_eventdispatcher().observe_event(
                observer_name="omni.physx.clashdetection.ui:ClashDetectionUiExtension",
                event_name=usd_context.stage_event_name(omni.usd.StageEventType(i)),
                on_event=self._on_stage_event
            )
            for i in range(int(omni.usd.StageEventType.COUNT))
        ]

        ui.Workspace.set_show_window_fn(ClashDetectionWindow.WINDOW_NAME, self.show_window)

        stage = omni_get_current_stage()
        if stage:
            self._clash_data.stage_opened(True)  # manually trigger opened stage event if we came late to the party

        async def sync_clash_window_state_async():
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()  # type: ignore
            settings = carb.settings.get_settings()
            if settings and settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW):
                settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, True)

        asyncio.ensure_future(sync_clash_window_state_async())

    def _on_stage_event(self, event):
        event_type = omni.usd.get_context(ExtensionSettings.usd_context_name).stage_event_type(event.event_name)
        if not ExtensionSettings.ignore_save_load_events and self._clash_data:
            if event_type == omni.usd.StageEventType.CLOSED:
                self._clash_data._layer_assoc_db_clean_up()
            elif event_type == omni.usd.StageEventType.CLOSING:
                self._clash_data.close()
            elif event_type == omni.usd.StageEventType.OPENING:
                self._clash_data._layer_assoc_db_clean_up()
            elif event_type == omni.usd.StageEventType.OPENED:
                self._clash_data.stage_opened()
            elif event_type == omni.usd.StageEventType.SAVING:
                # We need to save clash data before clash data layer picks it up and saves them to clash layer.
                # Note this works also for 'SAVE AS' as the saved clash data will only be written to the new layer.
                err_msg = "Failed to save clash data!\nSee app log for more info."
                stage_name = clean_path(event.payload.get("savingRootLayer", None))
                saving_sub_layers = event.payload.get("savingSublayers", None)
                if stage_name and self._clash_data.usd_file_path != stage_name:  # save as scenario
                    if not self._clash_data.save_as(stage_name):
                        show_notification(err_msg, True)
                elif saving_sub_layers is not None:  # it can be empty, we check only presence of the key
                    if not self._clash_data.save():
                        show_notification(err_msg, True)
            elif event_type == omni.usd.StageEventType.SAVED:
                self._clash_data.saved()

        if event_type == omni.usd.StageEventType.OPENED:
            if ExtensionSettings.clash_selection:
                ExtensionSettings.clash_selection.clear_selection()
            ExtensionSettings.clash_query = None

        if self._clash_window:
            self._clash_window.on_stage_event(event_type)

    def _show_clash_window_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            enabled = settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW)
            if not enabled:
                if self._clash_window:
                    self._clash_window.destroy()
                    self._clash_window = None
            else:
                self.create_window()

    def _show_full_paths_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            enabled = settings.get_as_bool(ExtensionSettings.SETTING_SHOW_FULL_PATHS)
            ExtensionSettings.show_full_clash_paths = enabled
            if self._clash_window and self._clash_window.window:
                self._clash_window.refresh_table()

    def _use_async_clash_pipeline_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            enabled = settings.get_as_bool(ExtensionSettings.SETTING_USE_ASYNC_CLASH_PIPELINE)
            ExtensionSettings.use_async_clash_pipeline = enabled

    def _clash_timeline_slider_immediate_update_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            enabled = settings.get_as_bool(ExtensionSettings.SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE)
            ExtensionSettings.clash_timeline_slider_immediate_update = enabled

    def _debug_logging_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            enabled = settings.get_as_bool(ExtensionSettings.SETTING_DEBUG_LOGGING)
            ExtensionConfig.debug_logging = enabled
            ExtensionSettings.debug_logging = enabled
            ClashTelemetry.debug_logging = enabled  # debug logging also includes telemetry logging
            # anim module is optional so set the debug logging in the try block
            try:
                from omni.physxclashdetectionanim.bindings._clashDetectionAnim import SETTINGS_LOGGING_ENABLED

                settings.set(SETTINGS_LOGGING_ENABLED, enabled)
            except:
                pass

    def show_window(self, show: bool):
        """Shows or hides the clash detection window.

        Args:
            show (bool): Whether to show the window.
        """
        if show:
            self.create_window()
        elif self._clash_window and self._clash_window.window:
            self._clash_window.window.visible = False

    def create_window(self):
        """Creates and displays the clash detection window."""
        if not self._clash_detect:
            return
        if self._clash_window is None:
            self._clash_window = ClashDetectionWindow(self._clash_detect, self._clash_bake_view)
        self._clash_window.build_window()
        if self._clash_window.window:
            w = self._clash_window.window
            w.set_visibility_changed_fn(self._window_visibility_changed_fn)
            w.width = 1900
            w.height = 300
            w.visible = True
            w.deferred_dock_in("Content", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def _window_visibility_changed_fn(self, visible):
        # handle the case when user closes the window by the top right cross
        if not visible:
            settings = carb.settings.get_settings()
            window_enabled = settings.get_as_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW)
            if window_enabled:
                settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, False)
        if self._menu:
            self._menu.refresh()

    def on_shutdown(self):
        """Performs cleanup and resource deallocation on shutdown."""
        if self._open_clash_detection_window_action:
            omni.kit.actions.core.get_action_registry().deregister_action(self._open_clash_detection_window_action)
            self._open_clash_detection_window_action = None
        if self._open_clash_detection_window_hotkey:
            get_hotkey_registry().deregister_hotkey(self._open_clash_detection_window_hotkey)
            self._open_clash_detection_window_hotkey = None
        self._shutdown_subs = None
        ui.Workspace.set_show_window_fn(ClashDetectionWindow.WINDOW_NAME, None)  # type: ignore
        settings = carb.settings.get_settings()
        settings.set_bool(ExtensionSettings.SETTING_CLASH_DETECTION_WINDOW, False)
        if self._menu:
            self._menu.remove()
            self._menu = None
        self._stage_event_sub = None
        self._clash_bake_view.destroy()
        del self._clash_bake_view
        self._clash_bake_async.destroy()
        del self._clash_bake_async
        if self._clash_window is not None:
            self._clash_window.destroy()
            self._clash_window = None
        self._settings_subs = None
        if self._clash_selection:
            self._clash_selection.clear_selection()
        ExtensionSettings.clash_selection = None
        if ExtensionSettings.clash_viewport:
            ExtensionSettings.clash_viewport.destroy()
            ExtensionSettings.clash_viewport = None
        self._clash_selection = None
        ExtensionSettings.clash_data = None
        if self._clash_data:
            self._clash_data.destroy()
            self._clash_data = None
        ExtensionSettings.clash_query = None
        self._clash_query = None
        ExtensionSettings.users = None
        self._users = None
        if self._clash_detect:
            self._clash_detect.destroy()
            self._clash_detect = None
