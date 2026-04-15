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
from typing import Optional, Dict, Any
from pxr import Usd, Sdf
import omni.client


class ClashDetectLayerHelper:
    """Static class with clash detect layer helper methods.

    This class provides methods for creating, removing, reloading, and managing clash detection layers within a USD stage.
    """

    CLASH_DETECT_FORMAT = "clashDetection"
    CLASH_DETECT_LAYER_PREFIX = "clashdata:"
    CLASH_LAYER_IDENTIFIER = f"{CLASH_DETECT_LAYER_PREFIX}{CLASH_DETECT_FORMAT}"

    @classmethod
    def create_new_clash_detect_layer(cls, stage: Usd.Stage, layer_path_name: str) -> Optional[Sdf.Layer]:
        """Creates a new clash detection layer.

        Args:
            stage (Usd.Stage): The USD stage to which the layer is added.
            layer_path_name (str): The path name for the new layer.

        Returns:
            Optional[Sdf.Layer]: The created clash detection layer, or None on failure.
        """
        file_format = Sdf.FileFormat.FindById(cls.CLASH_DETECT_FORMAT)
        if not file_format:
            carb.log_error(f"Clash detection layer format '{cls.CLASH_DETECT_FORMAT}' does not exist!")
            return None
        if not stage:
            return None
        clash_detection_layer = None
        layer_fmt_args = {
            "format": cls.CLASH_DETECT_FORMAT,
        }
        if layer_path_name:
            existing_layer = Sdf.Layer.Find(layer_path_name)
            if existing_layer:
                return existing_layer
            # add disk based layer
            try:
                clash_detection_layer = Sdf.Layer.CreateNew(layer_path_name, args=layer_fmt_args)  # type: ignore
            except Exception as e:
                carb.log_error(f"Create new layer failed with exception: '{e}'.\nLayer path: '{layer_path_name}'")
        else:
            # add in-memory layer
            existing_layer = Sdf.Layer.Find(cls.CLASH_LAYER_IDENTIFIER)
            if existing_layer:
                return existing_layer
            # Use Sdf.Layer.New over Sdf.Layer.CreateNew so we don't try to write the URL to disk
            try:
                clash_detection_layer = Sdf.Layer.CreateAnonymous(
                    cls.CLASH_LAYER_IDENTIFIER, file_format, args=layer_fmt_args
                )
            except Exception as e:
                carb.log_error(
                    f"Create new anonymous in-memory layer failed with exception: '{e}'.\nLayer identifier: '{cls.CLASH_LAYER_IDENTIFIER}'"
                )

        if clash_detection_layer:
            root_layer = stage.GetRootLayer()
            preexisting_layer = False
            clash_detection_layer_relative_path = omni.client.utils.make_relative_url_if_possible(
                root_layer.identifier, root_layer.ComputeAbsolutePath(clash_detection_layer.identifier)
            )
            try:
                root_layer.subLayerPaths.append(clash_detection_layer_relative_path)
            except Exception as e:
                # Duplicated layer?
                # This can happen when there is already a layer with the same path (it might have failed to load)
                carb.log_info(
                    f"Could not append layer, will try to remove any pre-existing layer '{clash_detection_layer.identifier}'.\nReason: {e}"
                )
                preexisting_layer = True
            if preexisting_layer:
                try:
                    cls.remove_layer(root_layer, clash_detection_layer.identifier)
                    root_layer.subLayerPaths.append(clash_detection_layer_relative_path)
                except Exception as e:
                    carb.log_error(
                        f"Failed to insert new clashDetection layer '{clash_detection_layer.identifier}' under root with exception:\n{e}"
                    )
            return clash_detection_layer
        else:
            carb.log_error(f"Failed to create clashDetection layer: '{layer_path_name}'")
            return None

    @classmethod
    def get_sublayer_position_in_parent(cls, parent_layer_identifier, layer_identifier) -> int:
        """Returns the position of a sublayer within its parent layer.

        Args:
            parent_layer_identifier (str): The identifier of the parent layer.
            layer_identifier (str): The identifier of the sublayer.

        Returns:
            int: Position of the sublayer, or -1 if not found.
        """
        parent_layer = Sdf.Find(parent_layer_identifier)  # type: ignore
        if not parent_layer:
            return -1
        sublayer_paths = parent_layer.subLayerPaths
        layer_identifier = parent_layer.ComputeAbsolutePath(layer_identifier)
        for i in range(len(sublayer_paths)):
            sublayer_path = sublayer_paths[i]
            sublayer_identifier = parent_layer.ComputeAbsolutePath(sublayer_path)
            if sublayer_identifier == layer_identifier:
                return i
        return -1

    @staticmethod
    def remove_sublayer(layer: Sdf.Layer, position: int) -> Optional[str]:
        """Removes a sublayer from a specified position.

        Args:
            layer (Sdf.Layer): The layer from which to remove the sublayer.
            position (int): The position of the sublayer to remove.

        Returns:
            Optional[str]: Identifier of the removed sublayer, or None if removal failed.
        """
        if len(layer.subLayerPaths) == 0:  # type: ignore
            return None
        if position < 0 or position >= len(layer.subLayerPaths):  # type: ignore
            return None
        layer_identifier = layer.ComputeAbsolutePath(layer.subLayerPaths[position])  # type: ignore
        del layer.subLayerPaths[position]  # type: ignore
        return layer_identifier

    @classmethod
    def remove_layer(cls, root_layer, layer_identifier) -> bool:
        """Removes a layer identified by layer_identifier from the root layer.

        Args:
            root_layer (Sdf.Layer): The root layer from which to remove the layer.
            layer_identifier (str): The identifier of the layer to remove.

        Returns:
            bool: True if the layer was removed, False otherwise.
        """
        if not root_layer or not layer_identifier:
            return False
        # root_layer.subLayerPaths.remove(layer.identifier) <- this does not always work
        position = cls.get_sublayer_position_in_parent(root_layer.identifier, layer_identifier)
        if position != -1:
            return layer_identifier == cls.remove_sublayer(root_layer, position)
        return False

    @classmethod
    def reload_layer(cls, layer: Sdf.Layer) -> bool:
        """Reloads the specified layer.

        Args:
            layer (Sdf.Layer): The layer to reload.

        Returns:
            bool: True if the layer was successfully reloaded, False otherwise.
        """
        if layer:
            try:
                return layer.Reload(True)
            except Exception as e:
                carb.log_info(f"Could not reload layer '{layer}'.\nReason: {e}")
                return False
        return False

    @classmethod
    def find_clash_detect_layer(cls, layer_path_name: str) -> Optional[Sdf.Layer]:
        """Returns the clash detection layer identified by path.

        Args:
            layer_path_name (str): The path name of the clash detection layer.

        Returns:
            Optional[Sdf.Layer]: The found clash detection layer, or None if not found.
        """
        return Sdf.Layer.Find(layer_path_name if layer_path_name else cls.CLASH_LAYER_IDENTIFIER)

    @classmethod
    def get_custom_layer_data(cls, layer) -> Optional[Dict[Any, Any]]:
        """Returns custom data of a layer as a dictionary.

        Args:
            layer (Sdf.Layer): The layer from which to get custom data.

        Returns:
            Optional[Dict[Any, Any]]: The custom data of the layer, or None if not found.
        """
        if not layer:
            return None
        d = layer.customLayerData
        return d

    @classmethod
    def set_custom_layer_data(cls, layer: Sdf.Layer, d: Optional[Dict[Any, Any]]) -> None:
        """Sets custom data for a layer using a dictionary.

        Args:
            layer (Sdf.Layer): The layer for which to set custom data.
            d (Optional[Dict[Any, Any]]): The custom data to set.
        """
        if not layer:
            return None
        layer_data = layer.customLayerData
        if layer_data:
            layer_data.update(d)
        else:
            layer_data = d
        layer.customLayerData = layer_data  # type: ignore

    @classmethod
    def kit_remove_layer(cls, stage: Usd.Stage, layer_identifier: str) -> bool:
        """Removes a layer using a Kit command, ensuring the Layer Widget is aware.

        Args:
            stage (Usd.Stage): The USD stage from which to remove the layer.
            layer_identifier (str): The identifier of the layer to remove.

        Returns:
            bool: True if the layer was successfully removed, False otherwise.
        """
        if not layer_identifier:
            return False
        kit_cmd_performed = False
        referenced = False
        try:
            # the kit command works on omni usd stage so if it's not available then we can skip it.
            # the stage passed as param cannot be used here but in the non-kit version.
            import omni
            import omni.usd
            import omni.kit.commands

            ctx = omni.usd.get_context()
            if ctx:
                stage = ctx.get_stage()  # type: ignore
                if stage:
                    root_layer = stage.GetRootLayer()
                    if not root_layer:
                        return False
                    pos = cls.get_sublayer_position_in_parent(root_layer.identifier, layer_identifier)
                    if pos == -1:
                        # carb.log_info(f"Could not find layer '{layer_identifier}'.")
                        return False  # layer not found
                    referenced = True
                    # perform the command
                    omni.kit.commands.execute(
                        "RemoveSublayer",
                        layer_identifier=root_layer.identifier,
                        sublayer_position=ClashDetectLayerHelper.get_sublayer_position_in_parent(
                            root_layer.identifier, layer_identifier
                        ),
                    )
                    kit_cmd_performed = True
        except Exception as e:
            carb.log_info(f"Could not remove layer '{layer_identifier}'.\nReason: {e}")

        if kit_cmd_performed:
            return True if referenced else False

        # non-kit layer remove
        if not stage:
            return False
        root_layer = stage.GetRootLayer()
        if not root_layer:
            return False
        try:
            return cls.remove_layer(root_layer, layer_identifier)
        except Exception as e:
            carb.log_info(f"Could not remove layer '{layer_identifier}'.\nReason: {e}")
            return False
