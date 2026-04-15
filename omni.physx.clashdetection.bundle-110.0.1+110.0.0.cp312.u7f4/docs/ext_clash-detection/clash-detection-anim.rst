.. _Clash_Detection_Anim:

=========================
Clash Detection Anim API
=========================

The Clash Detection Anim extension (included in the Clash Detection Bundle extension) is an API that provides functionality for recording animation curves within a USD stage.
It captures transform animations (translate, rotate, scale) from animated prims and saves them as time samples in a USD session layer (by default "ClashStageRecordedData" layer).


AnimRecorder
============

.. class:: AnimRecorder

A class for recording animation curves within a USD stage.

This class utilizes the `ICurveAnimRecorder` interface to record animation curves over a specified time range for a given set of USD prims. It supports functionalities such as starting and stopping recordings, resetting session properties, and configuring recording attributes.

Methods
-------

.. method:: destroy()

   Releases the stage recorder interface and cleans up the recorder API.

.. method:: reset_overridden_session_prim_props()

   Resets overridden session prim properties.

.. method:: get_recording_session_layer_name() -> str

   Gets the name of the recording session layer.

   :returns: The name of the recording session layer.
   :rtype: str

.. method:: run(stage: Usd.Stage, prims_int_path: List[int], start_time: float, end_time: float, fps: float) -> Generator[float, None, None]

   Records animation curves for the given prims from start_time to end_time at the specified fps.
   The recording is saved to a session layer that can be accessed via get_recording_session_layer_name().
   Yields the current timeline time in seconds as recording progresses.

   :param stage: The USD stage containing the prims to record.
   :type stage: Usd.Stage
   :param prims_int_path: List of integer prim paths to record.
   :type prims_int_path: List[int]
   :param start_time: Start time in seconds.
   :type start_time: float
   :param end_time: End time in seconds.
   :type end_time: float
   :param fps: Frames per second for the recording.
   :type fps: float
   :returns: Yields the current time in seconds as recording progresses.
   :rtype: Generator[float, None, None]

Attributes
----------

.. attribute:: copy_also_unrecorded_usd_attribs_on_save

   Gets or sets whether to copy unrecorded USD attributes on save.

   - **Getter**: Returns `True` if unrecorded attributes will be copied.
   - **Setter**: Sets whether to copy unrecorded USD attributes on save.

   :param value: If `True`, copies unrecorded attributes.
   :type value: bool

Usage Example
-------------

.. code-block:: python

   from pxr import Usd
   from omni.physxclashdetectionanim.scripts.anim_recorder import AnimRecorder

   # Create a USD stage (assuming you have a valid USD file path)
   stage = Usd.Stage.Open("path/to/your.usd")

   # Initialize the AnimRecorder
   anim_recorder = AnimRecorder()

   # Define the prims to record (using integer paths)
   prims_int_path = [0, 0, 0]  # Example integer paths

   # Define the recording parameters
   start_time = 0.0  # Start time in seconds
   end_time = 10.0   # End time in seconds
   fps = 24.0        # Frames per second

   # Run the recording
   for current_time in anim_recorder.run(stage, prims_int_path, start_time, end_time, fps):
       print(f"Recording at time: {current_time} seconds")

   # Get the name of the recording session layer
   session_layer_name = anim_recorder.get_recording_session_layer_name()
   print(f"Recording session layer name: {session_layer_name}")

   # Clean up the recorder
   anim_recorder.destroy()
