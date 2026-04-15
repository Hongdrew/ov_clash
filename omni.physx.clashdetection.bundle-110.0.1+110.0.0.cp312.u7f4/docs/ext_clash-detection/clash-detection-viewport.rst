.. _Clash_Detection_Viewport:

============================
Clash Detection Viewport API
============================

The Clash Detection Viewport extension implements an API to display meshes that are detected to be in clash (both soft and hard clash) and duplicate meshes in the main viewport and a dedicated viewport.

It has functionality to modify the camera in the main viewport and the dedicated clash viewport to center it on the clash area (if it exists).

Visualization
-----------------------

After clicking on a clash, the two meshes will change their appearance in the main viewport.
The two clashing meshes will be displayed in isolation from the rest of the stage also in the **Clash Detection Viewport** (if enabled).
The appearance of the meshes will depend on the settings of the **Clash Viewport** menu.

.. note:: The appearance of the meshes will be restored when deselecting a clash.

Enable Selection Groups ON (Default)
*******************************************

When using selection groups:

- The original source meshes will be put into a custom selection group to show them as an overlay over the original meshes. This is useful to see through occluded objects.
- Clash intersection profile will be shown in light-independent (emissive) purple.

.. tab-set::

    .. tab-item:: Hard Clash Before
        :sync: key8

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-group-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Hard Clash After
        :sync: key9

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-group-1.png

Enable Selection Groups OFF
*******************************************

.. warning:: This option is deprecated. It will be disabled by default and it will not be possible to enable it in future releases.

For Soft and Hard Clashes:

- The two meshes of the clash will be displayed using different colors (light blue and light orange).
- Non-clashing polygons composing the mesh will be drawn:
    - **Main Viewport**: non-clashing polygons will be shown with a flat shaded look
    - **Clash Viewport**: non-clashing polygons will be shown with a transparent material to avoid occluding the clash profile.

- Clashing polygons composing the mesh will be drawn:

    - **Main Viewport**: clashing polygons will be shown with an overlapping black wireframe and a light-independent look (emissive).
    - **Clash Viewport**: clashing polygons will be shown with non-transparent diffuse material.

For Hard Clashes Only:

- Clash intersection profile will be shown in light-independent (emissive) purple.

.. tab-set::

    .. tab-item:: Hard Clash Before
        :sync: key1

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Hard Clash After
        :sync: key1

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-1.png


.. tab-set::

    .. tab-item:: Soft Clash Before
        :sync: key2

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-soft-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Soft Clash After
        :sync: key2

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-soft-1.png


For Duplicates:

- Duplicated mesh will be displayed using light blue with overlapped wireframe
- If the first duplicated mesh is missing, the duplicate will be shown in orange

.. tab-set::

    .. tab-item:: Detected Duplicate Before
        :sync: key3

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-duplicate-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Detected Duplicate After
        :sync: key3

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-select-duplicate-1.png


Clash Viewport Menu
-----------------------

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-menu.png

The Clash Viewport menu button is located in the top right corner of the main and clash viewports.
Clicking it will open the menu that contains the following settings:

Camera
*******************************************
- **Center main viewport**: When enabled, the camera in the main viewport will be centered on the selected clash (``ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA``).
- **Center clash viewport**: When enabled, the camera in the clash viewport will be centered on the selected clash (``ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA``).
- **Re-centering far tolerance**: Positive tolerance that will prevent camera from being re-centered (from current position) when selecting a clash (``ClashViewportSettings.CAMERA_CENTERING_FAR_TOLERANCE``).
- **Re-centering near tolerance**: Negative tolerance that will prevent camera from being re-centered (from current position) when selecting a clash (``ClashViewportSettings.CAMERA_CENTERING_NEAR_TOLERANCE``).

.. note:: Set both tolerances to 0 to always re-center no matter the distance.

