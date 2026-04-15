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
import json
from typing import Callable, Any, Optional, Dict
import carb


def get_current_user_name() -> str:
    """Returns name of the currently logged-in user.

    Returns:
        str: The current user's name.
    """
    import getpass

    return getpass.getuser()


def make_int128(hi: int, lo: int) -> int:
    """Makes 128bit number out of two 64bit numbers.

    Args:
        hi (int): High 64 bits.
        lo (int): Low 64 bits.

    Returns:
        int: 128-bit integer combining hi and lo.
    """
    int128 = (hi << 64) | lo
    return int128


def html_escape(t: str) -> str:
    """Escapes special HTML characters (provided in t).

    Args:
        t (str): Text to escape.

    Returns:
        str: Escaped text.
    """
    return (
        t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;").replace('"', "&quot;")
    )


def get_available_system_memory() -> int:
    """Returns available system memory in bytes.

    Returns:
        int: Available system memory in bytes.
    """
    from omni.gpu_foundation_factory import get_memory_info

    memory_info = get_memory_info()
    return memory_info.get("available_memory", 0)


def file_exists(path_name: str) -> bool:
    """Checks if file specified by path_name exists and returns True on success, otherwise returns False.

    Args:
        path_name (str): Path to the file to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if not path_name:
        return False
    import os

    r = True
    try:
        r = os.path.isfile(path_name)
    except Exception as e:
        carb.log_error(f"Existence check on file '{path_name}' caused the following exception: {e}")
        r = False
    finally:
        return r


def get_random_word(length: int) -> str:
    """Generates random ascii lowercase word of 'length' characters.

    Args:
        length (int): Length of the random word.

    Returns:
        str: Randomly generated word.
    """
    import random
    import string

    letters = string.ascii_lowercase + string.digits
    return "".join(random.choice(letters) for _ in range(length))  #NOSONAR


def get_temp_file_path_name(suffix: str = "") -> str:
    """Generates temp file path name.

    Args:
        suffix (str): Optional suffix for the file name.

    Returns:
        str: Temporary file path name.
    """
    import carb.tokens
    temp_path = carb.tokens.get_tokens_interface().resolve("${temp}/")
    temp_path += get_random_word(8)  # add a random word to make sure the name is unique
    if suffix:
        temp_path += suffix
    return temp_path


def get_unique_temp_file_path_name(suffix: str = "") -> str:
    """Generates unique temp file path name (makes sure it does not exist yet).

    Args:
        suffix (str): Optional suffix for the file name.

    Returns:
        str: Unique temporary file path name.
    """
    temp_path = get_temp_file_path_name(suffix)
    while file_exists(temp_path):
        temp_path = get_temp_file_path_name(suffix)
    return temp_path


def is_local_url(url: str) -> bool:
    """Returns True if the url points to a local file. Returns False in case of remote URL.

    Args:
        url (str): URL to check.

    Returns:
        bool: True if the URL is local, False otherwise.
    """
    import omni.client
    from omni.client import Url

    parsed_url: Url = omni.client.break_url(url)
    from_local = parsed_url.is_raw or parsed_url.scheme == "file"
    return from_local


def safe_copy_file(src: str, dst: str, follow_symlinks: bool=True) -> bool:
    """Copies src to dst and returns True on success, otherwise returns False.
    Also supports URLs.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.
        follow_symlinks (bool): Whether to follow symlinks.

    Returns:
        bool: True if the file is successfully copied, False otherwise.
    """
    if not src or not dst:
        return False
    import shutil

    r = True
    try:
        shutil.copy(src, dst, follow_symlinks=follow_symlinks)
    except Exception as e:
        carb.log_error(f"File copy caused the following exception: {e}. Source: '{src}', destination: '{dst}'.")
        r = False
    finally:
        return r


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


def to_json_str_safe(obj: Any, **kwargs) -> str:
    """
    Safely converts a Python object into a JSON string.

    This function attempts to serialize a Python object into a JSON-formatted string.
    If serialization fails, it logs an error message and returns an empty string.
    By default, the JSON string is formatted with an indentation of 4 spaces, unless
    otherwise specified in the keyword arguments.

    Args:
        obj (Any): The Python object to be serialized into a JSON string.
        **kwargs: Additional keyword arguments passed to `json.dumps()`, such as
        formatting options.

    Returns:
        str: A JSON-formatted string representation of the object. Returns an empty
        string if serialization fails.
    """
    try:
        return json.dumps(obj, **kwargs)
    except Exception as e:
        carb.log_error(f"Failed to convert object to json string. Exception: {e}")
        return ""


def from_json_str_safe(json_str: str) -> Any:
    """
    Safely converts a JSON string into a Python object.

    This function attempts to parse a JSON-encoded string into a corresponding
    Python object. If the input string is empty or an error occurs during parsing,
    it logs an error message and returns an empty list.

    Args:
        json_str (str): The JSON string to be converted.

    Returns:
        Any: A Python object resulting from the parsed JSON string. Returns an
        empty list if the input is empty or if parsing fails.
    """
    if not json_str or len(json_str) == 0:
        carb.log_error("JSON string is empty!")
        return []
    try:
        d = json.loads(json_str)
    except Exception as e:
        carb.log_error(f"Failed to load from JSON string. Exception: {e}")
        return []
    return d


def clamp_value(value: Any, min_value: Any, max_value: Any) -> Any:
    """Clamps value within the min and max range.

    Args:
        value: The value to be clamped.
        min_value: The minimum allowable value.
        max_value: The maximum allowable value.

    Returns:
        The clamped value within the specified range.
    """
    return max(min_value, min(value, max_value))


def obj_to_dict(obj: Any, attr_convert_fn: Optional[Callable[[str, Any], Any]] = None) -> Dict[str, Any]:
    """Converts an object instance to a dictionary.

    Converts object attributes to a dictionary, handling special cases for Enum and datetime types.
    Enum values are converted to their string names and datetime objects are converted to ISO format strings.
    Other attributes can be customized using an optional conversion function.

    Args:
        obj (Any): The object to convert to a dictionary.
        attr_convert_fn (Optional[Callable[[str, Any], Any]]): Optional function to convert attribute values.
            Takes attribute name and value as arguments and returns the converted value.

    Returns:
        Dict[str, Any]: Dictionary containing the object's attributes and their converted values.
    """
    from datetime import datetime
    from enum import Enum

    result = {}

    for attr_name, value in vars(obj).items():
        if isinstance(value, Enum):
            result[attr_name] = value.name
        elif isinstance(value, datetime):
            result[attr_name] = value.isoformat()
        else:
            if attr_convert_fn:
                result[attr_name] = attr_convert_fn(attr_name, value)
            else:
                result[attr_name] = value
    return result


def dict_to_obj(obj: Any, data: Dict[str, Any], attr_convert_fn: Optional[Callable[[str, Any], Any]] = None) -> bool:
    """Converts a dictionary to an object instance.

    Args:
        obj (Any): The target object to populate with dictionary data.
        data (Dict[str, Any]): The source dictionary containing attribute values.
        attr_convert_fn (Optional[Callable[[str, Any], Any]]): Optional function to convert attribute values.
            Takes attribute name and value as arguments and returns the converted value.

    Returns:
        bool: Always returns True to indicate successful conversion.
    """
    from datetime import datetime
    from enum import Enum

    if not isinstance(data, dict):
        carb.log_error(f"dict_to_obj: data parameter must be a dict, got {type(data)}")
        return False

    r = True
    for attr_name, value in data.items():
        try:
            attr_type = type(getattr(obj, attr_name))
            if issubclass(attr_type, Enum):
                if type(value) is str:
                    setattr(obj, attr_name, attr_type[value])
                else:
                    setattr(obj, attr_name, attr_type(value))
            elif attr_type is datetime:
                setattr(obj, attr_name, datetime.fromisoformat(value))
            else:
                if attr_convert_fn:
                    setattr(obj, attr_name, attr_convert_fn(attr_name, value))
                else:
                    setattr(obj, attr_name, value)
        except Exception as e:
            carb.log_error(f"Restore attribute error. Exception: {e}.")
            r = False
            continue
    return r


def measure_execution_time(func: Callable) -> Callable:
    """A decorator to measure execution time.

    Args:
        func (Callable): The function to measure.

    Returns:
        Callable: Wrapped function with execution time measurement.
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function {func.__name__} took {execution_time:.4f} seconds to execute.")
        return result

    return wrapper


