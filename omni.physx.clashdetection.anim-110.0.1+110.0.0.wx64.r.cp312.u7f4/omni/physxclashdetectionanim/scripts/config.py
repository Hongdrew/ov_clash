# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Optional


class ExtensionConfig:
    """A configuration class for setting up extension parameters.

    This class provides options to configure various settings required for
    initializing and running an extension. It includes parameters for enabling
    debug logging and specifying the path to the extension.
    """

    debug_logging: bool = False  # printing of debugging messages into stdout
    extension_path: Optional[str] = None  # will be filled at extension startup
