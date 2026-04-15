# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

class ListenerSubscription:
    """
        This is a subscription class that auto-unsubscribes when the subscription references are set to None
    """
    def __init__(self, callback: callable, container: set, name: str):
        if not callable(callback):
            raise ValueError(f'Listener for {name} must be a callable object')
        self.__container = container
        self.__callback = callback
        self.__container.add(self.__callback)
        self.__name = name # this is just to know what system this belongs to in the debugger

    def destroy(self):
        if not self.__container:
            return
        container = self.__container
        callback = self.__callback
        self.__container = None
        self.__callback = None
        try:
            container.remove(callback)
        except KeyError:
            pass

    def __del__(self):
        self.destroy()
