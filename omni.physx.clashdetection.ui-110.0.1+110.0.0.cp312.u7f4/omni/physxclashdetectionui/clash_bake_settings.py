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
from omni.kit.widget.settings import get_style

HORIZONTAL_SPACING = 5
LABEL_WIDTH = 200


class LocalSettingWidgetBuilder:
    """
    Widget builder for local (non-carb) settings.
    Similar to SettingsWidgetBuilder but works with getter/setter functions.
    """

    @staticmethod
    def _get_checkbox_alignment():
        settings = carb.settings.get_settings()
        return settings.get("/ext/omni.kit.window.property/checkboxAlignment")

    @staticmethod
    def _get_label_alignment():
        settings = carb.settings.get_settings()
        return settings.get("/ext/omni.kit.window.property/labelAlignment")

    @classmethod
    def _create_label(cls, attr_name, tooltip="", additional_label_kwargs=None):
        alignment = ui.Alignment.RIGHT if cls._get_label_alignment() == "right" else ui.Alignment.LEFT
        label_kwargs = {
            "name": "label",
            "word_wrap": True,
            "width": LABEL_WIDTH,
            "height": 18,
            "alignment": alignment,
        }

        if tooltip:
            label_kwargs["tooltip"] = tooltip

        if additional_label_kwargs:
            label_kwargs.update(additional_label_kwargs)
        ui.Label(attr_name, **label_kwargs)
        ui.Spacer(width=5)

    @classmethod
    def _build_reset_button(cls, default_value, model, reset_fn):
        """Build a reset button that appears when value differs from default."""
        with ui.VStack(width=0, height=0):
            ui.Spacer()
            with ui.ZStack(width=15, height=15):
                with ui.HStack(style={"margin_width": 0}):
                    ui.Spacer()
                    with ui.VStack(width=0):
                        ui.Spacer()
                        ui.Rectangle(width=5, height=5, name="reset_invalid")
                        ui.Spacer()
                    ui.Spacer()
                btn = ui.Rectangle(width=12, height=12, name="reset", tooltip="Click to reset value")
                btn.visible = False

            btn.set_mouse_pressed_fn(lambda *_: reset_fn(default_value, model, btn))
            ui.Spacer()

        return btn

    @classmethod
    def createBoolWidget(cls, model):
        """Create a boolean widget."""
        widget = None
        with ui.HStack():
            left_aligned = cls._get_checkbox_alignment() == "left"
            if not left_aligned:
                ui.Spacer(width=10)
                ui.Line(style={"color": 0x338A8777}, width=ui.Fraction(1))
                ui.Spacer(width=5)
            with ui.VStack(style={"margin_width": 0}, width=10):
                ui.Spacer()
                widget = ui.CheckBox(width=10, height=0, name="greenCheck", model=model)
                ui.Spacer()
            if left_aligned:
                ui.Spacer(width=10)
                ui.Line(style={"color": 0x338A8777}, width=ui.Fraction(1))
        return widget


