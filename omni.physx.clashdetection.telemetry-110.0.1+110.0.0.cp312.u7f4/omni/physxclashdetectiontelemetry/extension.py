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
import carb.settings
import carb
from .clash_telemetry import ClashTelemetry

SETTING_CLASH_DETECTION_TELEMETRY_ENABLED = "/persistent/clashDetection/enableTelemetry"

try:
    from omni.physx.scripts.utils import safe_import_tests
    safe_import_tests("omni.physxclashdetectiontelemetry.tests")
except:
    pass


class ClashDetectionTelemetryExtension(omni.ext.IExt):

    def __init__(self) -> None:
        super().__init__()

    def on_startup(self, ext_id) -> None:
        # Read whatever persistent setting is set and store it in a class attribute
        _settings = carb.settings.get_settings()
        ClashTelemetry.telemetry_is_enabled = _settings.get_as_bool(SETTING_CLASH_DETECTION_TELEMETRY_ENABLED)

    def on_shutdown(self) -> None:
        pass
