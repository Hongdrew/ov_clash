# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.kit.test import AsyncTestCase
from pxr import Usd, UsdGeom, Sdf, Gf
from omni.physxclashdetectioncore.usd_utils import (
    get_prim_children_paths,
    get_list_of_prim_paths,
    serialize_matrix_to_json,
    deserialize_matrix_from_json,
    matrix_to_list,
    list_to_matrix,
    get_prim_matrix,
)

try:
    from omni.physxtests import utils
    omni_physxtests_utils_available = True
except:
    omni_physxtests_utils_available = False
print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")


class TestUsdUtils(AsyncTestCase):
    def setUp(self):
        # Create a stage and root prim
        self._stage = Usd.Stage.CreateInMemory()
        self._root = self._stage.DefinePrim("/root", "Xform")

        # Create test prims with different types and properties
        self._mesh = self._stage.DefinePrim("/root/mesh", "Mesh")
        UsdGeom.Cube.Define(self._stage, "/root/boundable")
        self._xform = self._stage.DefinePrim("/root/xform", "Xform")

        # Create invisible prim
        invisible = self._stage.DefinePrim("/root/invisible", "Mesh")
        UsdGeom.Imageable(invisible).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)

        # Create nested prims
        self._stage.DefinePrim("/root/xform/nested_mesh", "Mesh")
        self._stage.DefinePrim("/root/invisible/nested_mesh", "Mesh")

        # Create a collection on root
        collection = Usd.CollectionAPI.Apply(self._stage.GetPrimAtPath("/root"), "test_collection")
        collection.CreateIncludesRel().AddTarget("/root/mesh")
        collection.CreateIncludesRel().AddTarget("/root/boundable")

    def test_get_prim_children_paths(self):

        def is_geom(p: Usd.Prim) -> bool:
            return p.IsA(UsdGeom.Mesh) or p.IsA(UsdGeom.Boundable)
        # Test getting all children without filtering
        children = get_prim_children_paths(self._root, exclude_invisible=False)
        self.assertEqual(len(children), 7)  # All prims including invisible and nested

        # Test filtering to only geometry prims
        children = get_prim_children_paths(self._root, exclude_invisible=False, prim_accept_fn=is_geom)
        self.assertEqual(len(children), 5)  # Only Mesh and Boundable prims
        # Verify types
        boundable_count = sum(1 for path in children if self._stage.GetPrimAtPath(path).IsA(UsdGeom.Boundable))
        self.assertEqual(boundable_count, 5)  # Only one boundable (the cube) should exist

        mesh_count = sum(1 for path in children if self._stage.GetPrimAtPath(path).IsA(UsdGeom.Mesh))
        self.assertEqual(mesh_count, 4)  # Four meshes total (mesh, nested mesh, invisible, nested invisible)

        # Test excluding invisible prims and their children
        children = get_prim_children_paths(self._root, exclude_invisible=True, prim_accept_fn=is_geom)
        self.assertEqual(len(children), 3)  # Visible Mesh and Boundable prims only

        # Verify no invisible prims
        for path in children:
            visibility = UsdGeom.Imageable(self._stage.GetPrimAtPath(path)).GetVisibilityAttr().Get()
            self.assertNotEqual(visibility, UsdGeom.Tokens.invisible)

        # Test that inactive prims are always excluded
        self._mesh.SetActive(False)
        children = get_prim_children_paths(self._root, exclude_invisible=False, prim_accept_fn=is_geom)
        self.assertEqual(len(children), 4)  # One less than before (inactive mesh excluded)
        self.assertNotIn(self._mesh.GetPrimPath(), children)  # Verify inactive prim is not included
        self._mesh.SetActive(True)

    def test_get_list_of_prim_paths(self):

        def is_geom(p: Usd.Prim) -> bool:
            return p.IsA(UsdGeom.Mesh) or p.IsA(UsdGeom.Boundable)

        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "Invalid stage supplied!",
                    "Invalid prim path 'invalid//path' supplied!",
                    "No prim or collection on path '/nonexistent'. Exception: ",  # we need partial match for this line
                ],
                partial_string_match=True
            ):
                # Test with invalid stage
                paths = get_list_of_prim_paths(None, "/root")
                self.assertEqual(len(paths), 0)

                # Test with invalid path
                paths = get_list_of_prim_paths(self._stage, "invalid//path")
                self.assertEqual(len(paths), 0)

                # Test with non-existent but valid path
                paths = get_list_of_prim_paths(self._stage, "/nonexistent")
                self.assertEqual(len(paths), 0)

        # Test with non-existent collection
        paths = get_list_of_prim_paths(self._stage, "/Root/Utils.collection:StationCollectionInvalid")
        self.assertEqual(len(paths), 0)

        # Test with collection
        paths = get_list_of_prim_paths(self._stage, "/root.collection:test_collection")
        self.assertEqual(len(paths), 2)  # Should contain mesh and boundable
        self.assertTrue(Sdf.Path("/root/mesh") in paths)
        self.assertTrue(Sdf.Path("/root/boundable") in paths)

        # Test with empty path
        paths = get_list_of_prim_paths(self._stage, "")
        self.assertEqual(len(paths), 0)

        # Test with valid prim path and is_geom filter
        paths = get_list_of_prim_paths(self._stage, "/root", True, is_geom)
        self.assertEqual(len(paths), 3)  # Should return same number as get_prim_children with only_geom=True
        self.assertTrue(all(isinstance(path, Sdf.Path) for path in paths))

        # Test with not only_geom
        paths = get_list_of_prim_paths(self._stage, "/root", True)
        self.assertEqual(len(paths), 5)  # Should return all children exludin invisible and inactive

    def test_matrix_json_serialization(self):
        # Test valid matrix serialization/deserialization
        matrix = Gf.Matrix4d((
            (1.0, 2.0, 3.0, 4.0),
            (5.0, 6.0, 7.0, 8.0),
            (9.0, 10.0, 11.0, 12.0),
            (13.0, 14.0, 15.0, 16.0)
        ))

        json_str = serialize_matrix_to_json(matrix)
        deserialized = deserialize_matrix_from_json(json_str)
        self.assertTrue(Gf.IsClose(matrix, deserialized, 1e-7))

        # Test with empty matrix
        self.assertEqual(serialize_matrix_to_json(None), "[]")
        self.assertIsNone(deserialize_matrix_from_json(""))

        # Test with malformatted json
        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    "Failed to load from JSON string. Exception: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
                    "Failed to load from JSON string. Exception: Expecting value: line 1 column 2 (char 1)",
                    "Failed to load from JSON string. Exception: Expecting value: line 1 column 11 (char 10)",
                    "Failed to deserialize matrix from JSON string. Exception: No registered converter was able to produce a C++ rvalue",  # we need partial match for this line
                ],
                partial_string_match=True
            ):
                self.assertIsNone(deserialize_matrix_from_json("{bad json}"))
                self.assertIsNone(deserialize_matrix_from_json("[bad json}"))
                self.assertIsNone(deserialize_matrix_from_json("[1,2,3]"))
                self.assertIsNone(deserialize_matrix_from_json("[[1,2],[3,"))

        # Test with malformed matrix data
        result = deserialize_matrix_from_json("[[1,2,3,4],[5,6,7,8],[9,10,11,12]]")  # Missing row
        matrix2 = Gf.Matrix4d((
            (1.0, 2.0, 3.0, 4.0),
            (5.0, 6.0, 7.0, 8.0),
            (9.0, 10.0, 11.0, 12.0),
            (0.0, 0.0, 0.0, 1.0)
        ))
        self.assertTrue(Gf.IsClose(result, matrix2, 1e-7))  # Should be equal to matrix2

        result = deserialize_matrix_from_json("[[1,2,3],[4,5,6],[7,8,9],[10,11,12]]")  # Missing column
        matrix2 = Gf.Matrix4d((
            (1.0, 2.0, 3.0, 0.0),
            (4.0, 5.0, 6.0, 0.0),
            (7.0, 8.0, 9.0, 0.0),
            (10.0, 11.0, 12.0, 1.0)
        ))
        self.assertTrue(Gf.IsClose(result, matrix2, 1e-7))  # Should be equal to matrix2

    def test_matrix_to_list_and_back(self):
        # Test matrix_to_list returns row-major list of 16 floats
        mat = Gf.Matrix4d(
            1.0, 2.0, 3.0, 4.0,
            5.0, 6.0, 7.0, 8.0,
            9.0, 10.0, 11.0, 12.0,
            13.0, 14.0, 15.0, 16.0
        )
        expected_flat = [
            1.0, 2.0, 3.0, 4.0,
            5.0, 6.0, 7.0, 8.0,
            9.0, 10.0, 11.0, 12.0,
            13.0, 14.0, 15.0, 16.0
        ]

        mat_as_list = matrix_to_list(mat)
        self.assertIsInstance(mat_as_list, list)
        self.assertEqual(len(mat_as_list), 16)
        self.assertEqual(mat_as_list, expected_flat)

        # Test list_to_matrix correctly reconstructs matrix
        reconstructed = list_to_matrix(expected_flat)
        self.assertIsInstance(reconstructed, Gf.Matrix4d)
        self.assertTrue(Gf.IsClose(mat, reconstructed, 1e-7))

        # Check that converting, then reconstructing gives original matrix
        original = Gf.Matrix4d(
            1.1, 2.2, 3.3, 4.4,
            5.5, 6.6, 7.7, 8.8,
            9.9, 10.10, 11.11, 12.12,
            13.13, 14.14, 15.15, 16.16
        )
        roundtrip_flat = matrix_to_list(original)
        self.assertEqual(len(roundtrip_flat), 16)
        roundtrip_matrix = list_to_matrix(roundtrip_flat)
        self.assertTrue(Gf.IsClose(original, roundtrip_matrix, 1e-7))

        # Test list_to_matrix with invalid inputs (None, wrong length, etc)
        self.assertIsNone(list_to_matrix(None))
        self.assertIsNone(list_to_matrix([]))
        self.assertIsNone(list_to_matrix([1.0]*15))
        self.assertIsNone(list_to_matrix([1.0]*17))

        # Test list_to_matrix with bigger values
        weird_list = [float(i * 1000) for i in range(16)]
        weird_matrix = list_to_matrix(weird_list)
        self.assertTrue(Gf.IsClose(weird_matrix, Gf.Matrix4d(
            0.0, 1000.0, 2000.0, 3000.0,
            4000.0, 5000.0, 6000.0, 7000.0,
            8000.0, 9000.0, 10000.0, 11000.0,
            12000.0, 13000.0, 14000.0, 15000.0
        ), 1e-7))

        # Test roundtrip with negative/fractional values
        negmatrix = Gf.Matrix4d(
            -1.0, -2.5, 3.2, 0.0,
            4.4, -5.1, 6.7, 8.8,
            9.9, 0.0, -10.1, 11.2,
            12.3, -13.5, 14.6, -15.7
        )
        negflat = matrix_to_list(negmatrix)
        negmatrix2 = list_to_matrix(negflat)
        self.assertTrue(Gf.IsClose(negmatrix, negmatrix2, 1e-7))

        # Test with NaN and Inf
        import math
        nanmat = Gf.Matrix4d(
            math.nan, 0.0, 0.0, 0.0,
            0.0, math.inf, 0.0, 0.0,
            0.0, 0.0, -math.inf, 0.0,
            0.0, 0.0, 0.0, math.nan
        )
        flat = matrix_to_list(nanmat)
        rec = list_to_matrix(flat)
        # Can't compare NaN with equality, but Inf/-Inf does preserve
        self.assertTrue(math.isinf(rec[1, 1]) and rec[1, 1] > 0)
        self.assertTrue(math.isinf(rec[2, 2]) and rec[2, 2] < 0)
        self.assertTrue(math.isnan(rec[0, 0]))
        self.assertTrue(math.isnan(rec[3, 3]))

        # Test using list of ints (should be cast to float)
        intlist = [i for i in range(16)]
        intmatrix = list_to_matrix(intlist)
        for i in range(4):
            for j in range(4):
                self.assertEqual(intmatrix[i, j], float(i * 4 + j))

        # Test that list_to_matrix produces Gf.Matrix4d objects for valid input
        fl = [0.1*i for i in range(16)]
        self.assertIsInstance(list_to_matrix(fl), Gf.Matrix4d)

    def test_get_prim_matrix(self):
        # Create test prim with transform
        prim = self._stage.GetPrimAtPath("/root")
        xform = UsdGeom.Xformable(prim)
        translate = Gf.Vec3d(1.0, 2.0, 3.0)
        xform.AddTranslateOp().Set(translate)

        # Test getting matrix at default time
        matrix = get_prim_matrix(self._stage, "/root")
        self.assertIsNotNone(matrix)
        self.assertEqual(Gf.Transform(matrix).GetTranslation(), translate)

        # Test with invalid prim path
        self.assertIsNone(get_prim_matrix(self._stage, "/nonexistent"))

        # Test with non-xformable prim
        result = get_prim_matrix(self._stage, "/root/mesh")
        self.assertTrue(Gf.IsClose(result, matrix, 1e-7))  # Should be equal to matrix2

        # Test with specific time
        self._stage.SetTimeCodesPerSecond(24.0)  # Set FPS
        matrix_at_time = get_prim_matrix(self._stage, "/root", time=1.0)  # Test at 1 second
        self.assertIsNotNone(matrix_at_time)
        self.assertEqual(Gf.Transform(matrix_at_time).GetTranslation(), translate)

        # Test with invalid FPS
        self._stage.SetTimeCodesPerSecond(0.0)
        self.assertIsNone(get_prim_matrix(self._stage, "/root", time=1.0))
