========
config
========

.. module:: omni.physxclashdetectioncore.config

This module provides configuration settings for the clash detection extension.

Classes
=======

ExtensionConfig
---------------

.. class:: ExtensionConfig

   A configuration class for managing extension settings.

   This class is used to configure various settings for an extension, including
   enabling or disabling debug logging and specifying the path to the extension.

   **Class Attributes:**

   .. attribute:: debug_logging
      :type: bool
      :value: False

      Indicates whether debugging messages should be printed.

   .. attribute:: extension_path
      :type: Optional[str]
      :value: None

      The file path to the extension, set at startup if available.

   .. attribute:: update_clash_states_after_detection
      :type: bool
      :value: True

      Indicates whether to update clash states after running clash detection.

      When set to True, clashes that were previously detected but are no longer found
      will be marked as RESOLVED, and newly detected clashes will be marked as ACTIVE.


Example
=======

Using ExtensionConfig:

.. code-block:: python

   from omni.physxclashdetectioncore.config import ExtensionConfig

   # Enable debug logging
   ExtensionConfig.debug_logging = True

   # Disable automatic clash state updates
   ExtensionConfig.update_clash_states_after_detection = False

   # Access extension path (set during startup)
   if ExtensionConfig.extension_path:
       print(f"Extension path: {ExtensionConfig.extension_path}")

