# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
from datetime import datetime, timedelta
from omni.kit.test import AsyncTestCase
from omni.physxclashdetectionui.utils import (
    contains_url,
    string_match,
    whole_string_encapsulation_ctrl_chars,
    get_time_delta_str,
    DeferredAction,
)


class TestUtils(AsyncTestCase):

    def test_contains_url(self):
        # http
        self.assertTrue(contains_url("http://example.com"))  #NOSONAR
        self.assertTrue(contains_url("http://www.example.com"))  #NOSONAR
        # ftp
        self.assertTrue(contains_url("ftp://example.com/"))  #NOSONAR
        # https
        self.assertTrue(contains_url("https://secure-site.org"))
        # no protocol
        self.assertFalse(contains_url("www.example.com"))
        # port in url
        self.assertTrue(contains_url("http://example.com:8080"))  #NOSONAR
        # localhost and port
        self.assertTrue(contains_url("http://localhost:8080"))  #NOSONAR
        # no url
        self.assertFalse(contains_url("This string has no URL"))
        # malformed_url
        self.assertFalse(contains_url("htp:/not-a-url"))
        # empty url
        self.assertFalse(contains_url(""))
        self.assertFalse(contains_url(None))
        # multiple urls
        self.assertFalse(contains_url("http://first.com and https://second.com"))  #NOSONAR
        # subdomain
        self.assertTrue(contains_url("https://sub.domain.com/aaa/bbb/"))
        self.assertTrue(contains_url("https://sub.domain.com/aaa//bbb/"))
        # ip address
        self.assertTrue(contains_url("http://192.168.1.1/aaa"))  #NOSONAR
        # omniverse
        self.assertTrue(contains_url("omniverse://a.bb.ccc.com/aaa/bbb/file.usd"))
        self.assertFalse(contains_url("omniverse:/a.bb.ccc.com/aaa/bbb/file.usd"))
        self.assertFalse(contains_url("a.bb.ccc.com/aaa/bbb/file.usd"))

    def test_string_match(self):
        ctrl_char = whole_string_encapsulation_ctrl_chars

        # Exact match with control characters
        self.assertTrue(string_match(
            f"{ctrl_char}hello{ctrl_char}",
            "hello",
            ctrl_char
        ))
        # No match with control characters
        self.assertFalse(string_match(
            f"{ctrl_char}hello{ctrl_char}",
            "world",
            ctrl_char
        ))
        # Substring match
        self.assertTrue(string_match("lo", "hello"))
        # No substring match
        self.assertFalse(string_match("world", "hello"))
        # Search text None
        self.assertTrue(string_match(None, "hello"))
        # Empty search text
        self.assertTrue(string_match("", "hello"))
        # Empty string
        self.assertFalse(string_match("hello", ""))
        # Both empty
        self.assertTrue(string_match("", ""))
        # Control characters not at edges
        self.assertFalse(string_match(f"{ctrl_char}hello", "hello", ctrl_char))
        self.assertFalse(string_match(f"hello{ctrl_char}", "hello", ctrl_char))

        # Exact match with custom control characters
        ctrl_char = "@"
        self.assertTrue(string_match(
            f"{ctrl_char}hello{ctrl_char}",
            "hello",
            ctrl_char
        ))

    def test_get_time_delta_str(self):
        # test_zero_seconds
        self.assertEqual(get_time_delta_str(0), "00:00.00")
        # test_only_seconds
        self.assertEqual(get_time_delta_str(45.67), "00:45.67")
        # test_minutes_and_seconds
        self.assertEqual(get_time_delta_str(125.89), "02:05.89")
        # test_hours_minutes_seconds
        self.assertEqual(get_time_delta_str(3661.23), "01:01:01.23")
        # test_exact_minutes
        self.assertEqual(get_time_delta_str(180), "03:00.00")
        # test_exact_hours
        self.assertEqual(get_time_delta_str(7200), "02:00:00.00")
        # test_large_number
        self.assertEqual(get_time_delta_str(123456.789), "34:17:36.78")

    async def test_deferred_action(self):
        executed_time = None

        def my_action():
            nonlocal executed_time
            executed_time = datetime.now()
            return False  # stop

        def_action = DeferredAction(my_action, 0.01)
        expected_time = datetime.now() + timedelta(seconds=0.2)
        def_action.set_next_action_at(expected_time)
        while executed_time is None:
            await asyncio.sleep(0.1)
        self.assertIsNotNone(executed_time)
        self.assertTrue(executed_time >= expected_time)
