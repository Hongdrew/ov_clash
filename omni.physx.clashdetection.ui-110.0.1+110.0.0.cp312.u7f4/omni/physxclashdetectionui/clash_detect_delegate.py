# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, Callable, Optional, Tuple
import omni.ui as ui
from omni.physxclashdetectioncore.clash_info import ClashInfo, ClashState
from .table_delegates import TableColumnDef, EditableColumn, TableDelegate
from .clash_detect_viewmodel import ClashDetectTableRowItem, ClashDetectTableColumnEnum, ClashDetectTableModel
from .styles import Styles
from .pic_viewmodel import PersonInChargeComboBoxModel, PersonInChargeColumnModel, PersonInChargeComboBoxItem
from .clash_state_viewmodel import ClashStateComboBoxModel
from .clash_info_dropdown_viewmodel import ClashInfoDropdownModel
from .clash_state_viewmodel import ClashStateComboBoxItem
from .clash_priority_viewmodel import ClashPriorityComboBoxItem, ClashPriorityComboBoxModel
from .models import SortablePathModel
from .settings import ExtensionSettings

__all__ = []


class InvisibleTableColumnDef(TableColumnDef):
    """
    A class for defining invisible table columns.

    This class is used to create table columns that are not visible in the UI, but may still hold data or be used for other purposes.
    """

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders a cell in the invisible table column.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model containing the cell.
            model (ui.AbstractItemModel): The table model to which the cell belongs.
        """
        pass


class ClashNumberColumn(TableColumnDef):
    """
    A class for representing a column in a table that displays the clash number.

    This class extends the TableColumnDef class and is specifically designed to render cells that show the minimal distance of a clash in a clash detection table. The column is titled 'Min Distance' and aligns its content to the right with a specific width and minimum width.
    """

    def __init__(self):
        """Initializes an MinDistanceColumn instance."""
        super().__init__("#", ui.Alignment.LEFT, 48, 25)

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell for the MinDistanceColumn.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The item model for the cell.
        """
        clash_info = row_model._clash_info
        if not clash_info:
            return
        tooltip = f"Clash ID: {clash_info.overlap_id}"
        num_style = Styles.CLASH_NUM_INDICATOR
        if not clash_info.present:
            num_style = Styles.CLASH_NUM_INDICATOR_NOTPRESENT
            tooltip = "Clash is no longer present"
        with ui.ZStack(style=Styles.TABLE_CELL_STYLE):
            ui.Rectangle(tooltip=tooltip, style=num_style)
            ui.Label(f"{row_model.row_num}", alignment=ui.Alignment.CENTER, tooltip=tooltip, style=num_style)


class OverlapTypeColumn(TableColumnDef):
    """
    A class for representing a column in a table that displays the type of overlap."""

    def __init__(self):
        """Initializes the instance."""
        super().__init__("Type", ui.Alignment.LEFT, 50, 20, tooltip="Type of overlap")

    @staticmethod
    def get_tooltip(clash_info: ClashInfo) -> str:
        if clash_info.is_duplicate:
            return "Duplicate"
        if clash_info.is_hard_clash:
            return "Hard Clash"
        if clash_info.is_soft_clash:
            return f"Soft Clash with minimal distance of {clash_info.min_distance:{'.8f'}}"
        if clash_info.is_contact:
            return f"Contact with maximal local depth of {clash_info.max_local_depth:{'.8f'}}"
        return ""

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell for the OverlapTypeColumn.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The item model for the cell.
        """
        if not row_model._clash_info:
            return
        cell_tooltip = OverlapTypeColumn.get_tooltip(row_model._clash_info) if row_model._clash_info else ""
        with ui.HStack():
            ui.Label(value_model.as_string, alignment=self.alignment, tooltip=cell_tooltip)


class MinDistanceColumn(TableColumnDef):
    """
    A class for representing a column in a table that displays the minimal distance of a clash.

    This class extends the TableColumnDef class and is specifically designed to render cells that show the minimal distance of a clash in a clash detection table. The column is titled 'Min Distance' and aligns its content to the right with a specific width and minimum width.
    """

    def __init__(self):
        """Initializes an MinDistanceColumn instance."""
        super().__init__("Min Distance", ui.Alignment.RIGHT, 80, 20, tooltip="Minimum distance between the two objects")

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell for the MinDistanceColumn.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The item model for the cell.
        """
        with ui.HStack():
            min_distance = value_model.as_string if value_model else ""
            ui.Label(min_distance, alignment=self.alignment, tooltip=min_distance)


