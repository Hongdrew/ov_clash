.. _Clash_Detection_Bake:

========================================
Clash Detection Bake API
========================================


The Clash Detection Bake extension (included in the Clash Detection Bundle extension) is an API that allows baking the resulting meshes of a clash detection to a time-sampled OpenUSD layer.
The time sampled OpenUSD layer containing the animated clash will be playing along with the existing animations.

The suggested integration of the Clash Detection Bake API is in the clash detection pipeline as a headless process.
Nevertheless, a simple integration of the Clash Bake API has been added to the `Clash Detection Window` (reference implementation).

.. tab-set::

    .. tab-item:: Clash at frame 0
        :sync: key1

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-intro-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Clash at frame 38
        :sync: key1

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-intro-1.png
            :alt: Two clashing meshes at frame 38.

    .. tab-item:: Clash at frame 71
        :sync: key1

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-intro-2.png
            :alt: Two clashing meshes at frame 71.

Reference implementation UI
--------------------------------------------

The reference implementation (``omni.physx.clashdetection.ui`` extension) uses clash bake API to build an interactive UI for baking the clash meshes and materials that is integrated inside the ``Clash Detection Window``.
It allows baking the clash meshes and materials on the fly, interleaving with the UI updates to keep it responsive.
It takes care of loading the baked layers in the session layer to show them in the main viewport when switching clash queries and provides buttons to save, reload and clear the baked layers.
A settings menu allows customizing the bake process and the visual options for the baked layers.

Typical workflow
****************************************
The typical workflow for baking clash meshes and materials on a given clash query is the following:

1. Create a new clash detection query or select an existing one. It can be dynamic or static.
2. Make sure to run the clash detection for the first time or update the results.
3. Click the ``Bake Layer (OFF)`` button to open the sub-menu window (if not already enabled).
4. Select ``Enable Clash Bake Layer`` (if not already enabled).
5. Select all the clashes for which to generate clash meshes from the clash detection results window.
6. Right Click on any of the selected rows to show the context menu.
7. Left click on ``Generate Clash Meshes`` to start the bake process from the context menu.

.. tab-set::

    .. tab-item:: Select Clashes
        :sync: key3

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-generate-0.png
            :alt: Two clashing meshes.

    .. tab-item:: Generated Clash Meshes
        :sync: key3

        .. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-generate-1.png
            :alt: Generated clash meshes


The ``Generate Clash Meshes`` menu item will:

- Remove all overlay clash meshes previously created for selected clash records
- Generate all relevant overlay clash meshes for selected clash records
- If the same mesh is impacted by multiple clashes, the API will generate a merged clash mesh, where relevant clash polygons will be highlighted at the right timecode
- The generated meshes will respect the options configured in the Bake Layer menu (outlines, wireframe, clashing polygons, etc.)


After clicking the ``Generate Clash Meshes`` menu item:

- A progress bar will appear inside the ``Clash Detection Window`` and the clash meshes will be baked in background. Depending on the batch size, the progress bar will update more or less frequently and the FPS may be affected accordingly.
- Once the bake process is completed, the highlights will be visible in the main viewport.
- Scrolling the timeline will animate the highlights along with the keyframed animations of the original meshes.
- To save the baked layer, click ``Save Clash Bake Layers`` to save the progress to a .usd file that will be loaded automatically next time the same file is opened and ``Enable Clash Bake Layer`` is enabled.

.. note::
    - The clash baking process can be interrupted at any time by clicking on the clash detection window progress bar.
    - Use the ``Clear Clash Meshes`` option to remove all overlay clash meshes previously created for selected clash records.

.. warning::
    - When ``Run Clash Detection`` is clicked, the current clash bake layer will be cleared to avoid meshes added by it from being used in the clash detection, generating false / fake clashes between real geometry and their visual representation.
    - The clash bake layer will NOT be saved to disk when ``Run Clash Detection`` is clicked, so if this has been done by mistake just press ``Reload`` to restore the previous state (assuming the layer was saved before).

Settings menu
****************************************

