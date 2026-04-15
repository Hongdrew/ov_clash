# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import json
from typing import Optional, Sequence
from .utils import html_escape


class ExportColumnDef:
    """A class for defining export column properties.

    This class encapsulates the properties of a column definition used for exporting data, including the order of the column, its name, and its text alignment.

    Args:
        order (int): The order of the column in the export.
        name (str): The name of the column.
        alignment (bool): The alignment of the text in the column; False for left alignment, True for right alignment.
    """

    def __init__(self, order: int, name: str, alignment: bool = False) -> None:  # alignment False = left, True = right
        """Initializes an instance of the ExportColumnDef class."""
        self._order = order
        self._name = name
        self._alignment = alignment

    @property
    def order(self) -> int:
        """Order of the column.

        Returns:
            int: The order of the column.
        """
        return self._order

    @property
    def name(self) -> str:
        """Name of the column.

        Returns:
            str: The name of the column.
        """
        return self._name

    @property
    def alignment(self) -> bool:
        """Alignment of the column. False for left alignment, True for right alignment.

        Returns:
            bool: The alignment of the column.
        """
        return self._alignment


def export_to_json(
    column_defs: Sequence["ExportColumnDef"],
    rows: Sequence[Sequence[str]],
    additional_info: Optional[dict[str, str]] = None,
) -> bytes:
    """Convert the given data to a JSON format.

    Args:
        column_defs (Sequence[ExportColumnDef]): List of column definitions.
        rows (Sequence[Sequence[str]]): Data rows to be exported.
        additional_info (dict[str, str], optional): Additional info as name-value pairs.

    Returns:
        bytes: JSON representation of the data encoded in UTF-8.
    """
    json_dict: dict[str, object] = {}
    if additional_info and len(additional_info) > 0:
        json_dict["additional_info"] = additional_info
    json_dict["columns"] = [cd.name for cd in column_defs]
    json_dict["rows"] = rows
    return json.dumps(json_dict, indent=4).encode("utf-8")


def export_to_html(
    title: str,
    subtitle: str,
    column_defs: Sequence["ExportColumnDef"],
    rows: Sequence[Sequence[str]],
    additional_info: Optional[dict[str, str]] = None,
) -> bytes:
    """Convert the given data to an HTML format.

    Args:
        title (str): Title of the HTML document.
        subtitle (str): Subtitle of the HTML document.
        column_defs (Sequence[ExportColumnDef]): List of column definitions.
        rows (Sequence[Sequence[str]]): Data rows to be exported.
        additional_info (dict[str, str], optional): Additional info as name-value pairs.

    Returns:
        bytes: HTML representation of the data encoded in UTF-8.
    """

    def get_alignment_str(right_aligned: bool):
        return "right" if right_aligned is True else "left"

    html_heading = f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <head>
        <title>{title}</title>
        <style>
            body {{font-family:\"Segoe UI\",SegoeUI,\"Helvetica Neue\",Helvetica,Calibri,Arial,sans-serif;}}
            th, td {{padding: 4px; border-bottom: 1px solid #ddd; word-wrap: break-word;}}
            th {{background-color: #EEEEEE;}}
            tr:hover {{background-color: #EEEEEE;}}
            .info-table {{
                margin-bottom: 24px;
                margin-top: 8px;
                border-collapse: collapse;
                width: auto;
                min-width: 200px;
            }}
            .info-table th, .info-table td {{
                border-top: 1px solid #ddd;
                padding: 4px 10px;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <h2>{subtitle}</h2>
"""

    # Additional info table
    html_additional_info = ""
    if additional_info and len(additional_info) > 0:
        html_additional_info += '        <table class="info-table">\n'
        # html_additional_info += "          <tr><th>Name</th><th>Value</th></tr>\n"
        for k, v in additional_info.items():
            html_additional_info += f"          <tr><td>{html_escape(str(k))}</td><td>{html_escape(str(v))}</td></tr>\n"
        html_additional_info += "        </table>\n"

    # Main data table
    html_table_start = "        <table>\n"

    # table header
    html_table_header = "           <tr>"
    for cd in column_defs:
        value = html_escape(cd.name)
        html_table_header += f'<th align="{get_alignment_str(cd.alignment)}">{value}</th>'
    html_table_header += "</tr>\n"

    # table body
    body_parts = []
    for rm in rows:
        body_parts.append("           <tr>")
        for cd in column_defs:
            if cd.name == "Image":
                value = f'<img width="200" src="{rm[cd.order]}"/>'
            else:
                value = html_escape(rm[cd.order])
                if value.startswith("/"):
                    value = value.replace("/", "<wbr>/<wbr>")  # allow word break between separators on paths
            body_parts.append(f'<td align="{get_alignment_str(column_defs[cd.order].alignment)}">{value}</td>')
        body_parts.append("</tr>\n")
    html_table_body = "".join(body_parts)

    signature = "<br><i>Document generated by NVIDIA Omniverse Clash Detection.</i>"
    html_footer = f"       </table>\n     {signature}\n    </body>\n</html>"

    html = html_heading + html_additional_info + html_table_start + html_table_header + html_table_body + html_footer
    return html.encode("utf-8")
