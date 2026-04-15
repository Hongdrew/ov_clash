# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import time
from omni.kit.test import AsyncTestCase
import omni.client
from omni.physxclashdetectioncore.utils import (
    make_int128,
    get_random_word,
    html_escape,
    clamp_value,
    file_exists,
    safe_copy_file,
    safe_delete_file,
    get_unique_temp_file_path_name,
    obj_to_dict,
    dict_to_obj,
    OptimizedProgressUpdate,
)


class TestUtils(AsyncTestCase):

    def test_make_int128(self):
        # Test zero values
        self.assertEqual(make_int128(0, 0), 0)
        # Test only low part
        self.assertEqual(make_int128(0, 1), 1)
        self.assertEqual(make_int128(0, 2**64 - 1), 2**64 - 1)
        # Test only high part
        self.assertEqual(make_int128(1, 0), 1 << 64)
        self.assertEqual(make_int128(2**63, 0), 2**127)
        # Test combined values
        self.assertEqual(make_int128(1, 1), (1 << 64) | 1)
        self.assertEqual(make_int128(2**63, 2**63), (2**127) | (2**63))
        # Test max values
        self.assertEqual(make_int128(2**64 - 1, 2**64 - 1), (2**128 - 1))

    def test_get_random_word(self):
        import string
        # Test if the generated word has the correct length,
        # and test if the generated word contains only lowercase letters and digits.
        valid_characters = string.ascii_lowercase + string.digits
        for length in range(1, 11):
            word = get_random_word(length)
            self.assertEqual(len(word), length, f"Failed for length: {length}")
            for char in word:
                self.assertIn(char, valid_characters, f"Invalid character found: {char}")

        # Test if the function handles zero length correctly.
        word = get_random_word(0)
        self.assertEqual(word, "", "Expected empty string for zero length")

        # Test if the function handles negative length correctly.
        word = get_random_word(-1)
        self.assertEqual(word, "", "Expected empty string for zero length")

    def test_html_escape(self):
        # Test a string with multiple special characters
        self.assertEqual(html_escape("<div>Tom & Jerry's \"Adventure\"</div>"),
                         "&lt;div&gt;Tom &amp; Jerry&#39;s &quot;Adventure&quot;&lt;/div&gt;")
        # Test a string with no special characters
        self.assertEqual(html_escape("Hello, World!"), "Hello, World!")
        # Test an empty string
        self.assertEqual(html_escape(""), "")
        # Test a string with only special characters
        self.assertEqual(html_escape("&<>'\""), "&amp;&lt;&gt;&#39;&quot;")

    def test_clamp_value(self):
        # test_value_within_range
        self.assertEqual(clamp_value(5, 0, 10), 5)
        self.assertEqual(clamp_value(0, -10, 10), 0)
        self.assertEqual(clamp_value(-5, -10, 0), -5)
        # test_value_below_min
        self.assertEqual(clamp_value(-5, 0, 10), 0)
        self.assertEqual(clamp_value(-20, -10, 10), -10)
        self.assertEqual(clamp_value(-15, -10, 0), -10)
        # test_value_above_max
        self.assertEqual(clamp_value(15, 0, 10), 10)
        self.assertEqual(clamp_value(20, -10, 10), 10)
        self.assertEqual(clamp_value(5, -10, 0), 0)
        # test_min_equals_max
        self.assertEqual(clamp_value(5, 5, 5), 5)
        self.assertEqual(clamp_value(0, 0, 0), 0)
        self.assertEqual(clamp_value(-5, -5, -5), -5)
        # test_edge_cases
        self.assertAlmostEqual(clamp_value(2.5, 1.1, 3.3), 2.5)
        self.assertAlmostEqual(clamp_value(4.4, 1.1, 3.3), 3.3)
        self.assertAlmostEqual(clamp_value(0.9, 1.1, 3.3), 1.1)

    def test_file_ops(self):
        try:
            from omni.physxtests import utils
            omni_physxtests_utils_available = True
        except:
            omni_physxtests_utils_available = False
        print("omni.physxtests utils available." if omni_physxtests_utils_available else "omni.physxtests utils NOT available, some checks will be skipped.")

        self.assertFalse(file_exists("/?non_existen_file*"))

        if omni_physxtests_utils_available:
            with utils.ExpectMessage(
                self,
                [
                    # Windows
                    "Removal of file '/?non_existen_file*' caused the following exception: [WinError 123] The filename, directory name, or volume label syntax is incorrect: '/?non_existen_file*'.",
                    # Linux
                    "Removal of file '/?non_existen_file*' caused the following exception: [Errno 2] No such file or directory: '/?non_existen_file*'.",
                ],
                expect_all=False  # expect one of the above messages
            ):
                self.assertFalse(safe_delete_file("/?non_existen_file*"))

            with utils.ExpectMessage(
                self,
                [
                    # Windows
                    "File copy caused the following exception: [Errno 22] Invalid argument: '/?non_existen_file*'. Source: '/?non_existen_file*', destination: '/?non_existen_file2*'.",
                    # Linux
                    "File copy caused the following exception: [Errno 2] No such file or directory: '/?non_existen_file*'. Source: '/?non_existen_file*', destination: '/?non_existen_file2*'.",
                ],
                expect_all=False  # expect one of the above messages
            ):
                self.assertFalse(safe_copy_file("/?non_existen_file*", "/?non_existen_file2*"))

        test_string = "File operations: A Test String."
        test_file_path = get_unique_temp_file_path_name("_test_file_ops.ext")
        test_file_path2 = get_unique_temp_file_path_name("_test_file_ops2.ext")

        print(f"Writing '{test_file_path}'...")
        self.assertEqual(omni.client.write_file(test_file_path, bytes(test_string, "utf-8")), omni.client.Result.OK)
        self.assertTrue(file_exists(test_file_path))

        print(f"Copying '{test_file_path}' to '{test_file_path2}'...")
        self.assertTrue(safe_copy_file(test_file_path, test_file_path2))
        self.assertTrue(file_exists(test_file_path2))

        print(f"Reading back '{test_file_path2}'...")
        result, version, content = omni.client.read_file(test_file_path2)
        self.assertEqual(result, omni.client.Result.OK)
        readback_str = memoryview(content).tobytes().decode("utf-8")
        self.assertEqual(readback_str, test_string)

        print(f"Deleting '{test_file_path}'...")
        self.assertTrue(safe_delete_file(test_file_path))
        print(f"Deleting '{test_file_path2}'...")
        self.assertTrue(safe_delete_file(test_file_path2))
        self.assertFalse(file_exists(test_file_path))
        self.assertFalse(file_exists(test_file_path2))

    def test_obj_to_dict_and_back(self):
        from datetime import datetime
        from enum import Enum

        class TestEnum(Enum):
            VAL1 = 1
            VAL2 = 2

        class TestClass:
            def __init__(self):
                self.enum_val = TestEnum.VAL1
                self.date_val = datetime(2023, 1, 1)
                self.str_val = "test"
                self.int_val = 42
                self.float_val = 420.0

        # Test obj_to_dict
        test_obj = TestClass()
        result_dict = obj_to_dict(test_obj)

        self.assertEqual(result_dict["enum_val"], "VAL1")
        self.assertEqual(result_dict["date_val"], "2023-01-01T00:00:00")
        self.assertEqual(result_dict["str_val"], "test")
        self.assertEqual(result_dict["int_val"], 42)
        self.assertEqual(result_dict["float_val"], 420.0)

        # Test dict_to_obj
        new_obj = TestClass()
        success = dict_to_obj(new_obj, result_dict)

        self.assertTrue(success)
        self.assertEqual(vars(test_obj), vars(new_obj))

        # Test with custom conversion function
        def custom_convert(name, val):
            return str(val) + "_converted" if isinstance(val, str) else val

        result_dict = obj_to_dict(test_obj, custom_convert)
        self.assertEqual(result_dict["str_val"], "test_converted")

    def test_opt_progress(self):
        num_steps = 100
        update_rate = 0.1
        force_update_rate = 0.2
        hit = False

        progress_update = OptimizedProgressUpdate(update_rate, force_update_rate)

        # test update_rate
        start_time = time.time()
        for i in range(num_steps):
            time.sleep(0.01)
            # skit first update which is always triggered
            if i == 0 and progress_update.update(float(i) * 0.01):
                start_time = time.time()
            elif progress_update.update(float(i) * 0.01):
                elapsed_time = time.time() - start_time
                self.assertTrue(elapsed_time >= update_rate)
                hit = True
                break
        if not hit:
            # in case of no hit make sure that time hasn't elapsed
            elapsed_time = time.time() - start_time
            self.assertTrue(elapsed_time < update_rate)

        # test force_update_rate
        # (even with no change in progress value update must be triggered at force_update_rate rate)
        hit = False
        progress_update.start()
        for i in range(num_steps):
            time.sleep(0.01)
            # skit first update which is always triggered
            if i == 0 and progress_update.update(0):
                start_time = time.time()
            elif progress_update.update(0):
                elapsed_time = time.time() - start_time
                self.assertTrue(elapsed_time >= force_update_rate)
                hit = True
                break
        if not hit:
            # in case of no hit make sure that time hasn't elapsed
            elapsed_time = time.time() - start_time
            self.assertTrue(elapsed_time < force_update_rate)
