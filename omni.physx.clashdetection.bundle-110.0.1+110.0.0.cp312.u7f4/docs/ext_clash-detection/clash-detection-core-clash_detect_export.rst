========================
clash_detect_export
========================

.. module:: omni.physxclashdetectioncore.clash_detect_export

This module provides export functionality for clash detection results to various formats.

Classes
=======

ExportColumnDef
---------------

.. class:: ExportColumnDef(order: int, name: str, alignment: bool = False)

   A class for defining export column properties.

   This class encapsulates the properties of a column definition used for exporting data, including the order of the column, its name, and its text alignment.

   :param order: The order of the column in the export.
   :type order: int
   :param name: The name of the column.
   :type name: str
   :param alignment: The alignment of the text in the column; False for left alignment, True for right alignment. Defaults to False.
   :type alignment: bool

   **Properties:**

   .. attribute:: order
      :type: int

      Order of the column.

   .. attribute:: name
      :type: str

      Name of the column.

   .. attribute:: alignment
      :type: bool

      Alignment of the column. False for left alignment, True for right alignment.


Functions
=========

.. function:: export_to_json(column_defs: Sequence[ExportColumnDef], rows: Sequence[Sequence[str]], additional_info: Optional[dict[str, str]] = None) -> bytes

   Convert the given data to a JSON format.

   :param column_defs: List of column definitions.
   :type column_defs: Sequence[ExportColumnDef]
   :param rows: Data rows to be exported.
   :type rows: Sequence[Sequence[str]]
   :param additional_info: Additional info as name-value pairs. Defaults to None.
   :type additional_info: Optional[dict[str, str]]
   :return: JSON representation of the data encoded in UTF-8.
   :rtype: bytes

   **Example:**

   .. code-block:: python

      from omni.physxclashdetectioncore.clash_detect_export import export_to_json, ExportColumnDef

      column_defs = [
          ExportColumnDef(0, "Clash ID"),
          ExportColumnDef(1, "Min Distance", True),
          ExportColumnDef(2, "Object A"),
          ExportColumnDef(3, "Object B")
      ]

      rows = [
          ["0x1a2b3c", "0.523", "/World/ObjectA", "/World/ObjectB"],
          ["0x4d5e6f", "1.234", "/World/ObjectC", "/World/ObjectD"]
      ]

      additional_info = {
          "Stage": "/path/to/stage.usd",
          "Query": "Full Scene"
      }

      json_bytes = export_to_json(column_defs, rows, additional_info)


.. function:: export_to_html(title: str, subtitle: str, column_defs: Sequence[ExportColumnDef], rows: Sequence[Sequence[str]], additional_info: Optional[dict[str, str]] = None) -> bytes

   Convert the given data to an HTML format.

   :param title: Title of the HTML document.
   :type title: str
   :param subtitle: Subtitle of the HTML document.
   :type subtitle: str
   :param column_defs: List of column definitions.
   :type column_defs: Sequence[ExportColumnDef]
   :param rows: Data rows to be exported.
   :type rows: Sequence[Sequence[str]]
   :param additional_info: Additional info as name-value pairs. Defaults to None.
   :type additional_info: Optional[dict[str, str]]
   :return: HTML representation of the data encoded in UTF-8.
   :rtype: bytes

   **Example:**

   .. code-block:: python

      from omni.physxclashdetectioncore.clash_detect_export import export_to_html, ExportColumnDef

      column_defs = [
          ExportColumnDef(0, "Clash ID"),
          ExportColumnDef(1, "Min Distance", True),
          ExportColumnDef(2, "Object A"),
          ExportColumnDef(3, "Object B")
      ]

      rows = [
          ["0x1a2b3c", "0.523", "/World/ObjectA", "/World/ObjectB"],
          ["0x4d5e6f", "1.234", "/World/ObjectC", "/World/ObjectD"]
      ]

      additional_info = {
          "Stage": "/path/to/stage.usd",
          "Query": "Full Scene"
      }

      html_bytes = export_to_html(
          "Clash Detection Results",
          "/path/to/stage.usd",
          column_defs,
          rows,
          additional_info
      )

