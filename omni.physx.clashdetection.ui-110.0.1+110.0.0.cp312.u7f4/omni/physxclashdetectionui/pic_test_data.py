# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
from .pic_provider import PersonInCharge, PersonsInCharge

__all__ = []


class PersonsInChargeTestData(PersonsInCharge):
    """A class for handling test data related to persons in charge.

    This class extends the functionality of the PersonsInCharge class by providing a method to fetch data from a JSON file and populate the internal dictionary with PersonInCharge instances.

    Methods:
        fetch(source: str) -> bool: Loads data from a JSON file and populates the internal dictionary with PersonInCharge instances.
    """

    # override
    def fetch(self, source: str) -> bool:
        """Fetches and loads data from a specified source.

        A username that already exists in the internal dictionary will be updated with the new one.

        Args:
            source (str): The path to the source file.

        Returns:
            bool: True if data was loaded successfully, False otherwise.
        """
        import json

        try:
            with open(source, "r") as f:
                json_data = json.load(f)
                self.reset()
                for pic in json_data["pic"]:
                    self._pic_dict[pic["username"]] = PersonInCharge(
                        pic["username"], pic["first_name"], pic["last_name"], pic["email"]
                    )
        except Exception as e:
            carb.log_error(f"PersonsInCharge: Failed to load file '{source}' with exception:\n{e}.")
            return False
        return True