The reference implementation includes a settings menu that can be opened by clicking the ``Bake Layer (ON/OFF)`` button.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-settings.png
    :alt: Bake Layer Settings


The first section is always visible and contains the main enable/disable controls:

- When Bake Layer is **OFF** the sub-menu only contains the ``Enable Clash Bake Layer`` and ``Clash Selection Highlight`` options.
- When Bake Layer is **ON** the sub-menu contains many additional options to bake the clash meshes and materials (see next sections for more details).

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-layer-options.png
    :alt: Bake Layer options

- ``Enable Clash Bake Layer`` (default: **disabled**):
    - Enabled: attaches clash bake layers to the current stage, making other options visible.
    - Disabled: detaches the clash bake layers from the current stage.
- ``Clash Selection Highlight`` (default: **disabled**):
    - Enabled: Clash Viewport **will highlight** the current selection in the main viewport even if bake layer is enabled.
    - Disabled: Clash Viewport **will not highlight** the current selection in the main viewport even if bake layer is enabled.


Layer Actions
****************************************

This section is only visible when the clash bake layer is **enabled**.
It provides buttons to manage the baked data (save, reload, clear):

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-actions.png
    :alt: Bake Layer Actions

- ``Save``: Saves the clash bake layer for current query to persistent storage.
- ``Reload``: Replaces content in the clash bake layer for current query with content from persistent storage
- ``Clear``: Clears all contents of the current clash bake layer.


Generation options
********************************************

This section is collapsed by default and controls the baking process behavior:

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-generation.png
    :alt: Bake Generation Options


- ``Keep DB Data in Memory`` (default: **enabled**):
    - If enabled keeps the data for each baked record in memory to avoid reloading it.
    - As a downside it consumes additional memory.
- ``Show Notification`` (default: **enabled**):
    - If enabled shows a notification when the clash baking process is completed.
- ``Finalize When Cancelled`` (default: **enabled**):
    - If enabled finalizes meshes baked so far when the process is cancelled.
- ``Batch Size`` (default: **5**):
    - Number of clashes to process in each batch, between each UI update.
    - Smaller batches will take longer to process updating the UI more frequently.
    - Larger batches will take less time to process updating the UI less frequently.

Visual options
****************************************

This section is collapsed by default and controls what visual elements get baked:


.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-visual.png
    :alt: Bake Visual Options

- ``Use Selection Groups`` (default: **enabled**):
    - If enabled uses selection groups to highlight the meshes during the clash.
- ``Bake Clash Outlines`` (default: **enabled**):
    - If enabled bakes clash outlines for each frame.
- ``Bake Clash Meshes`` (default: **enabled**):
    - If enabled bakes clones of the clashing meshes to highlight them with a different material or with the selection group.
    - The cloned meshes are visible for the entire duration of the clash.

When **not using Layer API** or when **Use Selection Groups is disabled**, the following additional options are visible:

- ``Bake Wireframe`` (default: **disabled**):
    - If enabled bakes wireframes on top of clashing polygons for each frame (high performance cost).
- ``Bake Clashing Polygons`` (default: **disabled**):
    - If enabled bakes time sampled clashing polygons for each frame (very high performance cost).

**Outline Width Options:**

These options control the width of outline edges:

- ``Outline Size`` (float slider):
    - Size of the outline in world space units.
- ``Outline Scale`` (float slider):
    - Scale factor for the outline width.

Developer options
********************************************

This section is collapsed by default and only visible when development mode is enabled (``/physics/developmentMode==true``):


.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-developer.png
    :alt: Bake Developer Options

- ``USD Sdf Layer API`` (default: **enabled**): **DEPRECATED.**
    - Sdf API will be the only one supported in future releases.
    - If enabled bakes using layer API instead of stage API.
- ``Save as USD`` (default: **enabled**):
    - If enabled saves as usd instead of usda.

**Deprecated Options (Stage API mode only):**

The following option is only visible when ``USD Sdf Layer API`` is disabled:

- ``Bake Using Display Opacity`` (default: **enabled**): **DEPRECATED.**
    - Sdf API will be the only one supported in future releases.
    - If enabled bakes using display opacity instead of hole indices.


