# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Optional
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_query import ClashQuery
from .pic_provider import PersonsInCharge
from .selection.clash_selection import ClashSelection
from .clash_viewport_bridge import ClashViewportBridge
from .clash_bake_view import ClashBakeView

__all__ = []


class ExtensionSettings:
    """A class that encapsulates the settings and global variables for the clash detection extension.

    This class provides various settings and global variables used throughout the clash detection extension,
    including UI settings, logging options, and data providers. It serves as a centralized configuration
    and state management entity for the extension, facilitating easier access and modification of settings.
    """

    # settings
    DEFAULT_SETTING_PREFIX = "/defaults"
    SETTING_CLASH_DETECTION_WINDOW = "/physics/showClashDetectionWindow"
    SETTING_CLASH_DETECT_KEY = "clashDetection"
    SETTING_RELOAD_UI = f"/{SETTING_CLASH_DETECT_KEY}/reloadUi"
    SETTING_DEBUG_LOGGING = f"/persistent/{SETTING_CLASH_DETECT_KEY}/debugLogging"
    SETTING_DEBUG_LOGGING_DEFAULT = f"/defaults/persistent/{SETTING_CLASH_DETECT_KEY}/debugLogging"
    SETTING_SHOW_FULL_PATHS = f"/persistent/{SETTING_CLASH_DETECT_KEY}/showFullPaths"
    SETTING_SHOW_FULL_PATHS_DEFAULT = f"/defaults/persistent/{SETTING_CLASH_DETECT_KEY}/showFullPaths"
    SETTING_USE_ASYNC_CLASH_PIPELINE = f"/persistent/{SETTING_CLASH_DETECT_KEY}/useAsyncClashPipeline"
    SETTING_USE_ASYNC_CLASH_PIPELINE_DEFAULT = f"/defaults/persistent/{SETTING_CLASH_DETECT_KEY}/useAsyncClashPipeline"
    SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE = f"/persistent/{SETTING_CLASH_DETECT_KEY}/clashTimelineSliderImmediateUpdate"
    SETTING_CLASH_TIMELINE_SLIDER_IMMEDIATE_UPDATE_DEFAULT = f"/defaults/persistent/{SETTING_CLASH_DETECT_KEY}/clashTimelineSliderImmediateUpdate"
    SETTING_QUERY_WINDOW_AUTOSAVE = f"/persistent/{SETTING_CLASH_DETECT_KEY}/queryWndAutoSave"
    SETTING_QUERY_WINDOW_TIMECODES_AS_FRAMES = f"/persistent/{SETTING_CLASH_DETECT_KEY}/queryWndTimecodesAsFrames"
    SETTING_GROUPS_WINDOW_SHOW_EMPTY_GROUPS = f"/persistent/{SETTING_CLASH_DETECT_KEY}/groupsWndShowEmptyGroups"
    # global vars
    debug_logging: bool = False  # printing of debugging messages into application log
    development_mode: bool = False  # enable development mode
    show_prompts: bool = True  # handy for tests to remove all prompts by setting show_prompts to False
    show_full_clash_paths = False  # show full paths of clashing objects or just last part
    clash_results_typing_search_delay: float = 0.9  # wait time (in seconds) before searching for clashes in the results table after typing
    clash_pairs_table_display_limit: int = 1000000  # maximum number of clash pairs to be displayed in the clash results table
    no_timestamp_str: str = "*** ***"  # 'no timestamp' UI representation for consistent comparison of visual tests
    ui_no_timestamps: bool = False  # no timestamps in the UI for consistent comparison during capturing visual tests
    ui_no_locale_formatting: bool = False  # no locale formatting in the UI for consistent comparison during capturing visual tests
    ignore_save_load_events = False  # enable/disable save/load stage events hook-ups handling clash data serialization
    extension_path: Optional[str] = None  # will be filled at extension startup
    clash_data: Optional[ClashData] = None  # clash data provider internally calls serializer/deserializer
    clash_query: Optional[ClashQuery] = None  # currently opened query
    clash_selection: Optional[ClashSelection] = None  # Active Selection (query and selected overlaps)
    clash_viewport: Optional[ClashViewportBridge] = None  # Bridge to the Viewport extension
    clash_bake_view: Optional[ClashBakeView] = None  # Bridge to the Bake extension
    clash_timeline_slider_immediate_update: bool = False  # enable/disable immediate update of clashing prims in the main viewport when dragging timeline slider
    use_async_clash_pipeline: bool = True  # use asynchronous clash pipeline
    users: Optional[PersonsInCharge] = None  # list of available people that user can assign clashes to
    pic_file_path: str = ""  # path to the custom PIC (person in change) json file to load users from
    usd_context_name: str = ""  # Optional USD context name. Empty string means default USD context.
