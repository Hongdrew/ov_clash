# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any
import carb
import omni.usd
from omni.physxclashdetectioncore.clash_query import ClashQuery
from omni.physxclashdetectioncore.clash_detect_settings import SettingId
from omni.physxclashdetectioncore.clash_detect import ClashDetection
from .utils import get_time_delta_str, truncate_string
from .settings import ExtensionSettings


__all__ = []


def get_clash_query_summary(clash_query: ClashQuery) -> str:
    """Gets the summary of the query.

    The summary is a string that contains the query name, the tolerance type, the static/dynamic time, and the object paths.

    Returns:
        str: The summary of the query.
    """
    def default_value(setting_id: SettingId) -> Any:
        return ClashDetection.get_default_setting_value(setting_id)

    timecodes_in_frames = carb.settings.get_settings().get_as_bool(ExtensionSettings.SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES)
    stage = omni.usd.get_context(ExtensionSettings.usd_context_name).get_stage()
    timeline_fps = stage.GetTimeCodesPerSecond() if stage else 0.0

    setting_tolerance = clash_query.clash_detect_settings.get(SettingId.SETTING_TOLERANCE.name, default_value(SettingId.SETTING_TOLERANCE))
    setting_dynamic = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC.name, default_value(SettingId.SETTING_DYNAMIC))
    setting_find_duplicates = clash_query.clash_detect_settings.get(SettingId.SETTING_DUP_MESHES.name, default_value(SettingId.SETTING_DUP_MESHES))
    if setting_find_duplicates:
        static_start_time = clash_query.clash_detect_settings.get(SettingId.SETTING_STATIC_TIME.name, default_value(SettingId.SETTING_STATIC_TIME))
        timecode_str = f"frame {int(static_start_time * timeline_fps)}" if timecodes_in_frames else f"{get_time_delta_str(static_start_time)}"
        static_dynamic = f"find duplicates at {timecode_str}"
    elif setting_dynamic:
        dyn_start_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_START_TIME.name, default_value(SettingId.SETTING_DYNAMIC_START_TIME))
        dyn_end_time = clash_query.clash_detect_settings.get(SettingId.SETTING_DYNAMIC_END_TIME.name, default_value(SettingId.SETTING_DYNAMIC_END_TIME))
        timecode_str = f"frame {int(dyn_start_time * timeline_fps)}" if timecodes_in_frames else f"{get_time_delta_str(dyn_start_time)}"
        timecode_str += f" - frame {int(dyn_end_time * timeline_fps)}" if timecodes_in_frames else f" - {get_time_delta_str(dyn_end_time)}"
        static_dynamic = f"dynamic {timecode_str}"
    else:
        static_start_time = clash_query.clash_detect_settings.get(SettingId.SETTING_STATIC_TIME.name, default_value(SettingId.SETTING_STATIC_TIME))
        timecode_str = f"frame {int(static_start_time * timeline_fps)}" if timecodes_in_frames else f"{get_time_delta_str(static_start_time)}"
        static_dynamic = f"static at {timecode_str}"
    soft_hard = (
        f"soft tolerance {setting_tolerance}"
        if setting_tolerance != 0.0 and not setting_find_duplicates
        else "hard"
    )
    searchsets = f"object A: {clash_query.object_a_path}, object B: {clash_query.object_b_path}"
    text = f"{clash_query.query_name} [{soft_hard}] [{static_dynamic}] [{searchsets}]"
    if len(clash_query.comment) > 0:
        text += " //" + truncate_string(clash_query.comment, 100)  # show only first 100 chars
    return text
