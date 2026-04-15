# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from enum import IntEnum, auto


class SettingId(IntEnum):
    """An enumeration.

    This class is an enumeration for various setting identifiers used by the clash detection process.
    IMPORTANT: make sure all existing settings have default values set in ClashDetection.DEFAULT_SETTINGS!
    """

    # Log info & perf results to console.
    SETTING_LOGGING = auto()

    # Tells the clash detection engine to run dynamic clash detection inspecting time sampled animations.
    SETTING_DYNAMIC = auto()

    # Start Time on Timeline in seconds. Works only when dynamic clash detection is enabled.
    # 0 = timeline start time (auto-detected).
    SETTING_DYNAMIC_START_TIME = auto()

    # End Time on Timeline in seconds. Works only when dynamic clash detection is enabled.
    # 0 = timeline end time (auto-detected).
    SETTING_DYNAMIC_END_TIME = auto()

    # Tells the system to discard pairs of dynamic objects that always overlap over the tested time interval.
    # Works only when dynamic clash detection is enabled.
    SETTING_PURGE_PERMANENT_OVERLAPS = auto()

    # Quantized trees use less memory but usually give slower performance.
    SETTING_QUANTIZED = auto()

    # Run single-threaded or multi-threaded code. Mainly for testing.
    SETTING_SINGLE_THREADED = auto()

    # Use new task manager implementation.
    # It manages number of spawned tasks automatically, so SETTING_NB_TASKS setting is ignored.
    SETTING_NEW_TASK_MANAGER = auto()

    # Experimental filtering. Ignore pairs whose meshes have a direct similar sub-component.
    SETTING_FILTER_TEST = auto()

    # Use tight bounds for meshes.
    SETTING_TIGHT_BOUNDS = auto()

    # Detect collisions between coplanar triangles.
    SETTING_COPLANAR = auto()

    # Number of tasks used when running multi-threaded. Generally speaking, the more the better.
    SETTING_NB_TASKS = auto()

    # Epsilon value used when comparing mesh poses.
    # This is used when detecting "duplicate meshes", i.e. meshes with the same vertex/triangle data in the same place.
    SETTING_POSE_EPSILON = auto()

    # Epsilon value used to enlarge mesh bounds a bit.
    # This ensures that flat bounds or bounds that are just touching are properly processed.
    SETTING_BOUNDS_EPSILON = auto()

    # Epsilon value used to cull small triangles or slivers.
    # Triangles whose area is lower than this value are ignored. Use 0 to keep all triangles.
    SETTING_AREA_EPSILON = auto()

    # Number of triangles per leaf. Tweak this for a memory vs. performance trade-off
    SETTING_TRIS_PER_LEAF = auto()

    # Tolerance distance for overlap queries. Use zero for hard clashes, non-zero for soft (clearance) clashes.
    SETTING_TOLERANCE = auto()

    # If checked, the clash engine stops after locating the first pair of overlapping triangles; otherwise, it goes on to detect all overlaps.
    # Can provide better performance if only a quick overview of what's clashing is wanted.
    SETTING_ANY_HIT = auto()

    # Use alternative triangle-triangle overlap code.
    SETTING_OVERLAP_CODE = auto()

    # Instructs the clash detection engine to only report meshes that completely overlap with other identical meshes.
    # Dynamic detection is not supported, only static clashes at current time on the timeline are.
    # This option is exclusive - no other clashes are reported when this option is enabled!
    SETTING_DUP_MESHES = auto()

    # Time on Timeline in seconds for executing static clash detection.
    # The value is clamped into timeline range if necessary.
    # Taken into account only when performing static clash detection!
    SETTING_STATIC_TIME = auto()

    # Helps with identification of contact cases between objects.
    SETTING_COMPUTE_MAX_LOCAL_DEPTH = auto()

    # Epsilon value used to classify hard clashes vs contact cases.
    # Clashes whose max local depth is below the epsilon are ignored.
    # Use a negative value to keep all clashes.
    SETTING_DEPTH_EPSILON = auto()

    # Instructs the clash detection engine to not report found touching contacts.
    # The Depth Epsilon must be set to a positive number and any values between 0 and that epsilon are considered as touching contacts.
    SETTING_DISCARD_TOUCHING_CONTACTS = auto()

    # Tells the system to discard pairs of static objects that always overlap over the tested time interval.
    # Works only when dynamic clash detection is enabled.
    SETTING_PURGE_PERMANENT_STATIC_OVERLAPS = auto()

    # When enabled, provides faster initial stage traversal for full-scene queries only.
    SETTING_USE_USDRT = auto()

    # Abort narrow-phase query after this amount of triangle pairs has been found.
    # Use 0 for unlimited.
    SETTING_TRIANGLE_LIMIT = auto()

    # Ignore redundant overlaps.
    SETTING_IGNORE_REDUNDANT_OVERLAPS = auto()

    # Ignore invisible prims.
    SETTING_IGNORE_INVISIBLE_PRIMS = auto()

    # Cutoff value used to compute the max local depth.  Use a negative value to disable it.
    # The cutoff value should be larger than the contact epsilon.
    # The code aborts the computation of the max local depth as soon as it is found to be larger than the cutoff value.
    SETTING_CONTACT_CUTOFF = auto()

    # Max local depth computation mode.
    # 0 - Legacy (fastest).
    # 1 - Medium (medium accuracy).
    # 2 - High (highest accuracy).
    SETTING_MAX_LOCAL_DEPTH_MODE = auto()