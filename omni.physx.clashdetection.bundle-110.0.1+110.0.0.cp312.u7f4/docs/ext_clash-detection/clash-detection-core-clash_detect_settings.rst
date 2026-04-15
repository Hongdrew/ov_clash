===========================
clash_detect_settings
===========================

.. module:: omni.physxclashdetectioncore.clash_detect_settings

This module defines the settings enumeration for clash detection.

Enumerations
============

SettingId
---------

.. class:: SettingId

   An enumeration for various setting identifiers used by the clash detection process.

   .. warning::
      Make sure all existing settings have default values set in ``ClashDetection.DEFAULT_SETTINGS``!

   **Values:**

   .. attribute:: SETTING_LOGGING

      Log info & perf results to console.

   .. attribute:: SETTING_DYNAMIC

      Tells the clash detection engine to run dynamic clash detection inspecting time sampled animations.

   .. attribute:: SETTING_DYNAMIC_START_TIME

      Start Time on Timeline in seconds. Works only when dynamic clash detection is enabled.
      0 = timeline start time (auto-detected).

   .. attribute:: SETTING_DYNAMIC_END_TIME

      End Time on Timeline in seconds. Works only when dynamic clash detection is enabled.
      0 = timeline end time (auto-detected).

   .. attribute:: SETTING_PURGE_PERMANENT_OVERLAPS

      Tells the system to discard pairs of dynamic objects that always overlap over the tested time interval.
      Works only when dynamic clash detection is enabled.

   .. attribute:: SETTING_QUANTIZED

      Quantized trees use less memory but usually give slower performance.

   .. attribute:: SETTING_SINGLE_THREADED

      Run single-threaded or multi-threaded code. Mainly for testing.

   .. attribute:: SETTING_NEW_TASK_MANAGER

      Use new task manager implementation.
      It manages number of spawned tasks automatically, so SETTING_NB_TASKS setting is ignored.

   .. attribute:: SETTING_FILTER_TEST

      Experimental filtering. Ignore pairs whose meshes have a direct similar sub-component.

   .. attribute:: SETTING_TIGHT_BOUNDS

      Use tight bounds for meshes.

   .. attribute:: SETTING_COPLANAR

      Detect collisions between coplanar triangles.

   .. attribute:: SETTING_NB_TASKS

      Number of tasks used when running multi-threaded. Generally speaking, the more the better.

   .. attribute:: SETTING_POSE_EPSILON

      Epsilon value used when comparing mesh poses.
      This is used when detecting "duplicate meshes", i.e. meshes with the same vertex/triangle data in the same place.

   .. attribute:: SETTING_BOUNDS_EPSILON

      Epsilon value used to enlarge mesh bounds a bit.
      This ensures that flat bounds or bounds that are just touching are properly processed.

   .. attribute:: SETTING_AREA_EPSILON

      Epsilon value used to cull small triangles or slivers.
      Triangles whose area is lower than this value are ignored. Use 0 to keep all triangles.

   .. attribute:: SETTING_TRIS_PER_LEAF

      Number of triangles per leaf. Tweak this for a memory vs. performance trade-off.

   .. attribute:: SETTING_TOLERANCE

      Tolerance distance for overlap queries. Use zero for hard clashes, non-zero for soft (clearance) clashes.

   .. attribute:: SETTING_ANY_HIT

      If checked, the clash engine stops after locating the first pair of overlapping triangles; otherwise, it goes on to detect all overlaps.
      Can provide better performance if only a quick overview of what's clashing is wanted.

   .. attribute:: SETTING_OVERLAP_CODE

      Use alternative triangle-triangle overlap code.

   .. attribute:: SETTING_DUP_MESHES

      Instructs the clash detection engine to only report meshes that completely overlap with other identical meshes.
      Dynamic detection is not supported, only static clashes at current time on the timeline are.
      This option is exclusive - no other clashes are reported when this option is enabled!

   .. attribute:: SETTING_STATIC_TIME

      Time on Timeline in seconds for executing static clash detection.
      The value is clamped into timeline range if necessary.
      Taken into account only when performing static clash detection!

   .. attribute:: SETTING_COMPUTE_MAX_LOCAL_DEPTH

      Helps with identification of contact cases between objects.

   .. attribute:: SETTING_DEPTH_EPSILON

      Epsilon value used to classify hard clashes vs contact cases.
      Clashes whose max local depth is below the epsilon are ignored.
      Use a negative value to keep all clashes.

   .. attribute:: SETTING_DISCARD_TOUCHING_CONTACTS

      Instructs the clash detection engine to not report found touching contacts.
      The Depth Epsilon must be set to a positive number and any values between 0 and that epsilon are considered as touching contacts.

   .. attribute:: SETTING_PURGE_PERMANENT_STATIC_OVERLAPS

      Tells the system to discard pairs of static objects that always overlap over the tested time interval.
      Works only when dynamic clash detection is enabled.

   .. attribute:: SETTING_USE_USDRT

      When enabled, provides faster initial stage traversal for full-scene queries only.

   .. attribute:: SETTING_TRIANGLE_LIMIT

      Abort narrow-phase query after this amount of triangle pairs has been found.
      Use 0 for unlimited.

   .. attribute:: SETTING_IGNORE_REDUNDANT_OVERLAPS

      Ignore redundant overlaps.

   .. attribute:: SETTING_IGNORE_INVISIBLE_PRIMS

      Ignore invisible prims.

   .. attribute:: SETTING_CONTACT_CUTOFF

      Cutoff value used to compute the max local depth. Use a negative value to disable it.
      The cutoff value should be larger than the contact epsilon.
      The code aborts the computation of the max local depth as soon as it is found to be larger than the cutoff value.

   .. attribute:: SETTING_MAX_LOCAL_DEPTH_MODE

      Max local depth computation mode.

      - 0 - Legacy (fastest).
      - 1 - Medium (medium accuracy).
      - 2 - High (highest accuracy).

