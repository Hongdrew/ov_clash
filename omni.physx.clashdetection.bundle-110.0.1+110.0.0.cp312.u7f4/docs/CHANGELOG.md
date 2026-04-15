# Changelog

## [110.0.1] - 2026-02-06

### Fixed

-   Fixed a memory leak that occurred while retrieving clash results.

## [110.0.0] - 2026-01-16
Version bump.

## [109.0.12] - 2026-01-07

### Improved

-   Reproducible clash detection results when using USDRT with renderer instancing enabled.
-   Clash Viewport: Improved reliability global viewport setting by ensuring render settings are properly restored, even in cases of errors when the clash viewport is opened.

## [109.0.11] - 2025-12-10

### Added

-   Clash Results Window

    -   Added advanced filtering capabilities with support for expressions, including references to columns, string and numeric values, comparison, and logical operators.
    -   Automatic clash status change after each clash detection run:
        -   If a clash is newly detected in the latest clash detection run, it is marked as New.
        -   The state will automatically change from New to Resolved if the clash is no longer found in the stage.
        -   If the clash continues to appear in updated data, its state automatically changes from New to Active.
    -   New columns now display penetration depths in all six directions: +X, -X, +Y, -Y, +Z, -Z.
    -   New commands in the context menu:
        -   Compute Max Local Depth for current frame: Compute the maximum local depth for the current frame.
        -   Compute Max Local Depth for all clashing frames: Compute the maximum local depth for all clashing frames.
        -   Compute Penetration Depths for current frame: Compute penetration depths in all six directions for the current frame.
        -   Compute Penetration Depths for all clashing frames: Compute penetration depths in all six directions for all clashing frames.
    -   Ability to start the Clash Viewport from the main panel.

-   New Grouped View

    -   This window displays detected clashes organized into groups, making it easier to work with large numbers of clashes. Grouping is done automatically based on scene hierarchy—USD prim path and kind.

-   New Query Statistics Summary Window

    -   This window provides a summary of statistics for every query in the open USD project, including the total number of detected clashes and a breakdown by clash status.

-   Clash Query Window

    -   Base section: Added the possibility to edit the query name and comment also in the query settings property list.
    -   New ability to edit query settings’ time codes as frames via a setting option.
    -   Introduced Triangle Limit option.
    -   New option to consider or ignore invisible/inactive prims.

-   Clash Bake:

    -   New API to bake directly to a non-composed layer (Sdf Layer Mode, used by default in the reference implementation).
    -   Highlight clash meshes only during the clash start-end interval.
    -   New option to use Selection Groups, enabling seeing through occlusions (on by default in the reference implementation).
    -   Enabled baking of duplicates, static clashes, and recursively nested instanced prims.
    -   New option to decide the granularity of batches for the clash bake process ("Batch size").
    -   New option to enable or disable regular clash viewport selection highlight when bake is active.
    -   New option to control whether to keep database-loaded data in memory ("Keep db data in memory").
    -   New option to control whether to keep baked clashes created until user cancellation ("Finalize when cancelled").
    -   Shows a notification with bake details after the process is finished, interrupted, or when an error occurs ("Show notification").

-   Clash Viewport:

    -   Enables selecting multiple clash result rows in the Clash Detection window and viewport.
    -   New setting to control the maximum number of selectable clashes in viewports.
    -   New settings to control camera centering and fine-tuning behavior.
    -   New option to control how many frames to wait before and after taking a clash screenshot for export in the reference implementation.
    -   New setting to disable selection group highlight fill (also affects clash bake visualization).
    -   New settings to selectively show clash meshes, outlines, and wireframes in the main viewport and in the clash viewport.
    -   New options to log profile data for debugging.

-   Clash Detection API:
    -   New clash database migration system; it is now possible to migrate older clash databases to a new version.
    -   HTML/JSON export: Added support for a custom (header) name/value section.
    -   Added methods to compute depths on demand: compute_max_local_depth and compute_penetration_depth.
    -   A feature to compute penetration depths along world-space coordinate axes has been added. This measures how much the objects should be moved in the requested directions to fully resolve the overlap and separate the objects.

### Improved

-   Clash Results Window

    -   Clash fetching process is now up to 3x faster.
    -   Improved copy-to-clipboard feature to also include the header.

-   Clash Query Window

    -   Scope section:
        -   The Pick... button now appends selected prims to the search set edit box, so it is possible to add multiple targets by using the Pick button.
        -   The drag-and-drop feature has been improved: dragging multiple prims into the search set edit box now correctly displays all dropped prim paths, rather than only the first one.
    -   The currently selected query in the query drop-down in the Clash Results window is now automatically opened when the user opens the Query Management window.
    -   Depth computation improved: introduced computation modes and further extended with the Contact Cutoff value; the code aborts the computation of the max local depth as soon as it is found to be larger than the cutoff value.

-   Clash Bake:

    -   Significantly faster clash bake process with the "Sdf Layer Mode".
    -   Significantly faster runtime clash performance, particularly when using Selection Groups.
    -   Significantly faster enabling/disabling of bake layers in the reference implementation.
    -   Significantly faster bake layer switching performance when selecting different clash queries in the reference implementation.

