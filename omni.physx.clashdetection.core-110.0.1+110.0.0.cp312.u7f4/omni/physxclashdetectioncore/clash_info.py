# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Sequence, Optional, Dict, Any
import warp as wp
import numpy as np
from enum import IntEnum, auto
from datetime import datetime
import bisect
from pxr import Gf, Usd
from .utils import get_current_user_name, obj_to_dict, dict_to_obj, to_json_str_safe, from_json_str_safe
from .usd_utils import get_prim_matrix, serialize_matrix_to_json, deserialize_matrix_from_json


class OverlapType(IntEnum):
    """An enumeration.

    This enumeration represents the various overlap types.
    """

    NORMAL = auto()  # normal overlap
    DUPLICATE = auto()  # completely overlapping with another identical mesh with identical transformation matrix


class ClashState(IntEnum):
    """An enumeration.

    This enumeration represents the various states a clash can be in, such as new, active, approved, resolved, closed, or invalid.
    """

    NEW = auto()
    APPROVED = auto()
    RESOLVED = auto()
    CLOSED = auto()
    INVALID = auto()
    ACTIVE = auto()


class ClashFrameInfo:
    """A class for storing information about a specific frame in a clash detection sequence.

    This class contains details about a particular frame, including the timecode, minimum distance between objects,
    maximum local depth of a contact, number of overlapping triangles, the faces involved in the clash,
    collision outline, and world matrices of both objects.

    Args:
        timecode (float): The timecode in seconds of the frame at which the clash occurs.
        min_distance (float): The minimum distance between clashing objects. 0=Hard clash, otherwise soft clash.
        max_local_depth (float): The maximum depth of the local space of the clashing objects. -1 means no depth check.
        overlap_tris (int): The number of overlapping triangles at this frame.
        usd_faces_0 (wp.array): The face indices from the first object involved in the clash. Must have dtype=wp.uint32.
        usd_faces_1 (wp.array): The face indices from the second object involved in the clash. Must have dtype=wp.uint32.
        collision_outline (wp.array): Sequence of 3D points forming the collision outline. Must have dtype=wp.float32.
        object_0_matrix (Gf.Matrix4d): World transformation matrix of the first object at this frame.
        object_1_matrix (Gf.Matrix4d): World transformation matrix of the second object at this frame.
        device (str): Target device for warp arrays. Can be "cpu" or "cuda:0" etc.
    """

    VERSION = 6
    EPSILON = 1e-6

    def __init__(
        self,
        timecode: float = 0.0,
        min_distance: float = 0.0,
        max_local_depth: float = -1.0,
        overlap_tris: int = 0,
        usd_faces_0: Optional[wp.array] = None,  # wp.array(dtype=wp.uint32)
        usd_faces_1: Optional[wp.array] = None,  # wp.array(dtype=wp.uint32)
        collision_outline: Optional[wp.array] = None,  # wp.array(dtype=wp.float32)
        object_0_matrix: Optional[Gf.Matrix4d] = None,
        object_1_matrix: Optional[Gf.Matrix4d] = None,
        device: str = "cpu",  # target device for warp arrays: cpu" or "cuda:0" ...
    ) -> None:
        """Initializes a new instance of the ClashFrameInfo class."""
        self._timecode = timecode
        self._min_distance = min_distance
        self._max_local_depth = max_local_depth
        self._overlap_tris = overlap_tris
        self._usd_faces_0 = usd_faces_0 if usd_faces_0 else wp.empty(dtype=wp.uint32, device=device)
        self._usd_faces_1 = usd_faces_1 if usd_faces_1 else wp.empty(dtype=wp.uint32, device=device)
        self._collision_outline = collision_outline if collision_outline else wp.empty(dtype=wp.float32, device=device)
        self._object_0_matrix = object_0_matrix if object_0_matrix else Gf.Matrix4d()
        self._object_1_matrix = object_1_matrix if object_1_matrix else Gf.Matrix4d()
        self._penetration_depth_px: float = -1.0  # penetration depth in the +X direction (1.0, 0.0, 0.0)
        self._penetration_depth_nx: float = -1.0  # penetration depth in the -X direction (-1.0, 0.0, 0.0)
        self._penetration_depth_py: float = -1.0  # penetration depth in the +Y direction (0.0, 1.0, 0.0)
        self._penetration_depth_ny: float = -1.0  # penetration depth in the -Y direction (0.0, -1.0, 0.0)
        self._penetration_depth_pz: float = -1.0  # penetration depth in the +Z direction (0.0, 0.0, 1.0)
        self._penetration_depth_nz: float = -1.0  # penetration depth in the -Z direction (0.0, 0.0, -1.0)

    def __eq__(self, other):
        """Overrides the default equality implementation"""
        return (
            self.timecode == other.timecode
            and self.min_distance == other.min_distance
            and self.max_local_depth == other.max_local_depth
            and self.overlap_tris == other.overlap_tris
            and np.array_equal(self.usd_faces_0.numpy(), other.usd_faces_0.numpy())
            and np.array_equal(self.usd_faces_1.numpy(), other.usd_faces_1.numpy())
            and np.array_equal(self.collision_outline.numpy(), other.collision_outline.numpy())
            and self.object_0_matrix == other.object_0_matrix
            and self.object_1_matrix == other.object_1_matrix
            and self.penetration_depth_px == other.penetration_depth_px
            and self.penetration_depth_nx == other.penetration_depth_nx
            and self.penetration_depth_py == other.penetration_depth_py
            and self.penetration_depth_ny == other.penetration_depth_ny
            and self.penetration_depth_pz == other.penetration_depth_pz
            and self.penetration_depth_nz == other.penetration_depth_nz
        )

    def serialize_to_dict(self) -> Dict[str, Any]:
        """Converts the ClashFrameInfo instance to a dictionary in JSON-serializable format.

        Returns:
            Dict[str, Any]: Dictionary containing the serialized ClashFrameInfo data.
        """
        def attr_convert(attr_name: str, value: Any) -> Any:
            if isinstance(value, Gf.Matrix4d):
                return serialize_matrix_to_json(value)
            elif isinstance(value, wp.array):
                return to_json_str_safe(value.numpy().tolist())
            return value

        return obj_to_dict(self, attr_convert)

    @classmethod
    def deserialize_from_dict(cls, data: Dict[str, Any]) -> 'ClashFrameInfo | None':
        """Deserializes a ClashFrameInfo instance from a JSON-serializable dictionary format.

        Args:
            data (Dict[str, Any]): Dictionary containing serialized ClashFrameInfo data.

        Returns:
            ClashFrameInfo | None: New ClashFrameInfo instance if deserialization succeeds, None if it fails.
        """
        new_instance = cls()

        def attr_convert(attr_name: str, value: Any) -> Any:
            attr_type = type(getattr(new_instance, attr_name))
            if attr_type is wp.array:
                return wp.array(from_json_str_safe(value), dtype=wp.uint32 if 'usd_faces' in attr_name else wp.float32)
            elif attr_type is Gf.Matrix4d:
                return deserialize_matrix_from_json(value)
            return value

        if dict_to_obj(new_instance, data, attr_convert):
            return new_instance

        return None

    def check_object_0_matrix_changed(self, mtx: Gf.Matrix4d) -> bool:
        """Determines whether the matrix of the first object is different from the provided matrix.

        Args:
            mtx (Gf.Matrix4d): The matrix to compare against the object's stored matrix.

        Returns:
            bool: Returns True if the object's matrix differs; otherwise, False.
        """
        if mtx and self._object_0_matrix:
            chg = not Gf.IsClose(mtx, self._object_0_matrix, self.EPSILON)
            return chg
        return False

    def check_object_1_matrix_changed(self, mtx: Gf.Matrix4d) -> bool:
        """Determines whether the matrix of the second object is different from the provided matrix.

        Args:
            mtx (Gf.Matrix4d): The matrix to compare against the object's stored matrix.

        Returns:
            bool: Returns True if the object's matrix differs; otherwise, False.
        """
        if mtx and self._object_1_matrix:
            chg = not Gf.IsClose(mtx, self._object_1_matrix, self.EPSILON)
            return chg
        return False

    @property
    def timecode(self) -> float:
        """Read-only property that returns the timecode (time in seconds) of the frame where the clash was detected.

        Returns:
            float: The timecode value.
        """
        return self._timecode

    @property
    def min_distance(self) -> float:
        """Gets the minimal distance between clashing objects.

        Returns:
            float: The minimal distance value.
        """
        return self._min_distance

    @property
    def max_local_depth(self) -> float:
        """Gets the maximum local depth between clashing objects.

        Returns:
            float: The maximum local depth value.
        """
        return self._max_local_depth

    @max_local_depth.setter
    def max_local_depth(self, value: float):
        """Sets the maximum local depth of the frame.

        Args:
            value (float): The new maximum local depth value.
        """
        self._max_local_depth = value

    @property
    def penetration_depth_px(self) -> float:
        """Gets the penetration depth in the +X direction.

        Returns:
            float: The penetration depth in the +X direction.
        """
        return self._penetration_depth_px

    @penetration_depth_px.setter
    def penetration_depth_px(self, value: float):
        """Sets the penetration depth in the +X direction.

        Args:
            value (float): The new penetration depth in the +X direction.
        """
        self._penetration_depth_px = value

    @property
    def penetration_depth_nx(self) -> float:
        """Gets the penetration depth in the -X direction.

        Returns:
            float: The penetration depth in the -X direction.
        """
        return self._penetration_depth_nx

    @penetration_depth_nx.setter
    def penetration_depth_nx(self, value: float):
        """Sets the penetration depth in the -X direction.

        Args:
            value (float): The new penetration depth in the -X direction.
        """
        self._penetration_depth_nx = value

    @property
    def penetration_depth_py(self) -> float:
        """Gets the penetration depth in the +Y direction.

        Returns:
            float: The penetration depth in the +Y direction.
        """
        return self._penetration_depth_py

    @penetration_depth_py.setter
    def penetration_depth_py(self, value: float):
        """Sets the penetration depth in the +Y direction.

        Args:
            value (float): The new penetration depth in the +Y direction.
        """
        self._penetration_depth_py = value

    @property
    def penetration_depth_ny(self) -> float:
        """Gets the penetration depth in the -Y direction.

        Returns:
            float: The penetration depth in the -Y direction.
        """
        return self._penetration_depth_ny

    @penetration_depth_ny.setter
    def penetration_depth_ny(self, value: float):
        """Sets the penetration depth in the -Y direction.

        Args:
            value (float): The new penetration depth in the -Y direction.
        """
        self._penetration_depth_ny = value

    @property
    def penetration_depth_pz(self) -> float:
        """Gets the penetration depth in the +Z direction.

        Returns:
            float: The penetration depth in the +Z direction.
        """
        return self._penetration_depth_pz

    @penetration_depth_pz.setter
    def penetration_depth_pz(self, value: float):
        """Sets the penetration depth in the +Z direction.

        Args:
            value (float): The new penetration depth in the +Z direction.
        """
        self._penetration_depth_pz = value

    @property
    def penetration_depth_nz(self) -> float:
        """Gets the penetration depth in the -Z direction.

        Returns:
            float: The penetration depth in the -Z direction.
        """
        return self._penetration_depth_nz

    @penetration_depth_nz.setter
    def penetration_depth_nz(self, value: float):
        """Sets the penetration depth in the -Z direction.

        Args:
            value (float): The new penetration depth in the -Z direction.
        """
        self._penetration_depth_nz = value

    @property
    def overlap_tris(self) -> int:
        """Read-only property that returns the number of overlapping triangles detected in this frame.

        Returns:
            int: The number of overlapping triangles.
        """
        return self._overlap_tris

    @property
    def usd_faces_0(self) -> wp.array:  # wp.array(dtype=wp.uint32)
        """Read-only property that returns the indices of the faces from the first object involved in the clash.

        Returns:
            wp.array(dtype=wp.uint32): The warp array of USD face indices for the first object.
        """
        return self._usd_faces_0

    @property
    def usd_faces_1(self) -> wp.array:  # wp.array(dtype=wp.uint32)
        """Read-only property that returns the indices of the faces from the second object involved in the clash.

        Returns:
            wp.array(dtype=wp.uint32): The warp array of USD face indices for the second object.
        """
        return self._usd_faces_1

    @property
    def collision_outline(self) -> wp.array:  # wp.array(dtype=wp.float32)
        """Read-only property that returns the collision outline.

        This is a flat list of floats representing a sequence of couples of 3D points, each forming a segment.

        Returns:
            wp.array(dtype=wp.float32): The warp array of collision outline points.
        """
        return self._collision_outline

    @property
    def object_0_matrix(self) -> Optional[Gf.Matrix4d]:
        """Gets the world transformation matrix of the first object at the `timecode` of the clash.

        Returns:
            Optional[Gf.Matrix4d]: The world matrix of the first object at the `timecode` of the clash.
        """
        return self._object_0_matrix

    @property
    def object_1_matrix(self) -> Optional[Gf.Matrix4d]:
        """Gets the world transformation matrix of the second object at the `timecode` of the clash.

        Returns:
            Optional[Gf.Matrix4d]: The world matrix of the second object at the `timecode` of the clash.
        """
        return self._object_1_matrix


