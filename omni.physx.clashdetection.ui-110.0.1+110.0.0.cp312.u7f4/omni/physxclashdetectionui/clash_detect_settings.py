# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any, Dict, Callable, Optional, List, Tuple
from collections import OrderedDict
import json
import carb
import omni.ui as ui
import omni.kit.app
import omni.usd
from .styles import Styles
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.utils import clamp_value
from .settings import ExtensionSettings

__all__ = []


class SettingDef:
    """A class for defining settings with a label, tooltip, and default value.

    This class provides the structure for settings, including default values and UI elements.
    Settings can be enabled or disabled, and their values can be accessed and modified.

    Args:
        label (str): The label for the setting.
        tooltip (str): The tooltip providing additional information about the setting.
        default_value (Any): The default value of the setting.
        refresh_state_fnc (Optional[Callable[['SettingDef'], None]]): Custom function to refresh the setting.
        convert_value_fnc (Optional[Callable[[Any, bool], Any]]): Custom conversion function; bool: False → on assignment; True → on retrieval.
    """

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        default_value: Any = None,
        refresh_state_fnc: Optional[Callable[['SettingDef'], None]] = None,
        convert_value_fnc: Optional[Callable[[Any, bool], Any]] = None,
    ):
        """Initializes the SettingDef instance."""
        super().__init__()
        self._label = label
        self._tooltip = tooltip
        self._default_value = default_value
        self._model = None
        self._sub = None
        self._control = None
        self._refresh_state_fnc = refresh_state_fnc
        self._convert_value_fnc = convert_value_fnc

    def destroy(self):
        """Cleans up the resources used by the setting."""
        self._sub = None
        self._model = None
        self._control = None
        self._refresh_state_fnc = None
        self._convert_value_fnc = None

    @property
    def label(self) -> str:
        """Gets the label of the setting.

        Returns:
            str: The label of the setting.
        """
        return self._label

    @property
    def tooltip(self) -> str:
        """Gets the tooltip of the setting.

        Returns:
            str: The tooltip of the setting.
        """
        return self._tooltip

    @property
    def model(self) -> Any:
        """Gets the model associated with the setting.

        Returns:
            Any: The model associated with the setting.
        """
        return self._model

    @property
    def default_value(self) -> Any:
        """Gets the default value of the setting.

        Returns:
            Any: The default value of the setting.
        """
        return self._default_value

    @property
    def value(self) -> Any:
        """Gets the current value of the setting.

        Returns:
            Any: The current value of the setting.
        """
        return None

    @value.setter
    def value(self, value) -> None:  # NOTE: to override
        """Sets the value of the setting.

        Args:
            value (Any): The new value for the setting.
        """
        pass

    @property
    def control(self) -> Any:
        """Gets the control element of the setting.

        Returns:
            Any: The control element of the setting.
        """
        return self._control

    @property
    def enabled(self) -> bool:
        """Gets the enabled state of the setting.

        Returns:
            bool: The enabled state of the setting.
        """
        return self._control.enabled if self._control else True

    @enabled.setter
    def enabled(self, value) -> None:
        """Sets the enabled state of the setting.

        Args:
            value (bool): The enabled state to set.
        """
        if self._control:
            self._control.enabled = value

    def reset_value_to_default(self) -> None:
        """Resets the value of the setting to the default value."""
        if self._model:
            self._model.set_value(self._default_value)

    def refresh_state(self):
        """Refreshes the state of the setting if refresh_state_fnc is set."""
        if self._refresh_state_fnc:
            self._refresh_state_fnc(self)

    # base implementation to override
    def build_ui(self, label_width=None, value_width=None) -> None:
        """Builds the user interface for the setting.

        Args:
            label_width (Optional[int]): Width of the label.
            value_width (Optional[int]): Width of the value field.
        """
        pass


class BoolSetting(SettingDef):
    """A class for managing boolean settings with UI support.

    This class extends SettingDef and provides functionality specific to boolean settings, including the creation of a UI checkbox and handling value changes.

    Args:
        label (str): The label for the setting.
        tooltip (str): The tooltip for the setting.
        default_value (bool): The default value for the setting.
        refresh_state_fnc (Optional[Callable[['SettingDef'], None]]): custom function to refresh the setting.
        convert_value_fnc (Optional[Callable[[Any, bool], Any]]): Custom conversion function; bool: False → on assignment; True → on retrieval.
        on_value_changed_fnc (Optional[Callable[[ui.AbstractValueModel], None]]): A callback function that is called when the value changes.
    """

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        default_value: bool = False,
        refresh_state_fnc: Optional[Callable[['SettingDef'], None]] = None,
        convert_value_fnc: Optional[Callable[[Any, bool], Any]] = None,
        on_value_changed_fnc: Optional[Callable[[ui.AbstractValueModel], None]] = None,
    ):
        """Initializes the BoolSetting class."""
        super().__init__(label, tooltip, default_value, refresh_state_fnc, convert_value_fnc)
        self._model = ui.SimpleBoolModel(default_value)
        if on_value_changed_fnc:
            self._sub = self._model.subscribe_value_changed_fn(on_value_changed_fnc)

    @property
    def value(self):
        """Gets the current value of the boolean setting.

        Returns:
            bool: The current value of the setting.
        """
        return self._convert_value_fnc(self._model.as_bool, True) if self._convert_value_fnc else self._model.as_bool

    @value.setter
    def value(self, value):
        """Sets the value of the boolean setting.

        Args:
            value (bool): The new value to set.
        """
        self._model.as_bool = self._convert_value_fnc(value, False) if self._convert_value_fnc else value

    # base implementation to override
    def build_ui(self, label_width=None, value_width=None):
        """Builds the user interface for the boolean setting.

        Args:
            label_width (int): The width of the label.
            value_width (int): The width of the value field.
        """
        tooltip = self.tooltip
        tooltip += f"\nDefault Value: {self._default_value}"
        self._control = ui.HStack(style=Styles.SETTINGS_LINE_STYLE)
        with self._control:
            ui.Label(self.label, width=label_width, tooltip=tooltip)
            ui.Spacer()
            ui.CheckBox(self.model, width=50, alignment=ui.Alignment.RIGHT, tooltip=tooltip)