Clash Bake Layer Creation
******************************

- A Clash Bake layer is created when ``Enable Clash Bake Layer`` is enabled.
- A Clash Bake layer is always associated with a specific query, by its query ID.
- When enabling a Clash Bake layer, two additional `.usd` files will be created in the same folder where the root layer of current stage lives.
- One ``.usd`` file will start with the same file name as the root layer and end with ``_CLASH_MATERIALS.usd``.
- One ``.usd`` file will start with the same file name as the root layer and end with ``_CLASH_QUERY_{query_id}.usd`` where ``{query_id}`` is the integer ID of the selected clash query.
- Both files will be saved in the same directory where the root layer lives.
- Additional support files (for example ``ClashMaterials.mdl``) will be created in the same directory.
- A Clash Bake layer is loaded if an already existing file with the expected file name exists in the destination folder.
- Once a bake layer has been enabled for a given Clash Query, when switching to other queries other clash mesh layers will be created.
    - This allows to bake clash meshes for a given query, save the baked layer and then switch to other queries without having to bake again for each query.

As an example given a source root layer named ``cylinder_sphere_animated.usda`` that has 4 queries (with ID from ``1`` to ``4``), the generated files will be:

- ``cylinder_sphere_animated_CLASH_MATERIALS.usd``
- ``cylinder_sphere_animated_CLASH_QUERY_1.usd``
- ``cylinder_sphere_animated_CLASH_QUERY_2.usd``
- ``cylinder_sphere_animated_CLASH_QUERY_3.usd``
- ``cylinder_sphere_animated_CLASH_QUERY_4.usd``
- ``ClashMaterials.mdl``

.. note::
    - Clash Bake layers are added as an anonymous sublayer of the session layer.
    - Such layer will be saved / loaded from persistent storage using the ``Layer Actions`` buttons.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-layers-0.png
    :alt: Clash Bake anonymous layer is added as sublayers of session layer and ClashMaterials added to the session layer

Runtime performance costs
*******************************

Adding a dynamic clash bake layer to a stage affects the performance of stage animation.
The selected options can have a significant impact on the performance.

The performance cost of the features is the following:

- ``Use selection groups``: **LOW**
    - Layer mode only.
    - Enabled by default.
- ``Bake Clash Meshes``: **LOW to MEDIUM**
    - Enabled by default
    - Highlights clashing objects from clash start to end.
    - It can be medium if a lot of instanced prims are clashing as highlights will happen on a reference to the instanced prims with the instancing flag disabled.
    - If a stage heavily relies on instancing for performance, then clash bake may be causing significant performance drops.
- ``Bake Outlines``: **MEDIUM to HIGH**
    - Depends on how many intersection edges are detected for a given clash and how many points are in the outline.
    - Animated outlines are topology changing meshes and they are computationally expensive for the renderer.
    - If the size of the outline is very large in screen space, the performance cost can be high. In that case lower the ``Outline Size`` or ``Outline Scale`` value.
- ``Bake Wireframe``: **HIGH**
    - Computationally expensive.
    - Only available with ``Use Selection Groups`` disabled
    - They increase memory usage and file size because the over layer will contain the offset vertices for each highlighted mesh.
- ``Bake clashing polygons``: **HIGH**
    - Very computationally expensive.
    - Only available with ``Use Selection Groups`` disabled
    - They increase memory usage and file size because the over layer will contain some time-sampled primvars to highlight each polygon that is clashing at a given timecode.

.. note:: It's possible to bake any selection with different options (enabling or disabling wireframe, outlines, clash meshes, etc.) from whatever was already baked for all the other records.
    Users can take advantage of this to only highlight meshes with a different color and add the more expensive clash polygons and wireframes or outlines only for a subset of clashes of interest.


Bake layers standalone usage
--------------------------------

The clash baked layer can be composed in the same way as any other USD layer and viewed without the need of almost all clash detection extension, because the output of clash bake layer extension is just pure USD.

.. note:: The only exception to the above statement is that the ``omni.physx.clashdetection.viewport`` extension must be enabled to be able viewing the highlights coming from the ``Selection Groups`` options.

