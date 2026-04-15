========
utils
========

.. module:: omni.physxclashdetectioncore.utils

This module provides utility functions for file operations, data conversion, and progress tracking.

Functions
=========

File Operations
---------------

.. function:: file_exists(path_name: str) -> bool

   Checks if file specified by path_name exists and returns True on success, otherwise returns False.

   :param path_name: Path to the file to check.
   :type path_name: str
   :return: True if the file exists, False otherwise.
   :rtype: bool


.. function:: safe_copy_file(src: str, dst: str, follow_symlinks: bool = True) -> bool

   Copies src to dst and returns True on success, otherwise returns False.
   Also supports URLs.

   :param src: Source file path.
   :type src: str
   :param dst: Destination file path.
   :type dst: str
   :param follow_symlinks: Whether to follow symlinks. Defaults to True.
   :type follow_symlinks: bool
   :return: True if the file is successfully copied, False otherwise.
   :rtype: bool


.. function:: safe_delete_file(file_name: str) -> bool

   Deletes file specified by file_name from drive and returns True on success, otherwise returns False.

   :param file_name: Name of the file to delete.
   :type file_name: str
   :return: True if the file is successfully deleted, False otherwise.
   :rtype: bool


.. function:: get_temp_file_path_name(suffix: str = "") -> str

   Generates temp file path name.

   :param suffix: Optional suffix for the file name. Defaults to "".
   :type suffix: str
   :return: Temporary file path name.
   :rtype: str


.. function:: get_unique_temp_file_path_name(suffix: str = "") -> str

   Generates unique temp file path name (makes sure it does not exist yet).

   :param suffix: Optional suffix for the file name. Defaults to "".
   :type suffix: str
   :return: Unique temporary file path name.
   :rtype: str


.. function:: is_local_url(url: str) -> bool

   Returns True if the url points to a local file. Returns False in case of remote URL.

   :param url: URL to check.
   :type url: str
   :return: True if the URL is local, False otherwise.
   :rtype: bool


Data Conversion
---------------

.. function:: make_int128(hi: int, lo: int) -> int

   Makes 128bit number out of two 64bit numbers.

   :param hi: High 64 bits.
   :type hi: int
   :param lo: Low 64 bits.
   :type lo: int
   :return: 128-bit integer combining hi and lo.
   :rtype: int


.. function:: html_escape(t: str) -> str

   Escapes special HTML characters (provided in t).

   :param t: Text to escape.
   :type t: str
   :return: Escaped text.
   :rtype: str


.. function:: to_json_str_safe(obj: Any, **kwargs) -> str

   Safely converts a Python object into a JSON string.

   This function attempts to serialize a Python object into a JSON-formatted string.
   If serialization fails, it logs an error message and returns an empty string.

   :param obj: The Python object to be serialized into a JSON string.
   :type obj: Any
   :param kwargs: Additional keyword arguments passed to json.dumps(), such as formatting options.
   :return: A JSON-formatted string representation of the object. Returns an empty string if serialization fails.
   :rtype: str


.. function:: from_json_str_safe(json_str: str) -> Any

   Safely converts a JSON string into a Python object.

   This function attempts to parse a JSON-encoded string into a corresponding
   Python object. If the input string is empty or an error occurs during parsing,
   it logs an error message and returns an empty list.

   :param json_str: The JSON string to be converted.
   :type json_str: str
   :return: A Python object resulting from the parsed JSON string. Returns an empty list if the input is empty or if parsing fails.
   :rtype: Any


.. function:: clamp_value(value: Any, min_value: Any, max_value: Any) -> Any

   Clamps value within the min and max range.

   :param value: The value to be clamped.
   :param min_value: The minimum allowable value.
   :param max_value: The maximum allowable value.
   :return: The clamped value within the specified range.


.. function:: obj_to_dict(obj: Any, attr_convert_fn: Optional[Callable[[str, Any], Any]] = None) -> Dict[str, Any]

   Converts an object instance to a dictionary.

   Converts object attributes to a dictionary, handling special cases for Enum and datetime types.
   Enum values are converted to their string names and datetime objects are converted to ISO format strings.

   :param obj: The object to convert to a dictionary.
   :type obj: Any
   :param attr_convert_fn: Optional function to convert attribute values. Takes attribute name and value as arguments and returns the converted value.
   :type attr_convert_fn: Optional[Callable[[str, Any], Any]]
   :return: Dictionary containing the object's attributes and their converted values.
   :rtype: Dict[str, Any]


