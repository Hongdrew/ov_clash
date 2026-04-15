# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_info import ClashInfo
from .selection.clash_selection import ClashSelection
from typing import Sequence
import asyncio
import omni.kit
import tempfile
import omni.client
from pathlib import Path
import carb.settings
import traceback
import sys

__all__ = []


class ClashViewportBridge:
    """A class for managing the interaction between clash detection data and the viewport.

    This class provides mechanisms to display clash detection results in the viewport and handle selection and timecode changes.

    Args:
        clash_data (ClashData): The clash detection data to be used.
        clash_selection (ClashSelection): The selection handler for clash detection.
    """

    def __init__(self, clash_data: ClashData, clash_selection: ClashSelection):
        """Initializes the ClashViewportBridge instance."""
        self._clash_data = clash_data
        self._clash_selection = clash_selection
        self._clash_selection_sub = self._clash_selection.subscribe_to_selection_changes(
            self._on_clash_selection_changed
        )
        self._clash_timecode_sub = self._clash_selection.subscribe_to_timecode_changes(self._on_clash_timecode_change)

    def destroy(self):
        """Cleans up resources and subscriptions."""
        self._clash_selection_sub = None
        self._clash_timecode_sub = None
        self._clash_selection = None
        self._clash_data = None

    def _on_clash_selection_changed(self):
        self.display_clash_by_clash_info(self._clash_selection.selection, self._clash_selection.timecode) # type: ignore

    def display_clash_by_clash_info(self, clash_infos: Sequence[ClashInfo], timecode: float):
        """Displays a clash by its identifier.

        Args:
            overlap_id (Sequence[int]): The identifier of the overlap.
            timecode (float): The timecode for displaying the clash.
        """
            # display viewport meshes until the display limit is reached
        try:
            from omni.physxclashdetectionviewport import get_api_instance, ClashViewportSettings
            display_limit = carb.settings.get_settings().get_as_int(ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT)

            clash_viewport = get_api_instance()
            clash_info_items = {}
            for i, item in enumerate(clash_infos):
                clash_info_items[item.overlap_id] = item
                if i >= display_limit:
                    break
            clash_viewport.display_clashes(timecode, clash_info_items)
        except ModuleNotFoundError:
            pass
        except Exception as e:
            carb.log_error(e)
            carb.log_error(self._format_exception(e))

    def _format_exception(self, e):
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

        exception_str = "Traceback (most recent call last):\n"
        exception_str += "".join(exception_list)
        # Removing the last \n
        exception_str = exception_str[:-1]

        return exception_str

    def set_display_clashes_in_main_viewport(self, display_clashes_in_main_viewport: bool):
        """Sets whether to display clashes in the main viewport."""
        try:
            from omni.physxclashdetectionviewport import ClashViewportSettings
            carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, display_clashes_in_main_viewport)
            carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES, display_clashes_in_main_viewport)
        except ModuleNotFoundError:
            # Viewport extension not available, which is expected in some configurations
            pass
        except Exception as e:
            carb.log_error(f"Failed to set display clashes in main viewport: {e}")

    def _on_clash_timecode_change(self):
        self.hide_all_clash_meshes()

    def hide_all_clash_meshes(self):
        try:
            from omni.physxclashdetectionviewport import get_api_instance

            clash_viewport = get_api_instance()
            clash_viewport.hide_all_clash_meshes()
        except:
            pass

    def setup_for_screenshot_export(self):
        try:
            from omni.physxclashdetectionviewport import get_api_instance, ClashViewportSettings
        except:
            raise Exception("omni.physx.clashdetection.viewport extension not loaded")
        self.previous_main_viewport_show_clashes = carb.settings.get_settings().get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES)
        self.previous_clash_viewport_show_clashes = carb.settings.get_settings().get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES)
        self.previous_main_viewport_center_camera = carb.settings.get_settings().get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA)
        self.previous_clash_viewport_center_camera = carb.settings.get_settings().get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA)
        self.previous_main_viewport_enable_camera_tolerance = carb.settings.get_settings().get_as_bool(ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE)
        self.previous_clash_viewport_enable_camera_tolerance = carb.settings.get_settings().get_as_bool(ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE)
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, False)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, True)
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, False)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, True)
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE, False)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE, False)

    def teardown_for_screenshot_export(self):   
        try:
            from omni.physxclashdetectionviewport import get_api_instance, ClashViewportSettings
        except:
            raise Exception("omni.physx.clashdetection.viewport extension not loaded")
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, self.previous_main_viewport_show_clashes)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, self.previous_clash_viewport_show_clashes)
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, self.previous_main_viewport_center_camera)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, self.previous_clash_viewport_center_camera)
        carb.settings.get_settings().set_bool(ClashViewportSettings.MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE, self.previous_main_viewport_enable_camera_tolerance)
        carb.settings.get_settings().set_bool(ClashViewportSettings.CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE, self.previous_clash_viewport_enable_camera_tolerance)

    @staticmethod
    async def export_screenshot_to_file(
        clash_info: ClashInfo,
        timecode: float,
        clash_screenshot_path: str,
        current_export_index: int,
        total_number_of_exports: int,
        clear_frames: int = 5,
        render_frames: int = 100,
    ):
        """Exports a screenshot of the clash to a file.

        Args:
            clash_info (ClashInfo): Information about the clash.
            timecode (float): The timecode for the clash.
            clash_screenshot_path (str): Path to save the screenshot.
            current_export_index (int): Index of the current export.
            total_number_of_exports (int): Total number of exports.

        Returns:
            None

        Raises:
            Exception: If the viewport extension is not loaded or the viewport window is not created.
            asyncio.CancelledError: If the export operation is cancelled.
        """
        # Check if the viewport extension is enabled
        try:
            from omni.physxclashdetectionviewport import get_api_instance, ClashViewportSettings
            from omni.kit.viewport.utility import capture_viewport_to_file
            import omni.kit.app
            import omni.ui as ui
            import carb.settings

            clash_viewport = get_api_instance()
        except:
            raise Exception("omni.physx.clashdetection.viewport extension not loaded")

        # Make sure there is a valid clash viewport window initialized on screen
        if clash_viewport.clash_viewport_window:
            if not clash_viewport.clash_viewport_window.visible:
                clash_viewport.clash_viewport_window.visible = True
        else:
            carb.settings.get_settings().set_bool(ClashViewportSettings.SHOW_CLASH_VIEWPORT_WINDOW, True)
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async() # type: ignore
            try:
                clash_viewport.clash_viewport_window.dock_in(ui.Workspace.get_window("Property"), ui.DockPosition.SAME) # type: ignore
            except:
                pass
        if not clash_viewport.clash_viewport_window:
            raise Exception("omni.physx.clashdetection.viewport: Clash Viewport Window has not been created")

        # Try to actually grab a screenshot
        try:
            clashes = dict()
            clashes[clash_info.overlap_id] = clash_info
            omni.timeline.get_timeline_interface().set_current_time(timecode) # type: ignore
            for _ in range(clear_frames):
                await omni.kit.app.get_app().next_update_async() # type: ignore
            clash_viewport.display_clashes(
                clash_timecode=timecode,
                clash_info_items=clashes,
            )
            await ClashViewportBridge.__wait_for_stage_loading_status(
                clash_viewport.clash_viewport_window.viewport_api.usd_context, 15 # type: ignore
            )
            # wait quite some  frames for rendering, as translucent materials take a while to settle
            for _ in range(render_frames):
                await omni.kit.app.get_app().next_update_async() # type: ignore
            # Generate a random temporary png path in the temp directory
            temporary_path = tempfile.mktemp(suffix=".png", prefix="clash_screenshot_")

            async def check_if_file_exists(image_path: Path, max_timeout: float, poll_interval: float):
                if not image_path.exists():
                    exists = False
                    current_time_elapsed = 0
                    while current_time_elapsed < max_timeout:
                        await asyncio.sleep(poll_interval)
                        current_time_elapsed += poll_interval
                        if image_path.exists():
                            exists = True
                            break
                    if not exists:
                        raise Exception(
                            f"Timeout.\nTimeout while waiting for capture viewport to file:\n\n{temporary_path}"
                        )

            image_path = Path(temporary_path)

            capture = capture_viewport_to_file(clash_viewport.clash_viewport_window.viewport_api, temporary_path)
            await capture.wait_for_result()
            # wait_for_result doesn't tell when the file is actually written to disk, so we need to poll-checking
            await check_if_file_exists(image_path, 2, 0.05)  # max 2 seconds, poll every 50ms

            result = await omni.client.copy_async( # type: ignore
                temporary_path, clash_screenshot_path, omni.client.CopyBehavior.OVERWRITE # type: ignore
            )
            if result != omni.client.Result.OK: # type: ignore
                raise Exception(
                    f"Error {result}.\nFailed to copy file:\n\n{temporary_path}\n\nto\n\n{clash_screenshot_path}"
                )

            if current_export_index + 1 == total_number_of_exports:
                clash_viewport.hide_all_clash_meshes()  # Empty the viewport after last item processed
        except asyncio.CancelledError as e:  # User Clicked to cancel current export operation
            clash_viewport.hide_all_clash_meshes()  # Empty the viewport on async cancellation
            raise e

    @staticmethod
    async def __wait_for_stage_loading_status(usd_context, wait_frames):
        max_loops = 0
        while max_loops < wait_frames:
            _, files_loaded, total_files = usd_context.get_stage_loading_status()
            await omni.kit.app.get_app().next_update_async() # type: ignore
            if files_loaded or total_files:
                continue
            max_loops = max_loops + 1