class ClashBakeSettingsWindow(ui.Window):
    def __init__(self, clash_bake_view):
        super().__init__(
            "Bake Layer Settings###ClashBake",
            visible=False,
            auto_resize=True,
            flags=(
                ui.WINDOW_FLAGS_POPUP
                | ui.WINDOW_FLAGS_NO_SAVED_SETTINGS
                | ui.WINDOW_FLAGS_NO_COLLAPSE
            ),
        )
        self._clash_bake_view = clash_bake_view
        self._reset_buttons = {}
        self._widget_refs = {}
        self._section_collapsed_states = {}

    def destroy(self) -> None:
        """Destroy the window."""
        super().destroy()
        self._reset_buttons = {}
        self._widget_refs = {}
        self._section_collapsed_states = {}

    def show(self, x, y):
        self.build_ui()
        self.position_x, self.position_y = x, y
        self.visible = True
        self.focus()

    def hide(self):
        self.visible = False

    def _update_reset_button(self, name, value, default_value):
        """Update reset button visibility based on whether value differs from default."""
        if name in self._reset_buttons:
            button = self._reset_buttons[name]
            if button:
                button.visible = (value != default_value)

    def _reset_bool_setting(self, default_value, model, button):
        """Reset a boolean setting to its default value."""
        model.set_value(default_value)
        button.visible = False

    def _reset_int_setting(self, default_value, model, button):
        """Reset an integer setting to its default value."""
        model.set_value(default_value)
        button.visible = False

    def _reset_float_setting(self, default_value, model, button):
        """Reset a float setting to its default value."""
        model.set_value(default_value)
        button.visible = False

    def _add_bool_setting(self, name, getter_fn, setter_fn, default_value, tooltip="", rebuild_fn=None, identifier=None):
        """Add a boolean setting with label, checkbox, and reset button.
        
        Args:
            name: Display name of the setting
            getter_fn: Function to get the current value
            setter_fn: Function to set a new value (can be async)
            default_value: Default value for the setting
            tooltip: Tooltip text
            rebuild_fn: Optional function to call when value changes (for rebuilding UI)
            identifier: Optional identifier for UI testing
        """
        with ui.HStack(skip_draw_when_clipped=True):
            LocalSettingWidgetBuilder._create_label(name, tooltip, additional_label_kwargs={"width": LABEL_WIDTH})
            value = getter_fn()
            model = ui.SimpleBoolModel()
            model.set_value(value)
            widget = LocalSettingWidgetBuilder.createBoolWidget(model)
            
            # Add identifier for UI testing if provided
            if identifier:
                widget.identifier = identifier

            def on_value_changed(m, setter=setter_fn, name_ref=name, default=default_value, rebuild=rebuild_fn):
                import asyncio
                import inspect
                
                bool_val = m.as_bool
                
                async def handle_async_setter():
                    if inspect.iscoroutinefunction(setter):
                        await setter(bool_val)
                    else:
                        setter(bool_val)
                    self._update_reset_button(name_ref, bool_val, default)
                    if rebuild:
                        rebuild()
                
                asyncio.ensure_future(handle_async_setter())

            model.add_value_changed_fn(on_value_changed)

            reset_btn = LocalSettingWidgetBuilder._build_reset_button(
                default_value, model, self._reset_bool_setting
            )
            self._reset_buttons[name] = reset_btn
            self._update_reset_button(name, value, default_value)

        ui.Spacer(height=3)
        return widget

    def _add_int_slider(self, name, model, tooltip=""):
        """Add an integer slider setting."""
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            ui.IntSlider(
                model=model,
                min=model.min,
                max=model.max,
                tooltip=tooltip,
            )
            ui.Label(name)

    def _add_float_slider(self, name, model, tooltip=""):
        """Add a float slider setting."""
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            ui.FloatSlider(
                model=model,
                min=model.min,
                max=model.max,
                tooltip=tooltip,
            )
            ui.Label(name)

    def build_ui(self):
        self.frame.set_style(get_style())

        bake_async = self._clash_bake_view.get_bake_async()
        clash_bake_enabled = bake_async.is_bake_layer_enabled() and self._clash_bake_view._clash_query is not None

        def build_section(name, build_func, collapsed=False):
            # Use saved collapsed state if available, otherwise use default
            actual_collapsed = self._section_collapsed_states.get(name, collapsed)
            frame = ui.CollapsableFrame(name, height=0, collapsed=actual_collapsed)
            # Store reference to track state
            self._widget_refs[f"section_{name}"] = frame
            with frame:
                with ui.HStack():
                    ui.Spacer(width=20)
                    with ui.VStack():
                        build_func()

        async def _async_rebuild_ui():
            import omni.kit.app
            # Save current collapsed states before rebuilding
            for key, widget in self._widget_refs.items():
                if key.startswith("section_"):
                    section_name = key.replace("section_", "")
                    if hasattr(widget, "collapsed"):
                        self._section_collapsed_states[section_name] = widget.collapsed
            
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async()  # type: ignore
            self.build_ui()

        def rebuild_ui():
            """Rebuild the UI to reflect option changes."""
            import asyncio
            asyncio.ensure_future(_async_rebuild_ui())

        def build_bake_layer_options_section():
            async def toggle_bake_layer(value):
                if value:
                    await self._clash_bake_view.enable_clash_bake()
                else:
                    self._clash_bake_view.disable_clash_bake()

            self._add_bool_setting(
                "Enable Clash Bake Layer",
                lambda: clash_bake_enabled,
                toggle_bake_layer,
                False,
                tooltip="When enabled attaches clash bake layers to current stage",
                rebuild_fn=rebuild_ui,
                identifier="enable_clash_bake_layer_checkbox",
            )

            self._add_bool_setting(
                "Clash Selection Highlight",
                self._clash_bake_view.get_enable_clash_viewport_highlight,
                self._clash_bake_view.set_enable_clash_viewport_highlight,
                False,
                tooltip="Allows clash viewport extension to highlight current selection in the main viewport even if bake layer is enabled.\nClash viewport highlight will still be visible in the clash viewport in any case.",
            )

        def build_actions_section():
            """Build actions section with buttons."""
            ui.Spacer(height=5)
            with ui.HStack(spacing=5):
                ui.Button(
                    "Save",
                    clicked_fn=bake_async.save_clash_bake,
                    height=25,
                    tooltip="Save the clash bake layers to disk",
                )
                ui.Button(
                    "Reload",
                    clicked_fn=bake_async.load_clash_bake,
                    height=25,
                    tooltip="Reload the clash bake layers from disk",
                )
                ui.Button(
                    "Clear",
                    clicked_fn=bake_async.clear_clash_bake,
                    height=25,
                    tooltip="Clear all clash bake layers",
                )
            ui.Spacer(height=5)

        def build_generation_options_section():
            self._add_bool_setting(
                "Keep DB Data in Memory",
                bake_async.get_keep_db_data_in_memory,
                bake_async.set_keep_db_data_in_memory,
                True,
                tooltip="If enabled keeps the data for each baked record in memory.\nThis avoids reloading the data from the database for each batch but it will consume additional memory.",
            )

            self._add_bool_setting(
                "Show Notification",
                self._clash_bake_view.get_show_notification,
                self._clash_bake_view.set_show_notification,
                True,
                tooltip="If enabled shows a notification when the clash baking process is completed",
            )

            self._add_bool_setting(
                "Finalize When Cancelled",
                bake_async.get_finalize_when_cancelled,
                bake_async.set_finalize_when_cancelled,
                True,
                tooltip="If enabled finalizes meshes baked so far when the process is cancelled",
            )

            ui.Spacer(height=5)
            self._add_int_slider(
                "Batch Size",
                self._clash_bake_view._batch_size_model,
                tooltip="Batch size for clash bake",
            )
            ui.Spacer(height=5)

        def build_visual_options_section():
            if bake_async.get_use_layer_api():
                self._add_bool_setting(
                    "Use Selection Groups",
                    bake_async.get_use_selection_groups,
                    bake_async.set_use_selection_groups,
                    True,
                    tooltip="If enabled uses selection groups to highlight the meshes during the clash",
                    rebuild_fn=rebuild_ui,
                )
            else:
                self._add_bool_setting(
                    "Bake Using Display Opacity",
                    bake_async.get_use_display_opacity,
                    bake_async.set_use_display_opacity,
                    True,
                    tooltip="DEPRECATED. Sdf API will be the only one supported in future releases.\nIf enabled bakes using display opacity instead of hole indices",
                )

            self._add_bool_setting(
                "Bake Clash Outlines",
                bake_async.get_generate_outlines,
                bake_async.set_generate_outlines,
                True,
                tooltip="If enabled bakes clash outlines for each frame",
            )

            self._add_bool_setting(
                "Bake Clash Meshes",
                bake_async.get_generate_clash_meshes,
                bake_async.set_generate_clash_meshes,
                True,
                tooltip="If enabled bakes clash meshes for the entire duration of the clash, highlighting them at clash start and end.\n(It replaces source meshes during the clash with a clone of the same meshes)",
            )

            if not bake_async.get_use_layer_api() or not bake_async.get_use_selection_groups():
                self._add_bool_setting(
                    "Bake Wireframe",
                    bake_async.get_generate_wireframe,
                    bake_async.set_generate_wireframe,
                    False,
                    tooltip="If enabled bakes wireframes on top of clashing polygons for each frame",
                )

                self._add_bool_setting(
                    "Bake Clashing Polygons",
                    bake_async.get_generate_clash_polygons,
                    bake_async.set_generate_clash_polygons,
                    False,
                    tooltip="If enabled bakes time sampled clashing polygons for each frame",
                )

            ui.Spacer(height=5)
            self._add_float_slider(
                "Outline Size",
                self._clash_bake_view._outline_width_size_model,
                tooltip="Size of the outline in world space units",
            )
            ui.Spacer(height=5)
            self._add_float_slider(
                "Outline Scale",
                self._clash_bake_view._outline_width_scale_model,
                tooltip="Scale factor for the outline width",
            )
            ui.Spacer(height=5)

        def build_developer_section():
            self._add_bool_setting(
                "USD Sdf Layer API",
                bake_async.get_use_layer_api,
                bake_async.set_use_layer_api,
                True,
                tooltip="DEPRECATED. Sdf API will be the only one supported in future releases.\nIf enabled bakes using layer API instead of stage API",
                rebuild_fn=rebuild_ui,
            )

            self._add_bool_setting(
                "Save as USD",
                bake_async.get_save_as_usd,
                bake_async.set_save_as_usd,
                True,
                tooltip="If enabled saves as usd instead of usda",
            )

        with self.frame:
            with ui.VStack(height=0, spacing=1):
                build_section("Bake Layer Options", build_bake_layer_options_section)
                
                if clash_bake_enabled:
                    ui.Spacer(height=4)
                    build_section("Bake Layer Actions", build_actions_section)
                    
                    ui.Spacer(height=4)
                    build_section("Bake Generation Options", build_generation_options_section, collapsed=True)
                    
                    ui.Spacer(height=4)
                    build_section("Bake Visual Options", build_visual_options_section, collapsed=True)

                    development_mode = carb.settings.get_settings().get("/physics/developmentMode")
                    if development_mode:
                        ui.Spacer(height=4)
                        build_section("Bake Developer Options", build_developer_section, collapsed=True)