class MaxLocalDepthColumn(TableColumnDef):
    """
    A class for representing a column in a table that displays the minimal distance of a clash.

    This class extends the TableColumnDef class and is specifically designed to render cells that show the minimal distance of a clash in a clash detection table. The column is titled 'Min Distance' and aligns its content to the right with a specific width and minimum width.
    """

    def __init__(self):
        """Initializes an MaxLocalDepthColumn instance."""
        super().__init__("Max Depth", ui.Alignment.RIGHT, 68, 20, tooltip="Maximum local depth")

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell for the MaxLocalDepthColumn.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The item model for the cell.
        """
        if not row_model._clash_info:
            return
        max_local_depth = value_model.as_string if value_model else ""
        with ui.HStack():
            if row_model._clash_info.is_soft_clash:
                tooltip = f"Soft clash\nNote: internal representation is {max_local_depth}"
                ui.Label("N/A", alignment=self.alignment, tooltip=tooltip)
            else:
                ui.Label(max_local_depth, alignment=self.alignment, tooltip=max_local_depth)


class OverlapTrisColumn(TableColumnDef):
    """
    A class for representing a column in a table that displays the maximum number of overlaps in triangles.

    This class extends the TableColumnDef class and is specifically designed to render cells that show the number of overlapping triangles in a clash detection table. The column is titled 'Max Overlaps' and aligns its content to the right with a specific width and minimum width.
    """

    def __init__(self):
        """Initializes an OverlapTrisColumn instance."""
        super().__init__("Triangles", ui.Alignment.RIGHT, 60, 30, tooltip="Maximum number of overlapping triangles")

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell for the OverlapTrisColumn.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The item model for the cell.
        """
        with ui.HStack():
            tris_cnt = value_model.as_string if value_model else ""
            ui.Label(tris_cnt, alignment=self.alignment, tooltip=tris_cnt + " triangles")


class ClashObjectColumn(TableColumnDef):
    """
    A class for creating and rendering columns in a clash detection table.

    This class is responsible for creating table columns that represent clash objects, including their names and associated colors. It provides methods to render the header and the cells of the column.

    Args:
        name (str): The name of the column.
        color (str): The color associated with the column.
    """

    def __init__(self, name, color):
        """Initializes ClashObjectColumn with the given name and color."""
        super().__init__(name, ui.Alignment.LEFT, 100, 50)
        self._color = color

    def render_header_inner(self):
        """Renders the inner content of the header."""
        with ui.HStack():
            ui.Rectangle(width=22, height=22, style={"background_color": self._color, "margin": Styles.MARGIN_DEFAULT})
            ui.Label(self.name, alignment=self.alignment, style={"margin": Styles.MARGIN_DEFAULT})

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders a cell in the table.

        Args:
            value_model (ui.AbstractValueModel): Model holding the cell value.
            row_model (ClashDetectTableRowItem): Model holding the row data.
            model (ui.AbstractItemModel): The table's item model.
        """
        if isinstance(value_model, SortablePathModel):
            name = value_model.full_path if ExtensionSettings.show_full_clash_paths else value_model.name
            full_path = value_model.full_path
        else:
            name = value_model.as_string
            full_path = value_model.as_string
        ui.Label(name, alignment=self.alignment, tooltip=full_path)


class LastModifiedColumn(TableColumnDef):
    """
    A class for displaying the 'Last Modified' column in a table.

    This class provides functionality for rendering a cell in the 'Last Modified' column, which includes the timestamp of the last modification and the username of the person who made the modification. The timestamp is displayed as a label with a tooltip showing both the timestamp and the username.
    """

    def __init__(self):
        """Initialize the LastModifiedColumn with specific attributes."""
        super().__init__("Last Modified", ui.Alignment.LEFT, 140, 60, tooltip="Last time the clash was modified")

    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Render the cell for the Last Modified column.

        Args:
            value_model (ui.AbstractValueModel): Model containing the cell's value.
            row_model (ClashDetectTableRowItem): Model containing the row's data.
            model (ui.AbstractItemModel): Model containing the table's data.
        """
        timestamp = value_model.as_string
        username = row_model.clash_info.last_modified_by if row_model.clash_info else ""
        tooltip = f"{timestamp} by {username}"
        ui.Label(timestamp, alignment=self.alignment, tooltip=tooltip)


