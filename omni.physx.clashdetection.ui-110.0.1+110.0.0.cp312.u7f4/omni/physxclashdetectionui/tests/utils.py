# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, Tuple, Callable, Optional
import time
import gc


def get_used_mem() -> int:
    """
    Returns the amount of memory used by the current process in bytes.
    """
    import psutil
    return psutil.Process().memory_info().rss


class CodeTimer:
    """
    Context manager and utility for timing code execution and tracking memory usage.

    Usage:
        with CodeTimer("label") as ct:
            # code to time
            ct.check_mem()  # optionally track memory peak during execution

    Features:
        - Records elapsed time and memory usage for each labeled code block.
        - Aggregates results for later reporting or processing.
        - Provides class methods to clear, dump, and process timing/memory records.
        - check_mem() can be called within the context to update memory peak.

    Attributes:
        _records (dict): Stores timing, memory usage, and units for each label.
    """

    _records: dict = {}  # label: (time, memory, units_tuple)

    @classmethod
    def clear_records(cls):
        """Clear all timing records."""
        cls._records = {}

    @classmethod
    def dump_records(cls):
        """Print all timing/memory records."""
        if not cls._records:
            return
        max_label_length = max(len(label) for label in cls._records)
        for label, (tm, mem, units) in cls._records.items():
            print(f"{label:<{max_label_length}}: {tm:15.9f} {units[0]}, used memory: {mem / 1024 ** 2:15.9f} MB")

    @classmethod
    def process_records_cb(cls, cb_fnc: Callable[[str, float, str], None]):
        """Call cb_fnc for each record (time and RAM)."""
        for label, (tm, mem, units) in cls._records.items():
            cb_fnc(label + f" ({units[2]})", tm, units[1])
            cb_fnc(label + " (RAM)", mem / 1024 ** 2, "MB")

    @classmethod
    def find_record(cls, label: str) -> Optional[Tuple[float, int, Tuple[str, str, str]]]:
        """Return the (time, memory, units_tuple) tuple for the given label, or None if not found."""
        return cls._records.get(label, None)

    @classmethod
    def add_record(cls, label: str, time_val: float, mem_val: int, time_val_units: Tuple[str, str, str] = ("sec", "s", "Time")):
        """Add or overwrite a custom value/memory record for a label.
        
        Args:
            label: Label for the record
            time_val: Time value (or custom value)
            mem_val: Memory value
            time_val_units: Tuple of (display_units, callback_units, label_suffix)
                   e.g., ("sec", "s", "Time") or ("fps", "fps", "FPS")
        """
        cls._records[label] = (time_val, mem_val, time_val_units)

    def check_mem(self):
        """Update memory peak if higher."""
        used_mem = get_used_mem()
        if self._mem_peak is None or used_mem > self._mem_peak:
            self._mem_peak = used_mem

    def __init__(self, label: str = ""):
        """Init CodeTimer with label."""
        self._label = label
        self._start_time = 0
        self._end_time = 0
        self._mem_base = None
        self._mem_peak = None

    def __enter__(self):
        """Start timer and memory tracking."""
        gc.collect()
        self._start_time = time.perf_counter()
        self._mem_base = get_used_mem()
        return self

    def __exit__(self, *args):
        """Stop timer, record results, print summary."""
        self._end_time = time.perf_counter()
        interval = self._end_time - self._start_time

        self.check_mem()
        used_mem = self._mem_peak - self._mem_base if self._mem_peak and self._mem_base else 0

        CodeTimer.add_record(self._label, interval, used_mem)
        print(f"Execution time [{self._label}]: {interval:.9f} seconds, used memory: {used_mem / 1024 ** 2:.9f} MB")


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