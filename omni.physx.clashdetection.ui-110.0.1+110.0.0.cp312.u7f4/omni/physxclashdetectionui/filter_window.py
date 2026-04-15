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
from typing import Callable, Optional
import sys
import carb.input
import omni.ui as ui
import omni.kit.app
from .styles import Styles

__all__ = []


class FilterWindow(ui.Window):
    """
    Modal window for editing and applying a custom filter expression to clash results.

    - Lets users enter, preview, and validate filter expressions (e.g., [Column] = 'foo' AND [Value] > 10).
    - Supports toggling filter usage and editing the current filter string.
    - Does not manage clash queries themselves, only the filter UI and callback.

    note: if you set on this class visible = False, the window will be automatically self-destroyed in the next frame.

    Args:
        filter_expression (str): Initial filter expression to display in the field.
        use_filter (bool): Initial state for whether filtering is enabled.
        apply_filter_fn (Optional[Callable[[str, bool], bool]]): Callback to apply the filter. Should return True to close the window.
        width (int): Window width in pixels.
        height (int): Window height in pixels.
        position_x (Optional[float]): X position of window (default: None).
        position_y (Optional[float]): Y position of window (default: None).
    """
    def __init__(
        self,
        filter_expression: str = "",
        use_filter: bool = True,
        apply_filter_fn: Optional[Callable[[str, bool], bool]] = None,
        width=700,
        height=0,
        position_x=None,
        position_y=None,
    ) -> None:
        """Initialize the FilterWindow."""
        window_title = "Custom Expression Filter###Clash"
        super().__init__(
            window_title,
            width=width,
            height=height,
            flags=ui.WINDOW_FLAGS_MODAL | ui.WINDOW_FLAGS_NO_RESIZE | ui.WINDOW_FLAGS_NO_SCROLLBAR,
            visibility_changed_fn=self._on_visibility_changed,
        )
        if position_x is not None:
            self.position_x = position_x
        if position_y is not None:
            self.position_y = position_y
        self.frame.set_style(Styles.FILTER_WND_STYLE)
        self.set_key_pressed_fn(self._on_key_pressed)
        self._apply_filter_fn = apply_filter_fn
        self._filter_expression_model = ui.SimpleStringModel(filter_expression)
        self._use_filter_model = ui.SimpleBoolModel(use_filter)
        self._clear_search_button = None
        self._carb_subs = []
        self._filter_exp_string_field = None

    def destroy(self) -> None:
        """Destroy the FilterWindow."""
        super().destroy()
        self._apply_filter_fn = None
        self._use_filter_model = None
        self._filter_expression_model = None
        self._clear_search_button = None
        self._filter_exp_string_field = None
        self._carb_subs = []

    async def _destroy_window_in_next_frame(self):
        """Destroy the FilterWindow in the next frame."""
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.destroy()

    def _destroy_filter_window(self):
        asyncio.ensure_future(self._destroy_window_in_next_frame())

    def _on_key_pressed(self, key, mod, pressed):
        """Handle key presses."""
        if not pressed:
            return
        if key == int(carb.input.KeyboardInput.ESCAPE):
            self.visible = False

    def _on_visibility_changed(self, visible: bool):
        """Handle visibility changes."""
        if not visible:
            self._destroy_filter_window()

    def _apply_filter(self) -> bool:
        """Apply the filter expression. Returns True if the filter was applied successfully, False otherwise."""
        if self._apply_filter_fn and self._filter_expression_model and self._use_filter_model:
            return self._apply_filter_fn(self._filter_expression_model.as_string, self._use_filter_model.as_bool)
        return False

    def build_ui(self):
        """Build the FilterWindow UI."""
        if not self._filter_expression_model or not self._use_filter_model:
            return

        def on_ok_clicked():
            if self._apply_filter():
                self.visible = False

        def on_apply_clicked():
            self._apply_filter()

        def on_cancel_clicked():
            self.visible = False

        def on_use_filter_label_mouse_pressed(*_):
            if self._use_filter_model:
                self._use_filter_model.set_value(not self._use_filter_model.as_bool)

        def filter_expression_value_changed():
            if not self._filter_expression_model:
                return
            has_filter_expression = len(self._filter_expression_model.as_string) > 0
            if self._clear_search_button:
                self._clear_search_button.visible = has_filter_expression
            if has_filter_expression and self._use_filter_model:
                self._use_filter_model.set_value(True)

        def filter_expression_begin_edit():
            filter_expression_value_changed()

        def filter_expression_end_edit():
            pass

        def clear_filter_expression():
            if self._filter_expression_model:
                self._filter_expression_model.set_value("")
            filter_expression_value_changed()

        def on_help_collapsed_changed(*_):
            self.height = 0

        help_title = "Filtering expression syntax"
        help_text = (
            "    - Column references: [ColumnName] (Enclose column names in square brackets)\n"
            "    - String and numeric literals (Enclose 'strings' in single quotes).\n"
            "    - Operators: '=', '<', '>', '<=', '>=', '<>', '!=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE'\n"
            "    - Logical operators: AND, OR\n"
            "    - Parentheses for grouping\n"
            "    - Comma-separated lists for IN/NOT IN\n"
            "Notes:\n"
            "    - LIKE: Checks if the right-hand string (pattern) is a substring of the left-hand value (column).\n"
            "    - IN: Checks if the left-hand value (column) is present in the right-hand list. E.g., [State] IN ('A','B').\n"
            "    - Can LIKE be used together with IN? No, LIKE is only supported as a binary operator, not as a list operator.\n"
            "      You can't do [Name] IN LIKE ('foo', 'bar'). If you want to check if a value matches any of several LIKE\n"
            "      patterns, you must chain with OR: ([Name] LIKE 'foo' OR [Name] LIKE 'bar').\n"
            "Example:\n"
            "      ([State] IN ('Approved', 'New')) OR ([Type] LIKE 'Hard' AND [Records] > 10 AND [Max Overlaps] >= 100)"
        )

        self._carb_subs = [
            self._filter_expression_model.subscribe_begin_edit_fn(lambda _: filter_expression_begin_edit()),
            self._filter_expression_model.subscribe_value_changed_fn(lambda _: filter_expression_value_changed()),
            self._filter_expression_model.subscribe_end_edit_fn(lambda _: filter_expression_end_edit()),
        ]

        with self.frame:
            with ui.VStack(height=0, style={"margin": Styles.MARGIN_DEFAULT}):
                with ui.CollapsableFrame(
                    help_title,
                    name="help_frame",
                    height=0,
                    collapsed=True,
                    collapsed_changed_fn=on_help_collapsed_changed,
                    tooltip=help_title + ":\n" + help_text,
                    multiline=True,
                ):
                    ui.Label(help_text)
                ui.Label("Your custom filter expression:", width=0)
                with ui.ZStack(height=0, style={"margin": 2}):
                    ui.Rectangle(style_type_name_override="StringFieldFrame")
                    with ui.HStack():
                        self._filter_exp_string_field = ui.StringField(
                            self._filter_expression_model,
                            width=ui.Fraction(1),
                            name="filter_expression_field",
                        )
                        self._clear_search_button = ui.Button(
                            name="clear_string",
                            tooltip="Clear filter expression",
                            visible=False,
                            width=Styles.IMG_BUTTON_SIZE_H,
                            height=Styles.IMG_BUTTON_SIZE_V - 2,
                            image_width=Styles.IMG_BUTTON_SIZE_H,
                            image_height=Styles.IMG_BUTTON_SIZE_V - 2,
                            clicked_fn=clear_filter_expression,
                        )
                with ui.HStack(width=0):
                    ui.CheckBox(model=self._use_filter_model)
                    ui.Label("Use this filter", mouse_pressed_fn=on_use_filter_label_mouse_pressed)
                with ui.HStack(alignment=ui.Alignment.BOTTOM):
                    ui.Spacer()
                    ui.Button("OK", name="ok_button", width=100, clicked_fn=on_ok_clicked)
                    ui.Button("Apply", name="apply_button", width=100, clicked_fn=on_apply_clicked)
                    ui.Button("Cancel", width=100, clicked_fn=on_cancel_clicked)
        filter_expression_value_changed()

    def show(self):
        """Show the FilterWindow."""
        self.build_ui()
        self.visible = True
        self.focus()
        if self._filter_exp_string_field:
            self._filter_exp_string_field.focus_keyboard()
