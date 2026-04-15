.. _Clash_Detection_UI:

===================
Clash Detection UI
===================

This section documents the `Clash Query Management` and `Clash Detection Results` windows.

To initiate clash detection, you must first create a clash detection query using the Clash Query Management window. You can define as many queries as necessary.

.. important:: Clash detection only works with meshes, not shapes.

Clash Detection Basic Concepts
------------------------------

The system can identify two main kinds of clashes:

- **Hard clashes**
- **Soft clashes**

Hard Clashes
############

Hard clashes, also known as `geometric clashes`, occur when two components **physically intersect** or **pass through** each other.

Hard clashes can be further categorized into two subsets:

- **Contact case**

   - Occurs when two components *just touch* each other by design (e.g., a crate resting on the ground naturally touches it).
   - In this case, there is no significant overlap or intersection between geometries.
   - The **max local depth**, which is an approximate measure of the local overlap around the clash location, can be used to identify contact cases.
   - For contact cases, this value should be **close to zero**.

- **Overlap case**

   - Occurs when two components *clearly intersect* each other by accident.
   - This is unexpected: these are the mistakes we are looking for, and what is usually understood as a **hard clash**.
   - For overlap cases, the **max local depth** will be an arbitrarily large **positive value**.

The user-defined **contact epsilon** value is the limit below which a hard clash is classified as a contact case.

Soft Clashes
############

Soft clashes, also known as `clearance clashes` or `proximity clashes`, occur when two components are located **too close to each other**, specifically **closer than the user-defined tolerance value**.

The **tolerance value** is the distance limit below which a clash is registered. In other words, if the distance between two components is **less than** this value, a clash is detected.

   - **Use a tolerance value of 0** to detect only **hard clashes** (*hard clash query*).
   - **Use a positive value** to detect both **hard** and **soft clashes** (*soft clash query*).

When the system finds two objects physically overlapping during a soft clash query, these objects are still reported as a **hard clash**.

.. important::

   The **max local depth** is **not applicable to soft clashes**, because there is no actual geometric overlap and therefore no depth to compute.


Max local depth and penetration depth (hard clashes)
####################################################

The **max local depth** and the **penetration depth** are related (they are both a measure of the overlap between two objects) but they are not the same value.

The difference is best explained with a "peg in a hole" case. Imagine a red object and a blue object. The red object is lodged inside the blue object. The red object slightly overlaps the blue one. This small overlap can be seen for example inside the orange circle in the picture.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-peg-in-hole.png
   :alt: Peg In A Hole

As we can clearly see here, there could be multiple local overlaps (one at each corner of the red cube in this example). This is why it is "local": the system will compute the overlap at each of these locations, and reports the largest overlap. Visually, this could be for example the orange segment in the following picture. The magnitude of that segment is the **max local depth**.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-max-local-depth.png
   :alt: Max Local Depth

If you depenetrate the red object in that direction though, you only increase the penetration on the other side. There is actually no direction vector that would both resolve the overlap and keep the red object inside the blue one.

The `Minimal Translation Distance` (MTD) is the length of the shortest relative translation that results in two objects being in contact or, if intersecting, determines the depth of penetration. This is how we define the **penetration depth**, i.e. a value that would actually separate the objects and resolve their overlap.

For this case it would be e.g. the green vector in the following picture. The **penetration depth** would be the magnitude of this vector, a bigger value than the one from the orange vector. This penetration depth is now a `global` value, as opposed to the previously discussed `max local depth`, because it takes the entire object into account. Translating the red object by that value would move it entirely out of the blue object.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-penetration-depth.png
   :alt: Penetration Depth

The system provides both a measure of the **max local depth**, and a measure of the **penetration depths** in a number of fixed directions. These two values can be used for different purposes:

- The max local depth can be used as a pruning mechanism to e.g. filter out "contact cases".
- The penetration depth can be used to actually resolve clashes, by moving objects by the reported value.


Clash Query Management Window
------------------------------

This window allows you to manage your clash detection queries.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-query-management-0.png
   :alt: Clash Detection Management Window

Below you can find all actions you can perform on your queries in the top toolbar and in the query list as well.

