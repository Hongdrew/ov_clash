# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.ui import color as cl
from omni.kit.widget.stage.stage_icons import StageIcons
from pathlib import Path
from datetime import datetime
from .utils import get_datetime_str, format_int_to_str
from .settings import ExtensionSettings

__all__ = []

ICON_FOLDER_NAME = "resources/icons"
CURRENT_PATH = Path(__file__).parent.absolute()
ICON_PATH = CURRENT_PATH.parent.parent.joinpath(ICON_FOLDER_NAME)


def format_timestamp(dt: datetime):
    """Format a datetime object into a string based on ExtensionSettings.

    Args:
        dt (datetime): The datetime object to format.

    Returns:
        str: The formatted datetime string or a no-timestamp string based on settings.
    """
    return get_datetime_str(dt) if not ExtensionSettings.ui_no_timestamps else ExtensionSettings.no_timestamp_str


def format_int(value: int):
    """Format an integer value to a string based on ExtensionSettings.

    Args:
        dt (datetime): The datetime object to format.

    Returns:
        str: The formatted datetime string or a no-timestamp string based on settings.
    """
    return format_int_to_str(value) if not ExtensionSettings.ui_no_locale_formatting else str(value)


class Styles:
    """A class for defining and storing UI styles and color themes.

    This class provides a collection of predefined styles and colors used across
    the user interface to ensure consistency and improve visual appearance.
    It includes color definitions for various UI elements, margin settings,
    and styles for specific components such as buttons, labels, and trees.

    It helps in standardizing the look and feel of the application, making it
    more visually appealing and easier to use.
    """

    # Clash Color Values
    # Typically, Red and Green are used to show contrast between clashing objects.
    # Red/Green color blindness is the most common type of color blindness.
    # Orange/Blue provides more contrast across all types and does not interfere with red color coding,
    # which should be reserved for reporting errors.
    COLOR_CLASH_A = cl("0D77B4")  # Blue
    COLOR_CLASH_B = cl("#FF7A00")  # Orange

    COLOR_CLASH_NOTPRESENT = cl("#CB6A6A")  # Dark Red
    COLOR_CLASH_OUTDATED = cl("#FF7A00")  # Orange

    COLOR_UI_BRIGHTER = cl.shade(cl("#34C7FF"))
    COLOR_UI_DIMMED = 0xFF8A8777  # Dimmed OV color (taken from Layer Window)
    COLOR_UI_VERY_DIMMED = 0xFF646464
    COLOR_UI_SUPER_DIMMED = 0xFF303030
    COLOR_BORDER = cl.shade(0xFFC9974C)
    COLOR_SEARCH_FIELD_FRAME = cl.shade(0xFF23211F, light=0xFF535354)
    COLOR_HILIGHT_TEXT = cl.yellow
    COLOR_SPLITTER_HOVER = 0xFFB0703B
    COLOR_SEPARATOR = 0xFF6F6F6F

    COLOR_PROGRESS_BAR_ANIM = cl("#4C9B00")  # dimmed green
    COLOR_2ND_PROGRESS_BAR_ANIM = cl.white
    COLOR_PROGRESS_BAR_CLASH = COLOR_CLASH_B
    COLOR_2ND_PROGRESS_BAR_CLASH = COLOR_CLASH_A
    COLOR_PROGRESS_BAR_FETCH = COLOR_CLASH_A
    COLOR_2ND_PROGRESS_BAR_FETCH = COLOR_CLASH_B

    MARGIN_DEFAULT = 3
    PADDING_DEFAULT = 3

    # dimmed label text
    LABEL_TEXT_DIMMED = {"color": COLOR_UI_DIMMED, "margin": 0, "padding": 0}

    HIGHLIGHT_LABEL_STYLE = {
        "HStack": {"margin": 4},
        "Label": {"color": cl.actions_text},
        "Label:selected": {"color": cl.actions_background},
    }

    DROPDOWN_COLUMN_STYLE = {"margin": 0, "padding": PADDING_DEFAULT}

    # toolbar button with image style
    IMG_BUTTON_SIZE_H = 16
    IMG_BUTTON_SIZE_V = IMG_BUTTON_SIZE_H

    SETTINGS_LINE_STYLE = {":disabled": {"color": COLOR_UI_DIMMED}}
    SETTINGS_WND_STYLE = {
        "CheckBox": {"color": cl("#2E86A9"), "margin": MARGIN_DEFAULT},
        "Titlebar.Background": {"background_color": cl.shade(cl("#1F2123"))},
        "Titlebar.Title": {"color": cl.shade(cl("#848484"))},
        "Titlebar.Reset": {"background_color": 0},
        "Titlebar.Reset.Label": {"color": cl.shade(cl("#2E86A9"))},
        "Titlebar.Reset.Label:hovered": {"color": COLOR_UI_BRIGHTER},
    }

    NOTICE_WIDGET_STYLE = {"Label::warning_text": {"color": COLOR_HILIGHT_TEXT}}

    FILTER_BUTTON_ACTIVE_STYLE = {"image_url": StageIcons().get("filter"), "color": COLOR_BORDER}
    FILTER_BUTTON_INACTIVE_STYLE = {"image_url": StageIcons().get("filter"), "color": COLOR_UI_DIMMED}

    CLASH_STATS_WND_STYLE = {
        "TreeView": {"secondary_color": COLOR_UI_SUPER_DIMMED},
    }

    GROUPS_WND_STYLE = {
        "TreeView::groups:selected": {"background_color": COLOR_BORDER},
        "Button.Image::refresh": {"image_url": StageIcons().get("refresh"), "color": COLOR_UI_DIMMED},
        "Button::refresh": {"background_color": 0x0, "padding": 2},
        "Button.Image::options": {"image_url": StageIcons().get("options"), "color": COLOR_UI_DIMMED},
        "Button::options": {"background_color": 0x0, "padding": 2},
    }

    CLASH_WND_STYLE = {
        "TreeView": {"secondary_color": COLOR_UI_SUPER_DIMMED},
        "Label::warning_text": {"color": COLOR_HILIGHT_TEXT},
        "Button.Label:disabled": {"color": COLOR_UI_VERY_DIMMED},
        "ProgressBar": {
            "margin": MARGIN_DEFAULT - 1,
            "color": COLOR_PROGRESS_BAR_CLASH,
            "secondary_color": COLOR_2ND_PROGRESS_BAR_CLASH
        },
        "Button.Image::filter": FILTER_BUTTON_ACTIVE_STYLE,
        "Button::filter": {"background_color": 0x0, "padding": 2},
        "Button.Image::options": {"image_url": StageIcons().get("options"), "color": COLOR_UI_DIMMED},
        "Button::options": {"background_color": 0x0, "padding": 2},
        "Button.Image::refresh": {"image_url": StageIcons().get("refresh"), "color": COLOR_UI_DIMMED},
        "Button::refresh": {"background_color": 0x0, "padding": 2},
        "Button.Image::clear_search": {"image_url": f"{ICON_PATH}/remove.svg"},
        "Button::clear_search": {"padding": PADDING_DEFAULT, "margin": 1, "background_color": cl.shade(0x00000000)},
        "Image::search_icon": {
            "image_url": f"{ICON_PATH}/search.svg",
            "color": COLOR_UI_VERY_DIMMED,
            "margin": 0,
            "padding": 0,
        },
        "Label::search_label": {"color": COLOR_UI_VERY_DIMMED, "margin": 0, "padding": 0},
        "SearchFieldFrame": {"padding": 0, "margin": 0, "background_color": COLOR_SEARCH_FIELD_FRAME},
        "SearchFieldFrame:selected": {
            "padding": 0,
            "margin": 0,
            "background_color": COLOR_SEARCH_FIELD_FRAME,
            "border_color": COLOR_BORDER,
        },
        "Splitter": {"background_color": COLOR_UI_VERY_DIMMED, "margin_width": 0},
        "Splitter:hovered": {"background_color": COLOR_SPLITTER_HOVER},
        "Splitter:pressed": {"background_color": COLOR_SPLITTER_HOVER},
    }

    TABLE_CELL_STYLE = {
        "Label": {"color": COLOR_UI_DIMMED, "margin": MARGIN_DEFAULT},
        "Label:hovered": {"color": cl.white},
        "Label:selected": {"color": cl.black},
    }

    CLASH_NUM_INDICATOR = {"margin": 0, "padding": 0, "Label:selected": {"color": cl.white}}
    CLASH_NUM_INDICATOR_NOTPRESENT = CLASH_NUM_INDICATOR | {
        "color": COLOR_UI_SUPER_DIMMED,
        "background_color": COLOR_CLASH_NOTPRESENT,
    }

    FILTER_WND_STYLE = {
        "CheckBox": {"color": cl("#2E86A9"), "margin": 3},
        "StringFieldFrame": {"padding": 0, "margin": 0, "background_color": COLOR_SEARCH_FIELD_FRAME},
        "Button::clear_string": {"padding": 3, "margin": 1, "background_color": COLOR_SEARCH_FIELD_FRAME},
        "Button.Image::clear_string": {"image_url": f"{ICON_PATH}/remove.svg"},
    }