class ClashInfo:
    """A class for managing and storing information about object clashes.

    This class encapsulates details about object clashes such as their identifiers,
    overlap information, object paths, matrices, timestamps, and other metadata
    relevant to clash detection and management.

    Args:
        identifier (int): Unique identifier for the clash. -1 means not yet assigned / uninitialized.
        query_id (int): Identifier for the originating clash set query.
        overlap_id (str): 128-bit hash representing the overlap.
        overlap_type (OverlapType): Type of the overlap.
        present (bool): Indicates if the clash was present during the last run.
        min_distance (float): Minimal distance between clashing objects. 0=Hard clash, otherwise soft clash.
        max_local_depth (float): The maximum depth of the local space of the clashing objects. -1 means no depth check.
        depth_epsilon (float): The depth epsilon of the clash.
        tolerance (float): Overlapping tolerance; 0.0 means hard clashes, any value above means soft clashes.
        object_a_path (str): Prim path to a search set A.
        object_a_mesh_crc (str): 128-bit mesh checksum for object A.
        object_b_path (str): Prim path to a search set B.
        object_b_mesh_crc (str): 128-bit mesh checksum for object B.
        start_time (float): Timecode of the first clash for dynamic clashes.
        end_time (float): Timecode of the last clash for dynamic clashes.
        num_records (int): Number of clashing frames for dynamic clashes.
        overlap_tris (int): Number of overlapping triangles.
        state (ClashState): Current state of the clash (e.g., NEW, APPROVED, RESOLVED).
        priority (int): Priority level of the clash for management purposes.
        person_in_charge (str): Identifier of the person responsible for the clash.
        creation_timestamp (Optional[datetime]): Timestamp when the clash was first found.
        last_modified_timestamp (Optional[datetime]): Timestamp of the last user modification.
        last_modified_by (str): Username of the person who made the last modification.
        comment (str): User-defined comment.
        clash_frame_info_items (Optional[Sequence[ClashFrameInfo]]): Information for each clashing frame.
    """

    VERSION = 17
    EPSILON = 1e-6

    def __init__(
        self,
        identifier: int = -1,  # db unique identifier. -1 means not yet assigned / uninitialized
        query_id: int = 0,  # originating clash set query
        overlap_id: str = "",  # 128bit hash
        overlap_type: OverlapType = OverlapType.NORMAL,  # normal, duplicate
        present: bool = True,  # indicates if the clash was present in the stage during the last run. 0=no, 1=yes
        min_distance: float = 0.0,  # minimal distance between clashing objects. 0=Hard clash, otherwise soft clash
        max_local_depth: float = 0.0,  # maximum depth of the local space of the clashing objects. -1 means no depth check.
        depth_epsilon: float = -1.0,  # epsilon value used to classify hard clashes vs contact cases. Clashes whose max local depth is below the epsilon are ignored. Use a negative value to keep all clashes.
        tolerance: float = 0.0,  # overlapping tolerance. 0.0 means hard clashes, any value above means soft (=clearance) clashes
        object_a_path: str = "",  # prim path to a searchset A (USD collection is also supported)
        object_a_mesh_crc: str = "",  # 128bit mesh checksum - so we can detect modified meshes
        object_b_path: str = "",  # prim path to a searchset B (USD collection is also supported)
        object_b_mesh_crc: str = "",  # 128bit mesh checksum - so we can detect modified meshes
        start_time: float = 0.0,  # for static clashes: timecode of a clash, for dynamic clashes: timecode of the first clash
        end_time: float = 0.0,  # for static clashes: timecode of a clash, for dynamic clashes: timecode of the last clash
        num_records: int = 0,  # for static clashes: always 1, for dynamic clashes: number of clashing 'frames'
        overlap_tris: int = 0,  # for static clashes: # of overlapping tris, for dynamic clashes: max # of overlapping tris
        state: ClashState = ClashState.NEW,  # new, validated, invalid, ...
        priority: int = 0,  # priority of the clash for management purposes
        person_in_charge: str = "",  # person identifier (usually a system-wide unique username)
        creation_timestamp: Optional[datetime] = None,  # timestamp when the clash for first found
        last_modified_timestamp: Optional[datetime] = None,  # last user modification timestamp
        last_modified_by: str = "",  # system username of a person who made the last modification
        comment: str = "",  # any user-defined comment
        clash_frame_info_items: Optional[Sequence[ClashFrameInfo]] = None,  # info for each clashing frame. None indicates that it was not loaded.
    ) -> None:
        """Initializes a new instance of the ClashInfo class."""
        self._identifier = identifier
        self._query_id = query_id
        self._overlap_id = overlap_id
        self._overlap_type = overlap_type
        self._present = present
        self._min_distance = min_distance
        self._max_local_depth = max_local_depth
        self._depth_epsilon = depth_epsilon
        self._tolerance = tolerance
        self._object_a_path = object_a_path
        self._object_a_mesh_crc = object_a_mesh_crc
        self._object_b_path = object_b_path
        self._object_b_mesh_crc = object_b_mesh_crc
        self._start_time = start_time
        self._end_time = end_time
        self._num_records = num_records
        self._overlap_tris = overlap_tris
        self._state = state
        self._priority = priority
        self._person_in_charge = person_in_charge
        self._creation_timestamp = creation_timestamp if creation_timestamp is not None else datetime.now()
        self._last_modified_timestamp = last_modified_timestamp if last_modified_timestamp is not None else datetime.now()
        self._last_modified_by = last_modified_by if last_modified_by else get_current_user_name()
        self._comment = comment
        self._clash_frame_info_items = clash_frame_info_items
        self._penetration_depth_px: float = -1.0  # penetration depth in the +X direction (1.0, 0.0, 0.0)
        self._penetration_depth_nx: float = -1.0  # penetration depth in the -X direction (-1.0, 0.0, 0.0)
        self._penetration_depth_py: float = -1.0  # penetration depth in the +Y direction (0.0, 1.0, 0.0)
        self._penetration_depth_ny: float = -1.0  # penetration depth in the -Y direction (0.0, -1.0, 0.0)
        self._penetration_depth_pz: float = -1.0  # penetration depth in the +Z direction (0.0, 0.0, 1.0)
        self._penetration_depth_nz: float = -1.0  # penetration depth in the -Z direction (0.0, 0.0, -1.0)

    def serialize_to_dict(self) -> Dict[str, Any]:
        """Converts the ClashInfo instance to a dictionary in JSON-serializable format.

        Returns:
            Dict[str, Any]: Dictionary containing the serialized ClashInfo data, with all attributes
            converted to JSON-serializable format using the default obj_to_dict behavior.
        """
        def attr_convert(attr_name: str, value: Any) -> Any:
            if isinstance(value, list):
                return [item.serialize_to_dict() for item in value if hasattr(item, 'serialize_to_dict')]
            return value

        return obj_to_dict(self, attr_convert)

    @classmethod
    def deserialize_from_dict(cls, data: Dict[str, Any], reset_identifier: bool = False) -> 'ClashInfo | None':
        """Deserializes a ClashInfo instance from a JSON-serializable dictionary format.

        Args:
            data (Dict[str, Any]): Dictionary containing serialized ClashInfo data.
            reset_identifier (bool): If True, resets the identifier to -1 after deserialization.

        Returns:
            ClashInfo | None: New ClashInfo instance populated with the deserialized data.
                Returns None if deserialization fails.
        """
        new_instance = cls()

        def attr_convert(attr_name: str, value: Any) -> Any:
            if isinstance(value, list) and attr_name == '_clash_frame_info_items':
                return [ClashFrameInfo.deserialize_from_dict(item) for item in value]
            return value

        if dict_to_obj(new_instance, data, attr_convert):
            if reset_identifier:
                new_instance._identifier = -1
            return new_instance

        return None

    def get_frame_info_index_by_timecode(self, timecode: float) -> int:
        """Finds the index of the frame info closest to the given timecode.

        Args:
            timecode (float): The target timecode to search for.

        Returns:
            int: Index of the closest frame info.
        """

        def find_closest_number(arr, target):
            index_right = bisect.bisect_left(arr, target, key=lambda i: i.timecode)
            if index_right == 0:
                return 0
            if index_right == len(arr):
                return len(arr) - 1
            index_left = index_right - 1
            diff_left = abs(arr[index_left].timecode - target)
            diff_right = abs(arr[index_right].timecode - target)
            return index_left if diff_left < diff_right else index_right

        return find_closest_number(self.clash_frame_info_items, timecode)

    def check_object_a_matrix_changed(self, stage: Usd.Stage, frame_info_index: int = 0) -> bool:
        """Checks whether the matrix of object A at a given frame in the specified stage is different from the stored matrix.

        Args:
            stage (Usd.Stage): The stage containing the object.
            frame_info_index (int): ClashFrameInfo index

        Returns:
            bool: Returns True if the object's matrix differs; otherwise, False.
        """
        frame_info = self.get_clash_frame_info(frame_info_index)
        if not frame_info:
            return False
        mtx = get_prim_matrix(stage, self._object_a_path, frame_info.timecode)
        return frame_info.check_object_0_matrix_changed(mtx)

    def check_object_b_matrix_changed(self, stage: Usd.Stage, frame_info_index: int = 0) -> bool:
        """Checks whether the matrix of object B at a given frame in the specified stage is different from the stored matrix.

        Args:
            stage (Usd.Stage): The stage containing the object.
            frame_info_index (int): ClashFrameInfo index

        Returns:
            bool: Returns True if the object's matrix differs; otherwise, False.
        """
        frame_info = self.get_clash_frame_info(frame_info_index)
        if not frame_info:
            return False
        mtx = get_prim_matrix(stage, self._object_b_path, frame_info.timecode)
        return frame_info.check_object_1_matrix_changed(mtx)

    def update_last_modified_timestamp(self) -> None:
        """Updates the last modified timestamp to the current datetime."""
        self.last_modified_timestamp = datetime.now()

    def get_clash_frame_info(self, index) -> ClashFrameInfo | None:
        """Retrieves the clash frame info at the specified index.

        Args:
            index (int): The index of the clash frame info to retrieve.

        Returns:
            ClashFrameInfo | None: The clash frame info at the specified index or None if not found.
        """
        if not self._clash_frame_info_items:
            return None
        if self._num_records == 1 and len(self._clash_frame_info_items) == 0:
            return ClashFrameInfo(self._start_time, self._min_distance, self._max_local_depth, self._overlap_tris)
        if self._num_records == len(self._clash_frame_info_items):  # check if frames are fully loaded
            if 0 <= index < self._num_records:
                return self._clash_frame_info_items[index]
        return None

    def get_last_clash_frame_info(self) -> ClashFrameInfo | None:
        """Retrieves the last clash frame info.

        Returns:
            ClashFrameInfo | None: The last clash frame info or None if not found.
        """
        return self.get_clash_frame_info(self._num_records - 1)

    @property
    def identifier(self) -> int:
        """Gets the unique identifier of the clash.

        Returns:
            int: The unique identifier.
        """
        return self._identifier

    @property
    def query_id(self) -> int:
        """Gets the originating clash set query ID.

        Returns:
            int: The query ID.
        """
        return self._query_id

    @property
    def overlap_id(self) -> str:
        """Gets the overlap ID of the clash.

        Returns:
            str: The overlap ID.
        """
        return self._overlap_id

    @property
    def overlap_type(self) -> OverlapType:
        """Gets the overlapping type of the clash.

        Returns:
            OverlapType: The overlap type.
        """
        return self._overlap_type

    @property
    def is_contact(self) -> bool:
        """Gets whether the clash is a contact.

        Returns:
            bool: True if it is a contact, otherwise False.
        """
        if self._overlap_type == OverlapType.NORMAL and self.min_distance == 0.0:
            if self.depth_epsilon > 0.0:
                return self.max_local_depth <= self.depth_epsilon
            else:
                return self.max_local_depth == 0.0
        return False

    @property
    def is_hard_clash(self) -> bool:
        """Gets whether the clash is a hard clash.

        Returns:
            bool: True if it is a hard clash, otherwise False.
        """
        return (
            self._overlap_type == OverlapType.NORMAL
            and self.min_distance == 0.0
            and not self.is_contact
        )

    @property
    def is_soft_clash(self) -> bool:
        """Gets whether the clash is a soft clash.

        Returns:
            bool: True if it is a soft clash, otherwise False.
        """
        return (
            self._overlap_type == OverlapType.NORMAL
            and self.min_distance > 0.0
            and not self.is_contact
        )

    @property
    def is_duplicate(self) -> bool:
        """Gets whether the clash is a duplicate (fully overlapping identical meshes with identical transformation matrices).

        Returns:
            bool: True if it is a duplicate clash, otherwise False.
        """
        return self._overlap_type == OverlapType.DUPLICATE

    @property
    def present(self) -> bool:
        """Gets the presence status of the clash in the stage during the last run.

        Returns:
            bool: True if present, otherwise False.
        """
        return self._present

    @property
    def min_distance(self) -> float:
        """Gets the minimal distance between clashing objects.

        Returns:
            float: The minimal distance value.
        """
        return self._min_distance

    @property
    def max_local_depth(self) -> float:
        """Gets the maximum local depth between clashing objects.

        Returns:
            float: The maximum local depth value.
        """
        return self._max_local_depth

    @max_local_depth.setter
    def max_local_depth(self, value: float):
        """Sets the maximum local depth of the clash.

        Args:
            value (float): The new maximum local depth value.
        """
        self._max_local_depth = value
        self.update_last_modified_timestamp()

    @property
    def depth_epsilon(self) -> float:
        """Gets the depth epsilon of the clash.
        Epsilon value is used to classify hard clashes vs contact cases.
        Clashes whose max local depth is below the epsilon are ignored.
        Use a negative value to keep all clashes.

        Returns:
            float: The depth epsilon value.
        """
        return self._depth_epsilon

    @property
    def penetration_depth_px(self) -> float:
        """Gets the penetration depth in the +X direction.

        Returns:
            float: The penetration depth in the +X direction.
        """
        return self._penetration_depth_px

    @penetration_depth_px.setter
    def penetration_depth_px(self, value: float):
        """Sets the penetration depth in the +X direction.

        Args:
            value (float): The new penetration depth in the +X direction.
        """
        self._penetration_depth_px = value
        self.update_last_modified_timestamp()

    @property
    def penetration_depth_nx(self) -> float:
        """Gets the penetration depth in the -X direction.

        Returns:
            float: The penetration depth in the -X direction.
        """
        return self._penetration_depth_nx

    @penetration_depth_nx.setter
    def penetration_depth_nx(self, value: float):
        """Sets the penetration depth in the -X direction.

        Args:
            value (float): The new penetration depth in the -X direction.
        """
        self._penetration_depth_nx = value
        self.update_last_modified_timestamp()

    @property
    def penetration_depth_py(self) -> float:
        """Gets the penetration depth in the +Y direction.

        Returns:
            float: The penetration depth in the +Y direction.
        """
        return self._penetration_depth_py

    @penetration_depth_py.setter
    def penetration_depth_py(self, value: float):
        """Sets the penetration depth in the +Y direction.

        Args:
            value (float): The new penetration depth in the +Y direction.
        """
        self._penetration_depth_py = value
        self.update_last_modified_timestamp()

    @property
    def penetration_depth_ny(self) -> float:
        """Gets the penetration depth in the -Y direction.

        Returns:
            float: The penetration depth in the -Y direction.
        """
        return self._penetration_depth_ny

    @penetration_depth_ny.setter
    def penetration_depth_ny(self, value: float):
        """Sets the penetration depth in the -Y direction.

        Args:
            value (float): The new penetration depth in the -Y direction.
        """
        self._penetration_depth_ny = value
        self.update_last_modified_timestamp()

    @property
    def penetration_depth_pz(self) -> float:
        """Gets the penetration depth in the +Z direction.

        Returns:
            float: The penetration depth in the +Z direction.
        """
        return self._penetration_depth_pz

    @penetration_depth_pz.setter
    def penetration_depth_pz(self, value: float):
        """Sets the penetration depth in the +Z direction.

        Args:
            value (float): The new penetration depth in the +Z direction.
        """
        self._penetration_depth_pz = value
        self.update_last_modified_timestamp()

    @property
    def penetration_depth_nz(self) -> float:
        """Gets the penetration depth in the -Z direction.

        Returns:
            float: The penetration depth in the -Z direction.
        """
        return self._penetration_depth_nz

    @penetration_depth_nz.setter
    def penetration_depth_nz(self, value: float):
        """Sets the penetration depth in the -Z direction.

        Args:
            value (float): The new penetration depth in the -Z direction.
        """
        self._penetration_depth_nz = value
        self.update_last_modified_timestamp()

    @property
    def tolerance(self) -> float:
        """Gets the overlapping tolerance of the clash.

        Returns:
            float: The overlapping tolerance value.
        """
        return self._tolerance

    @property
    def object_a_path(self) -> str:
        """Gets the path to object A.

        Returns:
            str: The path to object A.
        """
        return self._object_a_path

    @property
    def object_a_mesh_crc(self) -> str:
        """Gets CRC checksum representing the mesh of the first object at the time of the clash.

        Returns:
            str: The mesh checksum for object A.
        """
        return self._object_a_mesh_crc

    @property
    def object_b_path(self) -> str:
        """Gets the path to object B.

        Returns:
            str: The path to object B.
        """
        return self._object_b_path

    @property
    def object_b_mesh_crc(self) -> str:
        """Gets CRC checksum representing the mesh of the second object at the time of the clash.

        Returns:
            str: The mesh checksum for object B.
        """
        return self._object_b_mesh_crc

    @property
    def start_time(self) -> float:
        """Gets the start time of the clash.

        The start time of the clash in the scene's timeline.

        Returns:
            float: The start time of the clash.
        """
        return self._start_time

    @property
    def end_time(self) -> float:
        """Gets the end time.

        The end time of the clash in the scene's timeline.

        Returns:
            float: The end time of the clash.
        """
        return self._end_time

    @property
    def num_records(self) -> int:
        """Gets the number of records.

        The number of records or instances where this clash was detected.

        Returns:
            int: The number of records.
        """
        return self._num_records

    @property
    def overlap_tris(self) -> int:
        """Gets the number of overlapping triangles.

        Returns:
            int: The number of overlapping triangles.
        """
        return self._overlap_tris

    @property
    def state(self) -> ClashState:
        """Gets the state of the clash.

        The current state of the clash, represented by a `ClashState` enum.

        Returns:
            ClashState: The current state of the clash.
        """
        return self._state

    @state.setter
    def state(self, value: ClashState):
        """Sets the state of the clash.

        The current state of the clash, represented by a `ClashState` enum.

        Args:
            value (ClashState): The new state of the clash.
        """
        self._state = value
        self.update_last_modified_timestamp()

    @property
    def priority(self) -> int:
        """Gets the priority of the clash.

        The priority level of the clash, used for sorting or categorization.

        Returns:
            int: The current priority of the clash.
        """
        return self._priority

    @priority.setter
    def priority(self, value: int):
        """Sets the priority of the clash.

        The priority level of the clash, used for sorting or categorization.

        Args:
            value (int): The new priority of the clash.
        """
        self._priority = value
        self.update_last_modified_timestamp()

    @property
    def person_in_charge(self) -> str:
        """Gets the person in charge.

        The name of the person responsible for addressing this clash.

        Returns:
            str: The current person in charge.
        """
        return self._person_in_charge

    @person_in_charge.setter
    def person_in_charge(self, value: str):
        """Sets the person in charge.

        The name of the person responsible for addressing this clash.

        Args:
            value (str): The new person in charge.
        """
        self._person_in_charge = value
        self.update_last_modified_timestamp()

    @property
    def creation_timestamp(self) -> datetime:
        """Gets the creation timestamp.

        The timestamp when the clash was first detected and recorded.

        Returns:
            datetime: The creation timestamp of the clash.
        """
        return self._creation_timestamp

    @property
    def last_modified_timestamp(self) -> datetime:
        """Gets the last modified timestamp.

        The timestamp of the last modification made to this clash record.

        Returns:
            datetime: The last modified timestamp of the clash.
        """
        return self._last_modified_timestamp

    @last_modified_timestamp.setter
    def last_modified_timestamp(self, value: datetime):
        """Sets the last modified timestamp.

        The timestamp of the last modification made to this clash record.

        Args:
            value (datetime): The new last modified timestamp.
        """
        self._last_modified_timestamp = value
        self._last_modified_by = get_current_user_name()

    @property
    def last_modified_by(self) -> str:
        """Gets the last modified by information.

        The name of the user who last modified this clash record.

        Returns:
            str: The username of the person who last modified the clash.
        """
        return self._last_modified_by if self._last_modified_by else ""

    @property
    def comment(self) -> str:
        """Gets the comment for the clash.

        A comment or note associated with the clash, typically used for additional information or resolution steps.

        Returns:
            str: The current comment for the clash.
        """
        return self._comment if self._comment else ""

    @comment.setter
    def comment(self, value: str):
        """Sets the comment for the clash.

        A comment or note associated with the clash, typically used for additional information or resolution steps.

        Args:
            value (str): The new comment for the clash.
        """
        self._comment = value
        self.update_last_modified_timestamp()

    @property
    def clash_frame_info_items(self) -> Optional[Sequence[ClashFrameInfo]]:
        """Gets the clash frame info items.

        A sequence of `ClashFrameInfo` objects representing detailed information about each frame in which the clash was detected.

        Returns:
            Optional[Sequence[ClashFrameInfo]]: The current clash frame info items.
        """
        return self._clash_frame_info_items

    @clash_frame_info_items.setter
    def clash_frame_info_items(self, value: Optional[Sequence[ClashFrameInfo]]):
        """Sets the clash frame info items.

        A sequence of `ClashFrameInfo` objects representing detailed information about each frame in which the clash was detected.

        Args:
            value (Optional[Sequence[ClashFrameInfo]]): The new clash frame info items.
        """
        self._clash_frame_info_items = value