class ClashInfoDropDownColumn(TableColumnDef):
    """
    A class representing a drop-down column in the Clash Detection table.

    This class is used to create a customizable drop-down column within the Clash Detection table, allowing users to select and interact with various clash information. It provides capabilities for rendering cells, activating editors, and handling data serialization.

    Args:
        name (str): The name of the column.
        alignment (ui.Alignment): The alignment of the column contents.
        default_width: The default width of the column.
        min_width: The minimum width of the column.
        is_sort_column (bool): Indicates if this column is used for sorting.
        sort_direction (bool): Specifies the sort order; False for descending, True for ascending.
        combo_model (Optional[ClashInfoDropdownModel]): The model used for the drop-down combo box.
        table_delegate (Optional[TableDelegate]): The table delegate this column belongs to.
    """

    def __init__(
        self,
        name: str = "",
        alignment: ui.Alignment = ui.Alignment.LEFT,
        default_width=None,
        min_width=None,
        is_sort_column: bool = False,
        sort_direction: bool = False,  # Specify False if data must be sorted in descending order; otherwise True.
        combo_model: Optional[ClashInfoDropdownModel] = None,
        table_delegate: Optional[TableDelegate] = None,  # table delegate this column belongs to
    ):
        """Initializes the ClashInfoDropDownColumn."""
        super().__init__(name, alignment, default_width, min_width, is_sort_column, sort_direction, table_delegate)
        self._combo_model: Optional[ClashInfoDropdownModel] = combo_model
        self._active_clash_info = None
        self.__edit_containers: Dict[ClashInfo, ui.HStack] = {}
        # we refresh the whole row on column update as it may have updated other fields as well
        self.__refresh_row: Dict[ClashInfo, Callable[[], None]] = {}

    def destroy(self):
        """Destroys the column and cleans up resources."""
        if self._combo_model:
            self._combo_model.destroy()
            self._combo_model = None
        self._active_clash_info = None
        self.__edit_containers = {}
        self.__refresh_row = {}
        self._table_delegate = None
        super().destroy()

    def hide_active_editor(self, refresh_row: bool = False):  # override
        """Hides the currently active editor, if any."""
        if self._active_clash_info:
            old_container = self.__edit_containers.get(self._active_clash_info)
            if old_container:
                old_container.visible = False
            if refresh_row:
                refresh_row_fn = self.__refresh_row.get(self._active_clash_info)
                if refresh_row_fn:
                    refresh_row_fn()
            self._active_clash_info = None

    def activate_editor(self, clash_info: ClashInfo):
        """Activates the editor for the given clash information.

        Args:
            clash_info (ClashInfo): The clash information to be edited.
        """
        if self._active_clash_info == clash_info:
            return
        if self._table_delegate:
            self._table_delegate.hide_all_active_editors()
        else:
            self.hide_active_editor()
        container = self.__edit_containers.get(clash_info)
        if self._combo_model:
            self._combo_model.set_clash_info(None)
            self._combo_model.select_item_index(-1)
            self._combo_model.set_clash_info(clash_info)
        if not container:
            return
        with container:
            container.clear()  # remove an existing control, if any
            container.visible = True
            ui.ComboBox(self._combo_model, style=Styles.DROPDOWN_COLUMN_STYLE)
        self._active_clash_info = clash_info

    def edit_mode(self, clash_info: ClashInfo):
        """Enters edit mode for the provided clash information.

        Args:
            clash_info (ClashInfo): The clash information to be edited.
        """
        self.activate_editor(clash_info)

    def update_row_model(self, model: ClashDetectTableModel, row_model: ClashDetectTableRowItem):
        """Updates the row model with new data.

        Args:
            model (ClashDetectTableModel): The table model to be updated.
            row_model (ClashDetectTableRowItem): The row model to be updated.
        """
        model.update_row(row_model)

    def get_text(self, value_model: ui.AbstractValueModel):
        """Gets the text representation of the value model.

        Args:
            value_model (ui.AbstractValueModel): The value model to be converted to text.

        Returns:
            str: The text representation of the value model.
        """
        return value_model.as_string

    def get_tooltip(self, value_model: ui.AbstractValueModel):
        """Gets the tooltip text for the value model.

        Args:
            value_model (ui.AbstractValueModel): The value model to get the tooltip for.

        Returns:
            str: The tooltip text.
        """
        return value_model.as_string

    # override
    def render_cell(
        self, value_model: ui.AbstractValueModel, row_model: ClashDetectTableRowItem, model: ui.AbstractItemModel
    ):
        """Renders the cell in the table with the given value model, row model, and table model.

        Args:
            value_model (ui.AbstractValueModel): The value model for the cell.
            row_model (ClashDetectTableRowItem): The row model for the cell.
            model (ui.AbstractItemModel): The table model.
        """
        if not value_model or not row_model or not model or not isinstance(model, ClashDetectTableModel):
            return
        text = self.get_text(value_model)
        tooltip = self.get_tooltip(value_model)
        cie = row_model.clash_info
        if not cie:
            return
        with ui.ZStack(height=0):
            ui.Label(
                text,
                alignment=self._alignment,
                tooltip=tooltip,
                mouse_pressed_fn=lambda x, y, b, m, ci=cie: self.edit_mode(ci),
            )
            self.__edit_containers[cie] = ui.HStack(height=0)
            self.__refresh_row[cie] = lambda m=model, r=row_model: self.update_row_model(m, r)


