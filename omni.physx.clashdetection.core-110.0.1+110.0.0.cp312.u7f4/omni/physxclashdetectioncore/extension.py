# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
import omni.kit.app
from .commands import register_commands, unregister_commands
from .config import ExtensionConfig

try:
    from omni.physx.scripts.utils import safe_import_tests

    safe_import_tests("omni.physxclashdetectioncore.tests")
except:
    pass


class ClashDetectionCoreExtension(omni.ext.IExt):
    """A class for managing the lifecycle of the Clash Detection Core Extension.

    This class handles the startup and shutdown procedures for the Clash Detection Core Extension, including registering and unregistering commands necessary for its operation.

    The class inherits from `omni.ext.IExt`, following the extension protocol of the Omni framework.
    """

    def __init__(self) -> None:
        """Initializes the ClashDetectionCoreExtension instance."""
        super().__init__()

    def on_startup(self, ext_id) -> None:
        """Handles startup procedures for the extension.

        Args:
            ext_id (str): The unique identifier of the extension.
        """
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        ExtensionConfig.extension_path = ext_path
        register_commands()  # Register all clash detection Kit commands

    def on_shutdown(self) -> None:
        """Handles shutdown procedures for the extension."""
        unregister_commands()  # Unregister all clash detection Kit commands
