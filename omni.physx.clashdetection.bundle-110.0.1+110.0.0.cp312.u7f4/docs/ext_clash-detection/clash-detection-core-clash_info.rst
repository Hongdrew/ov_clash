==============
clash_info
==============

.. module:: omni.physxclashdetectioncore.clash_info

This module provides data structures for storing clash detection information.

Enumerations
============

OverlapType
-----------

.. class:: OverlapType

   An enumeration representing the various overlap types.

   **Values:**

   .. attribute:: NORMAL

      Normal overlap between meshes.

   .. attribute:: DUPLICATE

      Completely overlapping with another identical mesh with identical transformation matrix.


ClashState
----------

.. class:: ClashState

   An enumeration representing the various states a clash can be in.

   **Values:**

   .. attribute:: NEW

      Newly detected clash.

   .. attribute:: APPROVED

      Clash has been approved/acknowledged.

   .. attribute:: RESOLVED

      Clash has been resolved.

   .. attribute:: CLOSED

      Clash has been closed.

   .. attribute:: INVALID

      Clash is marked as invalid.

   .. attribute:: ACTIVE

      Clash is currently active.


Classes
=======

ClashFrameInfo
--------------

.. class:: ClashFrameInfo(timecode: float = 0.0, min_distance: float = 0.0, max_local_depth: float = -1.0, overlap_tris: int = 0, usd_faces_0: Optional[wp.array] = None, usd_faces_1: Optional[wp.array] = None, collision_outline: Optional[wp.array] = None, object_0_matrix: Optional[Gf.Matrix4d] = None, object_1_matrix: Optional[Gf.Matrix4d] = None, device: str = "cpu")

   A class for storing information about a specific frame in a clash detection sequence.

   This class contains details about a particular frame, including the timecode, minimum distance between objects,
   maximum local depth of a contact, number of overlapping triangles, the faces involved in the clash,
   collision outline, and world matrices of both objects.

   :param timecode: The timecode in seconds of the frame at which the clash occurs. Defaults to 0.0.
   :type timecode: float
   :param min_distance: The minimum distance between clashing objects. 0=Hard clash, otherwise soft clash. Defaults to 0.0.
   :type min_distance: float
   :param max_local_depth: The maximum depth of the local space of the clashing objects. -1 means no depth check. Defaults to -1.0.
   :type max_local_depth: float
   :param overlap_tris: The number of overlapping triangles at this frame. Defaults to 0.
   :type overlap_tris: int
   :param usd_faces_0: The face indices from the first object involved in the clash. Must have dtype=wp.uint32. Defaults to None.
   :type usd_faces_0: Optional[wp.array]
   :param usd_faces_1: The face indices from the second object involved in the clash. Must have dtype=wp.uint32. Defaults to None.
   :type usd_faces_1: Optional[wp.array]
   :param collision_outline: Sequence of 3D points forming the collision outline. Must have dtype=wp.float32. Defaults to None.
   :type collision_outline: Optional[wp.array]
   :param object_0_matrix: World transformation matrix of the first object at this frame. Defaults to None.
   :type object_0_matrix: Optional[Gf.Matrix4d]
   :param object_1_matrix: World transformation matrix of the second object at this frame. Defaults to None.
   :type object_1_matrix: Optional[Gf.Matrix4d]
   :param device: Target device for warp arrays. Can be "cpu" or "cuda:0" etc. Defaults to "cpu".
   :type device: str

   **Class Constants:**

   .. attribute:: VERSION
      :type: int
      :value: 6

      Version of the ClashFrameInfo data structure.

   .. attribute:: EPSILON
      :type: float
      :value: 1e-6

      Epsilon value for floating point comparisons.

   **Methods:**

   .. method:: serialize_to_dict() -> Dict[str, Any]

      Converts the ClashFrameInfo instance to a dictionary in JSON-serializable format.

      :return: Dictionary containing the serialized ClashFrameInfo data.
      :rtype: Dict[str, Any]

   .. method:: deserialize_from_dict(data: Dict[str, Any]) -> ClashFrameInfo | None
      :classmethod:

      Deserializes a ClashFrameInfo instance from a JSON-serializable dictionary format.

      :param data: Dictionary containing serialized ClashFrameInfo data.
      :type data: Dict[str, Any]
      :return: New ClashFrameInfo instance if deserialization succeeds, None if it fails.
      :rtype: ClashFrameInfo | None

   .. method:: check_object_0_matrix_changed(mtx: Gf.Matrix4d) -> bool

      Determines whether the matrix of the first object is different from the provided matrix.

      :param mtx: The matrix to compare against the object's stored matrix.
      :type mtx: Gf.Matrix4d
      :return: Returns True if the object's matrix differs; otherwise, False.
      :rtype: bool

   .. method:: check_object_1_matrix_changed(mtx: Gf.Matrix4d) -> bool

      Determines whether the matrix of the second object is different from the provided matrix.

      :param mtx: The matrix to compare against the object's stored matrix.
      :type mtx: Gf.Matrix4d
      :return: Returns True if the object's matrix differs; otherwise, False.
      :rtype: bool

   **Properties:**

   .. attribute:: timecode
      :type: float

      Read-only property that returns the timecode (time in seconds) of the frame where the clash was detected.

   .. attribute:: min_distance
      :type: float

      Gets the minimal distance between clashing objects.

   .. attribute:: max_local_depth
      :type: float

      Gets or sets the maximum local depth between clashing objects.

   .. attribute:: penetration_depth_px
      :type: float

      Gets or sets the penetration depth in the +X direction (1.0, 0.0, 0.0).

   .. attribute:: penetration_depth_nx
      :type: float

      Gets or sets the penetration depth in the -X direction (-1.0, 0.0, 0.0).

   .. attribute:: penetration_depth_py
      :type: float

      Gets or sets the penetration depth in the +Y direction (0.0, 1.0, 0.0).

   .. attribute:: penetration_depth_ny
      :type: float

      Gets or sets the penetration depth in the -Y direction (0.0, -1.0, 0.0).

   .. attribute:: penetration_depth_pz
      :type: float

      Gets or sets the penetration depth in the +Z direction (0.0, 0.0, 1.0).

   .. attribute:: penetration_depth_nz
      :type: float

      Gets or sets the penetration depth in the -Z direction (0.0, 0.0, -1.0).

   .. attribute:: overlap_tris
      :type: int

      Read-only property that returns the number of overlapping triangles detected in this frame.

   .. attribute:: usd_faces_0
      :type: wp.array

      Read-only property that returns the indices of the faces from the first object involved in the clash.

   .. attribute:: usd_faces_1
      :type: wp.array

      Read-only property that returns the indices of the faces from the second object involved in the clash.

   .. attribute:: collision_outline
      :type: wp.array

      Read-only property that returns the collision outline as a flat list of floats representing segments.

   .. attribute:: object_0_matrix
      :type: Optional[Gf.Matrix4d]

      Gets the world transformation matrix of the first object at the timecode of the clash.

   .. attribute:: object_1_matrix
      :type: Optional[Gf.Matrix4d]

      Gets the world transformation matrix of the second object at the timecode of the clash.