class IntSetting(SettingDef):
    """A class for creating and managing integer settings with UI components.

    This class provides methods to create integer settings, set their values, and define their behavior within a user interface. It includes features such as setting minimum and maximum values, step values, and handling value changes with callback functions.

    Args:
        label (str): The label for the setting.
        tooltip (str): The tooltip text for the setting.
        default_value (int): The default value for the setting.
        min_value (int): The minimum allowable value for the setting.
        max_value (int): The maximum allowable value for the setting.
        step_value (int): The step increment for adjusting the value.
        refresh_state_fnc (Optional[Callable[['SettingDef'], None]]): custom function to refresh the setting.
        convert_value_fnc (Optional[Callable[[Any, bool], Any]]): Custom conversion function; bool: False → on assignment; True → on retrieval.
        on_value_changed_fnc (Optional[Callable[[ui.AbstractValueModel], None]]): A function to be called when the value changes.
    """

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        default_value: int = 0,
        min_value: int = 0,
        max_value: int = 0,
        step_value: int = 0,
        refresh_state_fnc: Optional[Callable[['SettingDef'], None]] = None,
        convert_value_fnc: Optional[Callable[[Any, bool], Any]] = None,
        on_value_changed_fnc: Optional[Callable[[ui.AbstractValueModel], None]] = None,
    ):
        """Initializes the IntSetting class."""
        super().__init__(label, tooltip, default_value, refresh_state_fnc, convert_value_fnc)
        self._min_value = min_value
        self._max_value = max_value
        self._step_value = step_value
        self._model = ui.SimpleIntModel(default_value)
        self._model.min = min_value
        self._model.max = max_value
        if on_value_changed_fnc:
            self._sub = self._model.subscribe_value_changed_fn(on_value_changed_fnc)

    @property
    def value(self):
        """Gets the current value of the IntSetting.

        Returns:
            int: The current value.
        """
        return self._convert_value_fnc(self._model.as_int, True) if self._convert_value_fnc else self._model.as_int

    @value.setter
    def value(self, value):
        """Sets the value of the IntSetting.

        Args:
            value (int): The new value to set.
        """
        val = self._convert_value_fnc(value, False) if self._convert_value_fnc else value
        self._model.as_int = clamp_value(val, self._min_value, self._max_value)

    # base implementation to override
    def build_ui(self, label_width=None, value_width=None):
        """Builds the UI for the IntSetting.

        Args:
            label_width (int): Width for the label.
            value_width (int): Width for the value input.
        """
        tooltip = self.tooltip
        tooltip += f"\nDefault Value: {self._default_value}, Min: {self._min_value}, Max: {self._max_value}"
        self._control = ui.HStack(style=Styles.SETTINGS_LINE_STYLE)
        with self._control:
            ui.Label(self.label, width=label_width, tooltip=tooltip)
            ui.Spacer()
            ui.IntDrag(
                self.model,
                min=self._min_value,
                max=self._max_value,
                step=self._step_value,
                width=value_width,
                alignment=ui.Alignment.RIGHT,
                tooltip=tooltip,
            )


