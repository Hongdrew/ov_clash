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
from omni.physxclashdetectionui.filtering import parse_filter_expression, apply_filter


class TestFiltering(AsyncTestCase):

    def test_parse_filter_expression(self):
        # test parse_filter_expression
        filter_expression = "[Name] = 'foo' AND ([Age] > 20 OR [Status] NOT IN ('Active','Pending'))"
        filter_tree = parse_filter_expression(filter_expression, upper_cased=False)
        self.assertIsNotNone(filter_tree)
        self.assertEqual(filter_tree.left.column, "Name")
        self.assertEqual(filter_tree.left.op, "=")
        self.assertEqual(filter_tree.left.value, "foo")
        self.assertEqual(filter_tree.right.left.column, "Age")
        self.assertEqual(filter_tree.right.left.op, ">")
        self.assertEqual(filter_tree.right.left.value, 20)
        self.assertEqual(filter_tree.right.right.column, "Status")
        self.assertEqual(filter_tree.right.right.op, "NOT IN")
        self.assertEqual(filter_tree.right.right.value, ["Active", "Pending"])

        # test apply_filter
        columns_dict = {"Name": 0, "Number": 1, "Status": 2}  # mapping of column names to indices in data
        columns_dict_upper_cased = {k.upper(): v for k, v in columns_dict.items()}
        data = [
            ["Foo", 25, "Active"],
            ["Bar", 19, "Inactive"],
            ["Doo", 30, "Pending"],
            ["Baz", -0.1, "Inactive"],
            ["Zap", 0.5, "Active"],
        ]

        def filter_data(expr, upper_cased=False):
            def get_column_value(row, col_name):
                d = columns_dict_upper_cased if upper_cased else columns_dict
                idx = d.get(col_name)
                if idx is None:
                    return None
                val = row[idx]
                return val.upper() if upper_cased and isinstance(val, str) else val

            filter_tree = parse_filter_expression(expr, upper_cased)
            if filter_tree is None:
                return []

            return [
                row
                for row in data
                if apply_filter(filter_tree, lambda col_name: get_column_value(row, col_name))
            ]

        def test_filter_data(upper_cased):
            result = filter_data("[Name] = 'Foo' AND ([Number] > 20 OR [Status] NOT IN ('Active','Pending'))", upper_cased)
            self.assertListEqual(result, [["Foo", 25, "Active"]])

            result = filter_data("[Number] < 25", upper_cased)
            self.assertListEqual(result, [["Bar", 19, "Inactive"], ["Baz", -0.1, "Inactive"], ["Zap", 0.5, "Active"]])

            result = filter_data("[Status] IN ('Active','Pending')", upper_cased)
            self.assertListEqual(result, [["Foo", 25, "Active"], ["Doo", 30, "Pending"], ["Zap", 0.5, "Active"]])

            result = filter_data("[Name] = 'Bar' OR [Number] >= 30", upper_cased)
            self.assertListEqual(result, [["Bar", 19, "Inactive"], ["Doo", 30, "Pending"]])

            # Test: Status != 'Inactive'
            result = filter_data("[Status] != 'Inactive'", upper_cased)
            self.assertListEqual(result, [["Foo", 25, "Active"], ["Doo", 30, "Pending"], ["Zap", 0.5, "Active"]])

            result = filter_data("[Name] LIKE 'Ba'", upper_cased)
            self.assertListEqual(result, [["Bar", 19, "Inactive"], ["Baz", -0.1, "Inactive"]])

            result = filter_data("[Name] NOT LIKE 'oo'", upper_cased)
            self.assertListEqual(result, [["Bar", 19, "Inactive"], ["Baz", -0.1, "Inactive"], ["Zap", 0.5, "Active"]])

            # Test: empty filter returns all
            # result = filter_data("", upper_cased)
            # self.assertListEqual(result, [["Foo", 25, "Active"], ["Bar", 19, "Inactive"], ["Doo", 30, "Pending"], ["Baz", -0.1, "Inactive"], ["Zap", 0.5, "Active"]])

            result = filter_data("[Nonexistent] = 'x'", upper_cased)
            self.assertListEqual(result, [])

            result = filter_data("([Name] IN ('Foo', 'Bar') AND [Number] >= 19) OR ([Status] = 'Inactive')", upper_cased)
            self.assertListEqual(result, [["Foo", 25, "Active"], ["Bar", 19, "Inactive"], ["Baz", -0.1, "Inactive"]])

            result = filter_data("[Name] LIKE 'zzz'", upper_cased)
            self.assertListEqual(result, [])

            result = filter_data("[Number] < 0", upper_cased)
            self.assertListEqual(result, [["Baz", -0.1, "Inactive"]])

            # Test: negative float starting with dot (should not match any row)
            result = filter_data("[Number] = -.1", upper_cased)
            self.assertListEqual(result, [["Baz", -0.1, "Inactive"]])

            # Test: negative float with leading zero
            result = filter_data("[Number] = -0.1", upper_cased)
            self.assertListEqual(result, [["Baz", -0.1, "Inactive"]])

            # Test: float number starting with dot
            result = filter_data("[Number] = .5", upper_cased)
            self.assertListEqual(result, [["Zap", 0.5, "Active"]])

            result = filter_data("[Number] = 0.5", upper_cased)
            self.assertListEqual(result, [["Zap", 0.5, "Active"]])

        test_filter_data(upper_cased=True)
        test_filter_data(upper_cased=False)

        # test for column-to-column comparison
        data[0][2] = "Foo"
        result = filter_data("[Name] = [Status]", True)
        self.assertListEqual(result, [["Foo", 25, "Foo"]])
