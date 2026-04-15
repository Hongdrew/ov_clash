# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Generator, List
import carb
from pxr import UsdUtils, Usd
from .config import ExtensionConfig
from ..bindings._clashDetectionAnim import (
    ICurveAnimRecorder,
    acquire_stage_recorder_interface,
    release_stage_recorder_interface,
    RecordingReturnCode,
    SESSION_SUBLAYER_NAME,
)


class AnimRecorder:
    """A class for recording animation curves within a USD stage.

    This class utilizes the ICurveAnimRecorder interface to record animation curves over a specified time range for a given set of USD prims. It supports functionalities such as starting and stopping recordings, resetting session properties, and configuring recording attributes.
    """

    def __init__(self) -> None:
        """Initializes the AnimRecorder instance."""
        self._recorder_api: ICurveAnimRecorder | None = acquire_stage_recorder_interface()
        self._copy_also_unrecorded_usd_attribs_on_save = False

    def destroy(self):
        """Releases the stage recorder interface and cleans up the recorder API."""
        if self._recorder_api:
            release_stage_recorder_interface(self._recorder_api)
            self._recorder_api = None

    @property
    def copy_also_unrecorded_usd_attribs_on_save(self) -> bool:
        """Gets whether to copy unrecorded USD attributes on save.

        Returns:
            bool: True if unrecorded attributes will be copied.
        """
        return self._copy_also_unrecorded_usd_attribs_on_save

    @copy_also_unrecorded_usd_attribs_on_save.setter
    def copy_also_unrecorded_usd_attribs_on_save(self, value: bool):
        """Sets whether to copy unrecorded USD attributes on save.

        Args:
            value (bool): If True, copies unrecorded attributes.
        """
        self._copy_also_unrecorded_usd_attribs_on_save = value

    def reset_overridden_session_prim_props(self) -> None:
        """Resets overridden session prim properties."""
        if self._recorder_api:
            self._recorder_api.reset_overridden_prim_deltas()

    def get_recording_session_layer_name(self) -> str:
        """Gets the name of the recording session layer.

        Returns:
            str: The name of the recording session layer.
        """
        if not self._recorder_api:
            return ""
        return self._recorder_api.get_recording_session_layer_name()

    def run(
        self, stage: Usd.Stage, prims_int_path: List[int], start_time: float, end_time: float, fps: float
    ) -> Generator[float, None, None]:
        """Records animation data for specified prims over a time range.

        Records animation curves for the given prims from start_time to end_time at the specified fps.
        The recording is saved to a session layer that can be accessed via get_recording_session_layer_name().
        Yields the current timeline time in seconds as recording progresses.

        Args:
            stage (Usd.Stage): The USD stage containing the prims to record
            prims_int_path (List[int]): List of integer prim paths to record
            start_time (float): Start time in seconds
            end_time (float): End time in seconds
            fps (float): Frames per second for the recording

        Returns:
            Generator[float, None, None]: Yields the current time in seconds as recording progresses

        Note:
            This is a generator method that yields the current timeline time in seconds.
            Recording results are saved to a session layer that can be accessed via get_recording_session_layer_name().
        """
        if not self._recorder_api:
            carb.log_error("Curve Anim Recorder is not initialized!")
            return

        if start_time > end_time:
            carb.log_error("start_time > end_time, nothing to record.")
            return

        start_frame: int = round(start_time * fps)
        end_frame: int = round(end_time * fps)

        if ExtensionConfig.debug_logging:
            carb.log_info(
                f"About to record anim starting at {start_time} ({int(start_frame)} frame), ending at {end_time} ({int(end_frame)} frame)"
            )

        if self._recorder_api.is_recording():
            self._recorder_api.stop_recording(True, False)

        self._recorder_api.set_recording_scope(UsdUtils.StageCache.Get().GetId(stage).ToLongInt(), prims_int_path)

        self._recorder_api.start_recording()
        if not self._recorder_api.is_recording():
            carb.log_error("Curve Anim Recorder failed to start recording!")
            return

        current_frame = 0
        for current_frame in range(start_frame, end_frame + 1):
            self._recorder_api.set_recording_frame_num(current_frame)
            yield float(current_frame) / fps

        rc: RecordingReturnCode = self._recorder_api.stop_recording(
            False, self.copy_also_unrecorded_usd_attribs_on_save
        )
        if rc != RecordingReturnCode.RECORDING_SUCCESS and rc != RecordingReturnCode.NO_CHANGES_DETECTED:
            carb.log_error(f"Curve anim recording to time samples failed with code {rc}")

        if ExtensionConfig.debug_logging:
            if rc == RecordingReturnCode.RECORDING_SUCCESS:
                carb.log_info(
                    f"Curve anim recording was successful, results were saved into {SESSION_SUBLAYER_NAME} session layer."
                )
            elif rc == RecordingReturnCode.NO_CHANGES_DETECTED:
                carb.log_info(
                    f"Curve anim recording detected no changes, {SESSION_SUBLAYER_NAME} session layer was not created (or was reset if already existing)."
                )

        self.reset_overridden_session_prim_props()
