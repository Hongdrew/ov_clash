"""pybind11 omni.physx.clashdetection.anim bindings"""
from __future__ import annotations
import omni.physxclashdetectionanim.bindings._clashDetectionAnim
import typing

__all__ = [
    "ICurveAnimRecorder",
    "RecordingReturnCode",
    "SESSION_SUBLAYER_NAME",
    "SETTINGS_LOGGING_ENABLED",
    "SETTINGS_LOGGING_ENABLED_DEFAULT",
    "acquire_stage_recorder_interface",
    "release_stage_recorder_interface"
]


class ICurveAnimRecorder():
    def clear_recording_scope(self) -> None: ...
    def get_recording_session_layer_name(self) -> str: ...
    def is_recording(self) -> bool: ...
    def reset_overridden_prim_deltas(self) -> bool: ...
    def set_recording_frame_num(self, arg0: int) -> None: ...
    @staticmethod
    @typing.overload
    def set_recording_scope(*args, **kwargs) -> typing.Any: ...
    @typing.overload
    def set_recording_scope(self, arg0: int, arg1: list) -> None: ...
    def start_recording(self) -> None: ...
    def stop_recording(self, arg0: bool, arg1: bool) -> RecordingReturnCode: ...
    pass
class RecordingReturnCode():
    """
    Members:

      RECORDING_SUCCESS

      NO_CHANGES_DETECTED

      PLUGIN_NOT_LOADED

      RECORDING_NOT_RUNNING

      TARGET_LAYER_ERROR

      ERROR_WRITING_USD
    """
    def __eq__(self, other: object) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: object) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    @property
    def name(self) -> str:
        """
        :type: str
        """
    @property
    def value(self) -> int:
        """
        :type: int
        """
    ERROR_WRITING_USD: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.ERROR_WRITING_USD: 5>
    NO_CHANGES_DETECTED: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.NO_CHANGES_DETECTED: 1>
    PLUGIN_NOT_LOADED: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.PLUGIN_NOT_LOADED: 2>
    RECORDING_NOT_RUNNING: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.RECORDING_NOT_RUNNING: 3>
    RECORDING_SUCCESS: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.RECORDING_SUCCESS: 0>
    TARGET_LAYER_ERROR: omni.physxclashdetectionanim.bindings._clashDetectionAnim.RecordingReturnCode # value = <RecordingReturnCode.TARGET_LAYER_ERROR: 4>
    __members__: dict # value = {'RECORDING_SUCCESS': <RecordingReturnCode.RECORDING_SUCCESS: 0>, 'NO_CHANGES_DETECTED': <RecordingReturnCode.NO_CHANGES_DETECTED: 1>, 'PLUGIN_NOT_LOADED': <RecordingReturnCode.PLUGIN_NOT_LOADED: 2>, 'RECORDING_NOT_RUNNING': <RecordingReturnCode.RECORDING_NOT_RUNNING: 3>, 'TARGET_LAYER_ERROR': <RecordingReturnCode.TARGET_LAYER_ERROR: 4>, 'ERROR_WRITING_USD': <RecordingReturnCode.ERROR_WRITING_USD: 5>}
    pass
def acquire_stage_recorder_interface(plugin_name: str = None, library_path: str = None) -> ICurveAnimRecorder:
    pass
def release_stage_recorder_interface(arg0: ICurveAnimRecorder) -> None:
    pass
SESSION_SUBLAYER_NAME = 'ClashStageRecordedData'
SETTINGS_LOGGING_ENABLED = '/persistent/physics/clashdetectionAnimLoggingEnabled'
SETTINGS_LOGGING_ENABLED_DEFAULT = '/defaults/persistent/physics/clashdetectionAnimLoggingEnabled'
