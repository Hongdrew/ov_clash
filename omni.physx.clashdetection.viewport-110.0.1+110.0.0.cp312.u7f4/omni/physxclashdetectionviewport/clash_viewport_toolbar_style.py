# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pathlib import Path


from omni.ui import color as cl

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.joinpath("icons")

UI_STYLE = {
    "Menu.Item.Icon::Clash Viewport": {"image_url": f"{ICON_PATH}/settings.svg"},
    "ComboBox::ratio": {"background_color": 0x0, "padding": 4, "margin": 0},
}

cl.save_background = cl.shade(cl("#1F2123"))
cl.input_hint = cl.shade(cl("#5A5A5A"))
SAVE_WINDOW_STYLE = {
    "Window": {"secondary_background_color": 0x0},
    "Titlebar.Background": {"background_color": cl.save_background},
    "Input.Hint": {"color": cl.input_hint},
    "Button": {"background_color": cl.save_background},
}
