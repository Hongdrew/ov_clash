===========
usd_utils
===========

.. module:: omni.physxclashdetectioncore.usd_utils

This module provides utility functions for working with USD prims and transformations.

Functions
=========

.. function:: get_prim_children_paths(prim: Usd.Prim, exclude_invisible: bool = True, prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None) -> List[Sdf.Path]

   Returns paths of all children of the given prim, optionally filtered by a custom predicate and visibility.

   This function traverses the prim hierarchy starting from the given prim and returns paths to all child prims
   that match the specified filtering criteria. The traversal also handles instance proxies.

   Inactive prims are always excluded from the results. If exclude_invisible is True, prims with visibility=invisible
   and all their descendants will be excluded.

   :param prim: The root prim to start traversal from.
   :type prim: Usd.Prim
   :param exclude_invisible: If True, excludes prims with visibility=invisible and their descendants. Defaults to True.
   :type exclude_invisible: bool
   :param prim_accept_fn: Optional predicate function that takes a Usd.Prim and returns True if the prim should be included. Defaults to None.
   :type prim_accept_fn: Optional[Callable[[Usd.Prim], bool]]
   :return: List of paths to child prims that match the filtering criteria.
   :rtype: List[Sdf.Path]


.. function:: get_list_of_prim_paths(stage: Usd.Stage, prim_str_path: str, add_prim_children: bool = False, prim_accept_fn: Optional[Callable[[Usd.Prim], bool]] = None) -> List[Sdf.Path]

   Returns list of prim paths for a given prim or collection.

   Can optionally include child prims but not for collections.

   :param stage: The stage containing the prims.
   :type stage: Usd.Stage
   :param prim_str_path: The path to the prim or collection.
   :type prim_str_path: str
   :param add_prim_children: If True, includes paths of all child prims that match prim_accept_fn. Defaults to False.
   :type add_prim_children: bool
   :param prim_accept_fn: Optional predicate function that takes a Usd.Prim and returns True if the prim should be included. Defaults to None.
   :type prim_accept_fn: Optional[Callable[[Usd.Prim], bool]]
   :return: List of prim paths. For a prim input, returns either just the prim path or paths of all matching child prims. For a collection input, returns paths of all prims in the collection. Returns empty list if prim/collection not found or on error.
   :rtype: List[Sdf.Path]


.. function:: matrix_to_list(matrix: Gf.Matrix4d) -> List[float]

   Converts a Gf.Matrix4d to a flat list of 16 floats in row-major order.

   :param matrix: The 4x4 matrix to convert.
   :type matrix: Gf.Matrix4d
   :return: The matrix elements as a flat list in row-major order.
   :rtype: List[float]


.. function:: list_to_matrix(lst: List[float]) -> Optional[Gf.Matrix4d]

   Converts a flat list of 16 floats in row-major order to a Gf.Matrix4d.

   :param lst: The list of 16 floats to convert.
   :type lst: List[float]
   :return: The resulting Gf.Matrix4d or None if input is invalid.
   :rtype: Optional[Gf.Matrix4d]


.. function:: serialize_matrix_to_json(matrix: Gf.Matrix4d) -> str

   Creates json string out of matrix.

   :param matrix: The matrix to serialize into a JSON string.
   :type matrix: Gf.Matrix4d
   :return: The JSON string representation of the matrix.
   :rtype: str


.. function:: deserialize_matrix_from_json(json_string: str) -> Optional[Gf.Matrix4d]

   Creates matrix out of json string. Returns None in case of failure.

   :param json_string: The JSON string to deserialize into a matrix.
   :type json_string: str
   :return: The deserialized matrix or None if failed.
   :rtype: Optional[Gf.Matrix4d]


.. function:: get_prim_matrix(stage: Usd.Stage, prim_path: str, time: Optional[float] = None) -> Optional[Gf.Matrix4d]

   Returns world transformation of a prim on 'prim_path' or None in case of failure.

   If 'time' is None then Usd.TimeCode.Default() is used.

   :param stage: The stage containing the prim.
   :type stage: Usd.Stage
   :param prim_path: The path to the prim.
   :type prim_path: str
   :param time: The time of the transformation in seconds. Defaults to Usd.TimeCode.Default().
   :type time: Optional[float]
   :return: The world transformation matrix or None if failed.
   :rtype: Optional[Gf.Matrix4d]


Example
=======

Working with USD utilities:

.. code-block:: python

   from omni.physxclashdetectioncore.usd_utils import (
       get_list_of_prim_paths,
       get_prim_matrix,
       matrix_to_list,
       list_to_matrix
   )
   from pxr import Usd

   # Open stage
   stage = Usd.Stage.Open("/path/to/stage.usd")

   # Get all prim paths under /World
   prim_paths = get_list_of_prim_paths(
       stage,
       "/World",
       add_prim_children=True
   )

   # Get transformation matrix for a prim at time 1.0 seconds
   matrix = get_prim_matrix(stage, "/World/Cube", time=1.0)

   if matrix:
       # Convert to list
       matrix_list = matrix_to_list(matrix)
       print(f"Matrix as list: {matrix_list}")

       # Convert back to matrix
       restored_matrix = list_to_matrix(matrix_list)

