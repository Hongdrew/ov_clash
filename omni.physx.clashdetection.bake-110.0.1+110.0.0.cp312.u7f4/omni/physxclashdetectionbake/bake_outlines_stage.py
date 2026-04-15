# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import numpy as np
import numpy.typing as npt
from pxr import Vt, UsdGeom, Kind, Usd, Sdf, Gf
import math


class ClashOutlinesStage:
    """Create an UsdGeom.BasisCurve out of the given sequence 3D points representing an outline."""

    def __init__(self, curve: UsdGeom.BasisCurves):
        """Init ClashOutlinesStage
        Args:
        - curve (UsdGeom.BasisCurves)   : A pre-existing curve that will be filled with the given collision outline data
        """
        self._curve = curve
        self._curve.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
        self._curve.CreateBasisAttr().Set("bspline")
        self._curve.CreateTypeAttr().Set("linear")
        self._curve.CreateWrapAttr().Set("nonperiodic")
        Usd.ModelAPI(self._curve).SetKind(Kind.Tokens.component)
        curve_xformable = UsdGeom.Xformable(self._curve)
        self._translate_op = curve_xformable.ClearXformOpOrder()
        self._translate_op: UsdGeom.XformOp = curve_xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)

    def build(
        self,
        outline: npt.NDArray,
        timecode=Usd.TimeCode.Default(),
        outline_width_size: float = 0.5,
        outline_width_scale: float = 1.0,
    ) -> bool:
        """Create an UsdGeom.BasisCurve out of the given sequence 3D points representing an outline.

        Args:
        - curve (UsdGeom.BasisCurves)   : A curve that will be filled with the given collision outline data
        - outline (np.array)            : List of floats that will be interpreted as 3d vectors defining the collision outline
        - outline_width_size (float)    : Size of the outline in world space units
        - outline_width_scale (float)   : Scale factor for the outline width
        """
        num_outlines = len(outline)
        if num_outlines < 2:
            return False
        num_points = num_outlines // 3
        num_segments = num_points // 2
        counts = Vt.IntArray(num_segments, 2)

        # Reshape the outline data into a NumPy array
        points = np.array(outline).reshape(num_points, 3)

        # Find the extents using a more numerically stable approach
        min_coords = np.min(points, axis=0)
        max_coords = np.max(points, axis=0)
        extent = np.array([min_coords, max_coords])

        outline_width = outline_width_scale * outline_width_size

        # Center the outline origin in the center of their extents using a more stable approach
        # Instead of adding min and max and dividing by 2, we compute the center as min + (max-min)/2
        extent_center = min_coords + (max_coords - min_coords) * 0.5

        # In case of a simple linear segment, extent will be 0 on some directions, so we give it at least some width
        extent_size = max_coords - min_coords
        if math.fabs(extent_size[0]) < 1e-6:
            extent_size[0] = outline_width * 4
        if math.fabs(extent_size[1]) < 1e-6:
            extent_size[1] = outline_width * 4
        if math.fabs(extent_size[2]) < 1e-6:
            extent_size[2] = outline_width * 4

        # Recenter points using a more stable approach
        # Instead of subtracting the center directly, we subtract min and then subtract half the extent
        points = points - min_coords - (max_coords - min_coords) * 0.5

        # Update extent to be centered around origin
        extent = np.array([-extent_size * 0.5, extent_size * 0.5])

        # Enlarge extent by double its size for better focusing
        extent[0] -= extent_size / 2
        extent[1] += extent_size / 2

        # Update the transformation to reflect the changed origin
        extent_float64 = tuple(extent_center.astype(np.float64))  # explicit cast to float64 to avoid precision loss
        self._translate_op.Set(extent_float64, timecode)

        # Fill all attributes from points, extents, widths
        self._curve.CreateCurveVertexCountsAttr().Set(counts, timecode)
        self._curve.CreateExtentAttr().Set(extent, timecode)
        self._curve.CreatePointsAttr().Set(points, timecode)

        widths = np.full(num_points, outline_width, dtype=np.float32)
        self._curve.CreateWidthsAttr().Set(widths, timecode)

        return True