-   Clash Detection API:
    -   The accuracy of the "max local depth" computation has been improved. There are now three available accuracy levels, from fastest/less accurate to slowest/most accurate. The default is a medium level, a good middle ground between the two. The max local depth is mainly used to identify and filter out "contact cases," where objects are just touching (e.g., resting on top of each other, without clear clashes).

## [107.3.17] - 2025-08-19

### Added

-   Clash Viewport:
    -   Added an option show or hide clash meshes or intersection profiles (outlines) in the main viewport.
    -   Added an option to use selection groups in main viewport to highlight clash meshes (on by default).
    -   Added an option to enable or disable visualization in main and clash viewports.
    -   Added an option to enable or disable use of translucent materials in clash viewport.

### Improved

-   Selection is triggered when clicking on the clash# column.
-   Clarified description of penetration depth related parameters.
-   Clash Viewport:
    -   Always center camera around clash intersection profiles (outlines) when they exist in current clash
    -   Center on the smaller clash mesh / source mesh if it's significantly smaller than the other clash / source mesh
    -   Avoid creating very small clash intersection profiles (outlines) and print a warning when that happens
    -   Avoid creating empty clash intersection profiles (outlines) to prevent USD warnings for clashes with no intersection profiles
    -   Display warnings when exceeding the number of allowed clash meshes to be displayed
    -   Fix Main viewport default light becoming disabled after opening clash viewport

## [107.3.9] - 2025-07-10

### Added

-   A row limit has been introduced in the Clash results table to restrict the number of rows displayed. The current limit is set to 1 million rows.
-   Introduced a per-clash outline triangle limit setting for the clash detection engine.
-   Added a new clash detection engine setting to ignore redundant overlaps.
-   Clash Baking feature:
    -   Added new options to enable / disable per polygon bake, wireframes and outlines.
    -   Added new display opacity mode to improve runtime performance for large meshes.
    -   Added support for baking meshes animated through animation curves.

### Improved

-   The clash detection engine can now process more clashing pairs than before, allowing it to run on even larger stages.
-   The clash report exporter now uses row numbers instead of clash IDs.
-   The currently edited query is now automatically saved when the window is closed.
-   Clash Visualization: Enhanced outline transform computation for clashes far from the origin and boosted performance by leveraging FSD.
-   Clash detection pipeline now runs asynchronously, not blocking the UI.

### Fixed

-   Certain "2D meshes" that were previously flagged as invalid during the clash detection process are now processed correctly.
-   Fixed an issue that occurred when assigning a person (PIC) in the Clash results table.

## [106.5.0] - 2025-03-07

### Added

-   Contact Depth: A new experimental feature that measures the local depth of contact between two objects. It also includes an adjustable Depth Epsilon value to differentiate between hard clashes and contact cases.
-   Clash Query settings were reorganized for better understanding.
-   Clash Query searchsets now support multiple object paths.
-   Improved viewport visualization for dynamic clashes, now capable of displaying animated clashes as actual animations.
-   Consumes considerably less RAM while processing clash detection results and manages out of memory conditions more effectively by halting clash detection and releasing all allocated memory.
-   Faster stage enumeration (first step of clash detection process).

## [106.4.0] - 2024-12-05

### Added

-   Duplicate Mesh Detection and Management: This feature identifies and manages duplicate meshes. It specifically targets static, identical meshes that overlap completely due to having identical transformations.
-   Clash Classification: The system now supports clear classification of clashes into soft and hard categories. This is achieved by measuring the minimal distance between clashing objects.
-   Static Clash Detection Timing: Users can specify a specific time for static clash detection, which previously defaulted to the current time on timeline.
-   Clash Query Export/Import: Users can now export and import clash queries using JSON files, streamlining data exchange.
-   Per-Frame Transformation Tracking for Clashing Objects: Transformations of both clashing objects are now saved for each frame where a clash occurs, rather than only at the first frame. This enhancement helps users determine if an object in the scene has moved at any time since the last clash detection run.
-   Different colors on the progress bar now represent various stages of clash detection:

    -   Green indicates the conversion of curve animations to time samples.
    -   Orange signifies the clash detection engine's activity.
    -   Blue denotes the result-fetching process.

## [106.2.0] - 2024-09-25

### Added

-   Support for curve animations has been added. Works seamlessly as a part of clash detection process.
-   The Clash Query combo box now displays the start and end times for dynamic queries.

### Improved

-   The retrieval of results at the end of the clash detection process is now five times faster.
-   Improved internal processing of clash detection files to ensure proper support for larger files (approximately 2GB and more).

### Fixed

-   The search set picker was not updating properly after a stage change.
-   If only a single search set was configured, no clash detection results were returned.

### Removed

-   The feature that indicated outdated transformations (an orange square) has been disabled, as it is no longer relevant. This change is due to our support for curve animations, which require conversion into time samples; a process that only occurs when the clash detection process begins.
