# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from datetime import datetime, timedelta
import carb
import carb.settings
from carb.eventdispatcher import get_eventdispatcher
from pxr import Usd
import omni.client
import omni.kit.usd.layers as usd_layers
import omni.kit.notification_manager as nm
from omni.physxclashdetectioncore.clash_data import ClashData
from omni.physxclashdetectioncore.clash_data_serializer import AbstractClashDataSerializer
from omni.physxclashdetectioncore.clash_detect_layer_utils import ClashDetectLayerHelper
from .usd_utils import omni_get_current_stage_id
from .utils import DeferredAction, show_notification
from .settings import ExtensionSettings

__all__ = []


class ClashDataUI(ClashData):
    """A class for managing and interacting with clash data within a USD stage.

    This class extends the functionality of ClashData to provide additional
    methods and utilities for handling user interface-related tasks, such as
    notifications and layer management. It ensures that the clash data is
    compatible with the serializer and provides mechanisms for resetting and
    resolving incompatibilities.

    Args:
        clash_data_serializer (AbstractClashDataSerializer): The serializer used
            for managing the serialization and deserialization of clash data.
    """

    def __init__(self, clash_data_serializer: AbstractClashDataSerializer) -> None:
        """Initializes the ClashDataUI class."""
        super().__init__(clash_data_serializer)
        self._incompatibility_notification = None
        self.__layers_event_sub = None
        layers = usd_layers.get_layers()
        if layers:
            self.__layers_event_sub = [
                get_eventdispatcher().observe_event(
                    observer_name="ClashDataUI Layer Event",
                    event_name=usd_layers.layer_event_name(event),
                    on_event=self.__on_layer_event,
                    filter=layers.get_event_key()
                )
                for event in (
                    usd_layers.LayerEventType.OUTDATE_STATE_CHANGED,  # type: ignore
                    usd_layers.LayerEventType.PRIM_SPECS_CHANGED,  # type: ignore
                    usd_layers.LayerEventType.AUTO_RELOAD_LAYERS_CHANGED,  # type: ignore
                )
            ]
        self._deferred_action = None

    def destroy(self) -> None:
        """Cleans up resources and dismisses notifications."""
        if self._deferred_action:
            self._deferred_action.destroy()
            self._deferred_action = None
        self.__layers_event_sub = None
        self.dismiss_notifications()
        super().destroy()

    def _on_layer_reload(self) -> bool:
        if not self._target_layer:
            return False
        if not self._target_layer.anonymous:
            if ExtensionSettings.debug_logging:
                carb.log_info(
                    f"Reloading clash detection UI because of a change in layer '{self._target_layer.identifier}'."
                )
            self.stage_opened()
            carb.settings.get_settings().set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh
        if self._deferred_action:
            self._deferred_action.destroy()
            self._deferred_action = None
        return False

    def __on_layer_event(self, event) -> None:
        """This is only here to clean-up old clash data dbs from local temp folder."""
        payload = usd_layers.get_layer_event_payload(event)
        if not payload or not payload.success:
            return
        if (
            payload.event_type == usd_layers.LayerEventType.OUTDATE_STATE_CHANGED  # type: ignore
            or payload.event_type == usd_layers.LayerEventType.PRIM_SPECS_CHANGED  # type: ignore # this seems to be triggered when reloading the clash detection layer
            or payload.event_type == usd_layers.LayerEventType.AUTO_RELOAD_LAYERS_CHANGED  # type: ignore
        ):
            reload = self._target_layer is not None and self._target_layer.identifier == payload.layer_identifier
            # handle special case when stage got externally added a clash detection layer which was not there previously
            if (not reload and self._target_layer is None) or (self._target_layer and self._target_layer.anonymous):
                usd_file_path = self._usd_file_path
                if not usd_file_path and self.stage:
                    root_layer = self.stage.GetRootLayer()
                    usd_file_path = root_layer.identifier if root_layer.realPath else None
                if usd_file_path:
                    clash_layer_path_name = self._compose_target_layer_path_name(usd_file_path)
                    target_layer = ClashDetectLayerHelper.find_clash_detect_layer(clash_layer_path_name)
                    if target_layer:
                        self._target_layer = target_layer
                        reload = True
            if reload:
                # clash detection layer got reloaded
                if not self._deferred_action:
                    self._deferred_action = DeferredAction(self._on_layer_reload)
                self._deferred_action.set_next_action_at(datetime.now() + timedelta(seconds=1.0))

    # override
    def _remove_layer(self, stage: Usd.Stage, layer_identifier: str) -> bool:
        # We are dealing with 2 options here:
        # 1. the layer is completely missing, but it's referenced by the stage -> remove it from layer references.
        # 2. the layer is corrupted, it failed to load, but it is not present in the filesystem -> delete it from there.
        if layer_identifier and stage:
            result, entry = omni.client.stat(layer_identifier)
            existing = result != omni.client.Result.ERROR_NOT_FOUND
            removed = super()._remove_layer(stage, layer_identifier)
            if (
                existing or removed
            ):  # if USD referenced a non-existing layer, its reference will be removed from the stage
                show_notification(f"Removed invalid clash detection layer\n'{layer_identifier}'", True, 10)
                return True
        return False

    def migrate_clash_data(self, clash_data_path: str) -> None:
        """Migrates the clash data to the latest version.

        Args:
            clash_data_path (str): Path to the clash data.
        """
        if not self._target_layer or not self._serializer or not clash_data_path:
            return

        if self._serializer.migrate_data_structures_to_latest_version(clash_data_path):
            show_notification(f"Clash data were migrated to the latest version successfully.")
        else:
            show_notification(f"Failed to migrate clash data to the latest version!\nSee log for more details.", True, 10)

        self._serializer.open(clash_data_path)
        carb.settings.get_settings().set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh

    def reset_clash_data(self, clash_data_path: str) -> None:
        """Removes the clash data from disk and creates new data.

        Args:
            clash_data_path (str): Path to the clash data.
        """
        if not self._target_layer or not self._serializer or not clash_data_path:
            return
        result, entry = omni.client.stat(clash_data_path)
        if result != omni.client.Result.ERROR_NOT_FOUND and self._serializer:
            self._serializer.close()
            omni.client.delete(clash_data_path)
            deferred_file_creation_until_first_write_op_prev_val = self.deferred_file_creation_until_first_write_op
            self.deferred_file_creation_until_first_write_op = False  # create the file immediately
            self._serializer.open(clash_data_path)
            self.deferred_file_creation_until_first_write_op = deferred_file_creation_until_first_write_op_prev_val
            carb.settings.get_settings().set_bool(ExtensionSettings.SETTING_RELOAD_UI, True)  # trigger the UI refresh

    def resolve_clash_data_incompatibility_user_action(self, clash_data_path: str):
        """Shows a floating notification for clash data incompatibility to the user.

        Args:
            clash_data_path (str): Path to the clash data.
        """
        self.dismiss_notifications()
        if not self.data_structures_compatible:
            if not self._target_layer or not self._serializer or not clash_data_path:
                return

            # Determine which operation is possible and set message/button accordingly
            if not self.data_structures_migration_to_latest_version_possible:
                message_text = (
                    "Press RESET button to reset the clash data to supported version.\n\n"
                    "Please note that RESET operation will destroy all the clash data and it cannot be undone!\n\n"
                )
                action_button = nm.NotificationButtonInfo(
                    "RESET", on_complete=lambda p=clash_data_path: self.reset_clash_data(p),  # type: ignore
                )
            else:
                message_text = "Press MIGRATE button to migrate the clash data\nto the latest version.\n\n"
                action_button = nm.NotificationButtonInfo(
                    "MIGRATE", on_complete=lambda p=clash_data_path: self.migrate_clash_data(p),  # type: ignore
                )

            self._incompatibility_notification = nm.post_notification(
                "Unsupported version of Clash Data!\n\n" + message_text,
                status=nm.NotificationStatus.WARNING,
                hide_after_timeout=False,
                button_infos=[action_button, nm.NotificationButtonInfo("CANCEL")],
            )

    def check_compatibility(self):
        """Determines if clash data is compatible with the serializer."""
        # Resolve clash data compatibility issue if there is any
        self.dismiss_notifications()
        clash_data_path = self.serializer_path
        _ = self.find_query(0)  # force clash data read access by calling this harmless query
        if not self.data_structures_compatible:
            self.resolve_clash_data_incompatibility_user_action(clash_data_path)

    def stage_opened(self, force_reload_clash_detect_layer: bool = False):
        """Handles actions when the stage is opened.

        Args:
            force_reload_clash_detect_layer (bool): Whether to force reload the clash detection layer.
        """
        stage_id = omni_get_current_stage_id()
        self.open(stage_id, force_reload_clash_detect_layer)
        self.check_compatibility()

    def dismiss_notifications(self):
        """Hides previous notifications."""
        if self._incompatibility_notification:
            self._incompatibility_notification.dismiss()
            self._incompatibility_notification = None