In the following example:

- ``ClashBakingCurve.usd``
    - The base layer containing original meshes with animation curves enabled
- ``ClashBakingCurveTimeSampled.usd``
    - The over layer containing time-sampled animation for all meshes and disabling the Animation Curves PushGraph
- ``ClashBakingCurveTimeSampled_CLASH_MATERIALS.usd``
    - The over layer containing clash materials (used by the clash meshes)
- ``ClashBakingCurveTimeSampled_CLASH_MESHES.usd``
    - The over layer containing clash meshes (higlights clashing objects from clash start to end)


.. image:: /images/ext_clashdetection/ext_physics_clashdetection-bake-layers-1.png
    :alt: How to compose clash bake layers

.. warning:: As explained in the dedicated section, Animation curves will need to be baked to a timesampled animation layer in order to delete (or disable) the PushGraph from the original layer.
    It can be difficult disabling multiple PushGraphs on a complex composed stage if they're nested in referenced or instanced prims.
    In such cases it's recommended to disable the animation curves runtime entirely (disabling the ``omni.anim.curve.core`` extension).

Technical Notes
---------------

The Generated clash layers contain only some `delta` that must be set as `over` to the original USD layer used to generate them.

Efficient usage of references allow such `delta` clash layer to be significantly smaller than a full time-sampled animated USD containing all mesh faces, indices and vertices. The `delta` contains just the time-sampled list of faces impacted by the clash over time.

The API is also able to visualize meshes that are part of an instanced prim (instancing proxies), through use of references.

.. warning::
    - The reference implementation centralizes the code handling live attachment / detachment of the bake layer to the session layer, and integrating the bake process with the UI to keep it responsive, through an helper class called ``ClashBakeAsync``.
    - Stability and future availability of ``ClashBakeAsync`` is not guaranteed, it should be considered sample code part of the reference implementation and not part of the public API.
    - The official API for clash bake is the :any:`ClashBakeLayer` class and the :any:`ClashBakeOptions` class.

Animation Curves Interaction
---------------------------------

.. warning::
    ``omni.physx.clashdetection.bake`` only supports **time sampled animated prims**.


- If the prims clashing are sub-nodes of some prim controlled by animation curves the baked layer will animate correctly with the timeline position.
- If the prims clashing are directly animated with Animation Curves (from ``omni.anim.curve.core`` extension) the baked layer will not be able to change visibility correctly for it.
    - In this case ``omni.anim.curve.core`` must be baked to a time-sampled layer before baking the clash meshes, otherwise the baked layer will not be able to change visibility correctly for it.
    - The original animation curves must be deleted or the corresponding PushGraph must be deleted or de-activated.
    - If deleting animation curves data is not feasible, disabling the ``omni.anim.curve.core`` extension while generating and viewing clash backed layer can avoid such issues.
    - Failure to do any of the above may cause clash meshes visibility to be incorrect and/or clash faces not to be animated correctly with the timeline position.

Known issues
---------------

.. warning::
    - RendererInstancing is an experimental feature. Setting ``app.usdrt.population.utils.enableRendererInstancing`` to ``true`` can cause clash bake to generate incorrect visualizations.


API Usage
---------

The high-level clash baking API usage workflow is the following:

One time:

1. [**Optional**] Create and attach any additional layer to write clash meshes and clash materials.
2. Copy support files (mainly MDL shaders) to the folder that will receive the USD file containing clash materials (:any:`ClashBakeLayer.get_support_files_paths`)
3. Bake Clash materials (:any:`ClashBakeLayer.bake_clash_materials`)

Every time there is need to bake an array of :any:`ClashInfo` objects:

1. Collect all paths to be baked in the current run
2. Remove previously baked meshes to avoid merging new results with them (:any:`ClashBakeLayer.remove_baked_meshes`)
3. Prepare meshes to be baked (:any:`ClashBakeLayer.prepare_clash_bake_infos`)
4. Bake clash meshes (:any:`ClashBakeLayer.bake_clash_meshes`)
5. Finalize clash meshes (:any:`ClashBakeLayer.finalize_clash_meshes`)