Main Viewport
*******************************************
- **Enable selection groups**: When enabled, the original source meshes will be put into a custom selection group to show them as an overlay over the original meshes. This is useful to see through occluded objects (``ClashViewportSettings.MAIN_VIEWPORT_USE_SELECTION_GROUPS``).

.. warning:: This option is deprecated. It will be enabled by default and it will not be possible to disable it in future releases.

- **Fill selection groups**: When enabled, fills selection groups with a semi-transparent solid color. Disable this option to improve depth perception of highlighted clashes (``ClashViewportSettings.CLASH_HIGHLIGHT_FILLED_MESHES``).
- **Show clash meshes**: When enabled, the clash meshes will be displayed in the main viewport (``ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES``).
- **Show clash outlines**: When enabled, the clash outlines will be displayed in the main viewport (``ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_OUTLINES``).

Clash Viewport
*******************************************
- **Show meshes and outlines**: When enabled, the meshes and outlines will be displayed in the clash viewport (``ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES``).
- **Show wireframes**: When enabled, wireframes will be displayed for clash meshes in the clash viewport (``ClashViewportSettings.CLASH_VIEWPORT_SHOW_WIREFRAMES``).
- **Use translucent materials**: When enabled, the meshes will be displayed with a transparent material to avoid occluding the clash profile (``ClashViewportSettings.CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS``).

Advanced
*******************************************
- **Log profile**: When enabled, prints the timings of the clash viewport to the console (``ClashViewportSettings.LOG_PROFILE``).
- **Log highlight**: When enabled, prints logs of clash viewport highlight process to the console (``ClashViewportSettings.LOG_HIGHLIGHT``).
- **Max displayed clashes**: The maximum number of clashes to display in the main and clash viewports. Only obeyed when 'Show clash meshes' is disabled or 'Use selection groups' is enabled (``ClashViewportSettings.CLASH_MESHES_DISPLAY_LIMIT``).
- **Outline size**: Size of the outline in world space (``ClashViewportSettings.CLASH_OUTLINE_WIDTH_SIZE``).
- **Outline scale**: Scale factor for the outline width (``ClashViewportSettings.CLASH_OUTLINE_WIDTH_SCALE``).
- **Outline min centering**: Minimum diagonal length for clash outline to be considered for camera centering (``ClashViewportSettings.CLASH_OUTLINE_DIAGONAL_MIN_CENTERING``).
- **Wireframe thickness**: Thickness of the wireframe in screen space (``ClashViewportSettings.CLASH_WIREFRAME_THICKNESS``).

Settings Reference
-----------------------

