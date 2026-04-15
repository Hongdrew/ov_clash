# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from datetime import datetime
from typing import Callable, List, Tuple
import asyncio
import carb

__all__ = []


async def ui_wait(updates_cnt=10):
    """Async waits for updates_cnt UI updates.

    Args:
        updates_cnt: The number of updates to wait for.
    """
    import omni.kit.app

    for _ in range(updates_cnt):
        await omni.kit.app.get_app().next_update_async()  # type: ignore


def get_current_user_name():
    """Returns name of the currently logged in user.

    Returns:
        str: The name of the currently logged in user.
    """
    import getpass

    return getpass.getuser()


whole_string_encapsulation_ctrl_chars = "`"  # currently defined as a backquote but can be even more characters


def string_match(search_text: str, string: str, ctrl_chars: str = whole_string_encapsulation_ctrl_chars):
    """Returns True if search_text matches string.
        ctrl_chars define which special characters that encapsulate the search_text will trigger whole string matching.
        Else it performs a substring match.

    Args:
        search_text (str): The text to search for.
        string (str): The string to search within.
        ctrl_chars (str): Characters defining whole string encapsulation.

    Returns:
        bool: True if search_text matches, otherwise False.
    """
    if not search_text:
        return True
    if search_text.startswith(ctrl_chars) and search_text.endswith(ctrl_chars):
        search_text_clean = search_text[len(ctrl_chars): -len(ctrl_chars)]
        return search_text_clean == string
    return search_text in string


def get_time_delta_str(t: float) -> str:
    """Returns float time value in seconds (provided in t) converted to stopwatch time format.

    Args:
        t (float): The time in seconds to be converted.

    Returns:
        str: The converted time in stopwatch format.
    """
    import math

    if t == 0:
        return "00:00.00"

    ms, _ = math.modf(t)
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    ms = int(ms * 100)
    if h == 0:
        return f"{m:02d}:{s:02d}.{ms:02d}"
    else:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:02d}"


def get_datetime_str(dt: datetime) -> str:
    """Returns the most convenient date time format.

    Args:
        dt (datetime): The datetime object to be formatted.

    Returns:
        str: The formatted datetime string.
    """
    # way to get OV specific date formatting. unfortunately preferred time formatting is missing
    # from omni.kit.widget.filebrowser.date_format_menu import get_datetime_format
    # return dt.strftime(f"{get_datetime_format()} %H:%M:%S")  # or AM/PM format %I:%M:%S%p
    return dt.strftime("%X %x")


def get_yes_no_str(value: bool) -> str:
    """Returns 'Yes' if value is True, otherwise returns 'No'.

    Args:
        value (bool): The boolean value to be converted.

    Returns:
        str: 'Yes' if True, otherwise 'No'.
    """
    return "Yes" if value else "No"


def format_int_to_str(value: int) -> str:
    """Formats an integer value to a string with thousands separators.

    Args:
        value (int): The integer value to be formatted.

    Returns:
        str: The formatted integer string.
    """
    import locale

    locale.setlocale(locale.LC_ALL, '')  # Set locale to user's default setting (usually from the OS)
    return locale.format_string("%d", int(value), grouping=True)


def clean_path(path: str):
    """Cleans the provided path by removing redundant characters.

    Args:
        path (str): The path to be cleaned.

    Returns:
        str: The cleaned path.
    """
    if not path:
        return path
    if contains_url(path):  # do not touch urls
        return path
    return path.replace("file:/", "").replace("//", "/").replace("\\\\", "\\")