.. table::
   :widths: 20 80

   =============== ==================
   Action          Description
   =============== ==================
   Create new      | Create a new clash query by clicking the **Create New Query** button.
                   | The new query will be created with a default name of "New Query ###".
   Rename          | Double-click the **Query Name** to rename the query.
                   | You can also change the query name in the right side pane under the "Base" section.
   Duplicate       | Click the **Duplicate** button to duplicate the selected clash queries.
   Comment         | Double-click the **empty space** in the `Comment` column to enter your own comment to further clarify a query's purpose.
                   | You can also change the query comment in the right side pane under the "Base" section.
   Delete          | Click the **Delete...** button to delete the selected clash queries.
   Statistics      Click the **Statistics** button to open the `Query Statistics Window`.
   Export          Click the **Export Queries...** button to export selected queries to a JSON file.
   Import          Click the **Import Queries...** button to import queries from a JSON file.
   Save Properties Click the **Save Properties** button to save the current query properties.
   =============== ==================

Query Timestamps
################

The `First Created` column shows the timestamp when the query was first created.
The `Last Modified` column shows the timestamp when the query was last modified.

Many commands can also be accessed through the context menu.

Keyboard Shortcuts
##################

Here are some useful keyboard shortcuts for the Clash Detection Query Management Window:

.. table::
   :widths: 15 85

   ================= ============
   Keyboard Shortcut Description
   ================= ============
   CTRL+A            Select all queries.
   ESCAPE            Deselect all queries and remove the clash visualization overlay from the main viewport.
   DELETE            Delete selected queries.
   ================= ============

On the right side pane, you can see various options that help you customize the clash detection query to your needs:

.. tab-set::

    .. tab-item:: Base
        :sync: key0

        You can set the name of the query and a comment to further clarify its purpose.

    .. tab-item:: Scope
        :sync: key1

        Limit the clash detection processing scope by defining search sets.

        - If both Searchset A and Searchset B are empty, the whole scene is processed.
        - If only Searchset A contains items, processing is limited to Searchset A items.
        - If both Searchset A and B contain items, process Searchset A against Searchset B.

        The **Pick...** button allows you to add several prims to the searchset edit box—each time you pick, the selected prims are added (not replaced), so you can accumulate multiple targets in the list.
        Tip: you can drag and drop multiple prims into the searchset edit box to add them all at once.

    .. tab-item:: Main Section
        :sync: key2

        =============================  ===============================================================================
        Option                         Description
        =============================  ===============================================================================
        Dynamic                        Tells the clash detection engine to run dynamic clash detection, inspecting time-sampled animations.
            Start Time on Timeline     | Start time on timeline in seconds. Works only when dynamic clash detection is enabled.
                                       | 0 = timeline start time (auto-detected).
            End Time on Timeline       | End time on timeline in seconds. Works only when dynamic clash detection is enabled.
                                       | 0 = timeline end time (auto-detected).
            Purge Permanent Overlaps   Tells the system to discard pairs of dynamic objects that always overlap over the tested time interval. Works only when dynamic clash detection is enabled.
        Tolerance                      | Tolerance distance for overlap queries.
                                       | Use zero to detect only hard clashes.
                                       | Use non-zero to detect both hard and soft clashes.
        Static Time on Timeline        Time on the timeline in seconds for executing static clash detection. The value is clamped into timeline range if necessary. Taken into account only when performing static clash detection!
        Report Duplicate Meshes Only   Instructs the clash detection engine to only report meshes that completely overlap with other identical meshes. Dynamic detection is not supported; only static clashes at the current time on the timeline are. This option is exclusive—no other clashes are reported when this option is enabled!
        Ignore Redundant Overlaps      Instructs the clash detection engine to ignore redundant overlaps.
        =============================  ===============================================================================

    .. tab-item:: Advanced Section
        :sync: key3

        =================================== ===============================================================================================
        Option                              Description
        =================================== ===============================================================================================
        Pose Epsilon                        Epsilon value used when comparing mesh poses. This is used when detecting "duplicate meshes," i.e., meshes with the same vertex/triangle data in the same place.
        Area Epsilon                        Epsilon value used to cull small triangles or slivers. Triangles whose area is lower than this value are ignored. Use 0 to keep all triangles.
        Bounds Epsilon                      Epsilon value used to enlarge mesh bounds slightly. This ensures that flat bounds or bounds that are just touching are properly processed.
        Tight Bounds                        Use tight bounds for meshes.
        Coplanar                            Detect collisions between coplanar triangles.
        Any hit                             If any hit is checked, the clash engine stops after locating the first pair of overlapping triangles; otherwise, it continues to detect all overlaps. This can improve performance if only a quick overview of what’s clashing is wanted.
        Quantized                           Enable quantized trees. Quantized trees use less memory but usually give slower performance.
        Tris per leaf                       Number of triangles per leaf. Tweak this for a memory vs. performance trade-off.
        Triangle Limit                      | Abort narrow-phase query after this number of triangle pairs has been found. Use 0 for unlimited.
                                            | The results fetching process at the end of clash detection retrieves only up to the predefined limit of triangle information, optimizing performance for cases where clash identification is needed without or with limited visualization (e.g. finding duplicates). Particularly beneficial for scenarios involving dense geometry.
        Purge Permanent Static Overlaps     Tells the system to discard pairs of static objects that always overlap over the tested time interval. Works only when dynamic clash detection is enabled.
        Use USDRT                           When enabled, provides faster initial-stage traversal for full-scene queries only.
        Ignore Invisible Prims              Instructs the clash detection engine to ignore invisible primitives.
        =================================== ===============================================================================================

    .. tab-item:: Local Depth (EXPERIMENTAL)
        :sync: key4

        =========================  ===============================================================================
        Option                     Description
        =========================  ===============================================================================
        Compute Max Local Depth    Enable max local depth computation. Helps with identification of contact cases between objects.
        Depth Epsilon              Epsilon value used to classify hard clashes vs. contact cases. Clashes whose max local depth is below the epsilon are ignored. Use a negative value to keep all (hard) clashes. This setting does not apply to soft clashes.
        Contact Cutoff             Cutoff value used to compute the max local depth. Use a negative value to disable it. The cutoff value should be larger than the contact epsilon. The code aborts computation of the max local depth as soon as it is found to be larger than the cutoff value.
        Discard Touching Contacts  Instructs the clash detection engine not to report found touching contacts. The Depth Epsilon must be set to a positive number and any values between 0 and that epsilon are considered as touching contacts.
        Max Local Depth Mode       Max local depth computation mode.
                                    - 0 - Legacy (fastest).
                                    - 1 - Medium (medium accuracy).
                                    - 2 - High (highest accuracy).
        =========================  ===============================================================================

    .. tab-item:: Multi-threading
        :sync: key5

        =========================  ===============================================================================
        Option                     Description
        =========================  ===============================================================================
        Single Threaded            Run in single-threaded or multi-threaded mode. Mainly for testing.
        Use New Task Manager       Use new task manager implementation. It automatically manages the number of spawned tasks, so the 'Number of Tasks' setting is ignored.
        Number of Tasks            Number of tasks used when running in multi-threaded mode. Generally, the more, the better.
        =========================  ===============================================================================

    .. tab-item:: Debugging Section
        :sync: key6

        =========================  ===============================================================================
        Option                     Description
        =========================  ===============================================================================
        Log info in Console        Log info and performance results to console.
        Overlap Code               Use alternative triangle-triangle overlap code.
        =========================  ===============================================================================