The following example shows how to generate a baked clashes layer offline from a non-interactive / headless command-line program:

.. warning::
    Make sure that the layers have same `timeCodesPerSecond` of the root layer being baked.

Clash Bake Layer Example
************************

.. code-block:: python

    from omni.physxclashdetectionbake import ClashBakeLayer, ClashBakeOptions

    # use clash detection core api to get ClashInfo objects from current stage

    # clash_infos = ... # list of ClashInfo objects coming from clash detection core api

    # ClashBakeOptions allows customizing the bake process, for example:
    # Enable clash meshes and outlines, but disable wireframe and clashing polygons for better performance
    options = ClashBakeOptions()
    options.generate_clash_meshes = True  # highlights clashing objects from clash start to end
    options.generate_outlines = True

    stage_path_name = self._test_data_dir + "ClashBaking/ClashBakingTimeSampled.usda"
    carb.log_info(f"Opening stage '{stage_path_name}'...")
    stage = Usd.Stage.Open(stage_path_name)
    self.assertIsNotNone(stage)
    UsdUtils.StageCache.Get().Insert(stage)

    # Collect all a/b paths
    paths = [(str(ci.object_a_path), str(ci.object_b_path)) for ci in clash_infos]

    # Create two dedicated layers for clash baking, one for materials and one for meshes
    # Using the ClashBakeLayer API, we don't need to insert these layers into the stage
    root_layer = stage.GetRootLayer()
    base_path, _ = os.path.splitext(root_layer.identifier)
    extension = "usd"
    layer_meshes_path = base_path + f"_CLASH_MESHES.{extension}"
    layer_materials_path = base_path + f"_CLASH_MATERIALS.{extension}"

    # It's possible also to open an existing layer before creating new ones
    layer_meshes: Sdf.Layer = Sdf.Layer.CreateNew(layer_meshes_path)
    layer_materials: Sdf.Layer = Sdf.Layer.CreateNew(layer_materials_path)

    # NOTE: The layers must have same time codes per second as the original stage
    layer_meshes.timeCodesPerSecond = root_layer.timeCodesPerSecond # type: ignore
    layer_materials.timeCodesPerSecond = root_layer.timeCodesPerSecond # type: ignore

    # Copy Support files (material shaders mainly) to same folder where layers live
    support_paths = ClashBakeLayer.get_support_files_paths(options=options)
    dest_folder = os.path.dirname(str(layer_materials.identifier))
    for src in support_paths:
        dest = os.path.join(dest_folder, os.path.basename(src))
        await omni.client.copy_async(src, dest, omni.client.CopyBehavior.OVERWRITE)

    # Generate materials before they're referenced by meshes
    # Using ClashBakeLayer API, we directly bake to the layer without setting edit target
    carb.log_info("Baking materials")
    materials = ClashBakeLayer.bake_clash_materials(layer=layer_materials, options=options)

    # Prepare bake infos
    bake_infos = ClashBakeLayer.prepare_clash_bake_infos(stage=stage, clash_infos=clash_infos, options=options)

    carb.log_info("Removing previously baked meshes")
    # Remove previously baked meshes (useful when opening an existing layer with pre-baked clash meshes)
    with Sdf.ChangeBlock():
        ClashBakeLayer.remove_baked_meshes(stage=stage, layer=layer_meshes, paths=paths, options=options)

    # Bake clash meshes directly to the layer
    # This can be taking some time so if needed just split the bake_infos in batches
    # to give some time to user interfaces updates in order to display progress.
    carb.log_info("Baking Meshes")
    ClashBakeLayer.bake_clash_meshes(layer=layer_meshes, bake_infos=bake_infos, materials=materials, options=options)

    # Finalize mesh baking (runs optimization / merge operations)
    # Also this operation can be taking some time so if needed split bake_infos in batches
    # and interleave with user interface updates in order to display progress.
    carb.log_info("Finalizing Meshes")
    with Sdf.ChangeBlock():
        ClashBakeLayer.finalize_clash_meshes(layer=layer_meshes, bake_infos=bake_infos, options=options)

    carb.log_info("Clash baking finished")

    # Save the layers
    layer_materials.Save()
    layer_meshes.Save()