class PersonInChargeColumn(ClashInfoDropDownColumn):
    """
    A class representing the 'Person In Charge' column in a table.

    This class extends the ClashInfoDropDownColumn and provides functionality to manage the 'Person In Charge' field in a clash detection table. The column allows users to select a person responsible for handling specific clashes from a dropdown menu.

    The class initializes the dropdown with a list of users, sorted alphabetically, and provides methods to serialize the selected person in charge, update the clash information, and manage the editor for the dropdown menu.
    """

    def __init__(self, table_delegate: Optional[TableDelegate] = None):
        """Initializes the PersonInChargeColumn with predefined settings and models."""
        if ExtensionSettings.users:
            items = [PersonInChargeComboBoxItem(user) for user in ExtensionSettings.users.get_items()]
        else:
            items = []
        items.sort()

        super().__init__(
            "Person In Charge",
            ui.Alignment.LEFT,
            120,
            40,
            combo_model=PersonInChargeComboBoxModel(items, lambda item, cie: self.serialize(item, cie)),
            table_delegate=table_delegate,
        )

    def serialize(self, item, cie):
        """Serializes the person in charge information.

        Args:
            item (PersonInChargeComboBoxItem): The item representing the person in charge.
            cie (ClashInfo): The clash information object.
        """
        if not item or not cie or not ExtensionSettings.clash_data:
            return
        if cie.person_in_charge == item.pic.username:
            return
        # print(f"cie.person_in_charge: {cie.person_in_charge} -> {item.pic.username}")  # debug only
        cie.person_in_charge = item.pic.username
        if ExtensionSettings.clash_data.update_overlap(cie, False, True) == 1:
            self.hide_active_editor(True)

    # overrides
    def get_tooltip(self, value_model: ui.AbstractValueModel) -> str:
        """Retrieves the tooltip text for the given value model.

        Args:
            value_model (PersonInChargeColumnModel): The value model to get the tooltip from.

        Returns:
            str: The tooltip text.
        """
        assert isinstance(value_model, PersonInChargeColumnModel)
        if not value_model.pic:
            return ""
        return value_model.pic.full_name_email

    def activate_editor(self, clash_info: ClashInfo):
        """Activates the editor for the specified clash information.

        Args:
            clash_info (ClashInfo): The clash information object.
        """
        super().activate_editor(clash_info)
        if self._combo_model and self._combo_model.items:
            for index, item in enumerate(self._combo_model.items):
                if item.pic.username == clash_info.person_in_charge:
                    self._combo_model.select_item_index(index)
                    break