.. note::
    - **Display and Edit Timecodes as Frames** is a setting that allows you to display and edit timecodes as frames instead of seconds.
    - Remember to click the **Save Properties** button to save your changes! By default, changes are automatically saved when you select a different query. This can be disabled in settings by unchecking **Save Edited Query on Selection Change**.

    .. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-query-management-1.png
      :alt: Toggle "Save Query on Selection Change" option

Query Statistics Window
########################

This window displays statistics for the selected clash query.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-query-statistics-0.png
    :alt: Query Statistics Window

- **Overview Table**: Displays a list of all clash queries, along with the number of clashes in each state (New, Approved, Resolved, Closed, Invalid, Active, and Total clashes).
- **Search**: Use the search box to filter queries by name or summary. Enter your search term and the table will update as you type.
- **Refresh**: Click the "Refresh" button to reload and update clash statistics.
- **Copy to Clipboard**: Right-click a row to access the context menu, then select "Copy to Clipboard (CSV)" to export selected rows as a table for use in spreadsheets or reporting.

Clash Detection Results Window
-------------------------------

This window displays results for each selected clash query.

There is a row limit that restricts the number of rows displayed. The current limit is set to one million rows. Users receive a notification if the number of rows is reduced because of this limit.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-0.png
    :alt: Clash Detection Results Window

First, choose a clash query to work with from the `Selected Clash Query` dropdown list. You can edit clash queries in the Clash Query Management window, described in the previous section. Click the **Query Management** button to open the `Clash Query Management` window.

