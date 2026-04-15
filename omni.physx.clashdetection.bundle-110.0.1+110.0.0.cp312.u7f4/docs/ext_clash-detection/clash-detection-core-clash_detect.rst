================
clash_detect
================

.. module:: omni.physxclashdetectioncore.clash_detect

This module provides the main clash detection functionality for USD stages.

Classes
=======

ClashDetection
--------------

.. class:: ClashDetection()

   A class for handling clash detection operations within a USD stage.

   This class provides methods for initializing and managing clash detection pipelines,
   setting configurations, processing overlaps, and handling clash data. It interfaces
   with the underlying clash detection API to perform these operations effectively.

   **Class Constants:**

   .. attribute:: DEFAULT_SETTINGS
      :type: Dict[SettingId, Any]

      Default settings for the clash detection engine. All existing settings have default values set here.

   **Methods:**

   .. method:: __init__()

      Initializes the ClashDetection class.

      Creates a new clash detection context and initializes telemetry tracking.

   .. method:: destroy() -> None

      Releases resources held by the clash detection context and API.

      This method cleans up the clash detection API and context, freeing any allocated resources.
      After calling this method, the instance will no longer be usable for clash detection operations.

   .. method:: reset() -> None

      Resets the clash detection context to its initial state.

      This method clears any existing clash detection results and settings, returning the context
      to its default state while maintaining the API connection. Use this to start fresh without
      destroying the instance.

   .. method:: get_default_setting_value(setting_id: SettingId) -> Any
      :classmethod:

      Returns the default (recommended default) value for a setting. If the setting is not found, returns None.

      :param setting_id: The setting ID.
      :type setting_id: SettingId
      :return: The default value for the setting. Returns None if the setting is not found.
      :rtype: Any

   .. method:: set_settings(settings: Dict[str, Any], stage: Optional[Usd.Stage] = None) -> bool

      Sets the settings for the clash detection.

      Settings which are not provided in the dictionary are left unchanged.

      :param settings: The clash detection settings.
      :type settings: Dict[str, Any]
      :param stage: The USD stage. Defaults to None.
      :type stage: Optional[Usd.Stage]
      :return: True if settings were applied successfully, False otherwise.
      :rtype: bool

   .. method:: get_list_of_prims_int_paths(stage: Usd.Stage, prim_str_path: str, add_prim_children: bool = False, prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None) -> Tuple[List[Sdf.Path], List[int]]
      :classmethod:

      Gets a list of prims in both Sdf.Path and integer path form.

      .. note::
         The returned Sdf.Path objects must be kept alive while using the integer paths,
         as the integer paths are derived from them.

      :param stage: The USD stage.
      :type stage: Usd.Stage
      :param prim_str_path: The path to the prim or collection. Can contain multiple paths separated by spaces.
      :type prim_str_path: str
      :param add_prim_children: If True, includes paths of all child prims that match prim_accept_fn. Defaults to False.
      :type add_prim_children: bool
      :param prim_accept_fn: Optional predicate function that takes a Usd.Prim and returns True if the prim should be included. Defaults to None.
      :type prim_accept_fn: Optional[Callable[[Usd.Prim], bool]]
      :return: A tuple containing list of Sdf.Path objects and list of integer path representations.
      :rtype: Tuple[List[Sdf.Path], List[int]]

   .. method:: set_scope(stage: Usd.Stage, obj_a: str, obj_b: str, merge_scopes: bool = False) -> bool

      Sets the scope for clash detection.

      - If both obj_a and obj_b are empty -> process full scene.
      - If only the obj_a list contains items -> limit processing only to obj_a items.
      - If obj_a and obj_b lists contain items -> process obj_a against obj_b.

      obj_a and obj_b can both contain multiple paths separated by spaces.

      :param stage: The USD stage.
      :type stage: Usd.Stage
      :param obj_a: Object A. Can contain multiple paths separated by space/tab/newline.
      :type obj_a: str
      :param obj_b: Object B. Can contain multiple paths separated by space/tab/newline.
      :type obj_b: str
      :param merge_scopes: if True, then scopes are merged into one. Makes sense for detection of duplicates.
      :type merge_scopes: bool
      :return: True if scope was set successfully, False otherwise.
      :rtype: bool

   .. method:: create_pipeline() -> int

      Creates and initializes the clash detection pipeline.

      This method sets up the pipeline for clash detection processing, records the start time,
      and captures initial memory state. The pipeline must be created before running any steps.

      :return: The number of pipeline steps that need to be executed. Returns 0 if the clash detection API is not initialized.
      :rtype: int

   .. method:: get_pipeline_step_data(index: int) -> Any

      Gets metadata about a specific pipeline step.

      Retrieves information about a pipeline step including its progress percentage and description.
      Can be called before or after executing the step.

      :param index: The index of the pipeline step to get data for.
      :type index: int
      :return: A data object containing progress (float 0.0-1.0) and name (str). Returns None if API not initialized.
      :rtype: Any

   .. method:: run_pipeline_step(index: int) -> None

      Executes a single step in the clash detection pipeline.

      This method processes one step of the clash detection algorithm. The pipeline must be created first
      by calling create_pipeline(). Steps must be executed sequentially starting from index 0.

      :param index: Zero-based index of the pipeline step to execute.
      :type index: int

   .. method:: get_async_pipeline_step_data(cookie: Any) -> Any

      Gets data for the current step in an asynchronous clash detection pipeline.

      :param cookie: Cookie obtained from run_async_pipeline() that identifies the pipeline instance.
      :type cookie: Any
      :return: A data object containing progress (float) and name (str). Returns None if API not initialized.
      :rtype: Any

   .. method:: run_async_pipeline() -> Any

      Starts asynchronous execution of the clash detection pipeline.

      Launches the clash detection process to run asynchronously in the background. The pipeline will
      execute all steps in separate threads without blocking the main thread.

      :return: A cookie identifying this async pipeline instance. Returns None if API not initialized.
      :rtype: Any

   .. method:: is_async_pipeline_running(cookie: Any) -> bool

      Checks if an asynchronous clash detection pipeline is still executing.

      :param cookie: Cookie obtained from run_async_pipeline().
      :type cookie: Any
      :return: True if pipeline is still running, False if completed or API not initialized.
      :rtype: bool

   .. method:: finish_async_pipeline(cookie: Any) -> bool

      Cleans up resources used by an asynchronous clash detection pipeline.

      This is a blocking call that waits for the pipeline to finish before cleaning up resources.

      :param cookie: Cookie identifying the async pipeline instance to finish.
      :type cookie: Any
      :return: True if cleanup was successful, False otherwise.
      :rtype: bool

   .. method:: cancel_async_pipeline(cookie: Any) -> None

      Cancels an asynchronous clash detection pipeline.

      Signals the pipeline to stop processing but does not clean up resources.
      finish_async_pipeline() must still be called after cancellation.

      :param cookie: Cookie identifying the pipeline instance to cancel.
      :type cookie: Any

   .. method:: compute_max_local_depth(mesh_path0: Sdf.Path, matrix0: Gf.Matrix4d, mesh_path1: Sdf.Path, matrix1: Gf.Matrix4d, clash_query: ClashQuery) -> float

      Computes the maximum local penetration depth between two meshes with given transforms.

      :param mesh_path0: USD path to the first mesh.
      :type mesh_path0: Sdf.Path
      :param matrix0: Transformation matrix for the first mesh.
      :type matrix0: Gf.Matrix4d
      :param mesh_path1: USD path to the second mesh.
      :type mesh_path1: Sdf.Path
      :param matrix1: Transformation matrix for the second mesh.
      :type matrix1: Gf.Matrix4d
      :param clash_query: ClashQuery object containing clash detection settings.
      :type clash_query: ClashQuery
      :return: The maximum local penetration depth. Returns 0.0 if API not initialized.
      :rtype: float

   .. method:: compute_penetration_depth(mesh_path0: Sdf.Path, matrix0: Gf.Matrix4d, mesh_path1: Sdf.Path, matrix1: Gf.Matrix4d, clash_query: ClashQuery, dir: Tuple[float, float, float]) -> Any

      Compute the penetration depth (amount and direction) necessary to resolve overlap between two meshes.

      :param mesh_path0: USD path of the first mesh.
      :type mesh_path0: Sdf.Path
      :param matrix0: Local-to-world transformation for the first mesh.
      :type matrix0: Gf.Matrix4d
      :param mesh_path1: USD path of the second mesh.
      :type mesh_path1: Sdf.Path
      :param matrix1: Local-to-world transformation for the second mesh.
      :type matrix1: Gf.Matrix4d
      :param clash_query: ClashQuery that provides the relevant clash detection settings.
      :type clash_query: ClashQuery
      :param dir: The penetration depth direction vector (x, y, z).
      :type dir: Tuple[float, float, float]
      :return: An object containing depth (float) and dir (Tuple[float, float, float]). Returns None if API not initialized.
      :rtype: Any

   .. method:: get_overlap_data(overlap_index: int, frame_index: int) -> OverlapData

      Gets detailed data about a specific overlap at a given frame.

      :param overlap_index: Index identifying the specific overlap to query.
      :type overlap_index: int
      :param frame_index: Frame number at which to get the overlap data.
      :type frame_index: int
      :return: Object containing detailed overlap information.
      :rtype: OverlapData

   .. method:: get_overlap_report(overlap_index: int, frame_index: int, mesh_index: MeshIndex, flags: int) -> Dict[str, Any]

      Generates a detailed report about a specific overlap's geometry.

      :param overlap_index: Index identifying the specific overlap to analyze.
      :type overlap_index: int
      :param frame_index: Frame number at which to analyze the overlap.
      :type frame_index: int
      :param mesh_index: Which mesh in the overlap pair to analyze.
      :type mesh_index: MeshIndex
      :param flags: Bit flags controlling which data to include in the report.
      :type flags: int
      :return: Report containing usd_faces (warp array) and collision_outline (warp array).
      :rtype: Dict[str, Any]

   .. method:: get_overlap_report2(overlap_index: int, frame_index: int, flags: int) -> Dict[str, Any]

      Generates a detailed report about a specific overlap's geometry for both meshes involved.

      This method queries the clash detection API for detailed information about an overlap at a given time/frame,
      returning the face indices for both meshes of the overlap, as well as the outline of the collision region.
      The results are converted into warp arrays for further processing and analysis.

      :param overlap_index: Index identifying the specific overlap to analyze.
      :type overlap_index: int
      :param frame_index: Frame number at which to analyze the overlap.
      :type frame_index: int
      :param flags: Bit flags controlling which data to include in the report (see OverlapReportFlag).
      :type flags: int
      :return: Report containing:
          - 'usd_faces0': Warp array of face indices for the first mesh in the overlap.
          - 'usd_faces1': Warp array of face indices for the second mesh in the overlap.
          - 'collision_outline': Warp array of outline vertices for the collision region.
          Returns an empty dict if the clash detection API is not initialized.
      :rtype: Dict[str, Any]

      .. note::

         The difference between :meth:`get_overlap_report` and :meth:`get_overlap_report2` is that
         :meth:`get_overlap_report` only returns face indices for a single mesh (specified by ``mesh_index``)
         and the collision outline, whereas :meth:`get_overlap_report2` returns face indices
         for both meshes (``usd_faces0``, ``usd_faces1``) as well as the collision outline,
         and does not require a mesh index argument.

   .. method:: process_overlap_generator(idx: int, existing_overlaps: Dict[str, ClashInfo], query_identifier: int, setting_tolerance: float, setting_depth_epsilon: float, yield_progress_range: Tuple[float, float] = (0.0, 1.0)) -> Generator[float, None, ClashInfo]

      Processes a detected overlap, updating or creating a ClashInfo object as necessary.

      Returns a generator that yields progress and finally returns ClashInfo.

      :param idx: The index of the overlap to process.
      :type idx: int
      :param existing_overlaps: Dictionary of existing clash info objects, keyed by clash hash.
      :type existing_overlaps: Dict[str, ClashInfo]
      :param query_identifier: Unique identifier for the clash detection query.
      :type query_identifier: int
      :param setting_tolerance: Distance tolerance value for determining soft clashes.
      :type setting_tolerance: float
      :param setting_depth_epsilon: Minimum collision depth to consider for clash detection.
      :type setting_depth_epsilon: float
      :param yield_progress_range: Range of progress values to yield, as (min, max). Defaults to (0.0, 1.0).
      :type yield_progress_range: Tuple[float, float]
      :return: Generator yielding progress values, returns ClashInfo when complete.
      :rtype: Generator[float, None, ClashInfo]

   .. method:: process_overlap(stage: Usd.Stage, idx: int, existing_overlaps: Dict[str, ClashInfo], query_identifier: int, setting_tolerance: float, setting_depth_epsilon: float) -> ClashInfo

      Processes a detected overlap, updating or creating a ClashInfo object as necessary.

      :param stage: The USD stage containing the overlapping prims.
      :type stage: Usd.Stage
      :param idx: The index of the overlap to process.
      :type idx: int
      :param existing_overlaps: Dictionary of existing clash info objects.
      :type existing_overlaps: Dict[str, ClashInfo]
      :param query_identifier: Unique identifier for the clash detection query.
      :type query_identifier: int
      :param setting_tolerance: Distance tolerance value for determining soft clashes.
      :type setting_tolerance: float
      :param setting_depth_epsilon: Minimum collision depth to consider.
      :type setting_depth_epsilon: float
      :return: A ClashInfo object representing the processed overlap.
      :rtype: ClashInfo

   .. method:: process_duplicate(stage: Usd.Stage, idx: int, existing_overlaps: Dict[str, ClashInfo], query_identifier: int) -> ClashInfo

      Processes a detected duplicate overlap.

      Duplicate overlap is an overlap between identical meshes with identical transformations fully overlapping each other.

      :param stage: The USD stage containing the overlapping meshes.
      :type stage: Usd.Stage
      :param idx: Index of the duplicate overlap to process.
      :type idx: int
      :param existing_overlaps: Dictionary of existing clash info objects.
      :type existing_overlaps: Dict[str, ClashInfo]
      :param query_identifier: Unique identifier for the current clash detection query.
      :type query_identifier: int
      :return: Updated or newly created clash info object.
      :rtype: ClashInfo

   .. method:: fetch_and_save_overlaps(stage: Usd.Stage, clash_data: ClashData, clash_query: ClashQuery) -> Iterator[float]

      Fetches and saves overlaps from clash detection, yielding progress updates.

      :param stage: The USD stage containing the meshes to check for clashes.
      :type stage: Usd.Stage
      :param clash_data: Container for storing and managing clash information.
      :type clash_data: ClashData
      :param clash_query: Query parameters and settings for clash detection.
      :type clash_query: ClashQuery
      :return: A generator yielding progress values between 0.0 and 1.0. Returns -1 on error.
      :rtype: Iterator[float]

   **Properties:**

   .. attribute:: clash_detect_api
      :type: Any

      Gets the low-level clash detection API interface.

   .. attribute:: clash_detect_context
      :type: Any

      Gets the clash detection context handle.

   .. attribute:: is_out_of_memory
      :type: bool

      Checks if the clash detection engine encountered memory exhaustion.

   .. method:: get_nb_overlaps() -> int

      Gets the total number of geometric overlaps detected.

      :return: The total number of overlaps found, or 0 if no clashes detected or API not initialized.
      :rtype: int

   .. method:: get_nb_duplicates() -> int

      Gets the number of duplicate meshes detected.

      :return: The number of duplicate meshes found, or 0 if none detected or API not initialized.
      :rtype: int


Example
=======

Basic clash detection workflow:

.. code-block:: python

   from omni.physxclashdetectioncore.clash_detect import ClashDetection
   from omni.physxclashdetectioncore.clash_detect_settings import SettingId
   from pxr import Usd

   # Initialize clash detection
   clash_detect = ClashDetection()

   # Configure settings
   settings = {
       SettingId.SETTING_TOLERANCE.name: 0.0,  # Hard clashes
       SettingId.SETTING_DYNAMIC.name: False,   # Static detection
       SettingId.SETTING_LOGGING.name: True     # Enable logging
   }

   # Open stage
   stage = Usd.Stage.Open("/path/to/stage.usd")

   # Apply settings
   clash_detect.set_settings(settings, stage)

   # Set scope (full scene)
   clash_detect.set_scope(stage, "", "")

   # Run pipeline
   num_steps = clash_detect.create_pipeline()
   for i in range(num_steps):
       clash_detect.run_pipeline_step(i)

   # Get results
   num_overlaps = clash_detect.get_nb_overlaps()
   print(f"Found {num_overlaps} overlaps")

