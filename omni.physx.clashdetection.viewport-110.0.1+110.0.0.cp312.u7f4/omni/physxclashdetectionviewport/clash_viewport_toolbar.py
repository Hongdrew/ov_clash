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
from typing import Any, Dict

import carb
import carb.settings

import omni.ui as ui
from omni.kit.viewport.menubar.core import (
    CheckboxMenuDelegate,
    FloatArraySettingColorMenuItem,
    IconMenuDelegate,
    SettingModel,
    SettingModelWithDefaultValue,
    SliderMenuDelegate,
    ViewportMenuContainer,
)

from .clash_viewport_settings import ClashViewportSettings, ClashViewportSettingValues
from .clash_viewport_toolbar_style import UI_STYLE


class ViewportSpecificContext:
    """A class to manage viewport-specific settings and context.

    This class provides a structure to handle settings specific to individual viewports in the application's user interface. It interacts with the application's settings system to store and retrieve these settings as needed.
    """

    def __init__(self):
        """Initializes the ViewportSpecificContext instance."""
        self.__settings = carb.settings.get_settings()

    def destroy(self):
        """Destroys the ViewportSpecificContext instance."""
        pass


class ViewportSetting:
    """A class for managing individual viewport settings.

    This class provides functionality to define and manage settings
    specific to a viewport. It allows setting default values and optionally
    applying these defaults to the settings storage.

    Args:
        key (str): The unique identifier for the setting.
        default (Any): The default value for the setting.
        set_default (bool): Whether to set this default value in the settings storage.
    """

    def __init__(self, key: str, default: Any, set_default: bool = True):
        """Initializes a new instance of the ViewportSetting class."""
        settings = carb.settings.get_settings()
        self.key = key
        self.default = default
        if set_default:
            settings.set_default(self.key, self.default)


class ViewportSettingModel(SettingModelWithDefaultValue):
    """A model for managing viewport settings with default values.

    This class extends the SettingModelWithDefaultValue to provide a way to manage viewport settings with optional draggable capability.

    Args:
        viewport_setting (ViewportSetting): The viewport setting instance containing the key and default value.
        draggable (bool): Optional; If set to True, the setting is draggable. Default is False.
    """

    def __init__(self, viewport_setting: ViewportSetting, draggable: bool = False):
        """Initializes the ViewportSettingModel with the given viewport setting and draggable flag."""
        super().__init__(viewport_setting.key, viewport_setting.default, draggable=draggable)


