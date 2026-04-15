==============================
clash_detect_layer_utils
==============================

.. module:: omni.physxclashdetectioncore.clash_detect_layer_utils

This module provides helper utilities for managing clash detection layers in USD.

Classes
=======

ClashDetectLayerHelper
----------------------

.. class:: ClashDetectLayerHelper

   Static class with clash detect layer helper methods.

   This class provides methods for creating, removing, reloading, and managing clash detection layers within a USD stage.

   **Class Constants:**

   .. attribute:: CLASH_DETECT_FORMAT
      :type: str
      :value: "clashDetection"

      Format identifier for clash detection layers.

   .. attribute:: CLASH_DETECT_LAYER_PREFIX
      :type: str
      :value: "clashdata:"

      Prefix for clash detection layer identifiers.

   .. attribute:: CLASH_LAYER_IDENTIFIER
      :type: str
      :value: "clashdata:clashDetection"

      Full identifier for clash detection layers.

   **Methods:**

   .. method:: create_new_clash_detect_layer(stage: Usd.Stage, layer_path_name: str) -> Optional[Sdf.Layer]
      :classmethod:

      Creates a new clash detection layer.

      :param stage: The USD stage to which the layer is added.
      :type stage: Usd.Stage
      :param layer_path_name: The path name for the new layer.
      :type layer_path_name: str
      :return: The created clash detection layer, or None on failure.
      :rtype: Optional[Sdf.Layer]

   .. method:: get_sublayer_position_in_parent(parent_layer_identifier, layer_identifier) -> int
      :classmethod:

      Returns the position of a sublayer within its parent layer.

      :param parent_layer_identifier: The identifier of the parent layer.
      :type parent_layer_identifier: str
      :param layer_identifier: The identifier of the sublayer.
      :type layer_identifier: str
      :return: Position of the sublayer, or -1 if not found.
      :rtype: int

   .. method:: remove_sublayer(layer: Sdf.Layer, position: int) -> Optional[str]
      :staticmethod:

      Removes a sublayer from a specified position.

      :param layer: The layer from which to remove the sublayer.
      :type layer: Sdf.Layer
      :param position: The position of the sublayer to remove.
      :type position: int
      :return: Identifier of the removed sublayer, or None if removal failed.
      :rtype: Optional[str]

   .. method:: remove_layer(root_layer, layer_identifier) -> bool
      :classmethod:

      Removes a layer identified by layer_identifier from the root layer.

      :param root_layer: The root layer from which to remove the layer.
      :type root_layer: Sdf.Layer
      :param layer_identifier: The identifier of the layer to remove.
      :type layer_identifier: str
      :return: True if the layer was removed, False otherwise.
      :rtype: bool

   .. method:: reload_layer(layer: Sdf.Layer) -> bool
      :classmethod:

      Reloads the specified layer.

      :param layer: The layer to reload.
      :type layer: Sdf.Layer
      :return: True if the layer was successfully reloaded, False otherwise.
      :rtype: bool

   .. method:: find_clash_detect_layer(layer_path_name: str) -> Optional[Sdf.Layer]
      :classmethod:

      Returns the clash detection layer identified by path.

      :param layer_path_name: The path name of the clash detection layer.
      :type layer_path_name: str
      :return: The found clash detection layer, or None if not found.
      :rtype: Optional[Sdf.Layer]

   .. method:: get_custom_layer_data(layer) -> Optional[Dict[Any, Any]]
      :classmethod:

      Returns custom data of a layer as a dictionary.

      :param layer: The layer from which to get custom data.
      :type layer: Sdf.Layer
      :return: The custom data of the layer, or None if not found.
      :rtype: Optional[Dict[Any, Any]]

   .. method:: set_custom_layer_data(layer: Sdf.Layer, d: Optional[Dict[Any, Any]]) -> None
      :classmethod:

      Sets custom data for a layer using a dictionary.

      :param layer: The layer for which to set custom data.
      :type layer: Sdf.Layer
      :param d: The custom data to set.
      :type d: Optional[Dict[Any, Any]]

   .. method:: kit_remove_layer(stage: Usd.Stage, layer_identifier: str) -> bool
      :classmethod:

      Removes a layer using a Kit command, ensuring the Layer Widget is aware.

      :param stage: The USD stage from which to remove the layer.
      :type stage: Usd.Stage
      :param layer_identifier: The identifier of the layer to remove.
      :type layer_identifier: str
      :return: True if the layer was successfully removed, False otherwise.
      :rtype: bool

