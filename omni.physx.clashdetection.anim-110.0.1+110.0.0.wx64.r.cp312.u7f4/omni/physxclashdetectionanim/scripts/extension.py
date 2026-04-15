# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
import carb
import carb.settings
import omni.kit.app
from .config import ExtensionConfig
from ..bindings._clashDetectionAnim import SETTINGS_LOGGING_ENABLED


try:
    from omni.physx.scripts.utils import safe_import_tests

    safe_import_tests("omni.physxclashdetectionanim.tests")
except:
    pass


class ClashDetectionAnimExtension(omni.ext.IExt):
    """A class for managing the Clash Detection Animation Extension.

    This class initializes and manages the settings for the Clash Detection Animation Extension, allowing for the enabling and disabling of debug logging based on user settings. It subscribes to setting changes and updates the configuration accordingly.
    """

    def __init__(self) -> None:
        """Initializes the ClashDetectionAnimExtension instance."""
        super().__init__()

    def on_startup(self, ext_id) -> None:
        """Handles the startup process for the extension.

        Args:
            ext_id (str): The extension identifier.
        """
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        ExtensionConfig.extension_path = ext_path

        ExtensionConfig.debug_logging = carb.settings.get_settings().get_as_bool(SETTINGS_LOGGING_ENABLED)

        self._settings_subs = []
        self._settings_subs.append(
            omni.kit.app.SettingChangeSubscription(SETTINGS_LOGGING_ENABLED, self._enable_logging_setting_changed)
        )

    def on_shutdown(self) -> None:
        """Handles the shutdown process for the extension."""
        self._settings_subs = []

    def _enable_logging_setting_changed(self, item, event_type):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            ExtensionConfig.debug_logging = carb.settings.get_settings().get_as_bool(SETTINGS_LOGGING_ENABLED)