class OptimizedProgressUpdate:
    """
    A utility class to manage progress updates efficiently by limiting excessive updates.

    This class determines whether a progress update should be propagated based on the elapsed
    time since the last update and the change in progress value. It ensures that updates are
    sent at a controlled rate, preventing unnecessary updates that could impact performance.

    Attributes:
        update_rate (float): Time interval (in seconds) between successive updates when the
            progress value changes. Default is 0.1 seconds.
        force_update_rate (float): Maximum allowable time interval (in seconds) before forcing
            an update, regardless of progress change. Default is 1.0 seconds.
        auto_start (bool): Whether to initialize progress tracking automatically upon instantiation.
            Default is True.

    Methods:
        start(): Resets the progress tracking state and allows immediate updates.
        update(progress_value: float) -> bool: Determines whether a given progress value warrants
            an update based on time and value change thresholds.
        progress_value: Property that returns the last recorded progress value.
    """

    def __init__(
        self,
        update_rate: float = 0.1,
        force_update_rate: float = 1.0,
        auto_start: bool = True
    ) -> None:
        """
        Initializes an instance of OptimizedProgressUpdate.

        Args:
            update_rate (float): Interval between updates when progress changes, in seconds. Default is 0.1.
            force_update_rate (float): Maximum interval before forcing an update, in seconds. Default is 1.0.
            auto_start (bool): If True, initializes progress tracking automatically. Default is True.
        """
        self._update_rate: float = update_rate
        self._force_update_rate: float = force_update_rate
        self._last_progress_value: float = 0
        self._last_update_time: float = 0
        if auto_start:
            self.start()

    @property
    def progress_value(self) -> float:
        """Gets the last recorded progress value.

        Returns:
            float: The last progress value between 0.0 and 1.0+
        """
        return self._last_progress_value

    def start(self):
        """
        Resets the progress tracking state.

        This method initializes or resets the internal state, ensuring that the first
        update is allowed immediately after calling this method.
        """
        self._last_progress_value = -1
        self._last_update_time = time.time() - self._update_rate

    def update(self, progress_value: float) -> bool:
        """
        Determines whether a progress update should be propagated.

        An update is triggered if either:
          - The elapsed time since the last update exceeds `force_update_rate`, or
          - The progress value has changed and the elapsed time exceeds `update_rate`.

        Args:
            progress_value (float): The current progress value as a fraction between 0.0 and 1.0.

        Returns:
            bool: True if an update should be propagated, False otherwise.
        """
        current_progress = progress_value
        current_time = time.time()
        elapsed = current_time - self._last_update_time

        if (
            elapsed >= self._force_update_rate
            or (current_progress != self._last_progress_value and elapsed >= self._update_rate)
        ):
            self._last_progress_value = current_progress
            self._last_update_time = current_time
            return True
        return False