API Reference
-------------

ClashBakeLayer Class
************************

.. class:: ClashBakeOptions()

    A class to customize the clash bake process.

    :param generate_outlines: Generate outlines for clashing polygons at every frame (default: True).
    :type generate_outlines: bool

    :param generate_clash_meshes: Generate clash meshes to highlight the meshes from clash start to end (layer mode only, default: True).
    :type generate_clash_meshes: bool

    :param generate_wireframe: Generate a wireframe mesh on top of clashing polygons (not useful with selection groups, default: False).
    :type generate_wireframe: bool

    :param generate_clash_polygons: Generate time samples for clashing polygons, resource intensive (not useful with selection groups, default: False).
    :type generate_clash_polygons: bool

    :param use_selection_groups: Use selection groups for highlighting (layer mode only, default: True).
    :type use_selection_groups: bool

    :param wireframe_offset_epsilon: Offset distance along normals to avoid z-fighting for wireframes (default: 0.001).
    :type wireframe_offset_epsilon: float

    :param group_name_clash_a: The name of the selection group for object A (default: "ClashDetection:ObjectA").
    :type group_name_clash_a: str

    :param group_name_clash_b: The name of the selection group for object B (default: "ClashDetection:ObjectB").
    :type group_name_clash_b: str

    :param group_name_outlines: The name of the selection group for outlines (default: "ClashDetection:Outlines").
    :type group_name_outlines: str

    :param group_name_duplicate: The name of the selection group for duplicate meshes (default: "ClashDetection:Duplicate").
    :type group_name_duplicate: str

    :param outline_width_size: Size of the outline in world space units (default: 0.5).
    :type outline_width_size: float

    :param outline_width_scale: Scale factor for the outline width (default: 1.0).
    :type outline_width_scale: float

.. class:: ClashBakeLayer()

    A class to bake clash meshes directly to a USD layer without requiring stage composition or edit target manipulation.
    All methods of this class are ``@staticmethod`` so this class doesn't need to be instantiated.

    The API enables baking a list of :any:`ClashInfo` objects from :any:`Clash_Detection_Core` extension to OpenUSD layers.

    **Advantages over ClashDetectionBake:**
        - No need to compose layers into the stage during baking
        - No need to manipulate edit targets
        - Better performance and memory efficiency
        - Cleaner workflow without try/finally blocks

    The general usage workflow is:

    Setup (when a new stage is loaded):
        - :any:`ClashBakeLayer.get_support_files_paths` obtains support files that must be copied where the result of clash bake will be
        - Create separate layers for clash materials and meshes (not composed into the stage)
        - :any:`ClashBakeLayer.bake_clash_materials` creates materials directly in the material layer

    Runtime:
        - :any:`ClashBakeLayer.prepare_clash_bake_infos` transforms a [:any:`ClashInfo`] (with :any:`clash_frame_info_items` filled) in a `[ClashBakeInfo]`
        - :any:`ClashBakeLayer.bake_clash_meshes` takes a [`ClashBakeInfo`] and writes the meshes directly to the layer
        - Finally :any:`ClashBakeLayer.finalize_clash_meshes` will finalize meshes, doing merging and / or keyframe simplifications

    Update:
        - :any:`ClashBakeLayer.remove_baked_meshes` removes the baked meshes from a previous run when needing to update an existing layer

Static Methods
^^^^^^^^^^^^^^

.. method:: ClashBakeLayer.remove_baked_meshes(stage: Usd.Stage, layer: Sdf.Layer, paths: list[tuple[str, str]], options: ClashBakeOptions = ClashBakeOptions()) -> list[str]

    Removes additional clash prims baked for prims at given paths directly from the specified layer.

    :param stage: The USD Stage (used for prim path validation).
    :type stage: Usd.Stage
    :param layer: The layer to remove the baked meshes from.
    :type layer: Sdf.Layer
    :param paths: List of tuples containing the paths of the prims to remove.
    :type paths: list[tuple[str, str]]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of paths of the prims that failed to be removed.
    :rtype: list[str]

