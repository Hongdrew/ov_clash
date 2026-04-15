# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from functools import partial
import omni.ui as ui
import carb.settings
from omni.kit.widget.settings import SettingsWidgetBuilder, get_style
from omni.kit.widget.settings.settings_widget import create_setting_widget_combo
from .settings import ExtensionSettings

class ExtensionSettingsWindow(ui.Window):
    def __init__(self):
        super().__init__(
            "Settings Menu###Clash",
            visible=False,
            auto_resize=True,
            flags=(
                ui.WINDOW_FLAGS_POPUP
                | ui.WINDOW_FLAGS_NO_SAVED_SETTINGS
                | ui.WINDOW_FLAGS_NO_COLLAPSE
            )
        )
        self._reset_buttons = {}

    def destroy(self) -> None:
        """Destroy the window."""
        super().destroy()
        self._reset_buttons = {}

    def show(self, x, y):
        self.build_ui()
        self.position_x, self.position_y = x, y
        self.visible = True
        self.focus()

    def hide(self):
        self.visible = False

    def _get_value(self, path):
        return carb.settings.get_settings().get(path)

    def _get_default_value(self, path):
        return carb.settings.get_settings().get(ExtensionSettings.DEFAULT_SETTING_PREFIX + path)

    def _is_default_value(self, path, value):
        default_value = self._get_default_value(path)
        if default_value is None:
            return True  # report no change when there is no default value
        return value == default_value

    def _update_reset_button(self, path, value):
        button, _ = self._reset_buttons.get(path)
        if button:
            button.visible = not self._is_default_value(path, value)

    def _reset_setting(self, path):
        default_value = self._get_default_value(path)
        _, model = self._reset_buttons.get(path)
        if model:
            model.set_value(default_value)

    def _setting_changed(self, path, value):
        bool_val = value.as_bool
        carb.settings.get_settings().set(path, bool_val)
        self._update_reset_button(path, bool_val)

    def _add_bool_setting(self, name, path, tooltip=""):
        with ui.HStack(skip_draw_when_clipped=True):
            SettingsWidgetBuilder._create_label(name, path, tooltip, additional_label_kwargs={"width": 310})
            value = self._get_value(path)
            model = ui.SimpleBoolModel()
            model.set_value(value)
            widget = SettingsWidgetBuilder.createBoolWidget(model)
            model.add_value_changed_fn(partial(self._setting_changed, path))
            if self._get_default_value(path) is None:
                self._reset_buttons[path] = None, model
            else:
                reset_btn = SettingsWidgetBuilder._build_reset_button(path)
                reset_btn.set_mouse_pressed_fn(lambda *_, path=path: self._reset_setting(path))
                reset_btn.set_tooltip("Click to set the default value")
                self._reset_buttons[path] = reset_btn, model
                self._update_reset_button(path, value)
        ui.Spacer(height=3)
        return widget

    def _add_combo_setting(self, name, path, values, tooltip=""):
        with ui.HStack(skip_draw_when_clipped=True):
            SettingsWidgetBuilder._create_label(name, path, tooltip, additional_label_kwargs={"width": 160})
            widget, model = create_setting_widget_combo(path, values)
            ui.Spacer(width=20)
        ui.Spacer(height=5)

    def build_ui(self):
        self.frame.set_style(get_style())

        def build_section(name, build_func):
            with ui.CollapsableFrame(name, height=0):
                with ui.HStack():
                    ui.Spacer(width=20)
                    with ui.VStack():
                        build_func()

        def build_user_interface_section():
            self._add_bool_setting(
                "Show Full Paths of Clashing Objects",
                ExtensionSettings.SETTING_SHOW_FULL_PATHS,
                tooltip="Display full paths of clashing objects in clash detection results grid",
            )
            self._add_bool_setting(
                "Immediate Update When Dragging Timeline Slider",
                ExtensionSettings.SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE,
                tooltip="Immediately update clashing prims visualization in main viewport during timeline slider drag",
            )
            self._add_bool_setting(
                "Use Asynchronous Clash Pipeline",
                ExtensionSettings.SETTING_USE_ASYNC_CLASH_PIPELINE,
                tooltip="Use asynchronous clash pipeline to not block the application responsiveness",
            )

        def build_info_section():
            self._add_bool_setting(
                "Enable Debug Logging",
                ExtensionSettings.SETTING_DEBUG_LOGGING,
                tooltip="Enable debug logging to the console",
            )

        with self.frame:
            with ui.VStack(height=0, spacing=1):
                build_section("User Interface", build_user_interface_section)
                ui.Spacer(height=4)
                build_section("Info", build_info_section)