All options of the Clash Viewport menu are available as ``carb.settings`` constants.
The following table shows the mapping between ClashViewportSettings constants and their corresponding settings paths:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - **Setting Constant**
     - **Settings Path**
   * - ``SHOW_CLASH_VIEWPORT_WINDOW``
     - ``/physics/clashDetectionViewport/showClashViewport``
   * - ``USE_SOURCE_NORMALS``
     - ``/physics/clashDetectionViewport/useSourceNormals``
   * - ``CAMERA_CENTERING_FAR_TOLERANCE``
     - ``/physics/clashDetectionViewport/cameraCenteringFarTolerance``
   * - ``CAMERA_CENTERING_NEAR_TOLERANCE``
     - ``/physics/clashDetectionViewport/cameraCenteringNearTolerance``
   * - ``CLASH_WIREFRAME_THICKNESS``
     - ``/physics/clashDetectionViewport/wireframeThickness``
   * - ``CLASH_OUTLINE_WIDTH_SIZE``
     - ``/physics/clashDetectionViewport/outlineWidthSize``
   * - ``CLASH_OUTLINE_WIDTH_SCALE``
     - ``/physics/clashDetectionViewport/outlineWidthScale``
   * - ``CLASH_OUTLINE_DIAGONAL_MIN_CENTERING``
     - ``/physics/clashDetectionViewport/outlineDiagonalMinCentering``
   * - ``CLASH_MESHES_DISPLAY_LIMIT``
     - ``/physics/clashDetectionViewport/clashMeshesDisplayLimit``
   * - ``MAIN_VIEWPORT_USE_SELECTION_GROUPS``
     - ``/physics/clashDetectionViewport/mainViewport/useSelectionGroups``
   * - ``MAIN_VIEWPORT_SHOW_CLASH_OUTLINES``
     - ``/physics/clashDetectionViewport/mainViewport/showClashOutlines``
   * - ``MAIN_VIEWPORT_SHOW_CLASH_MESHES``
     - ``/physics/clashDetectionViewport/mainViewport/showClashMeshes``
   * - ``MAIN_VIEWPORT_CENTER_CAMERA``
     - ``/physics/clashDetectionViewport/mainViewport/centerCamera``
   * - ``MAIN_VIEWPORT_ENABLE_CAMERA_TOLERANCE``
     - ``/physics/clashDetectionViewport/mainViewport/enableCameraTolerance``
   * - ``CLASH_VIEWPORT_SHOW_CLASHES``
     - ``/physics/clashDetectionViewport/clashViewport/showClashes``
   * - ``CLASH_VIEWPORT_SHOW_WIREFRAMES``
     - ``/physics/clashDetectionViewport/clashViewport/showWireframes``
   * - ``CLASH_VIEWPORT_USE_TRANSLUCENT_MATERIALS``
     - ``/physics/clashDetectionViewport/clashViewport/useTranslucentMaterials``
   * - ``CLASH_HIGHLIGHT_FILLED_MESHES``
     - ``/physics/clashDetectionViewport/clashViewport/highlightFilledMeshes``
   * - ``CLASH_VIEWPORT_CENTER_CAMERA``
     - ``/physics/clashDetectionViewport/clashViewport/centerCamera``
   * - ``CLASH_VIEWPORT_ENABLE_CAMERA_TOLERANCE``
     - ``/physics/clashDetectionViewport/clashViewport/enableCameraTolerance``
   * - ``LOG_PROFILE``
     - ``/physics/clashDetectionViewport/logProfile``
   * - ``LOG_HIGHLIGHT``
     - ``/physics/clashDetectionViewport/logHighlight``

These settings can be accessed programmatically using ``carb.settings.get_settings()`` as shown in the example code below.


Camera Centering
-----------------------

The clash viewport automatically centers the camera on the clash area when a clash is selected.

The camera re-centering follows this logic:

- If there is a valid outline larger than **Outline min centering**, the camera will be centered on the outline.
- If there is no valid outline, the camera will be centered on one of the two clashing meshes.
    - A mesh is considered *smaller* than another if the squared sum of its bounding box sides is three times smaller than the same calculation for the other mesh.
    - If ``Enable selection groups`` is enabled, the camera will be centered on the smallest source mesh (the original mesh that has been marked as clashing).
    - If ``Enable selection groups`` is disabled, the camera will be centered on the smallest clash mesh (mesh composed of the polygons that are in clash with the other mesh).


Performance
-----------------------

The performance of the clash detection viewport is affected by the following factors:

- Stage size in number of meshes
- Stage size in number of polygons
- Complexity of the meshes (in terms of generated overdraw when using Translucent Materials)
- Console warnings (and file logging)

Extended blocking of the main loop
***********************************

.. warning::
    Large stages can cause performance issues when ``Enable selection groups`` is disabled.
    Some stages that are incorrectly exported can print hundreds of thousands of warnings to the console (and in the log) that can affect performance.

    - Disable ``Show clash outlines`` and leave ``Enable selection groups`` enabled to avoid any kind of USD recomposition when switching results.
    - Disable ``Show clash meshes``, ``Show clash outlines`` and ``Show meshes and outlines`` to remove all visualization in both viewports.
    - Disabling and re-enabling some options will cause detach and re-attach of the clash session Layer.
    - Consider changing the options before loading the stage to avoid any performance issues.

