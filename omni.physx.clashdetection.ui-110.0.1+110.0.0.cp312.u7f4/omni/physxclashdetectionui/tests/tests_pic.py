# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import os
from omni.kit.test import AsyncTestCase
from omni.physxclashdetectionui.pic_test_data import PersonsInChargeTestData


class TestPersonInCharge(AsyncTestCase):

    def __init__(self, tests=()):
        super().__init__(tests)
        test_data_dir = os.path.dirname(__file__) + "/../../../testdata/"
        self._test_data_dir = os.path.abspath(os.path.normpath(test_data_dir)).replace("\\", "/") + '/'

    async def test_pic_provider(self):
        users = PersonsInChargeTestData()
        self.assertTrue(users.fetch(self._test_data_dir + "pic_test_data.json"))

        self.assertEqual(len(users.get_items()), 6)
        self.assertIsNotNone(users.get_person("non-existent_person"))

        user_name = "pparker"
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "Peter")
        self.assertEqual(pic.last_name, "Parker")
        self.assertEqual(pic.email, "peter@spider-man.com")
        self.assertEqual(pic.full_name, "Peter Parker")
        self.assertEqual(pic.full_name_email, "Peter Parker <peter@spider-man.com>")

        user_name = "empty"
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "")
        self.assertEqual(pic.last_name, "")
        self.assertEqual(pic.email, "")
        self.assertEqual(pic.full_name, user_name)
        self.assertEqual(pic.full_name_email, user_name)

        user_name = "onlyemail"
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "")
        self.assertEqual(pic.last_name, "")
        self.assertEqual(pic.email, "tom@email.com")
        self.assertEqual(pic.full_name, user_name)
        self.assertEqual(pic.full_name_email, f"{user_name} <tom@email.com>")

        user_name = "only1stname"
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "Tom")
        self.assertEqual(pic.last_name, "")
        self.assertEqual(pic.email, "")
        self.assertEqual(pic.full_name, "Tom")
        self.assertEqual(pic.full_name_email, "Tom")

        user_name = "onlyfullname"
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "Tom")
        self.assertEqual(pic.last_name, "Jelly")
        self.assertEqual(pic.email, "")
        self.assertEqual(pic.full_name, "Tom Jelly")
        self.assertEqual(pic.full_name_email, "Tom Jelly")

        user_name = ""
        pic = users.get_person(user_name)
        self.assertIsNotNone(pic)
        self.assertEqual(pic.username, user_name)
        self.assertEqual(pic.first_name, "<Empty>")
        self.assertEqual(pic.last_name, "")
        self.assertEqual(pic.email, "")
        self.assertEqual(pic.full_name, "<Empty>")
        self.assertEqual(pic.full_name_email, "<Empty>")

        del users