.. method:: ClashBakeLayer.prepare_clash_bake_infos(stage: Usd.Stage, clash_infos: list[ClashInfo], options: ClashBakeOptions = ClashBakeOptions()) -> list[ClashBakeInfo]

    Prepare ClashBakeInfo objects that are needed to bake meshes for a given list of clashes.

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param clash_infos: List of ClashInfo objects from omni.physx.clashdetection.core.
    :type clash_infos: list[ClashInfo]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of ClashBakeInfo objects that can be used with `bake_clash_meshes`.
    :rtype: list[ClashBakeInfo]

.. method:: ClashBakeLayer.get_support_files_paths(options: ClashBakeOptions) -> list[str]

    Obtain a list of paths to support files needed by `bake_clash_meshes`.

    For example it contains the path to material file used by the baked meshes materials.
    Copy these files in the target directory where the clash layer is saved.

    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of file paths to support files needed by `bake_clash_meshes`.
    :rtype: list[str]


.. method:: ClashBakeLayer.bake_clash_materials(layer: Sdf.Layer, options: ClashBakeOptions = ClashBakeOptions()) -> ClashMaterialsPaths

    Write materials used by `bake_clash_meshes` directly to the specified layer.

    Note: This method writes directly to the layer without requiring edit target manipulation.

    :param layer: The layer to write materials to.
    :type layer: Sdf.Layer
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: The materials created (to be passed in to `bake_clash_meshes`)
    :rtype: ClashMaterialsPaths


.. method:: ClashBakeLayer.bake_clash_meshes(layer: Sdf.Layer, bake_infos: list[ClashBakeInfo], materials: ClashMaterialsPaths, options: ClashBakeOptions = ClashBakeOptions()) -> None

    Bakes meshes prepared with `prepare_clash_bake_infos` applying the materials created with `bake_clash_materials` directly to the specified layer.

    Note: This method writes directly to the layer without requiring edit target manipulation or stage composition.

    :param layer: The layer to write clash meshes to.
    :type layer: Sdf.Layer
    :param bake_infos: List of ClashBakeInfo objects prepared with `prepare_clash_bake_infos`.
    :type bake_infos: list[ClashBakeInfo]
    :param materials: Materials created with `bake_clash_materials`.
    :type materials: ClashMaterialsPaths
    :param options: Options for the bake process.
    :type options: ClashBakeOptions


.. method:: ClashBakeLayer.finalize_clash_meshes(layer: Sdf.Layer, bake_infos: list[ClashBakeInfo], options: ClashBakeOptions = ClashBakeOptions()) -> None

    Merges multiple clash pairs previously baked with `bake_clash_meshes` directly in the specified layer.

    :param layer: The layer containing the baked meshes to finalize.
    :type layer: Sdf.Layer
    :param bake_infos: List of ClashBakeInfo objects that were baked.
    :type bake_infos: list[ClashBakeInfo]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions

ClashDetectionBake Class (Deprecated)
*************************************

.. deprecated:: 109.0
    The ``ClashDetectionBake`` class is deprecated and it will be removed in future releases.
    Use :any:`ClashBakeLayer` instead for better performance more flexible workflow.