.. dropdown:: Review descriptions of each results list column.
    :open:

        =========================  ===============================================================================
        Column                     Description
        =========================  ===============================================================================
        #                          Clash number. Each clash is assigned a unique number by the system. This number typically remains unique even after updating or deleting clashes across different sessions, with one exception: if you delete clashes and then reload the clash data, the clash numbers will change.

                                   If the background color of the number turns red, it indicates that the clash is no longer present in the stage.
        Present                    Indicates whether the clash is present in the stage. Note that even resolved clashes are never deleted; if you are no longer interested in a clash, simply delete it yourself.
        Type                       Type of clash: Duplicate, Hard, or Soft.
        Min distance               Minimum distance between clashing objects. 0=Hard clash, otherwise soft clash.
        Tolerance                  Tolerance that was set at the time when clash detection was run. For hard clashes, the tolerance is always zero. For soft clashes it is non-zero.
        Max Depth                  [EXPERIMENTAL] Estimated maximum local depth. It is always a positive value.
        Depth Epsilon              Maximum Local Depth Epsilon value that was set at the time when clash detection was run. The epsilon value is used to classify hard clashes vs. contact cases.
        PX +X                      Maximum penetration depth along the +X axis.
        PX -X                      Maximum penetration depth along the -X axis.
        PY +Y                      Maximum penetration depth along the +Y axis.
        PY -Y                      Maximum penetration depth along the -Y axis.
        PZ +Z                      Maximum penetration depth along the +Z axis.
        PZ -Z                      Maximum penetration depth along the -Z axis.
        Triangles                  The highest count of overlapping triangles found among all clashing frames for each clashing pair.
        Clash Start                Starting timestamp of the clash.
        Clash End                  Ending timestamp of the clash.
        Records                    Total number of clashing frames for each clashing pair.
        Object A                   Name of the first clashing object.
        Object B                   Name of the second clashing object.
        State                      Management flag. Shows the current status of the clash. Possible values are: New, Approved, Active, Resolved, Closed, or Invalid.

                                   - New: The clash is newly detected in the latest clash detection run.
                                   - Approved: The clash has been reviewed and approved for further investigation or action.
                                   - Active: The clash continues to appear in updated data.
                                   - Resolved: The clash has been addressed, and a solution has been implemented.
                                   - Closed: The clash has been closed and is no longer considered.
                                   - Invalid: The clash is invalid and is no longer considered.

                                   If a clash is newly detected in the latest clash detection run, it is marked as New.
                                   The state will automatically change from New to Resolved if the clash is no longer found in the stage.
                                   If the clash continues to appear in updated data, its state automatically changes from New to Active.
        Priority                   Management flag: Indicates the importance of the clash. This value ranges from 0 (lowest priority) to 5 (highest priority) and is used to help manage and sort clashes.
        Person in Charge           Management field: Specifies the individual responsible for resolving this clash.
        First Detected             Displays the date and time when this clash was initially found.
        Last Modified              Displays the most recent date and time when this clash was updated.
        Comment                    User-defined notes or remarks about the clash.
        =========================  ===============================================================================

Click the **Run Clash Detection** button to initiate the clash detection process on the currently open stage, using the parameters from the selected clash query in the `Selected Clash Query` dropdown list. Once clicked, the button transforms into a progress bar. If necessary, you can click the progress bar or press the Escape key to cancel the process. When the process is complete, the results view will display all detected clashes.


.. note:: Different colors on the progress bar now represent various stages of clash detection:

    - Green indicates the conversion of curve animations to time samples. For more information about the curve animations conversion process, please refer to the :doc:`Clash Detection Anim </ext_clash-detection/clash-detection-anim>` documentation page.
    - Orange signifies the clash detection engine's pipeline processing.
    - Blue represents the stage where all clashing pairs, their respective clashing frames, matrices, faces, and overlap outlines are being retrieved.

To delete selected clashes, click the **Delete Selected** button.

Keyboard Shortcuts
##################

Here are some useful shortcuts for the `Clash Detection Results Window`:

.. table::
   :widths: 15 85

   ================= ============
   Keyboard Shortcut Description
   ================= ============
   CTRL+A            Select all clashes.
   ESCAPE            Deselect the currently selected clashes and remove the clash visualization overlay from the main viewport.
   DELETE            Delete selected clashes. This functionality only works when the window is focused.
   ================= ============

Export
######