class VIEWPORT_SETTINGS:
    """A class that encapsulates various viewport settings for clash detection.

    This class provides a collection of settings related to clash detection in a viewport. Each setting is represented as an instance of the ViewportSetting class and encompasses different aspects such as wireframe thickness, outline scales, and camera centering tolerances. These settings are used to configure the behavior and appearance of the viewport when dealing with clash detection scenarios.
    """

    LOG_PROFILE = ViewportSetting(ClashViewportSettings.LOG_PROFILE, ClashViewportSettingValues.LOG_PROFILE)
    LOG_HIGHLIGHT = ViewportSetting(ClashViewportSettings.LOG_HIGHLIGHT, ClashViewportSettingValues.LOG_HIGHLIGHT)
    USE_SOURCE_NORMALS = ViewportSetting(
        ClashViewportSettings.USE_SOURCE_NORMALS,
        ClashViewportSettingValues.USE_SOURCE_NORMALS,
    )
    CAMERA_CENTERING_FAR_TOLERANCE = ViewportSetting(
        ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE,
        ClashViewportSettingValues.CAMERA_CENTERING_FAR_TOLERANCE,
    )
    CAMERA_CENTERING_NEAR_TOLERANCE = ViewportSetting(
        ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE,
        ClashViewportSettingValues.CAMERA_CENTERING_NEAR_TOLERANCE,
    )
    CLASH_WIREFRAME_THICKNESS = ViewportSetting(
        ClashViewportSettings.CLASH_WIREFRAME_THICKNESS,
        ClashViewportSettingValues.CLASH_WIREFRAME_THICKNESS,
    )
    CLASH_OUTLINE_WIDTH_SIZE = ViewportSetting(
        ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE,
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SIZE,
    )
    CLASH_OUTLINE_WIDTH_SCALE = ViewportSetting(
        ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE,
        ClashViewportSettingValues.CLASH_OUTLINE_WIDTH_SCALE,
    )
    CLASH_MESHES_DISPLAY_LIMIT = ViewportSetting(
        ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT,
        ClashViewportSettingValues.CLASH_MESHES_DISPLAY_LIMIT,
    )
    CLASH_OUTLINE_DIAGONAL_MIN_CENTERING = ViewportSetting(
        ClashViewportSettings.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING,
        ClashViewportSettingValues.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING,
    )
    MAIN_VIEWPORT_USE_SELECTION_GROUPS = ViewportSetting(
        ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS,
        ClashViewportSettingValues.MAIN_VIEWPORT_USE_SELECTION_GROUPS,
    )
    MAIN_VIEWPORT_SHOW_CLASH_MESHES = ViewportSetting(
        ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES,
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_MESHES,
    )
    MAIN_VIEWPORT_SHOW_CLASH_OUTLINES = ViewportSetting(
        ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES,
        ClashViewportSettingValues.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES,
    )
    CLASH_VIEWPORT_SHOW_CLASHES = ViewportSetting(
        ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES,
        ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_CLASHES,
    )
    CLASH_VIEWPORT_SHOW_WIREFRAMES = ViewportSetting(
        ClashViewportSettings.CLASH_VIEWPORT_SHOW_WIREFRAMES,
        ClashViewportSettingValues.CLASH_VIEWPORT_SHOW_WIREFRAMES,
    )
    CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS = ViewportSetting(
        ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS,
        ClashViewportSettingValues.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS,
    )
    CLASH_HIGHLIGHT_FILLED_MESHES = ViewportSetting(
        ClashViewportSettings.CLASH_HIGHLIGHT_FILLED_MESHES,
        ClashViewportSettingValues.CLASH_HIGHLIGHT_FILLED_MESHES,
    )
    MAIN_VIEWPORT_CENTER_CAMERA = ViewportSetting(
        ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA,
        ClashViewportSettingValues.MAIN_VIEWPORT_CENTER_CAMERA,
    )
    CLASH_VIEWPORT_CENTER_CAMERA = ViewportSetting(
        ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA,
        ClashViewportSettingValues.CLASH_VIEWPORT_CENTER_CAMERA,
    )


