============
commands
============

.. module:: omni.physxclashdetectioncore.commands

This module provides Omni Kit commands for clash detection operations.

Commands
========

OpenStageForClashDetectionCommand
----------------------------------

.. class:: OpenStageForClashDetectionCommand(**kwargs)

   A command to open a USD stage for clash detection.

   This command facilitates opening a USD stage and preparing it for clash detection processes. It ensures that the stage path is standardized and that the stage is correctly loaded into the cache.

   **Keyword Args:**

   :param path: The path to the USD stage.
   :type path: str
   :param stage_path: An alternative key for the path to the USD stage.
   :type stage_path: str

   **Methods:**

   .. method:: do() -> int

      Opens the stage for clash detection.

      :return: The ID of the loaded stage.
      :rtype: int

   .. method:: undo() -> None

      Undoes the clash detection stage opening.


SaveClashDetectionCommand
--------------------------

.. class:: SaveClashDetectionCommand(stage_id)

   A command to save the results of a clash detection process.

   This class provides the functionality to save the clash detection results for a given stage ID to a persistent storage.

   :param stage_id: The ID of the stage for which the clash detection results are to be saved.
   :type stage_id: int

   **Methods:**

   .. method:: do() -> int

      Executes the command to save clash detection results.

      :return: The stage ID if successful, otherwise 0.
      :rtype: int


CloseStageForClashDetectionCommand
-----------------------------------

.. class:: CloseStageForClashDetectionCommand(stage_id)

   A command to close a stage used for clash detection.

   This command handles the process of closing a stage by erasing it from the stage cache and destroying any associated clash data.

   :param stage_id: The identifier of the stage to be closed.
   :type stage_id: int

   **Methods:**

   .. method:: do() -> bool

      Closes the stage and cleans up clash detection data.

      :return: True if the stage was successfully closed, otherwise False.
      :rtype: bool


RunClashDetectionCommand
-------------------------

.. class:: RunClashDetectionCommand(stage_id: int, object_a_path: str = "", object_b_path: str = "", tolerance: float = 0.0, dynamic: bool = False, start_time: float = 0.0, end_time: float = 0.0, logging: bool = False, html_path_name: str = "", json_path_name: str = "", query_name: str = "RunClashDetectionCommand Query", comment: str = "")

   Run the clash detection on a stage.

   :param stage_id: ID of the stage to be processed.
   :type stage_id: int
   :param object_a_path: Absolute stage path or a USD collection to define searchset A. Defaults to "".
   :type object_a_path: str
   :param object_b_path: Absolute stage path or a USD collection to define searchset B. Defaults to "".
   :type object_b_path: str
   :param tolerance: Tolerance distance for overlap queries. Use zero for hard clashes, non-zero for soft (clearance) clashes. Defaults to 0.0.
   :type tolerance: float
   :param dynamic: True for dynamic clash detection, False for static. Defaults to False.
   :type dynamic: bool
   :param start_time: Start time in seconds. Only works when dynamic clash detection is enabled. Defaults to 0.0.
   :type start_time: float
   :param end_time: End time in seconds. Only works when dynamic clash detection is enabled. Defaults to 0.0.
   :type end_time: float
   :param logging: If True, logs info & performance results to console. Defaults to False.
   :type logging: bool
   :param html_path_name: Full path to HTML file if export to HTML is needed. No clash images will be exported. Defaults to "".
   :type html_path_name: str
   :param json_path_name: Full path to JSON file if export to JSON is needed. No clash images will be exported. Defaults to "".
   :type json_path_name: str
   :param query_name: Custom name for the clash detection query which will be generated based on parameters above. Defaults to "RunClashDetectionCommand Query".
   :type query_name: str
   :param comment: Custom comment for the clash detection query which will be generated based on parameters above. Defaults to "".
   :type comment: str

   **Methods:**

   .. method:: do() -> int

      Executes the clash detection command.

      :return: ID of the stage processed.
      :rtype: int

   .. method:: undo() -> bool

      Undoes the clash detection command.

      :return: True on success, otherwise False.
      :rtype: bool


Functions
=========

.. function:: register_commands()

   Register all commands in the current module.

.. function:: unregister_commands()

   Unregister all commands previously registered in the current module.


Example
=======

Running clash detection using commands:

.. code-block:: python

   import omni.kit.commands
   from omni.physxclashdetectioncore import commands

   # Register commands
   commands.register_commands()

   # Open stage
   stage_id = omni.kit.commands.execute(
       "OpenStageForClashDetectionCommand",
       path="/path/to/stage.usd"
   )

   # Run clash detection
   omni.kit.commands.execute(
       "RunClashDetectionCommand",
       stage_id=stage_id,
       object_a_path="",
       object_b_path="",
       tolerance=0.0,
       dynamic=False,
       logging=True,
       html_path_name="/path/to/output.html",
       query_name="My Clash Detection"
   )

   # Save results
   omni.kit.commands.execute(
       "SaveClashDetectionCommand",
       stage_id=stage_id
   )

   # Close stage
   omni.kit.commands.execute(
       "CloseStageForClashDetectionCommand",
       stage_id=stage_id
   )

   # Unregister commands when done
   commands.unregister_commands()