To save the results report as an HTML or JSON file, select **Export**. Once clicked, the following options are displayed:

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-1.png
   :alt: Export button options.

.. table::
   :widths: 27 73

   ============================ ============
   Option                       Description
   ============================ ============
   Export only filtered items   If checked, only visible clashes will be exported. If not, all clashes that belong to the selected clash query will be exported.
   Export clash screenshots     If checked, clash images for each clash will be captured and saved to the target location's ``<target-file-name>_images`` subfolder.
   ============================ ============

Grouped View
############

Clicking the **Grouped View** button opens the `Clash Groups Window`.
This window displays detected clashes organized into groups, making it easier to work with large numbers of clashes.
Grouping is done automatically based on scene hierarchy—USD prim path and kind.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-5.png
    :alt: Clash Groups Window

You can use the Groups window and the Clash Results tree at the same time—selections you make in one will be synchronized in the other.

Tip: By default, groups that do not contain any clashes (empty groups) are hidden.
If you want to see all groups, including those without clashes, turn on "Show Also Empty Groups" from the settings menu (this setting persists across sessions).

The Clash Groups Window is divided into several interactive areas, each offering specific features for managing large numbers of clashes.

**Top Toolbar**

+ **Refresh Button**
  - Click the "Refresh" (circle arrow) to regroup and reload all clash data.

+ **Search Field**
  - Instantly filter groups by typing any part of a path. The list updates as you type; clearing the field restores all groups.

+ **Settings (Hamburger Icon)**
  - Toggle “Show Also Empty Groups” to include or exclude groups with no clashes.

+ **Groups Count Label**
  - Shows how many groups are currently visible versus the total number.

**Tree/Table Display Area**

+ Groups appear in a hierarchical tree view.
+ Each group node can be:
    - Expanded/collapsed (double-click or (+)/(–) icon) to show/hide its subgroups and clash data.
    - Leaf nodes display tables listing that group's clash pairs.

**Context Menu (Right-click anywhere in the window)**

- **Select in Stage:** Highlights the selected group’s objects in the USD stage.
- **Expand/Collapse All Children:** Expands or collapses all subgroup nodes at once for easier navigation.

**Expand/Collapse:**
    - Click the (+)/(–) icons next to any node, or use right-click context menu entries for bulk actions.
**Group Selection:**
    - Click a group to select.
    - Use **Ctrl+A** for "Select All" (all groups).
    - Use **ESC** to clear selection.
    - Right-click and choose "Select in Stage" to select corresponding prims in the stage.

**Viewing and Synchronizing Clashes**
- Leaf group nodes contain tables of all clash pairs for that group.
- Selections stay in sync—highlighting a group or clash in either the Groups Window or the main Clash Results tree highlights it in both (if both are open).

Reload
#######

The **Reload** button will fully reload the clash results list, remove all filters, deselect all currently selected clashes, and remove the clash visualization overlay from the main viewport.

.. note:: Does not trigger any clash detection computations.

Basic Filtering
###############

You can instantly filter the resulting list by typing a string into the `Search field`. Filtering is case-insensitive.

