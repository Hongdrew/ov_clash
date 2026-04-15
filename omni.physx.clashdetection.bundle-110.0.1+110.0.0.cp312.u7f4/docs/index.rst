.. _ClashDetection:

============================================
Clash Detection
============================================

Overview
--------

The goal of clash detection is to prevent costly and time-consuming conflicts during the construction phase of a project. By identifying and resolving clashes early in the design process, project stakeholders can minimize rework, avoid delays, and improve overall project efficiency. It is an essential aspect of modern construction and design processes, especially in complex projects with numerous interconnected systems and components.

Resolving clashes often involves adjusting the positions of clashing components, modifying the design, or reconfiguring the layout.

.. note:: Clash detection only works with meshes, not shapes.

.. dropdown:: Learn about the types of clashes.

    **Hard**

    Hard clashes occur when physical components occupy the same space within a project. Examples include walls intersecting with doors or windows, structural elements conflicting with plumbing or electrical systems, or equipment interfering with pathways.

    **Soft**

    Soft clashes are clearance clashes. Such clashes occur when there is insufficient space between components, potentially leading to operational or safety issues. For instance, a piece of machinery might not have enough overhead clearance, or pipes might be too close to walls.

    **Static**

    A static clash refers to a clash between two or more building components or systems that are in fixed positions. For example a wall intersecting with a pipe.

    **Dynamic**

    A dynamic clash involves clashes that might occur during the operational phase of a project when components are in motion or change position.
    An example of a dynamic clash could be a situation where two robots are programmed to move along certain paths but would collide with each other if their paths cross at a certain point.

Clash Detection Video Tutorial
###############################

.. raw:: html

    <iframe type="text/javascript" src='https://cdnapisec.kaltura.com/p/2935771/embedPlaykitJs/uiconf_id/53712482?iframeembed=true&entry_id=1_1urp07p0' style="width: 700px; height: 394px" allowfullscreen webkitallowfullscreen mozAllowFullScreen allow="autoplay *; fullscreen *; encrypted-media *" frameborder="0"></iframe>

Using Clash Detection Extensions
---------------------------------
There are multiple extensions that work together to deliver flexible clash detection functionality. Extensions also expose APIs that allow customization of the process.

Using Clash Detection begins with enabling the Clash Detection Bundle extension, which bundles all clash detection extensions together in a single easy-to-enable dependency.

.. dropdown:: Learn about all of the clash detection extensions.
    :open:

    Here is list of extensions that work together to deliver flexible clash detection functionality.

Here is a list of extensions that work together to deliver flexible clash detection functionality:

- ``omni.physx.clashdetection.bundle``:

  Bundles all extensions together in a single easy-to-enable dependency.

- ``omni.physx.clashdetection``:

  Contains the clash detection C++ engine and low-level API to start the process and access results.

- ``omni.physx.clashdetection.core``:

  The primary Python-based clash detection extension that leverages the clash detection engine by introducing essential data structures for holding clash information and queries. It also incorporates support for serialization and deserialization.

- ``omni.physx.clashdetection.ui``:

  Responsible for user interface and workflow elements. It defines all UI components (except for the specialized clash detection viewport) and the user interaction flow.

- ``omni.physx.clashdetection.viewport``:

  Implements 3D visualization in the main viewport and in a dedicated *Clash Detection Viewport*.

- ``omni.physx.clashdetection.anim``:

  Adds support for curve animations by converting curve animations into time samples.

- ``omni.physx.clashdetection.bake``:

  Adds support for baking clash meshes to USD layers (including dynamic clashes).

- ``omni.physx.clashdetection.telemetry``:

  Provides telemetry facilities for performance and usage measurements to improve the product.

- ``omni.usd.schema.physx.clashdetection``:

  Allows saving the clash detection database as a USD layer. **Note:** Enabling or upgrading this extension requires a reboot of the kit application.

- ``omni.usd.schema.physx.clashdetection.viewport``:

  Allows highlighting clash objects in the viewport.

.. note:: Enabling Clash Detection Bundle ``omni.physx.clashdetection.bundle`` is sufficient to enable all needed extensions.

.. _ClashDetectionEnable:

