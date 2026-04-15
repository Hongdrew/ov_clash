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
import carb.settings
import omni.ui as ui
import omni.kit.app
from omni.physxclashdetectioncore.clash_info import ClashInfo
from .utils import show_notification
from .clash_viewport_bridge import ClashViewportBridge
from omni.physxclashdetectioncore.clash_query import ClashQuery
from .clash_bake_settings import ClashBakeSettingsWindow

BATCH_SIZE_DEFAULT = 5
HORIZONTAL_SPACING = 5


class ClashBakeView:
    def __init__(self, clash_bake_async):
        # Note: ClashBakeAsync is a private api, it's stability is not guaranteed.
        from omni.physxclashdetectionbake.private import ClashBakeAsync, ClashBakeAsyncStatus

        self._clash_bake_async: ClashBakeAsync = clash_bake_async
        self._show_notification = True
        self._batch_size_model = ui.SimpleIntModel(default_value=BATCH_SIZE_DEFAULT, min=1, max=100)
        self._outline_width_size_model = ui.SimpleFloatModel(default_value=0.5, min=0.0001, max=1.0)
        self._outline_width_scale_model = ui.SimpleFloatModel(default_value=1.0, min=1.0, max=100.0)

        # Subscribe to model changes to update clash_bake_async options
        self._outline_width_size_model.add_value_changed_fn(
            lambda m: self._clash_bake_async.set_outline_width_size(m.as_float)
        )
        self._outline_width_scale_model.add_value_changed_fn(
            lambda m: self._clash_bake_async.set_outline_width_scale(m.as_float)
        )

        self._last_bake_status = ClashBakeAsyncStatus()
        self._clash_bake_settings_window = ClashBakeSettingsWindow(self)
        self._btn_clash_bake = None
        self._clash_viewport: ClashViewportBridge | None = None
        self._clash_query: ClashQuery | None = None
        self._debug_logging = False
        self._enable_clash_viewport_highlight = False
        self._usd_context_name = ""
        self._process_complete = asyncio.Event()

    def destroy(self):
        if self._clash_bake_settings_window:
            self._clash_bake_settings_window.destroy()
            self._clash_bake_settings_window = None
        self._btn_clash_bake = None

    def set_clash_viewport(self, clash_viewport: ClashViewportBridge | None):
        self._clash_viewport = clash_viewport

    def set_clash_query(self, clash_query: ClashQuery | None):
        self._clash_query = clash_query

    def set_usd_context_name(self, usd_context_name: str):
        self._usd_context_name = usd_context_name

    def set_debug_logging(self, debug_logging: bool):
        self._debug_logging = debug_logging
        self._clash_bake_async.set_debug_logging(self._debug_logging)

    def get_batch_size(self):
        return self._batch_size_model.as_int

    def set_batch_size(self, value: int):
        self._batch_size_model.set_value(value)

    def get_bake_async(self):
        return self._clash_bake_async

    def set_visible(self, visible: bool):
        if self._btn_clash_bake:
            self._btn_clash_bake.visible = visible

    def set_show_notification(self, value):
        self._show_notification = value

    def get_show_notification(self):
        return self._show_notification

    def can_generate_clash_mesh(self):
        return self._clash_bake_async.can_generate_clash_mesh()

    def set_enable_clash_viewport_highlight(self, value: bool):
        self._enable_clash_viewport_highlight = value
        if self._clash_viewport:
            if self._enable_clash_viewport_highlight:
                self._clash_viewport.set_display_clashes_in_main_viewport(True)
            else:
                self._clash_viewport.set_display_clashes_in_main_viewport(False)
            self._clash_viewport.display_clash_by_clash_info([], 0)

    def get_enable_clash_viewport_highlight(self):
        return self._enable_clash_viewport_highlight

    def disable_clash_bake(self):
        self._clash_bake_async.detach_clash_bake()
        if self._clash_viewport and not self._enable_clash_viewport_highlight:
            self._clash_viewport.set_display_clashes_in_main_viewport(True)
            self._clash_viewport.display_clash_by_clash_info([], 0)
        self._btn_clash_bake.text = "Bake Layer (OFF)"  # type: ignore

    async def enable_clash_bake(self):
        if self._clash_viewport and not self._enable_clash_viewport_highlight:
            self._clash_viewport.set_display_clashes_in_main_viewport(False)
            self._clash_viewport.display_clash_by_clash_info([], 0)
        await self._async_attach_bake_layer()

    def clear_clash_bake(self):
        self._clash_bake_async.clear_clash_bake()

    async def _async_attach_bake_layer(self):
        stage = omni.usd.get_context(self._usd_context_name).get_stage()  # type: ignore
        if not self._clash_query:
            carb.log_error("self._clash_query is not set")
            return
        layer_suffix = self._get_layer_suffix()
        materials_suffix = self._get_materials_suffix()
        await self._clash_bake_async.attach_clash_bake(stage, stage.GetSessionLayer(), layer_suffix, materials_suffix)
        if self._clash_bake_async.can_generate_clash_mesh():
            self._btn_clash_bake.text = "Bake Layer (ON)"  # type: ignore
        else:
            self._btn_clash_bake.text = "Bake Layer (OFF)"  # type: ignore
            carb.log_error("Cannot create over layers on unsaved file")

    def _ensure_settings_window_exists(self):
        """Ensure the settings window exists, recreating it if necessary."""
        if not self._clash_bake_settings_window:
            self._clash_bake_settings_window = ClashBakeSettingsWindow(self)

    def _show_bake_settings(self):
        """Show the settings window below the button."""
        self._ensure_settings_window_exists()
        if self._clash_bake_settings_window and self._clash_query and self._btn_clash_bake:
            # Position the window below the button
            screen_x = self._btn_clash_bake.screen_position_x
            screen_y = self._btn_clash_bake.screen_position_y + self._btn_clash_bake.computed_height
            self._clash_bake_settings_window.show(screen_x, screen_y)

    def build_clash_bake_toolbar(self):
        self._btn_clash_bake = ui.Button(
            "Bake Layer (OFF)", name="bake", width=120, clicked_fn=self._show_bake_settings
        )

    def update_ui(self, cd_in_progress: bool):
        if self._btn_clash_bake:
            self._btn_clash_bake.enabled = not cd_in_progress

    def _get_layer_suffix(self):
        return f"CLASH_QUERY_{self._clash_query.identifier}"  # type: ignore

    def _get_materials_suffix(self):
        return "CLASH_MATERIALS"

    def on_query_changed(self):
        if self._clash_bake_async.is_bake_layer_enabled():
            self.set_enable_clash_viewport_highlight(self._enable_clash_viewport_highlight)
        if self._clash_query:
            self._clash_bake_async.reattach_clash_bake(self._get_layer_suffix())

    def get_status(self):
        return self._last_bake_status

    def get_process_complete_event(self):
        return self._process_complete

    async def process(self, clash_infos: list[ClashInfo], just_clear: bool, progress: ui.AbstractValueModel | None):
        if progress:
            progress.set_value(0.0)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        # Iterate over the async generator, calling next_update_async() after each yield
        self._last_bake_status = self._clash_bake_async.get_status()
        batch_size = self._batch_size_model.as_int

        async def update_ui():
            if progress:
                progress.set_value(self._last_bake_status.progress)
            await omni.kit.app.get_app().next_update_async()  # type: ignore

        try:
            if just_clear:
                await self._clash_bake_async.async_clear(clash_infos, batch_size, update_ui)
            else:
                await self._clash_bake_async.async_bake(clash_infos, batch_size, update_ui)
            if progress:
                progress.set_value(1.0)
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        finally:
            duration = 10 if self._debug_logging else 5
            if self._last_bake_status.error_message:
                show_notification(msg=self._last_bake_status.error_message, error=True, duration=duration)
            elif self._last_bake_status.info_message:
                if self._show_notification:
                    if just_clear:
                        show_notification(msg=self._last_bake_status.info_message, duration=5)
                    else:
                        show_notification(msg=self._last_bake_status.info_message, duration=duration)
                        if self._debug_logging:
                            print("-----------------------------------------------------")
                            print(self._last_bake_status.info_message)
                            print("-----------------------------------------------------")
            # Signal that process has completed
            self._process_complete.set()