.. note:: Encapsulate the search string with back quotes for exact whole word matches. E.g. \`mesh1\`.

Custom Advanced Filtering
#########################

Click the **Filter** button to open the `Custom Filter Window`.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-6.png
    :alt: Filter Window

The `Filter Window` allows users to input and evaluate filter expressions to filter clash results.
This enables users to write flexible expressions to select which data rows ("clashes") to display in the `Clash Results Window`.

**Main Features**

- Enter and edit a custom filter expression using the `Filter Expression Syntax` documented below.
- Toggle filtering on/off via a checkbox.
- Preview and validate the current filter expression by clicking the **Apply** button.
- Access an in-dialog help section describing filter syntax and examples.

**Filter Expression Syntax**

    - Column references (e.g., ``[Column Name]``)
    - String/number literals (e.g., ``'foo'``, ``3.14``)
    - Operators: ``=``, ``<``, ``>``, ``<=``, ``>=``, ``<>``, ``!=``, ``IN``, ``NOT IN``, ``LIKE``, ``NOT LIKE``
    - Logical operators: ``AND``, ``OR``
    - Parentheses for grouping sub-expressions
    - Comma-separated lists for ``IN``/``NOT IN``

**Notes:**

    - ``LIKE`` checks if the pattern appears as a substring in the column value.
    - ``IN`` requires a value to be in a list (e.g., ``[Status] IN ('A','B')``).
    - ``LIKE`` and ``IN`` cannot be combined (i.e., no ``[Name] IN LIKE (...)``).
    - Combine multiple ``LIKE`` patterns with ``OR``: ``[Name] LIKE 'foo' OR [Name] LIKE 'bar'``
    - The parser is case-insensitive by default.

**Example:**
  .. code-block:: text

     [State] IN ('Approved','New') OR ([Type] LIKE 'Hard' AND [Records] > 10)

**Troubleshooting & Tips**

If there are syntax errors, type mismatches, or unsupported expressions in your filter, they will be reported in the console. Please check the console for details.

    - Carefully check for unmatched parentheses or quotes in your filter expression.
    - Only use columns that exist in the current dataset.
    - When using ``LIKE``, remember it only performs substring matching, not regular expressions.
    - Use parentheses to control the order of logical operations.

**Examples**

To display only "Hard" type clashes that have more than 10 records, use:

.. code-block:: text

   [Type] LIKE 'Hard' AND [Records] > 10

To display either newly approved states or those with many overlaps:

.. code-block:: text

   [State] IN ('Approved', 'New') OR [Max Overlaps] >= 100

Context Menu
############

Right-click on an item in the list to open a contextual menu. This menu provides options such as selecting clashing objects, inspecting clashing frames, computing depth, copying information to the clipboard, and more.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-3.png

- **Inspect Clashing Frames on Timeline**: Displays a timeline with a slider (next to the **Refresh** button) to inspect the range of clashing frames. You can also double-click on a clash row to reveal the timeline. This feature is unavailable if more than one clash is selected.

  .. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-4.png
      :alt: Timeline with a slider of clashing frames.

  **Tip:** Hover to see the tooltip with detailed information about the current clashing frame.

    .. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-7.png
        :alt: Tooltip with the information about the clashing frame.

- **Generate Clash Mesh**: Generates a clash mesh for the selected clashes.
- **Clear Clash Mesh**: Clears the clash mesh for the selected clashes.

.. note:: For more information about clash mesh generation, please refer to the :doc:`Clash Detection Bake </ext_clash-detection/clash-detection-bake>` documentation page.

- **Compute Max Local Depth for current frame**: Calculates the maximum local depth for just the currently selected frame.
- **Compute Max Local Depth for all clashing frames**: Computes the maximum local depth for all clashing frames.

  The max local depth is mainly used to identify and filter out "contact cases," where objects are just touching (e.g., resting on top of each other, without clear clashes). It is computed from the clashing triangles and from their immediate neighbors. Entire objects are not taken into account here.

  .. note:: In the Results View, you will only see the highest max local depth across all frames. To see the max local depth for each individual frame, use the `Inspect Clashing Frames on Timeline` option.

- **Compute Penetration Depths for current frame**: Computes penetration depths in all six directions for the current frame.
- **Compute Penetration Depths for all clashing frames**: Computes penetration depths in all six directions for all clashing frames.

  Penetration depths take into account the entire objects.

  .. note:: In the Results View, you will only see the highest penetration depths for each of the six directions across all frames. To see the penetration depth for each individual frame, use the `Inspect Clashing Frames on Timeline` option.

- **Create Markup**: If the Markup extension is active, creates a markup (annotation in the 3D scene with a 2D whiteboard overlay) for all selected clashes. For more information about Markups, please refer to the `Markup <https://docs.omniverse.nvidia.com/extensions/latest/ext_markup.html?highlight=markup>`_ documentation page.
- **Filter View to Only Show Object A Clashes** and **Filter View to Only Show Object B Clashes**: Limits the results view to only show clashes of object A or B. This filter can be removed by clearing the `Search field`. It is not available if more than one row is selected!

When you click the menu icon, you can see several options:

- **Show Full Paths of Clashing Objects**: Check this to show full paths of clashing objects in the list.
- **Immediate Update When Dragging Timeline Slider**: Check this to immediately update the clashing prims visualization in the main viewport during timeline slider drag. If not checked, this update will be delayed until the timeline slider is released.
- **Use Asynchronous Clash Pipeline**: Check this to use the asynchronous clash pipeline. This will not block the application’s responsiveness.
- **Enable Debug Logging**: Check this to turn on debug logging and diagnostic messages.

  .. image:: /images/ext_clashdetection/ext_physics_clashdetection-ui-results-view-2.png