class ClashStateColumn(ClashInfoDropDownColumn):
    """A class for representing and managing the state of a clash in a table.

    This class provides functionalities to render the state of a clash in a table cell,
    activate an editor to change the state, and serialize the state changes.

    The ClashStateColumn class inherits from ClashInfoDropDownColumn and initializes
    a combo box model with various clash states. It allows users to select and update
    the state of a clash interactively within the table.
    """

    def __init__(self, table_delegate: Optional[TableDelegate] = None):
        """Initializes the ClashStateColumn instance."""
        items = [ClashStateComboBoxItem(cs) for cs in list(ClashState)]

        super().__init__(
            "State",
            ui.Alignment.LEFT,
            80,
            20,
            combo_model=ClashStateComboBoxModel(items, lambda item, cie: self.serialize(item, cie)),
            table_delegate=table_delegate,
        )

    def serialize(self, item, cie):
        """Serializes the clash state information.

        Args:
            item (ClashStateComboBoxItem): The clash state item to be serialized.
            cie (ClashInfo): The clash info entity.
        """
        if not item or not cie or not ExtensionSettings.clash_data:
            return
        if cie.state == item.clash_state:
            return
        # print(f"cie.state: {cie.state} -> {item.clash_state}")  # debug only
        cie.state = item.clash_state
        ExtensionSettings.clash_data.update_overlap(cie, False, True)
        self.hide_active_editor(True)

    # overrides
    def activate_editor(self, clash_info: ClashInfo):
        """Activates the editor for the given clash information.

        Args:
            clash_info (ClashInfo): The clash information for which the editor is activated.
        """
        super().activate_editor(clash_info)
        if self._combo_model and self._combo_model.items:
            for index, item in enumerate(self._combo_model.items):
                if item.clash_state == clash_info.state:
                    self._combo_model.select_item_index(index)
                    break


class ClashPriorityColumn(ClashInfoDropDownColumn):
    """
    A class for rendering and managing the Priority column in a clash detection table.

    This class provides methods to render, edit, and serialize the priority values of clashes in a clash detection table. It extends from ClashInfoDropDownColumn and incorporates a combo box model for selecting priority levels.
    """

    def __init__(self, table_delegate: Optional[TableDelegate] = None):
        """Initializes the ClashPriorityColumn with predefined priority items."""
        items = [ClashPriorityComboBoxItem(p) for p in range(6)]

        super().__init__(
            "Priority",
            ui.Alignment.LEFT,
            45,
            20,
            combo_model=ClashPriorityComboBoxModel(items, lambda item, cie: self.serialize(item, cie)),
            table_delegate=table_delegate,
        )

    def serialize(self, item, cie):
        """Updates the clash priority if it has changed.

        Args:
            item (ClashPriorityComboBoxItem): The selected priority item.
            cie (ClashInfo): The clash info entity.
        """
        if not item or not cie or not ExtensionSettings.clash_data:
            return
        if cie.priority == item.clash_priority:
            return
        # print(f"cie.priority: {cie.priority} -> {item.clash_priority}")  # debug only
        cie.priority = item.clash_priority
        ExtensionSettings.clash_data.update_overlap(cie, False, True)
        self.hide_active_editor(True)

    # overrides
    def activate_editor(self, clash_info: ClashInfo):
        """Activates the editor for the given clash info.

        Args:
            clash_info (ClashInfo): The clash info to activate the editor for.
        """
        super().activate_editor(clash_info)
        if self._combo_model and self._combo_model.items:
            for index, item in enumerate(self._combo_model.items):
                if item.clash_priority == clash_info.priority:
                    self._combo_model.select_item_index(index)
                    break


class CommentColumn(EditableColumn):
    """
    A class for representing the comment column in the clash detection table.

    This class provides functionality to render and edit the comment field for each row in the clash detection table. It allows users to add, modify, and serialize comments related to clash information.
    """

    def __init__(self, table_delegate: Optional[TableDelegate] = None):
        """Initializes the CommentColumn."""
        super().__init__("Comment", ui.Alignment.LEFT, 350, 20, table_delegate=table_delegate)

    def serialize_and_refresh_row(self, field_model, row_model: ClashDetectTableRowItem, model: ClashDetectTableModel):
        """Serializes the comment and refreshes the row.

        Args:
            field_model (ui.AbstractValueModel): The field model holding the comment.
            row_model (ClashDetectTableRowItem): The row model containing clash info.
            model (ClashDetectTableModel): The table model to update.
        """
        if not field_model or not row_model or not model or not ExtensionSettings.clash_data:
            return
        cie = row_model.clash_info
        if not cie:
            return
        cie.comment = field_model.as_string
        if ExtensionSettings.clash_data.update_overlap(cie, False, True):
            model.update_row(row_model)