Step 1: Enable the Clash Detection Bundle from Omniverse Extension Registry
###########################################################################

Regardless of whether your Omniverse application was built using the Omniverse `Kit Application Template <https://github.com/NVIDIA-Omniverse/kit-app-template>`__ or another method, the process for enabling the Clash Detection Bundle remains the same.

To learn how to build an Omniverse app using the Kit App Template, refer to the instructions provided in the official `documentation <https://github.com/NVIDIA-Omniverse/kit-app-template?tab=readme-ov-file>`__.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-enable_extension.png
    :alt: Enable clash detection extensions

To enable the extensions:

#. Navigate to ``Window > Extensions`` or sometimes to ``Developer > Extensions``.
#. In the search bar, enter ``Clash``.
#. Locate the ``Clash Detection Bundle`` extension and select it.
#. Select the ``Enabled`` toggle to enable the extension.
#. Select the ``Check Mark`` next to `AUTOLOAD` to load all of required extensions automatically on application start, if desired.
#. Close the Extensions Panel.

.. note::

   Upgrade Instructions:

   If you previously activated an older version of the Clash Detection Bundle, begin by individually disabling all Clash Detection extensions.
   Then, enable only the USD Schema For Clash Detection extension (``omni.usd.schema.physx.clashdetection``) and make sure the AUTOLOAD option is selected.
   After restarting the application, you can re-enable the other extensions by turning on the Clash Detection Bundle (``omni.physx.clashdetection.bundle``).

Step 2: Verify the Extension is Active
######################################

You can see if the extension is loaded by checking if the *Clash Detection* and *Clash Detection Viewport* menu items exist.

Click ``Window -> Physics -> Clash Detection`` and ``Window -> Physics -> Clash Detection Viewport`` menu items and you should now see the ``Clash Detection`` window (1) docked below and the ``Clash Detection Viewport`` window (2) docked to the right of the property panel.

.. image:: /images/ext_clashdetection/ext_physics_clashdetection-windows.png

How to Integrate Clash Detection Extensions from GitHub Samples into an Omniverse Application
---------------------------------------------------------------------------------------------

This chapter describes a process how to enable Clash Detection extensions in an Omniverse application like for example USD Composer.

#. First, you need to be granted access to `Clash Detection Samples GitHub <https://github.com/NVIDIA-Omniverse/clash-detection-samples>`_.
#. Once you have access, clone the Git repository to a local folder on your disk. Don't forget to read the `README.md <https://github.com/NVIDIA-Omniverse/clash-detection-samples/blob/main/README.md>`_ file.

#. Navigate to the root folder of the cloned Git repository and

    - On Windows execute `build.bat` file.
    - On Linux execute `./build.sh` file.

#. Locate where Clash Detection SDK extensions reside

    - On Windows, such folder is located in relative folder `_build/windows-x86_64/release/extsClashDetection`.
    - On Linux, such folder is located in relative folder `_build/linux-x86_64/release/extsClashDetection`.

#. Start the Omniverse application you are going to integrate Clash Detection SDK into (e.g. USD Composer).

    .. note:: Important: Please make sure that Omniverse application is based on the same Kit version as the Clash Detection SDK. You can find this information in the application About box.

#. Go to Window->Extensions.
#. Go to Settings (Hamburger menu on the right).
#. To `Extension Search Paths` section, add the full path to Clash Detection SDK extension folder (explained in the first bullet point above). Do not append path separator (slash or a backslash) to the end of the path.
#. Check the extensions 3rd party (second tab on the left).
#. Enable `omni.physx.clashdetection.bundle` extension. See :ref:`ClashDetectionEnable`.

    .. note:: Also check the `AUTOLOAD` checkbox if you want to have Clash Detection Bundle loaded on each application run automatically.

#. Restart the application.
#. Click Window->Physics->Clash Detection to open the main Clash Detection UI.

Learn More
##########

.. toctree::
   :maxdepth: 1

   ext_clash-detection/clash-detection-changelog
   ext_clash-detection/clash-detection-ui
   ext_clash-detection/clash-detection-viewport
   ext_clash-detection/clash-detection-core
   ext_clash-detection/clash-detection-anim
   ext_clash-detection/clash-detection-bake
