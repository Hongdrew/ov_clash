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


class ClashOutlinesLayer:
    """Create a BasisCurve using the low-level Sdf API out of the given sequence 3D points representing an outline."""

    def __init__(self, layer: Sdf.Layer, prim_path: Sdf.Path):
        """Init ClashOutlinesSdf
        Args:
        - layer (Sdf.Layer)      : The layer to create the curve in
        - prim_path (Sdf.Path)   : The path where the curve prim will be created
        """
        self._layer = layer
        self._prim_path = prim_path

        # Create or get the prim spec
        self._prim_spec: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, prim_path)
        self._prim_spec.specifier = Sdf.SpecifierDef  # type: ignore
        self._prim_spec.typeName = "BasisCurves"  # type: ignore
        self._prim_spec.kind = Kind.Tokens.component  # type: ignore

        # Create the basis curves attributes
        self._create_curve_attributes()
        self._create_xform_attributes()

    def apply_material(self, material_path: str):

        # Create new schema list with MaterialBindingAPI
        schemas = Sdf.TokenListOp.Create(prependedItems=["MaterialBindingAPI"])
        self._prim_spec.SetInfo("apiSchemas", schemas)

        # Create the material binding relationship
        material_bind_rel_spec = Sdf.RelationshipSpec(self._prim_spec, "material:binding")
        material_bind_rel_spec.targetPathList.Append(Sdf.Path(material_path))  # type: ignore

    def _create_curve_attributes(self):
        """Create the basic BasisCurves attributes with their default values."""
        # widthsInterpolation
        widths_interp_spec = Sdf.AttributeSpec(self._prim_spec, "widthsInterpolation", Sdf.ValueTypeNames.Token)
        widths_interp_spec.default = UsdGeom.Tokens.vertex  # type: ignore

        # basis
        basis_spec = Sdf.AttributeSpec(self._prim_spec, "basis", Sdf.ValueTypeNames.Token)
        basis_spec.default = "bspline"  # type: ignore

        # type
        type_spec = Sdf.AttributeSpec(self._prim_spec, "type", Sdf.ValueTypeNames.Token)
        type_spec.default = "linear"  # type: ignore

        # wrap
        wrap_spec = Sdf.AttributeSpec(self._prim_spec, "wrap", Sdf.ValueTypeNames.Token)
        wrap_spec.default = "nonperiodic"  # type: ignore

    def _create_xform_attributes(self):
        """Create the xform attributes for transformation."""
        # xformOpOrder
        xform_op_order_spec = Sdf.AttributeSpec(self._prim_spec, "xformOpOrder", Sdf.ValueTypeNames.TokenArray)
        xform_op_order_spec.default = Vt.TokenArray(["xformOp:translate"])  # type: ignore

        # xformOp:translate
        translate_spec = Sdf.AttributeSpec(self._prim_spec, "xformOp:translate", Sdf.ValueTypeNames.Double3)
        translate_spec.default = Gf.Vec3d(0.0, 0.0, 0.0)  # type: ignore

    def build(
        self,
        outline: npt.NDArray,
        timecode=Usd.TimeCode.Default(),
        outline_width_size: float = 0.5,
        outline_width_scale: float = 1.0,
    ):
        """Create a BasisCurve using Sdf API out of the given sequence 3D points representing an outline.

        Args:
        - outline (np.array)            : List of floats that will be interpreted as 3d vectors defining the collision outline
        - timecode (Usd.TimeCode)       : Usd timecode where to write the data
        - outline_width_size (float)    : Size of the outline in world space units
        - outline_width_scale (float)   : Scale factor for the outline width
        """
        # TODO: Remove consecutively duplicated time samples
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

        # Create or get attribute specs for the curve data
        self._create_curve_data_attributes()

        # Convert timecode to frame number for time samples
        time_sample = timecode.GetValue() if not timecode.IsDefault() else Sdf.TimeCode.Default().GetValue()

        # Set the transform translation
        extent_float64 = tuple(extent_center.astype(np.float64))  # explicit cast to float64 to avoid precision loss
        translate_attr_path = Sdf.Path(f"{self._prim_path}.xformOp:translate")
        if timecode.IsDefault():
            translate_spec = self._prim_spec.attributes["xformOp:translate"]  # type: ignore
            translate_spec.default = Gf.Vec3d(*extent_float64)
        else:
            self._layer.SetTimeSample(translate_attr_path, time_sample, Gf.Vec3d(*extent_float64))

        # Set curve vertex counts
        curve_vertex_counts_path = Sdf.Path(f"{self._prim_path}.curveVertexCounts")
        if timecode.IsDefault():
            curve_vertex_counts_spec = self._prim_spec.attributes["curveVertexCounts"]  # type: ignore
            curve_vertex_counts_spec.default = counts
        else:
            self._layer.SetTimeSample(curve_vertex_counts_path, time_sample, counts)

        # Set extent
        extent_path = Sdf.Path(f"{self._prim_path}.extent")
        if timecode.IsDefault():
            extent_spec = self._prim_spec.attributes["extent"]  # type: ignore
            extent_spec.default = Vt.Vec3fArray.FromNumpy(extent)
        else:
            self._layer.SetTimeSample(extent_path, time_sample, Vt.Vec3fArray.FromNumpy(extent))

        # Set points
        points_path = Sdf.Path(f"{self._prim_path}.points")
        points_vt = Vt.Vec3fArray.FromNumpy(points)
        if timecode.IsDefault():
            points_spec = self._prim_spec.attributes["points"]  # type: ignore
            points_spec.default = points_vt
        else:
            self._layer.SetTimeSample(points_path, time_sample, points_vt)

        # Set widths
        widths = np.full(num_points, outline_width, dtype=np.float32)
        widths_path = Sdf.Path(f"{self._prim_path}.widths")
        widths_vt = Vt.FloatArray.FromNumpy(widths)
        if timecode.IsDefault():
            widths_spec = self._prim_spec.attributes["widths"]  # type: ignore
            widths_spec.default = widths_vt
        else:
            self._layer.SetTimeSample(widths_path, time_sample, widths_vt)

    def _create_curve_data_attributes(self):
        """Create the curve data attributes if they don't exist."""
        # curveVertexCounts
        if "curveVertexCounts" not in self._prim_spec.attributes:  # type: ignore
            Sdf.AttributeSpec(self._prim_spec, "curveVertexCounts", Sdf.ValueTypeNames.IntArray)

        # extent
        if "extent" not in self._prim_spec.attributes:  # type: ignore
            Sdf.AttributeSpec(self._prim_spec, "extent", Sdf.ValueTypeNames.Float3Array)

        # points
        if "points" not in self._prim_spec.attributes:  # type: ignore
            Sdf.AttributeSpec(self._prim_spec, "points", Sdf.ValueTypeNames.Point3fArray)

        # widths
        if "widths" not in self._prim_spec.attributes:  # type: ignore
            Sdf.AttributeSpec(self._prim_spec, "widths", Sdf.ValueTypeNames.FloatArray)