Low FPS
***********************************

.. warning::
    For some large meshes the translucent material can affect performance.
    Consider disabling the corresponding option in the ``Clash Viewport`` menu if needed.

    In some cases the size of the clash outline can be very big in screen space, causing to see large portions of purple color on top of the clashes.
    Consider decreasing the ``Outline size`` or ``Outline scale`` to reduce the size of the outline in screen space to a reasonable level.


Warnings
-----------------------

The Clash Viewport will display yellow warnings when the meshes have been modified since the last clash detection run.
If needed, re-run the clash detection to refresh and update results to avoid these warnings.

The following conditions will cause warnings:

- If one of the two (or both) original source meshes have been **deleted** from the stage or layer
- If one of the two (or both) original source meshes have been **moved** from their original location
- If both source meshes for a duplicate have been **deleted** from the stage or layer
- If one of the two (or both) source duplicate meshes have been **moved** from their original location


.. tab-set::

    .. tab-item:: Removing Clash Mesh A
        :sync: key6

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-removed1.png

    .. tab-item:: Removing Clash Mesh B
        :sync: key6

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-removed2.png

    .. tab-item:: Removing Clash Mesh A and B
        :sync: key6

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-removed3.png


.. tab-set::

    .. tab-item:: Moving Clash Mesh A
        :sync: key7

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-moved1.png

    .. tab-item:: Moving Clash Mesh B
        :sync: key7

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-viewport-moved2.png

Dynamic Clashes
-----------------------

To visualize dynamic clashes, it's better to use the :ref:`Clash_Detection_Bake` extension to bake dynamic clashes.

If this is not possible, there are some limitations to keep in mind when using the **Clash Detection Viewport API**:

- When ``Enable selection groups`` is enabled, the meshes will follow the animation of the original meshes.
- When ``Enable selection groups`` is disabled, the meshes will not follow the animation of the original meshes.
- The outlines will not be updated in any case.
- The **Clash Detection Viewport** will not be updated in any case.
- Double clicking on a clash result will show the dedicated dynamic clash slider (see :ref:`Clash_Detection_UI`) that will update both viewports.
- Alternatively, you can use the **Inspect Clashing Frames on Timeline** option in the contextual menu of a clash result (see :ref:`Clash_Detection_UI`).

Known issues
-----------------------

.. warning::
    - RendererInstancing is an experimental feature. Setting ``app.usdrt.population.utils.enableRendererInstancing`` to ``true`` can cause visualizations to be incorrect.


API Reference
-------------

ClashDetectionViewportAPI Class
*********************************

.. class:: ClashDetectionViewportAPI(clash_viewport: ClashDetectionViewport)

    A class to manage and control the clash detection viewport.

    This class provides functionality to display and manage clash meshes in both the main viewport and a dedicated clash detection viewport.

    :param clash_viewport: An instance of ClashDetectionViewport to manage clashes.
    :type clash_viewport: ClashDetectionViewport

Methods
^^^^^^^

.. method:: hide_all_clash_meshes() -> None

    Removes all clash meshes from main viewport or clash viewport.

.. method:: display_clashes(clash_timecode: float, clash_info_items: Dict[str, Any]) -> None

    Displays a set of clashes at a specific timecode in main and/or dedicated clash viewport.

    The display and camera centering behavior is controlled by the viewport settings (see **Clash Viewport Menu** section above):

    - ``Show clash meshes`` and ``Show clash outlines`` in Main Viewport control visibility in the main viewport.
    - ``Show meshes and outlines`` in Clash Viewport controls visibility in the clash viewport.
    - ``Center main viewport`` and ``Center clash viewport`` control camera centering behavior.
    - ``Re-centering far tolerance`` and ``Re-centering near tolerance`` control camera movement thresholds.

    :param clash_timecode: Timecode at which the clash meshes should be displayed.
    :type clash_timecode: float
    :param clash_info_items: Dictionary of :any:`ClashInfo` to be displayed.
    :type clash_info_items: Dict[str, Any]