ClashInfo
---------

.. class:: ClashInfo(identifier: int = -1, query_id: int = 0, overlap_id: str = "", overlap_type: OverlapType = OverlapType.NORMAL, present: bool = True, min_distance: float = 0.0, max_local_depth: float = 0.0, depth_epsilon: float = -1.0, tolerance: float = 0.0, object_a_path: str = "", object_a_mesh_crc: str = "", object_b_path: str = "", object_b_mesh_crc: str = "", start_time: float = 0.0, end_time: float = 0.0, num_records: int = 0, overlap_tris: int = 0, state: ClashState = ClashState.NEW, priority: int = 0, person_in_charge: str = "", creation_timestamp: Optional[datetime] = None, last_modified_timestamp: Optional[datetime] = None, last_modified_by: str = "", comment: str = "", clash_frame_info_items: Optional[Sequence[ClashFrameInfo]] = None)

   A class for managing and storing information about object clashes.

   This class encapsulates details about object clashes such as their identifiers,
   overlap information, object paths, matrices, timestamps, and other metadata
   relevant to clash detection and management.

   **Class Constants:**

   .. attribute:: VERSION
      :type: int
      :value: 16

      Version of the ClashInfo data structure.

   .. attribute:: EPSILON
      :type: float
      :value: 1e-6

      Epsilon value for floating point comparisons.

   **Methods:**

   .. method:: serialize_to_dict() -> Dict[str, Any]

      Converts the ClashInfo instance to a dictionary in JSON-serializable format.

      :return: Dictionary containing the serialized ClashInfo data.
      :rtype: Dict[str, Any]

   .. method:: deserialize_from_dict(data: Dict[str, Any], reset_identifier: bool = False) -> ClashInfo | None
      :classmethod:

      Deserializes a ClashInfo instance from a JSON-serializable dictionary format.

      :param data: Dictionary containing serialized ClashInfo data.
      :type data: Dict[str, Any]
      :param reset_identifier: If True, resets the identifier to -1 after deserialization. Defaults to False.
      :type reset_identifier: bool
      :return: New ClashInfo instance populated with the deserialized data. Returns None if deserialization fails.
      :rtype: ClashInfo | None

   .. method:: get_frame_info_index_by_timecode(timecode: float) -> int

      Finds the index of the frame info closest to the given timecode.

      :param timecode: The target timecode to search for.
      :type timecode: float
      :return: Index of the closest frame info.
      :rtype: int

   .. method:: check_object_a_matrix_changed(stage: Usd.Stage, frame_info_index: int = 0) -> bool

      Checks whether the matrix of object A at a given frame in the specified stage is different from the stored matrix.

      :param stage: The stage containing the object.
      :type stage: Usd.Stage
      :param frame_info_index: ClashFrameInfo index. Defaults to 0.
      :type frame_info_index: int
      :return: Returns True if the object's matrix differs; otherwise, False.
      :rtype: bool

   .. method:: check_object_b_matrix_changed(stage: Usd.Stage, frame_info_index: int = 0) -> bool

      Checks whether the matrix of object B at a given frame in the specified stage is different from the stored matrix.

      :param stage: The stage containing the object.
      :type stage: Usd.Stage
      :param frame_info_index: ClashFrameInfo index. Defaults to 0.
      :type frame_info_index: int
      :return: Returns True if the object's matrix differs; otherwise, False.
      :rtype: bool

   .. method:: update_last_modified_timestamp() -> None

      Updates the last modified timestamp to the current datetime.

   .. method:: get_clash_frame_info(index) -> ClashFrameInfo | None

      Retrieves the clash frame info at the specified index.

      :param index: The index of the clash frame info to retrieve.
      :type index: int
      :return: The clash frame info at the specified index or None if not found.
      :rtype: ClashFrameInfo | None

   .. method:: get_last_clash_frame_info() -> ClashFrameInfo | None

      Retrieves the last clash frame info.

      :return: The last clash frame info or None if not found.
      :rtype: ClashFrameInfo | None

   **Properties:**

   .. attribute:: identifier
      :type: int

      Gets the unique identifier of the clash. -1 means not yet assigned.

   .. attribute:: query_id
      :type: int

      Gets the originating clash set query ID.

   .. attribute:: overlap_id
      :type: str

      Gets the overlap ID of the clash (128-bit hash as hex string).

   .. attribute:: overlap_type
      :type: OverlapType

      Gets the overlapping type of the clash.

   .. attribute:: is_contact
      :type: bool

      Gets whether the clash is a contact.

   .. attribute:: is_hard_clash
      :type: bool

      Gets whether the clash is a hard clash.

   .. attribute:: is_soft_clash
      :type: bool

      Gets whether the clash is a soft clash.

   .. attribute:: is_duplicate
      :type: bool

      Gets whether the clash is a duplicate (fully overlapping identical meshes).

   .. attribute:: present
      :type: bool

      Gets the presence status of the clash in the stage during the last run.

   .. attribute:: min_distance
      :type: float

      Gets the minimal distance between clashing objects.

   .. attribute:: max_local_depth
      :type: float

      Gets or sets the maximum local depth between clashing objects.

   .. attribute:: depth_epsilon
      :type: float

      Gets the depth epsilon of the clash used to classify hard clashes vs contact cases.

   .. attribute:: penetration_depth_px
      :type: float

      Gets or sets the penetration depth in the +X direction.

   .. attribute:: penetration_depth_nx
      :type: float

      Gets or sets the penetration depth in the -X direction.

   .. attribute:: penetration_depth_py
      :type: float

      Gets or sets the penetration depth in the +Y direction.

   .. attribute:: penetration_depth_ny
      :type: float

      Gets or sets the penetration depth in the -Y direction.

   .. attribute:: penetration_depth_pz
      :type: float

      Gets or sets the penetration depth in the +Z direction.

   .. attribute:: penetration_depth_nz
      :type: float

      Gets or sets the penetration depth in the -Z direction.

   .. attribute:: tolerance
      :type: float

      Gets the overlapping tolerance of the clash.

   .. attribute:: object_a_path
      :type: str

      Gets the path to object A.

   .. attribute:: object_a_mesh_crc
      :type: str

      Gets CRC checksum representing the mesh of the first object at the time of the clash.

   .. attribute:: object_b_path
      :type: str

      Gets the path to object B.

   .. attribute:: object_b_mesh_crc
      :type: str

      Gets CRC checksum representing the mesh of the second object at the time of the clash.

   .. attribute:: start_time
      :type: float

      Gets the start time of the clash in the scene's timeline.

   .. attribute:: end_time
      :type: float

      Gets the end time of the clash in the scene's timeline.

   .. attribute:: num_records
      :type: int

      Gets the number of records or instances where this clash was detected.

   .. attribute:: overlap_tris
      :type: int

      Gets the number of overlapping triangles.

   .. attribute:: state
      :type: ClashState

      Gets or sets the state of the clash.

   .. attribute:: priority
      :type: int

      Gets or sets the priority of the clash.

   .. attribute:: person_in_charge
      :type: str

      Gets or sets the name of the person responsible for addressing this clash.

   .. attribute:: creation_timestamp
      :type: datetime

      Gets the timestamp when the clash was first detected and recorded.

   .. attribute:: last_modified_timestamp
      :type: datetime

      Gets or sets the timestamp of the last modification made to this clash record.

   .. attribute:: last_modified_by
      :type: str

      Gets the name of the user who last modified this clash record.

   .. attribute:: comment
      :type: str

      Gets or sets a comment or note associated with the clash.

   .. attribute:: clash_frame_info_items
      :type: Optional[Sequence[ClashFrameInfo]]

      Gets or sets the clash frame info items representing detailed information about each frame.