class ClashDetectTableDelegate(TableDelegate):
    """
    Delegate is the representation layer.
    It creates custom widgets for each item in the table as per the TreeView's request.

    Keyword Args:
        _columns: Dictionary of column definitions.
    """

    def __init__(self, **kwargs):
        """Initializes the ClashDetectTableDelegate."""
        super().__init__(**kwargs)
        self._columns = {
            ClashDetectTableColumnEnum.OVERLAP_NUM: ClashNumberColumn(),
            ClashDetectTableColumnEnum.PRESENT: TableColumnDef("Present", ui.Alignment.LEFT, 50, 30, tooltip="Whether the clash was present during the last clash detection run"),
            ClashDetectTableColumnEnum.OVERLAP_TYPE: OverlapTypeColumn(),
            ClashDetectTableColumnEnum.MIN_DISTANCE: MinDistanceColumn(),
            ClashDetectTableColumnEnum.TOLERANCE: TableColumnDef("Tolerance", ui.Alignment.RIGHT, 70, 20, tooltip="Tolerance distance.\nUse zero to detect only hard clashes.\nUse non-zero to detect both hard and soft clashes."),
            ClashDetectTableColumnEnum.LOCAL_COLL_DEPTH: MaxLocalDepthColumn(),
            ClashDetectTableColumnEnum.DEPTH_EPSILON: TableColumnDef("Depth Epsilon", ui.Alignment.RIGHT, 70, 20, tooltip="Epsilon value used to classify hard clashes vs contact cases"),
            ClashDetectTableColumnEnum.PEN_DEPTH_PX: TableColumnDef("PD +X", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the +X axis"),
            ClashDetectTableColumnEnum.PEN_DEPTH_NX: TableColumnDef("PD -X", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the -X axis"),
            ClashDetectTableColumnEnum.PEN_DEPTH_PY: TableColumnDef("PD +Y", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the +Y axis"),
            ClashDetectTableColumnEnum.PEN_DEPTH_NY: TableColumnDef("PD -Y", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the -Y axis"),
            ClashDetectTableColumnEnum.PEN_DEPTH_PZ: TableColumnDef("PD +Z", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the +Z axis"),
            ClashDetectTableColumnEnum.PEN_DEPTH_NZ: TableColumnDef("PD -Z", ui.Alignment.RIGHT, 65, 20, tooltip="Maximum penetration depth along the -Z axis"),
            ClashDetectTableColumnEnum.OVERLAP_TRIS: OverlapTrisColumn(),
            ClashDetectTableColumnEnum.CLASH_START_TIME: TableColumnDef("Clash Start", ui.Alignment.LEFT, 70, 40, tooltip="First time the clash was detected"),
            ClashDetectTableColumnEnum.CLASH_END_TIME: TableColumnDef("Clash End", ui.Alignment.LEFT, 70, 40, tooltip="Last time the clash was detected"),
            ClashDetectTableColumnEnum.NUM_CLASH_RECORDS: TableColumnDef("Records", ui.Alignment.RIGHT, 50, 20, tooltip="Number of clash records (frames)"),
            ClashDetectTableColumnEnum.OBJECT_A: ClashObjectColumn("Object A", Styles.COLOR_CLASH_A),
            ClashDetectTableColumnEnum.OBJECT_B: ClashObjectColumn("Object B", Styles.COLOR_CLASH_B),
            ClashDetectTableColumnEnum.STATE: ClashStateColumn(table_delegate=self),
            ClashDetectTableColumnEnum.PRIORITY: ClashPriorityColumn(table_delegate=self),
            ClashDetectTableColumnEnum.PIC: PersonInChargeColumn(table_delegate=self),
            ClashDetectTableColumnEnum.CREATION_TIMESTAMP: TableColumnDef("First Detected", ui.Alignment.LEFT, 140, 60, tooltip="First time the clash was detected"),
            ClashDetectTableColumnEnum.LAST_MODIFIED_TIMESTAMP: LastModifiedColumn(),
            ClashDetectTableColumnEnum.COMMENT: CommentColumn(table_delegate=self),
        }

    def build_branch(self, model, item: ClashDetectTableRowItem, column_id, level, expanded):
        """Create a branch widget that opens or closes the subtree.

        Args:
            model: The data model.
            item (ClashDetectTableRowItem): The table row item.
            column_id: The column index.
            level: The tree level.
            expanded: Whether the branch is expanded.
        """
        pass