.. method:: display_clashes_at_timecode(clash_timecode: float, clash_info_items: Dict[str, Any], display_clash_in_main_viewport: bool = True, display_clash_in_clash_viewport: bool = True, center_main_viewport_on_clash: bool = True, center_clash_viewport_on_clash: bool = True, center_main_viewport_fine_tuning: bool = True, center_clash_viewport_fine_tuning: bool = True) -> None

    .. deprecated:: 109.0
        Use :meth:`display_clashes` instead, this method is deprecated and will be removed in future releases.

    Displays a set of clashes at a specific timecode in main and/or dedicated clash viewport.

    :param clash_timecode: Timecode at which the clash meshes should be displayed.
    :type clash_timecode: float
    :param clash_info_items: Dictionary of :any:`ClashInfo` to be displayed.
    :type clash_info_items: Dict[str, Any]
    :param display_clash_in_main_viewport: If True, displays clash meshes in the main viewport.
    :type display_clash_in_main_viewport: bool
    :param display_clash_in_clash_viewport: If True, displays clash meshes in the dedicated clash viewport.
    :type display_clash_in_clash_viewport: bool
    :param center_main_viewport_on_clash: If True, centers active camera on the clashes in the main viewport.
    :type center_main_viewport_on_clash: bool
    :param center_clash_viewport_on_clash: If True, centers active camera on the clashes in the clash viewport.
    :type center_clash_viewport_on_clash: bool
    :param center_main_viewport_fine_tuning: If True, avoids re-centering the camera in main viewport for small movements.
    :type center_main_viewport_fine_tuning: bool
    :param center_clash_viewport_fine_tuning: If True, avoids re-centering the camera in clash viewport for small movements.
    :type center_clash_viewport_fine_tuning: bool

Properties
^^^^^^^^^^

.. property:: clash_viewport_window

    Gets the ViewportWindow handle to dedicated Clash Detection Viewport.

    :returns: The handle to the dedicated Clash Detection Viewport window.
    :rtype: ViewportWindow | None

Getting the API Instance
^^^^^^^^^^^^^^^^^^^^^^^^^

.. function:: get_api_instance() -> ClashDetectionViewportAPI

    Retrieve the singleton instance of ClashDetectionViewportAPI.

    :returns: The singleton instance of the ClashDetectionViewportAPI.
    :rtype: ClashDetectionViewportAPI

Example Usage
^^^^^^^^^^^^^^

.. code-block:: python

    from omni.physxclashdetectionviewport import get_api_instance
    from omni.physxclashdetectionviewport.clash_viewport_settings import ClashViewportSettings
    import carb.settings

    def display_clash_by_clash_info(self, clash_infos: Sequence[ClashInfo], timecode: float):
        # Get the API instance
        viewport_api = get_api_instance()

        # Build clash info items dictionary
        clash_info_items = {}
        for item in clash_infos:
            clash_info_items[item.overlap_id] = item

        # Optional: Configure viewport settings before displaying clashes
        # Use ClashViewportSettings constants instead of raw paths for better maintainability
        # See the 'Settings Reference' section for all available settings
        settings = carb.settings.get_settings()
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_SHOW_CLASH_MESHES, True)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_SHOW_CLASHES, True)
        settings.set_bool(ClashViewportSettings.MAIN_VIEWPORT_CENTER_CAMERA, True)
        settings.set_bool(ClashViewportSettings.CLASH_VIEWPORT_CENTER_CAMERA, True)

        # Display clashes at a specific timecode
        viewport_api.display_clashes(
            clash_timecode=timecode,
            clash_info_items=clash_info_items
        )

        # Hide all clash meshes
        viewport_api.hide_all_clash_meshes()

        # Access the clash viewport window
        clash_window = viewport_api.clash_viewport_window
