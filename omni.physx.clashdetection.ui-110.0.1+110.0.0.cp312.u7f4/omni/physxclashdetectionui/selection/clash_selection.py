# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Sequence, NewType
from .listener_subscription import ListenerSubscription
from omni.physxclashdetectioncore.clash_info import ClashInfo

# Type definitions
QueryId = NewType("QueryId", int)
ListenerCallback = callable
SelectionContainer = tuple[ClashInfo, ...]
ListenersContainer = set[ListenerCallback]


class ClashSelection:
    """Clash Selection class to keep track of current query id and selected clashes
    This class is used to decouple additional systems that need to react to changes of current query
    or to changes in selected clashes.
    """

    def __init__(self):
        """Initializes the ClashSelection instance."""
        self._clash_selection: SelectionContainer = ()  # identifier in Query as an immutable tuple
        self._query_id: QueryId = 0  # Active query id
        self._selection_listeners: ListenersContainer = set()  # Holding the actual listeners
        self._timecode_listeners: ListenersContainer = set()  # Holding the actual listeners
        self._timecode: float = 0.0

    def clear_selection(self):
        """Clears selection. Will broadcast selection update to all listeners."""
        if not len(self._clash_selection):
            return
        self._clash_selection = ()
        for listener in self._selection_listeners:
            listener()

    def set_current_timecode(self, timecode: float):
        """Sets the current timecode and notifies listeners.

        Args:
            timecode (float): The new timecode value.
        """
        self._timecode = timecode
        for listener in self._timecode_listeners:
            listener()

    def update_query_id(self, query_id: QueryId):
        """Changes the query id (and empty selection). Will broadcast selection update to all listeners.

        Args:
            query_id (QueryId): The new query id.
        """
        self._query_id = query_id
        self._clash_selection = ()
        for listener in self._selection_listeners:
            listener()

    @property
    def query_id(self):
        """Gets the current query id.

        Returns:
            QueryId: The current query id.
        """
        return self._query_id

    @property
    def timecode(self):
        """Gets the current timecode.

        Returns:
            float: The current timecode value.
        """
        return self._timecode

    def update_selection(self, timecode: float, new_selection: Sequence[ClashInfo]):
        """Changes the Selection. Will broadcast selection update to all listeners.

        Args:
            timecode (float): The new timecode value.
            new_selection (Sequence[ClashInfo]): The new selection of clashes.
        """
        self._timecode = timecode
        self._clash_selection = tuple(new_selection)
        for listener in self._selection_listeners:
            listener()

    def subscribe_to_selection_changes(self, callback: ListenerCallback):
        """Allows registering a subscription to selection changes.

        Args:
            callback (ListenerCallback): The callback to be invoked on selection changes.
        """
        return ListenerSubscription(callback, self._selection_listeners, "ClashSelection.selection_listeners")

    def subscribe_to_timecode_changes(self, callback: ListenerCallback):
        """Allows registering a subscription to timecode changes.

        Args:
            callback (ListenerCallback): The callback to be invoked on timecode changes.
        """
        return ListenerSubscription(callback, self._timecode_listeners, "ClashSelection._timecode_listeners")

    @property
    def selection(self):
        """Gets the current selection.

        Returns:
            SelectionContainer: The current selection of clashes.
        """
        return self._clash_selection