.. function:: dict_to_obj(obj: Any, data: Dict[str, Any], attr_convert_fn: Optional[Callable[[str, Any], Any]] = None) -> bool

   Converts a dictionary to an object instance.

   :param obj: The target object to populate with dictionary data.
   :type obj: Any
   :param data: The source dictionary containing attribute values.
   :type data: Dict[str, Any]
   :param attr_convert_fn: Optional function to convert attribute values. Takes attribute name and value as arguments and returns the converted value.
   :type attr_convert_fn: Optional[Callable[[str, Any], Any]]
   :return: True if successful, False otherwise.
   :rtype: bool


System Information
------------------

.. function:: get_current_user_name() -> str

   Returns name of the currently logged-in user.

   :return: The current user's name.
   :rtype: str


.. function:: get_available_system_memory() -> int

   Returns available system memory in bytes.

   :return: Available system memory in bytes.
   :rtype: int


.. function:: get_random_word(length: int) -> str

   Generates random ascii lowercase word of 'length' characters.

   :param length: Length of the random word.
   :type length: int
   :return: Randomly generated word.
   :rtype: str


Decorators
----------

.. function:: measure_execution_time(func: Callable) -> Callable

   A decorator to measure execution time.

   :param func: The function to measure.
   :type func: Callable
   :return: Wrapped function with execution time measurement.
   :rtype: Callable


Classes
=======

OptimizedProgressUpdate
------------------------

.. class:: OptimizedProgressUpdate(update_rate: float = 0.1, force_update_rate: float = 1.0, auto_start: bool = True)

   A utility class to manage progress updates efficiently by limiting excessive updates.

   This class determines whether a progress update should be propagated based on the elapsed
   time since the last update and the change in progress value. It ensures that updates are
   sent at a controlled rate, preventing unnecessary updates that could impact performance.

   :param update_rate: Time interval (in seconds) between successive updates when the progress value changes. Defaults to 0.1 seconds.
   :type update_rate: float
   :param force_update_rate: Maximum allowable time interval (in seconds) before forcing an update, regardless of progress change. Defaults to 1.0 seconds.
   :type force_update_rate: float
   :param auto_start: Whether to initialize progress tracking automatically upon instantiation. Defaults to True.
   :type auto_start: bool

   **Methods:**

   .. method:: start()

      Resets the progress tracking state.

      This method initializes or resets the internal state, ensuring that the first
      update is allowed immediately after calling this method.

   .. method:: update(progress_value: float) -> bool

      Determines whether a progress update should be propagated.

      An update is triggered if either:

      - The elapsed time since the last update exceeds force_update_rate, or
      - The progress value has changed and the elapsed time exceeds update_rate.

      :param progress_value: The current progress value as a fraction between 0.0 and 1.0.
      :type progress_value: float
      :return: True if an update should be propagated, False otherwise.
      :rtype: bool

   **Properties:**

   .. attribute:: progress_value
      :type: float

      Gets the last recorded progress value between 0.0 and 1.0+.


Example
=======

Using utility functions and classes:

.. code-block:: python

   from omni.physxclashdetectioncore.utils import (
       file_exists,
       get_unique_temp_file_path_name,
       OptimizedProgressUpdate,
       measure_execution_time
   )

   # Check if file exists
   if file_exists("/path/to/file.txt"):
       print("File exists")

   # Get unique temp file path
   temp_file = get_unique_temp_file_path_name(suffix=".tmp")
   print(f"Temp file: {temp_file}")

   # Use progress tracker
   progress = OptimizedProgressUpdate()
   for i in range(100):
       # Your processing here
       if progress.update(float(i) / 100.0):
           print(f"Progress: {progress.progress_value * 100:.1f}%")

   # Measure execution time
   @measure_execution_time
   def my_function():
       # Your code here
       pass

   my_function()  # Will print execution time

