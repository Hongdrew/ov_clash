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
from typing import Callable, List
import carb


def safe_delete_file(file_name: str) -> bool:
    """Deletes file specified by file_name from drive and returns True on success, otherwise returns False.

    Args:
        file_name (str): Name of the file to delete.

    Returns:
        bool: True if the file is successfully deleted, False otherwise.
    """
    if not file_name:
        return False
    import os

    r = True
    try:
        os.remove(file_name)
    except Exception as e:
        carb.log_error(f"Removal of file '{file_name}' caused the following exception: {e}.")
        r = False
    finally:
        return r


def measure_execution_time(func: Callable):
    """ A decorator to measure execution time. """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function {func.__name__} took {execution_time:.4f} seconds to execute.")
        return result
    return wrapper


def compare_text_files(file1_name: str, file2_name: str, ignore_order: bool) -> List[str]:
    """ Compares provided text files and returns differences, if empty string if any.
        Is able to find matching lines if they are in different order.
    """
    def remove_matching_line(text_to_remove: str, lines: List[str]):
        """
        Remove the first occurrence of a matching line from the list.
        :param lines: List of strings (lines of text)
        :param text_to_remove: The text to find and remove
        :return: Modified list with the matching line removed
        """
        try:
            index_to_remove = lines.index(text_to_remove)
            del lines[index_to_remove]
            return True
        except ValueError:
            return False

    differences = []
    try:
        with open(file1_name, 'r') as f1, open(file2_name, 'r') as f2:
            file1_lines = f1.readlines()
            file2_lines = f2.readlines()
        if ignore_order:
            for line_num, line in enumerate(file1_lines, start=1):
                if not remove_matching_line(line, file2_lines):
                    differences.append((line_num, "Line not found: ", line.strip()))
            if len(file2_lines) != 0:
                differences.append((0, "Number of unmatched lines: ", len(file2_lines)))
        else:
            for line_num, (line1, line2) in enumerate(zip(file1_lines, file2_lines), start=1):
                if line1 != line2:
                    differences.append((line_num, line1.strip(), line2.strip()))
    except FileNotFoundError as e:
        differences.append(str(e))
    finally:
        return differences