class ClashDetectionViewportToolbar(ViewportMenuContainer):
    """A class for managing and interacting with the Clash Detection Viewport Toolbar.

    This class is responsible for initializing and managing the toolbar specific to the Clash Detection viewport. It handles the creation of various menu items and settings related to the viewport, such as wireframe thickness, outline scales, and camera tolerances.

    Args:
        clash_viewport: The viewport associated with the clash detection toolbar.
    """

    def __init__(self, clash_viewport):
        """Initializes the ClashDetectionViewportToolbar class."""
        super().__init__(
            name="Clash Viewport",
            delegate=IconMenuDelegate("Clash Viewport", text=True),
            visible_setting_path="/exts/omni.physx.clashdetection.viewport/visible",
            order_setting_path="/exts/omni.physx.clashdetection.viewport/order",
            style=UI_STYLE,
        )
        self.__viewport_specific_context: Dict[str, ViewportSpecificContext] = {}
        self._clash_viewport = clash_viewport

    def build_fn(self, factory_args: Dict):
        """Builds the menu using the provided factory.

        Args:
            factory_args (Dict): The factory to build the menu.
        """
        ui.Menu(
            self.name,
            delegate=self._delegate,
            on_build_fn=partial(self._build_menu, factory_args),
            style=self._style,
        )

    def _build_menu(self, factory: Dict) -> None:
        viewport_api = factory.get("viewport_api")
        if not viewport_api:
            return
        viewport_api_id = viewport_api.id
        viewport_specific_context = self.__viewport_specific_context.get(viewport_api_id)
        if viewport_specific_context:
            viewport_specific_context.destroy()
        viewport_specific_context = ViewportSpecificContext()
        self.__viewport_specific_context[viewport_api_id] = viewport_specific_context

        ui.Separator(text="Camera")
        ui.MenuItem(  # type: ignore
            "Center main viewport",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.MAIN_VIEWPORT_CENTER_CAMERA),  # type: ignore
                tooltip="Center camera in main viewport",
                has_reset=True,
            ),
        ),

        ui.MenuItem(  # type: ignore
            "Center clash viewport",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_VIEWPORT_CENTER_CAMERA),  # type: ignore
                tooltip="Center camera in clash viewport",
                has_reset=True,
            ),
        ),
        ui.MenuItem(
            "Re-centering far tolerance",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CAMERA_CENTERING_FAR_TOLERANCE),
                min=0,
                max=20,
                tooltip="Do not re-center camera if it would be translated less than this tolerance (going away from selected clash)",
                has_reset=True,
            ),
        )
        ui.MenuItem(  # type: ignore
            "Re-centering near tolerance",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CAMERA_CENTERING_NEAR_TOLERANCE),
                min=-20,
                max=0,
                tooltip="Do not re-center camera if it would be translated less than this tolerance (going towards the selected clash)",
                has_reset=True,
            ),
        ),
        ui.Separator(text="Main Viewport")
        ui.MenuItem(  # type: ignore
            "Enable selection groups",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.MAIN_VIEWPORT_USE_SELECTION_GROUPS),  # type: ignore
                tooltip="Highlight clash meshes in main viewport using selection groups (see through occluded objects).\nDEPRECATED. Will be enabled by default and it will not be possible to disable it in future releases.",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Fill selection groups",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_HIGHLIGHT_FILLED_MESHES),  # type: ignore
                tooltip="If enabled fills selection groups with a semi-transparent solid color.\nDisable this option to improve depth perception of highlighted clashes.",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Show clash meshes",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.MAIN_VIEWPORT_SHOW_CLASH_MESHES),  # type: ignore
                tooltip="Show clash meshes in main viewport",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Show clash outlines",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES),  # type: ignore
                tooltip="Show clash outlines in main viewport",
                has_reset=True,
            ),
        ),
        ui.Separator(text="Clash Viewport")
        ui.MenuItem(  # type: ignore
            "Show meshes and outlines",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_VIEWPORT_SHOW_CLASHES),  # type: ignore
                tooltip="Display clash meshes and outlines in clash viewport",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Show wireframes",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_VIEWPORT_SHOW_WIREFRAMES),  # type: ignore
                tooltip="Display wireframes for clash meshes in clash viewport",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Use translucent materials",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS),  # type: ignore
                tooltip="Use translucent materials for clash meshes in clash viewport",
                has_reset=True,
            ),
        ),
        ui.Separator(text="Advanced")
        ui.MenuItem(  # type: ignore
            "Log profile",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.LOG_PROFILE),  # type: ignore
                tooltip="Prints the timings of the clash viewport",
                has_reset=True,
            ),
        )
        ui.MenuItem(  # type: ignore
            "Log highlight",
            hide_on_click=False,
            delegate=CheckboxMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.LOG_HIGHLIGHT),  # type: ignore
                tooltip="Print logs of clash viewport highlight",
                has_reset=True,
            ),
        )
        ui.MenuItem(  # type: ignore
            "Max displayed clashes",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_MESHES_DISPLAY_LIMIT),
                min=1,
                max=100,
                slider_class=ui.IntSlider,  # type: ignore
                tooltip="Sets the maximum number of clashes shown at once. Only obeyed when 'Show clash meshes' is disabled or 'Use selection groups' is enabled.",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Outline size",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_OUTLINE_WIDTH_SIZE),
                min=0.0001,
                max=1.0,
                step=0.0001,
                tooltip="Size of the outline in world space units",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Outline scale",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_OUTLINE_WIDTH_SCALE),
                min=1.0,
                max=100.0,
                step=0.05,
                tooltip="Scale of the outline in world space units",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Outline min centering",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING),
                min=0.01,
                max=10,
                tooltip="Minimum diagonal length for clash outline to be considered for centering",
                has_reset=True,
            ),
        ),
        ui.MenuItem(  # type: ignore
            "Wireframe thickness",
            hide_on_click=False,
            delegate=SliderMenuDelegate(
                model=ViewportSettingModel(VIEWPORT_SETTINGS.CLASH_WIREFRAME_THICKNESS),
                min=0.01,
                max=10,
                tooltip="Thickness of the wireframe",
                has_reset=True,
            ),
        ),