def contains_url(string: str) -> bool:
    """Returns True if string contains an URL.

    Args:
        string (str): The string to be checked for URLs.

    Returns:
        bool: True if the string contains a URL, otherwise False.
    """
    if not string:
        return False

    import re
    regex = re.compile(
        r"^(https?|ftp|sftp|omniverse)://"  # http:// https:// and other protocols or nothing
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    r = regex.match(string)
    return r is not None


def truncate_string(string: str, max_length: int):
    """Truncates given string to given max_length.

    Args:
        string (str): The string to truncate.
        max_length (int): The maximum length of the truncated string.

    Returns:
        str: The truncated string.
    """
    return string[:max_length] + ".." if len(string) > max_length + 2 else string


def pick_target_file(
    title: str,
    filters: List[Tuple[str, str]],
    extension: str,
    set_target_fnc: Callable[[str], None],
    button_label: str = "Save"
) -> None:
    """Opens a file picker dialog to select a target file.

    Args:
        title (str): The title of the file dialog window.
        filters (List[Tuple[str, str]]): A list of tuples containing file extensions and descriptions
            (e.g. [("*.json", "JSON Files"), ("*", "All Files")],) to filter files shown in the dialog.
        extension (str): The default file extension to append if none is provided (e.g. ".json").
        set_target_fnc (Callable[[str], None]): Callback function that receives the selected file path.
            The path will have the extension appended if none was provided.
        button_label (str, optional): Text to show on the dialog's action button. Defaults to "Save".

    Returns:
        None
    """
    from omni.kit.window.file_importer import get_file_importer
    import os

    def on_filter_item(filename: str, filter_postfix: str, filter_ext: str) -> bool:
        if filename:
            _, ext = os.path.splitext(filename)
            if filter_ext == "*":
                return True
            elif filter_ext == "*" + extension and ext == extension:
                return True
            else:
                return False
        return True

    def on_choose(
        file_name: str,
        dir_path: str,
        sel: List[str],
        default_extension: str,
        set_fnc: Callable[[str], None]
    ):
        base_path, ext = os.path.splitext(os.path.join(dir_path, file_name))
        if not ext:
            ext = default_extension
        file_path = base_path + ext
        if set_fnc:
            set_fnc(file_path)

    file_importer = get_file_importer()
    if file_importer:
        file_importer.show_window(
            title=title,
            import_button_label=button_label,
            import_handler=lambda file_name, dir_name, selections, ext=extension, fnc=set_target_fnc: on_choose(
                file_name, dir_name, selections, ext, fnc
            ),
            file_extension_types=filters,
            file_filter_handler=on_filter_item,
        )


def show_notification(
    msg: str,
    error: bool = False,
    duration: int = 5,
    also_write_log: bool = True,
    log_error_as_warning: bool = False,
):
    """Posts a notification message with optional logging.

    Args:
        msg (str): The message to display in the notification.
        error (bool): Whether the message is an error.
        duration (int): The duration to display the notification. -1 = do not hide automatically.
        also_write_log (bool): Whether to also write the message to the log.
        log_error_as_warning (bool): Whether to log the error as a warning.
    """
    import omni.kit.notification_manager as nm
    import carb

    if also_write_log:
        if error:
            if log_error_as_warning:
                carb.log_warn(msg)
            else:
                carb.log_error(msg)
        else:
            carb.log_info(msg)

    nm.post_notification(
        msg,
        status=nm.NotificationStatus.WARNING if error else nm.NotificationStatus.INFO,
        duration=duration if duration != -1 else 1,
        hide_after_timeout=duration != -1,
    )


def find_common_parent_path(prim_paths: List[str]) -> str:
    """
    Find the deepest common ancestor Sdf path for a list of prim path strings.

    Args:
        prim_paths (List[str]): List of Sdf prim path strings.

    Returns:
        str: The Sdf path string of the deepest common parent, or an empty string if no common parent exists.
    """
    if not prim_paths:
        return ""
    # Find the common ancestor by comparing paths
    paths = [prim for prim in prim_paths if prim]
    if not paths:
        return ""
    # Split each path into its elements
    split_paths = [list(str(p).split('/')) for p in paths]
    # Find the minimum length to avoid index errors
    min_len = min(len(parts) for parts in split_paths)
    # Find the common prefix
    common = []
    for i in range(min_len):
        segment = split_paths[0][i]
        if all(parts[i] == segment for parts in split_paths):
            common.append(segment)
        else:
            break
    if not common or common == ['']:
        return ""
    # Reconstruct the common path
    return '/'.join(common)


class DeferredAction:
    """A class that handles a deferred custom action call. If 'action' returns False, the task is finalized.

    Args:
        action (Callable[[], bool]): The custom action to be called.
        check_interval (float): The interval in seconds to check for the action.
    """

    def __init__(self, action: Callable[[], bool], check_interval: float = 0.1) -> None:
        """Initializes the DeferredAction instance."""
        self._next_action_at = None  # time when to trigger the action
        self._action = action  # if action returns False, task is then finalized
        self._check_interval = check_interval
        self._task = None
        self.start_task()

    def __del__(self):
        self.destroy()

    def destroy(self) -> None:
        """Cleans up resources and cancels the task."""
        self._next_action_at = None
        self.cancel_task()  # make sure we don't release while task is still running
        if self._task:
            self._task = None
        self._action = None

    def set_next_action_at(self, tm: datetime) -> None:
        """Schedules the next action at a specified time.

        Args:
            time (datetime): The time to trigger the action.
        """
        self._next_action_at = tm

    def start_task(self) -> None:
        """Starts the asynchronous task associated with this action."""
        self._task = asyncio.ensure_future(self._coroutine())

    def cancel_task(self) -> None:
        """Cancels the ongoing task if it is running."""
        if self._task:
            if not self._task.done():
                self._task.cancel()

    async def _coroutine(self) -> None:
        try:
            while True:
                if self._next_action_at is not None:
                    if datetime.now() >= self._next_action_at:
                        self._next_action_at = None
                        if not self._action:  # terminate the loop if no _action is set
                            break
                        if not self._action():  # terminate the loop if _action returned False
                            break
                await asyncio.sleep(self._check_interval)
        except asyncio.CancelledError:
            # task canceled
            pass
        except Exception as e:
            carb.log_error(f"_coroutine exception: {e}")
        finally:
            pass