class FloatSetting(SettingDef):
    """A class for managing float settings in a UI.

    This class provides functionalities to define, manipulate, and display float settings with specific constraints and formats in a user interface.

    Args:
        label (str): The label for the setting.
        tooltip (str): The tooltip text for the setting.
        default_value (float): The default value for the setting.
        min_value (float): The minimum allowable value for the setting.
        max_value (float): The maximum allowable value for the setting.
        step_value (float): The step increment for the setting.
        num_format (str): The numerical format for displaying the value.
        refresh_state_fnc (Optional[Callable[['SettingDef'], None]]): custom function to refresh the setting.
        convert_value_fnc (Optional[Callable[[Any, bool], Any]]): Custom conversion function; bool: False → on assignment; True → on retrieval.
        on_value_changed_fnc (Optional[Callable[[ui.AbstractValueModel], None]]): A callback function that gets called when the value changes.
    """

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        default_value: float = 0.0,
        min_value: float = 0.0,
        max_value: float = 0.0,
        step_value: float = 0.0,
        num_format: str = ".6f",
        refresh_state_fnc: Optional[Callable[['SettingDef'], None]] = None,
        convert_value_fnc: Optional[Callable[[Any, bool], Any]] = None,
        on_value_changed_fnc: Optional[Callable[[ui.AbstractValueModel], None]] = None,
    ):
        """Initializes a new instance of the FloatSetting class."""
        super().__init__(label, tooltip, default_value, refresh_state_fnc, convert_value_fnc)
        self._min_value = min_value
        self._max_value = max_value
        self._step_value = step_value
        self._model = ui.SimpleFloatModel(default_value)
        self._model.min = min_value
        self._model.max = max_value
        self._num_format = num_format if num_format.startswith("%") else "%" + num_format
        if on_value_changed_fnc:
            self._sub = self._model.subscribe_value_changed_fn(on_value_changed_fnc)

    @property
    def value(self):
        """Gets the current value of the FloatSetting.

        Returns:
            float: The current value.
        """
        return self._convert_value_fnc(self._model.as_float, True) if self._convert_value_fnc else self._model.as_float

    @value.setter
    def value(self, value):
        """Sets the value of the FloatSetting.

        Args:
            value (float): The value to set.
        """
        val = self._convert_value_fnc(value, False) if self._convert_value_fnc else value
        self._model.as_float = clamp_value(val, self._min_value, self._max_value)

    # base implementation to override
    def build_ui(self, label_width=None, value_width=None):
        """Builds the user interface for the FloatSetting.

        Args:
            label_width (int): Width of the label.
            value_width (int): Width of the value display.
        """
        import locale

        tooltip = self.tooltip
        nf = self._num_format
        locale.setlocale(locale.LC_ALL, '')  # Set locale to user's default setting (OS locale)
        default_value = locale.format_string(nf, self._default_value)
        min_value = locale.format_string(nf, self._min_value)
        max_value = locale.format_string(nf, self._max_value)
        tooltip += f"\nDefault Value: {default_value}, Min: {min_value}, Max: {max_value}"
        self._control = ui.HStack(style=Styles.SETTINGS_LINE_STYLE)
        with self._control:
            ui.Label(self.label, width=label_width, tooltip=tooltip)
            ui.Spacer()
            ui.FloatDrag(
                self.model,
                format=self._num_format,
                min=self._min_value,
                max=self._max_value,
                step=self._step_value,
                width=value_width,
                alignment=ui.Alignment.RIGHT,
                tooltip=tooltip,
            )


class ComboBoxSetting(SettingDef):
    """A class for managing combo box settings with UI support.

    This class extends SettingDef and provides functionality specific to combo box settings, including the creation of a UI combo box and handling value changes.
    """

    class ValueModel(ui.AbstractValueModel):
        def __init__(self, text: str,value: Any):
            super().__init__()
            self._text = text
            self._value = value

        def get_value_as_string(self) -> str:
            return self._text

        @property
        def value(self) -> Any:
            return self._value

        @value.setter
        def value(self, value: Any):
            self._value = value


    class NameValueItem(ui.AbstractItem):
        def __init__(self, text: str, value: Any):
            super().__init__()
            self.model = ComboBoxSetting.ValueModel(text, value)


    class Model(ui.AbstractItemModel):
        """Model class for ComboBoxSetting.

        This nested class provides the data model for the ComboBoxSetting UI element.
        It manages the list of selectable items, current selection index, and provides
        methods for retrieving display strings and models associated with each item.
        """
        def __init__(self, items: Optional[List[Tuple[str, Any]]] = None, on_value_changed_fnc: Optional[Callable[[Optional[ui.AbstractValueModel]], None]] = None):
            super().__init__()
            self._current_index = ui.SimpleIntModel()
            self._current_index.add_value_changed_fn(lambda item: self._current_index_changed(item, on_value_changed_fnc))
            self._combo_items = [ComboBoxSetting.NameValueItem(item[0], item[1]) for item in items] if items else []

        def _current_index_changed(self, item, on_value_changed_fnc: Optional[Callable[[Optional[ui.AbstractValueModel]], None]] = None):
            self._item_changed(None)
            index = item.as_int
            if on_value_changed_fnc:
                on_value_changed_fnc(self._combo_items[index].model if index != -1 else None)

        def get_item_index_by_value(self, value) -> int:
            for idx, item in enumerate(self._combo_items):
                if item.model.value == value:
                    return idx
            return -1

        def get_item_text_by_value(self, value) -> str:
            index = self.get_item_index_by_value(value)
            return self._combo_items[index].model.as_string if index != -1 else ""

        def select_item_by_value(self, value):
            index = self.get_item_index_by_value(value)
            self._current_index.set_value(index)

        # AbstractItemModel interfaces
        def get_item_children(self, item):
            return self._combo_items

        def get_item_value_model(self, item, column_id):
            if item is None:
                return self._current_index
            return item.model

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        default_value: Any = None,
        items: Optional[List[Tuple[str, Any]]] = None,
        refresh_state_fnc: Optional[Callable[['SettingDef'], None]] = None,
        convert_value_fnc: Optional[Callable[[Any, bool], Any]] = None,
        on_value_changed_fnc: Optional[Callable[[ui.AbstractValueModel], None]] = None,
    ):
        """Initializes the ComboBoxSetting class."""
        super().__init__(label, tooltip, default_value, refresh_state_fnc, convert_value_fnc)
        self._model = ComboBoxSetting.ValueModel("Current Value", default_value)
        if on_value_changed_fnc:
            self._sub = self._model.subscribe_value_changed_fn(on_value_changed_fnc)
        self._combo_model = self.Model(items, self._combo_value_changed_fnc)
        self._combo_model.select_item_by_value(default_value)

    def destroy(self):
        """Cleans up the resources used by the setting."""
        self._combo_model = None
        super().destroy()

    def _combo_value_changed_fnc(self, value: Optional["ComboBoxSetting.ValueModel"]):
        self._model.value = value.value if value else None

    @property
    def value(self):
        """Gets the current value of the combo box setting.

        Returns:
            str: The current value of the setting.
        """
        return self._convert_value_fnc(self._model.value, True) if self._convert_value_fnc else self._model.value

    @value.setter
    def value(self, value):
        """Sets the value of the combo box setting.

        Args:
            value (str): The new value to set.
        """
        val = self._convert_value_fnc(value, False) if self._convert_value_fnc else value

        if self._combo_model:
            self._combo_model.select_item_by_value(val)
        else:
            self._model.set_value(val)

    # base implementation to override
    def reset_value_to_default(self) -> None:
        """Resets the value of the setting to the default value."""
        if self._model:
            if self._combo_model:
                self._combo_model.select_item_by_value(self._default_value)
            else:
                super().reset_value_to_default()

    def build_ui(self, label_width=None, value_width=None):
        """Builds the user interface for the combo box setting.

        Args:
            label_width (int): The width of the label.
            value_width (int): The width of the value field.
        """
        tooltip = self.tooltip
        if self._combo_model:
            tooltip += f"\nDefault Value: {self._combo_model.get_item_text_by_value(self._default_value)}"
        self._control = ui.HStack(style=Styles.SETTINGS_LINE_STYLE)
        with self._control:
            ui.Label(self.label, width=label_width, tooltip=tooltip)
            ui.Spacer()
            ui.ComboBox(self._combo_model, width=value_width, alignment=ui.Alignment.RIGHT, tooltip=tooltip)