.. class:: ClashDetectionBake()

    A deprecated class to bake clash meshes to a USD stage using edit targets.
    All methods of this class are ``@staticmethod`` so this class doesn't need to be instantiated.

    **Deprecated:** This API requires stage composition and edit target manipulation which causes performance overhead.
    Use :any:`ClashBakeLayer` instead which works directly with layers.

    The API enables baking a list of :any:`ClashInfo` objects from :any:`Clash_Detection_Core` extension to OpenUSD meshes.

    The general usage workflow is:

    Setup (when a new stage is loaded):
        - :any:`ClashDetectionBake.get_support_files_paths` obtains support files that must be copied where the result of clash bake will be
        - Set an edit target where clash materials need to be written
        - :any:`ClashDetectionBake.bake_clash_materials` creates materials in the current edit target for a given stage
        - Potentially create an additional layer to contain only the clash meshes
        - Attach the layer containing the material and the clash meshes one as sublayers of current session layer

    Runtime:
        - :any:`ClashDetectionBake.prepare_clash_bake_infos` transforms a [:any:`ClashInfo`] (with :any:`clash_frame_info_items` filled) in a `[ClashBakeInfo]`
        - Set an edit target where clash meshes need to be written
        - :any:`ClashDetectionBake.bake_clash_meshes` takes a [`ClashBakeInfo`] and a stage + materials and writes the meshes in the stage.
        - Finally :any:`ClashDetectionBake.finalize_clash_meshes` will finalize meshes, doing merging and / or keyframe simplifications.

    Update:
        - :any:`ClashDetectionBake.remove_baked_meshes` removes the baked meshes from a previous run when needing to update an existing layer.

Static Methods
^^^^^^^^^^^^^^

.. method:: ClashDetectionBake.remove_baked_meshes(stage: Usd.Stage, paths: list[tuple[str, str]], options: ClashBakeOptions = ClashBakeOptions()) -> list[str]

    Removes additional clash prims baked for prims at given paths.

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param paths: List of tuples containing the paths of the prims to remove.
    :type paths: list[tuple[str, str]]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of paths of the prims that failed to be removed.
    :rtype: list[str]


.. method:: ClashDetectionBake.prepare_clash_bake_infos(stage: Usd.Stage, clash_infos: list[ClashInfo], options: ClashBakeOptions = ClashBakeOptions()) -> list[ClashBakeInfo]

    Prepare ClashBakeInfo objects that are needed to bake meshes for a given list of clashes.

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param clash_infos: List of ClashInfo objects from omni.physx.clashdetection.core.
    :type clash_infos: list[ClashInfo]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of ClashBakeInfo objects that can be used with `bake_clash_meshes`.
    :rtype: list[ClashBakeInfo]


.. method:: ClashDetectionBake.get_support_files_paths(options: ClashBakeOptions) -> list[str]

    Obtain a list of paths to support files needed by `bake_clash_meshes`.

    For example it contains the path to material file used by the baked meshes materials.
    Copy these files in the target directory where the clash layer is saved.

    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: List of file paths to support files needed by `bake_clash_meshes`.
    :rtype: list[str]


.. method:: ClashDetectionBake.bake_clash_materials(stage: Usd.Stage, options: ClashBakeOptions = ClashBakeOptions()) -> ClashMaterialsPaths

    Write materials used by `bake_clash_meshes` to current stage.

    Note: Before calling this function you can change the edit layer to save the materials to.

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
    :returns: The materials created (to be passed in to `bake_clash_meshes`)
    :rtype: ClashMaterialsPaths


.. method:: ClashDetectionBake.bake_clash_meshes(stage: Usd.Stage, bake_infos: list[ClashBakeInfo], materials: ClashMaterialsPaths, options: ClashBakeOptions = ClashBakeOptions()) -> None

    Bakes meshes prepared with `prepare_clash_bake_infos` applying the materials created with `bake_clash_materials`.

    Note: Before calling this function you can change the edit layer to save the clash mesh USD overs to.

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param bake_infos: List of ClashBakeInfo objects prepared with `prepare_clash_bake_infos`.
    :type bake_infos: list[ClashBakeInfo]
    :param materials: Materials created with `bake_clash_materials`.
    :type materials: ClashMaterialsPaths
    :param options: Options for the bake process.
    :type options: ClashBakeOptions


.. method:: ClashDetectionBake.finalize_clash_meshes(stage: Usd.Stage, paths: list[tuple[str, str]], options: ClashBakeOptions = ClashBakeOptions()) -> None

    Merges multiple clash pairs at paths previously baked with `bake_clash_meshes`

    :param stage: The USD Stage.
    :type stage: Usd.Stage
    :param paths: List of tuples containing the paths of the prims to merge.
    :type paths: list[tuple[str, str]]
    :param options: Options for the bake process.
    :type options: ClashBakeOptions