class ClashDetectionSettings:
    """A class for managing clash detection settings.

    This class provides functionalities to manage, serialize, and deserialize settings related to clash detection. It offers methods to enable or disable specific settings, reset settings to their default values, and convert settings to and from JSON format.
    """

    def __init__(self):
        """Initializes the ClashDetectionSettings object."""
        super().__init__()

        self._all_settings = ()
        self._timecodes_in_frames = False
        self._timeline_fps = 0.0

        def set_state(setting: SettingDef, enabled: bool, force_value: Any | None = None):
            """Sets the enabled state and optionally forces a value for a setting.

            Args:
                setting (SettingDef): The setting to modify
                enabled (bool): Whether to enable or disable the setting
                force_value (Any | None, optional): Value to force set. Defaults to None.
            """
            if setting:
                setting.enabled = enabled
                if force_value is not None:
                    setting.value = force_value

        def get_state(setting_id: SettingId) -> bool:
            """Gets the boolean state of a setting.

            Args:
                setting_id (SettingId): ID of the setting to check

            Returns:
                bool: The setting's boolean value if it exists and is a bool, False otherwise
            """
            setting = self._get_setting(setting_id)
            if setting and isinstance(setting.value, bool):
                return setting.value
            return False

        # {SettingId: SettingDef}
        def build_main_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_DYNAMIC,
                    BoolSetting(
                        "Dynamic",
                        "Dynamic clash detection.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DYNAMIC),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_DYNAMIC_START_TIME,
                    FloatSetting(
                        "\tStart Time on Timeline (in seconds)",
                        "Start Time on Timeline in seconds.\nOnly works when dynamic clash detection is enabled.\n"
                        "0 = timeline start time (auto-detected).",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DYNAMIC_START_TIME),
                        0.0,
                        1440.0,
                        0.1,
                        ".2f",
                        refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_DYNAMIC_END_TIME,
                    FloatSetting(
                        "\tEnd Time on Timeline (in seconds)",
                        "End Time on Timeline in seconds.\nOnly works when dynamic clash detection is enabled.\n"
                        "0 = timeline end time (auto-detected).",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DYNAMIC_END_TIME),
                        0.0,
                        1440.0,
                        0.1,
                        ".2f",
                        refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_PURGE_PERMANENT_OVERLAPS,
                    BoolSetting(
                        "\tPurge Permanent Dynamic Overlaps",
                        "Tells the system to discard pairs of dynamic objects that always overlap over the tested time interval.\n"
                        "Dynamic clash detection only.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_PURGE_PERMANENT_OVERLAPS),
                        refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_TOLERANCE,
                    FloatSetting(
                        "Tolerance",
                        "Tolerance distance for overlap queries.\n"
                        "Use zero to detect only hard clashes.\n"
                        "Use non-zero to detect both hard and soft clashes.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_TOLERANCE),
                        0.0,
                        100000000,
                        1.0,
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_STATIC_TIME,
                    FloatSetting(
                        "Static Time on Timeline (in seconds)",
                        "Time on Timeline in seconds for executing static clash detection.\n"
                        "The value is clamped into timeline range if necessary.\n"
                        "Taken into account only when performing static clash detection!",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_STATIC_TIME),
                        0.0,
                        1440.0,
                        0.1,
                        ".2f",
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_DUP_MESHES,
                    BoolSetting(
                        "Report Duplicate Meshes Only",
                        "Instructs the clash detection engine to only report meshes that completely overlap with other identical meshes.\n"
                        "Dynamic detection is not supported, only static clashes at current time on the timeline are.\n"
                        "This option is exclusive - no other clashes are reported when this option is enabled!",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DUP_MESHES),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS,
                    BoolSetting(
                        "Ignore Redundant Overlaps",
                        "Instructs the clash detection engine to ignore redundant overlaps.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_IGNORE_REDUNDANT_OVERLAPS),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        def build_multithreading_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_NEW_TASK_MANAGER,
                    BoolSetting(
                        "Use New Task Manager",
                        "Use the new task manager.\n"
                        "It manages number of spawned tasks automatically, so 'Number of Tasks' setting is ignored.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_NEW_TASK_MANAGER),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_SINGLE_THREADED)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_SINGLE_THREADED,
                    BoolSetting(
                        "Single Threaded",
                        "Run single-threaded or multi-threaded code.\nMainly for testing.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_SINGLE_THREADED),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_NB_TASKS,
                    IntSetting(
                        "Number of Tasks",
                        "Number of tasks used in multi-threaded code.\nGenerally speaking, the more the better.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_NB_TASKS),
                        0,
                        256,
                        1,
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            not get_state(SettingId.SETTING_NEW_TASK_MANAGER)
                            and not get_state(SettingId.SETTING_SINGLE_THREADED),
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        def build_advanced_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_POSE_EPSILON,
                    FloatSetting(
                        "Pose Epsilon",
                        "Epsilon value used when comparing mesh poses.\n"
                        "This is used when detecting 'duplicate meshes', i.e. meshes with the same vertex/triangle data in the same place.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_POSE_EPSILON),
                        0.0,
                        1e-3,
                        1e-6,
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_AREA_EPSILON,
                    FloatSetting(
                        "Area Epsilon",
                        "Epsilon value used to cull small triangles or slivers.\n"
                        "Triangles whose area is lower than this value are ignored. Use 0 to keep all triangles.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_AREA_EPSILON),
                        0.0,
                        1.0,
                        1e-4,
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_BOUNDS_EPSILON,
                    FloatSetting(
                        "Bounds Epsilon",
                        "Epsilon value used to enlarge mesh bounds a bit.\n"
                        "This ensures that flat bounds or bounds that are just touching are properly processed.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_BOUNDS_EPSILON),
                        0.0,
                        0.1,
                        1e-4,
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_TIGHT_BOUNDS,
                    BoolSetting(
                        "Tight Bounds",
                        "Use tight bounds for meshes.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_TIGHT_BOUNDS),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_COPLANAR,
                    BoolSetting(
                        "Coplanar",
                        "Detect collisions between coplanar triangles.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_COPLANAR),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_ANY_HIT,
                    BoolSetting(
                        "Any hit",
                        "If checked, the clash engine stops after locating the first pair of overlapping triangles; otherwise, it goes on to detect all overlaps.\n"
                        "Can provide better performance if only a quick overview of what's clashing is wanted.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_ANY_HIT),
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            not get_state(SettingId.SETTING_DUP_MESHES)
                            and not get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH),
                            False if get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH) else None,
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_QUANTIZED,
                    BoolSetting(
                        "Quantized",
                        "Quantized trees use less memory but usually give slower performance.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_QUANTIZED),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_TRIS_PER_LEAF,
                    IntSetting(
                        "Tris per leaf",
                        "Number of tris per leaf.\n"
                        "Tweak this for a memory vs. performance trade-off.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_TRIS_PER_LEAF),
                        2,
                        15,
                        1,
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_TRIANGLE_LIMIT,
                    IntSetting(
                        "Triangle limit",
                        "Abort narrow-phase query after this amount of triangle pairs has been found.\n"
                        "Use 0 for unlimited.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_TRIANGLE_LIMIT),
                        0,
                        0xFFFFFFFF,
                        1,
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS,
                    BoolSetting(
                        "Purge Permanent Static Overlaps",
                        "Tells the system to discard pairs of static objects that always overlap over the tested time interval.\n"
                        "Dynamic clash detection only.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_PURGE_PERMANENT_STATIC_OVERLAPS),
                        refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_USE_USDRT,
                    BoolSetting(
                        "Use USDRT",
                        "When enabled, provides faster initial stage traversal for full-scene queries only.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_USE_USDRT),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_IGNORE_INVISIBLE_PRIMS,
                    BoolSetting(
                        "Ignore Invisible Prims",
                        "Instructs the clash detection engine to ignore invisible primitives.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_IGNORE_INVISIBLE_PRIMS),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        def build_depth_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH,
                    BoolSetting(
                        "Compute Max Local Depth",
                        "Enable max local depth computation.\n"
                        "Helps with identification of contact cases between objects.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_DEPTH_EPSILON,
                    FloatSetting(
                        "Depth Epsilon",
                        "Epsilon value used to classify hard clashes vs contact cases.\n"
                        "Clashes whose max local depth is below the epsilon are ignored.\n"
                        "Use a negative value to keep all (hard) clashes.\n"
                        "This setting does not apply to soft clashes.\n",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DEPTH_EPSILON),
                        -100000000,
                        100000000,
                        0.1,
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH)
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_CONTACT_CUTOFF,
                    FloatSetting(
                        "Contact Cutoff",
                        "Max local depth computation early-exits as soon as it is above the cutoff (optimization).\n"
                        "Use a negative value to disable this..",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_CONTACT_CUTOFF),
                        -100000000,
                        100000000,
                        0.1,
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH)
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_DISCARD_TOUCHING_CONTACTS,
                    BoolSetting(
                        "Discard Touching Contacts",
                        "Instructs the clash detection engine to not report found touching contacts.\n"
                        "The Depth Epsilon must be set to a positive number.\n"
                        "Any values between 0 and that epsilon are considered as touching contacts.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_DISCARD_TOUCHING_CONTACTS),
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH)
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_MAX_LOCAL_DEPTH_MODE,
                    ComboBoxSetting(
                        "Depth Computation Mode",
                        "Max local depth computation mode.\n"
                        "- Legacy (fastest).\n"
                        "- Medium (medium accuracy).\n"
                        "- High (highest accuracy).",
                        items=[
                            ("Legacy", 0),
                            ("Medium", 1),
                            ("High", 2)
                        ],
                        default_value=ClashDetection.get_default_setting_value(SettingId.SETTING_MAX_LOCAL_DEPTH_MODE),
                        refresh_state_fnc=lambda s: set_state(
                            s,
                            get_state(SettingId.SETTING_COMPUTE_MAX_LOCAL_DEPTH)
                        ),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        def build_debug_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_LOGGING,
                    BoolSetting(
                        "Log info in Console",
                        "Log info & perf results to console.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_LOGGING),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
                (
                    SettingId.SETTING_OVERLAP_CODE,
                    ComboBoxSetting(
                        "Overlap Code",
                        "Choose the triangle-triangle overlap code.",
                        items=[
                            ("Regular", 0),
                            ("Altern1", 1),
                            ("Altern2", 2),
                            ("Altern3", 3),
                        ],
                        default_value=ClashDetection.get_default_setting_value(SettingId.SETTING_OVERLAP_CODE),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        def build_hidden_settings_dict() -> OrderedDict[SettingId, SettingDef]:
            return OrderedDict([
                (
                    SettingId.SETTING_FILTER_TEST,
                    BoolSetting(
                        "Filter Test",
                        "Experimental filtering.\nIgnore pairs whose meshes have a direct similar sub-component.",
                        ClashDetection.get_default_setting_value(SettingId.SETTING_FILTER_TEST),
                        refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DUP_MESHES)),
                        on_value_changed_fnc=lambda _: self.refresh_settings_states(),
                    ),
                ),
            ])

        self._main_settings_seconds = build_main_settings_dict()
        self._multithreading_settings = build_multithreading_settings_dict()
        self._advanced_settings = build_advanced_settings_dict()
        self._depth_settings = build_depth_settings_dict()
        self._debug_settings = build_debug_settings_dict()
        self._hidden_settings = build_hidden_settings_dict()

        # create special props for frames editing instead of seconds
        def convert_value_to_frames_and_back(value, retrieve: bool):
            if self._timeline_fps > 0.0:
                if retrieve:
                    return float(value / self._timeline_fps)
                else:
                    return int(value * self._timeline_fps)
            else:
                return 0.0

        self._main_settings_frames = self._main_settings_seconds.copy()
        self._main_settings_frames[SettingId.SETTING_DYNAMIC_START_TIME] = IntSetting(
            "\tStart Time on Timeline (in frames)",
            "Start Time on Timeline in frames.\nOnly works when dynamic clash detection is enabled.\n"
            "0 = timeline start time (auto-detected).",
            int(ClashDetection.get_default_setting_value(SettingId.SETTING_DYNAMIC_START_TIME) * self._timeline_fps),
            0,
            100000000,
            1,
            refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
            convert_value_fnc=lambda v, r: convert_value_to_frames_and_back(v, r),
            on_value_changed_fnc=lambda _: self.refresh_settings_states(),
        )
        self._main_settings_frames[SettingId.SETTING_DYNAMIC_END_TIME] = IntSetting(
            "\tEnd Time on Timeline (in frames)",
            "End Time on Timeline in frames.\nOnly works when dynamic clash detection is enabled.\n"
            "0 = timeline end time (auto-detected).",
            int(ClashDetection.get_default_setting_value(SettingId.SETTING_DYNAMIC_END_TIME) * self._timeline_fps),
            0,
            100000000,
            1,
            refresh_state_fnc=lambda s: set_state(s, get_state(SettingId.SETTING_DYNAMIC)),
            convert_value_fnc=lambda v, r: convert_value_to_frames_and_back(v, r),
            on_value_changed_fnc=lambda _: self.refresh_settings_states(),
        )
        self._main_settings_frames[SettingId.SETTING_STATIC_TIME] = IntSetting(
            "Static Time on Timeline (in frames)",
            "Time on Timeline in frames for executing static clash detection.\n"
            "The value is clamped into timeline range if necessary.\n"
            "Taken into account only when performing static clash detection!",
            int(ClashDetection.get_default_setting_value(SettingId.SETTING_STATIC_TIME) * self._timeline_fps),
            0,
            100000000,
            1,
            refresh_state_fnc=lambda s: set_state(s, not get_state(SettingId.SETTING_DYNAMIC)),
            convert_value_fnc=lambda v, r: convert_value_to_frames_and_back(v, r),
            on_value_changed_fnc=lambda _: self.refresh_settings_states(),
        )

        self.set_timecodes_in_frames(self._timecodes_in_frames, True)

    def set_timecodes_in_frames(self, timecodes_in_frames = True, force: bool = False):
        if not force and self._timecodes_in_frames == timecodes_in_frames:
            return
        self._timecodes_in_frames = timecodes_in_frames
        stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
        self._timeline_fps = stage.GetTimeCodesPerSecond() if stage else 0.0
        self._all_settings = (
            self._main_settings_frames if self._timecodes_in_frames else self._main_settings_seconds,
            self._advanced_settings,
            self._depth_settings,
            self._multithreading_settings,
            self._debug_settings,
            self._hidden_settings,
        )

    def destroy(self):
        """Cleans up all resources and settings."""
        def destroy_settings_group(settings_group: OrderedDict[SettingId, SettingDef]):
            if settings_group is not None:
                for setting in settings_group.values():
                    setting.destroy()
                settings_group.clear()
        destroy_settings_group(self._main_settings_seconds)
        destroy_settings_group(self._main_settings_frames)
        destroy_settings_group(self._advanced_settings)
        destroy_settings_group(self._depth_settings)
        destroy_settings_group(self._multithreading_settings)
        destroy_settings_group(self._debug_settings)
        destroy_settings_group(self._hidden_settings)
        self._all_settings = None

    def _get_setting(self, setting_id) -> Optional[SettingDef]:
        """Returns SettingDef for provided SettingId. Returns None if not found."""
        if not self._all_settings:
            return None
        for settings in self._all_settings:
            if settings:
                s = settings.get(setting_id)
                if s is not None:
                    return s
        return None

    @property
    def main_settings(self):
        """Gets the main settings.

        Returns:
            OrderedDict: The main settings dictionary.
        """
        return self._main_settings_frames if self._timecodes_in_frames else self._main_settings_seconds

    @property
    def advanced_settings(self):
        """Gets the advanced settings.

        Returns:
            OrderedDict: The advanced settings dictionary.
        """
        return self._advanced_settings

    @property
    def depth_settings(self):
        """Gets the depth settings.

        Returns:
            OrderedDict: The depth settings dictionary.
        """
        return self._depth_settings

    @property
    def multithreading_settings(self):
        """Gets the multithreading settings.

        Returns:
            OrderedDict: The multithreading settings dictionary.
        """
        return self._multithreading_settings

    @property
    def debug_settings(self):
        """Gets the debug settings.

        Returns:
            OrderedDict: The debug settings dictionary.
        """
        return self._debug_settings

    @property
    def hidden_settings(self):
        """Gets the hidden settings.

        Returns:
            OrderedDict: The hidden settings dictionary.
        """
        return self._hidden_settings

    @property
    def all_settings(self):
        """Gets all settings.

        Returns:
            tuple: A tuple containing all settings dictionaries.
        """
        return self._all_settings if self._all_settings is not None else ()

    def refresh_settings_states(self):
        """Refreshes all settings. Calls refresh_state_fnc (if set) on each SettingDefs."""
        if self._all_settings:
            for settings_group in self._all_settings:
                if settings_group:
                    for setting in settings_group.values():
                        setting.refresh_state()

    def reset_settings_to_default(self):
        """Resets all settings to their default values."""
        if self._all_settings:
            for settings_group in self._all_settings:
                if settings_group:
                    for setting in settings_group.values():
                        setting.reset_value_to_default()

    def get_setting_value(self, setting_id) -> Any:
        """Retrieves the value of a specific setting.

        Args:
            setting_id (SettingId): The ID of the setting.

        Returns:
            Any: The value of the setting.
        """
        setting = self._get_setting(setting_id)
        return setting.value if setting is not None else None

    def set_setting_value(self, setting_id, value) -> bool:
        """Sets the value of a specific setting.

        Args:
            setting_id (SettingId): The ID of the setting.
            value (Any): The new value for the setting.

        Returns:
            bool: True if the value was set successfully, otherwise False.
        """
        setting = self._get_setting(setting_id)
        if setting is not None:
            setting.value = value
            return True
        return False

    def enable_setting(self, setting_id, enable) -> bool:
        """Enables or disables a specific setting.

        Args:
            setting_id (SettingId): The ID of the setting.
            enable (bool): Whether to enable or disable the setting.

        Returns:
            bool: True if the setting was enabled/disabled successfully, otherwise False.
        """
        setting = self._get_setting(setting_id)
        if setting:
            setting.enabled = enable
            return True
        return False

    def convert_values_to_dict(self) -> Dict[str, Any]:
        """Converts all settings values to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary of setting values.
        """
        if not self._all_settings:
            return dict()
        d = {k.name: v.value for settings in self._all_settings if settings is not None for k, v in settings.items()}
        return d

    def load_values_from_dict(self, d: Dict[str, Any]) -> bool:
        """Loads settings values from a dictionary.

        Args:
            d (Dict[str, Any]): Dictionary containing settings values.

        Returns:
            bool: True if all values were loaded successfully, otherwise False.
        """
        success = True
        for key, value in d.items():
            try:
                setting_id = SettingId[key]
            except KeyError:
                carb.log_error(f"Failed to deserialize setting ({key}: {value}). Key does not exist in SettingId.")
                success = False
            except Exception as e:
                carb.log_error(f"Failed to deserialize setting ({key}: {value}). {e}")
                success = False

            if not self.set_setting_value(setting_id, value):
                carb.log_error(f"Failed to deserialize setting ({key}: {value})")
                success = False

        return success

    def serialize_to_str(self) -> str:
        """Serializes setting values to a JSON string.

        Returns:
            str: The serialized JSON string.
        """
        return json.dumps(self.convert_values_to_dict())

    def deserialize_from_str(self, json_string: str) -> bool:
        """Deserializes settings values from a JSON string.

        Args:
            json_string (str): The JSON string containing settings values.

        Returns:
            bool: True if deserialization was successful, otherwise False.
        """
        if len(json_string) == 0:
            return False
        try:
            deserialized_json = json.loads(json_string)
            return self.load_values_from_dict(deserialized_json)
        except Exception as e:
            carb.log_error(f"Settings: deserialize from json string exception '{e}' occurred.")
            return False

    def serialize_to_file(self, file_name) -> bool:
        """Serializes setting values to a JSON file.

        Args:
            file_name (str): The name of the file to serialize to.

        Returns:
            bool: True if serialization was successful, otherwise False.
        """
        with open(file_name, "w") as json_file:
            try:
                json.dump(self.convert_values_to_dict(), json_file)
            except Exception as e:
                carb.log_error(f"Settings: serialize to file exception '{e}' occurred.")
                return False
        return True

    def deserialize_from_file(self, file_name) -> bool:
        """Deserializes setting values from a JSON file.

        Args:
            file_name (str): The name of the file to deserialize from.

        Returns:
            bool: True if deserialization was successful, otherwise False.
        """
        with open(file_name, "r") as json_file:
            try:
                deserialized_json = json.load(json_file)
                return self.load_values_from_dict(deserialized_json)
            except Exception as e:
                carb.log_error(f"Settings: deserialize from json file exception '{e}' occurred.")
                return False


class ClashDetectionSettingsUI:
    """
    Provides a user interface for configuring clash detection settings.

    This class includes static methods to build and display a user interface for manipulating
    settings related to clash detection. The interface allows for toggling settings and adjusting values
    through various UI elements.
    """

    @staticmethod
    def build_ui(target_frame, settings: ClashDetectionSettings, editable: bool = True):
        """Builds the UI for Clash Detection Settings.

        Args:
            target_frame (ui.Frame): The target frame for the UI components.
            settings (ClashDetectionSettings): The clash detection settings instance.
            editable (bool): Indicates if the UI is editable.
        """
        if target_frame is None:
            return

        target_frame.set_style(Styles.SETTINGS_WND_STYLE)

        def build_header(title, clicked_fn):
            with ui.ZStack(height=0):
                ui.Rectangle(style_type_name_override="Titlebar.Background")
                with ui.VStack():
                    ui.Spacer(height=3)
                    with ui.HStack():
                        ui.Spacer(width=10)
                        ui.Label(title, style_type_name_override="Titlebar.Title")
                        ui.Spacer()
                        ui.Button(
                            "Reset all" if clicked_fn else " ",
                            style_type_name_override="Titlebar.Reset",
                            width=15,
                            clicked_fn=clicked_fn,
                            enabled=editable,
                        )
                    ui.Spacer(height=3)

        def build_section(name, build_func):
            ui.Spacer(height=3)
            col_frame = ui.CollapsableFrame(name, height=0)
            with col_frame:
                with ui.HStack():
                    ui.Spacer(width=20)
                    with ui.VStack(enabled=editable):
                        build_func()
            return col_frame

        label_width = 160
        value_width = 80

        def build_main_section():
            if settings.main_settings:
                for setting in settings.main_settings.values():
                    setting.build_ui(label_width, value_width)

        def build_advanced_section():
            if settings.advanced_settings:
                for setting in settings.advanced_settings.values():
                    setting.build_ui(label_width, value_width)

        def build_multithreading_section():
            if settings.multithreading_settings:
                for setting in settings.multithreading_settings.values():
                    setting.build_ui(label_width, value_width)

        def build_depth_section():
            if settings.depth_settings:
                for setting in settings.depth_settings.values():
                    setting.build_ui(label_width, value_width)

        def build_debug_section():
            if settings.debug_settings:
                for setting in settings.debug_settings.values():
                    setting.build_ui(label_width, value_width)

        with target_frame:
            with ui.VStack():
                build_header("Options", settings.reset_settings_to_default)
                build_section("Main", build_main_section)
                build_section("Advanced", build_advanced_section)
                build_section("Local Depth (EXPERIMENTAL)", build_depth_section)
                build_section("Multi-threading", build_multithreading_section)
                debug_frame = build_section("Debugging", build_debug_section)
                debug_frame.collapsed = True

        settings.refresh_settings_states()


class ClashDetectionSettingsWindow(ui.Window):
    """A window for configuring clash detection settings.

    This class provides a user interface for modifying clash detection settings, allowing the user to interactively enable or disable specific settings, adjust numerical values, and reset to defaults.

    Args:
        settings (ClashDetectionSettings): An instance of ClashDetectionSettings containing the initial settings to be displayed and modified in the window.
    """

    def __init__(self, settings: ClashDetectionSettings):
        """Initializes the ClashDetectionSettingsWindow instance."""
        super().__init__(
            "Clash Detection Settings",
            visible=False,
            auto_resize=True,
            flags=(
                ui.WINDOW_FLAGS_NO_TITLE_BAR
                | ui.WINDOW_FLAGS_POPUP
                | ui.WINDOW_FLAGS_NO_SAVED_SETTINGS
                | ui.WINDOW_FLAGS_NO_COLLAPSE
            ),
        )
        self._settings = settings

    def destroy(self):
        """Destroys the settings window and cleans up resources."""
        if self._settings:
            self._settings.destroy()
            self._settings = None

    def show(self, x, y, editable: bool = True):
        """Shows the settings window at the specified position.

        Args:
            x (int): The x-coordinate for the window position.
            y (int): The y-coordinate for the window position.
            editable (bool): Whether the settings are editable.
        """
        self.build_ui(editable)
        self.position_x, self.position_y = x, y
        self.visible = True
        self.focus()

    def hide(self):
        """Hides the settings window."""
        self.visible = False

    def build_ui(self, editable: bool = True):
        """Builds the user interface for the settings window.

        Args:
            editable (bool): Whether the settings are editable.
        """
        if not self._settings:
            return
        ClashDetectionSettingsUI.build_ui(self.frame, self._settings, editable)
