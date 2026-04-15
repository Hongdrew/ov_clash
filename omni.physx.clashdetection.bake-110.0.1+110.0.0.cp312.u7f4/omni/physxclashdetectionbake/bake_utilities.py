# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb.profiler
import time
from pxr import Usd, UsdGeom, Gf, Sdf
from .bake_options import ClashBakeOptions


class ClashBakeUtils:
    @staticmethod
    def get_frame_time_code(time: float, fps):
        """Internal. Utility to convert fps into time code."""

        if fps <= 0:
            fps = 24
        return Usd.TimeCode(round(time * fps))

    @staticmethod
    def get_instance_root(source_prim: Usd.Prim) -> Usd.Prim:
        if not source_prim.IsInstanceProxy():
            raise Exception(f"Prim '{source_prim.GetPath()}' should be instance Proxy")
        # Cannot modify visibility of this prim because it's part of an instancing proxy
        prim = source_prim
        # Let's try to find its instancing root parent
        while prim.IsValid() and prim.IsInstanceProxy():
            prim = prim.GetParent()
        if prim and prim.IsValid() and not prim.IsPseudoRoot():
            return prim
        else:
            raise Exception(f"Failed to find parent prim of instancing proxy at '{source_prim.GetPath()}'")

    @staticmethod
    def get_instance_root_path(src_path: str, stage: Usd.Stage) -> Sdf.Path | None:
        src_prim: Usd.Prim = stage.GetPrimAtPath(src_path)
        if not src_prim:
            return None
        if src_prim.IsInstanceProxy():
            src_root_prim: Usd.Prim = ClashBakeUtils.get_instance_root(src_prim)
        else:
            src_root_prim = src_prim
        return src_root_prim.GetPath()

    @staticmethod
    def set_scope_visibility(scope: UsdGeom.Scope, visible: bool):
        prim = scope.GetPrim()
        if prim.IsInstanceProxy():
            # Cannot modify visibility of this prim because it's part of an instancing proxy
            # Best we can do hide is hiding the parent prim entirely, as we can't hide only some sub children
            parent_prim = ClashBakeUtils.get_instance_root(prim)
        else:
            parent_prim = prim
        parent_scope = UsdGeom.Scope(parent_prim)
        parent_scope.CreateVisibilityAttr("inherited" if visible else "invisible")  # type: ignore

    @staticmethod
    def set_visibility(prim: Usd.Prim, visible: bool):
        if prim.IsInstanceProxy():
            # Cannot modify visibility of this prim because it's part of an instancing proxy
            # Best we can do hide is hiding the parent prim entirely, as we can't hide only some sub children
            parent_prim = ClashBakeUtils.get_instance_root(prim)
        else:
            parent_prim = prim
        imageable = UsdGeom.Imageable(parent_prim)
        imageable.CreateVisibilityAttr("inherited" if visible else "invisible")  # type: ignore

    @staticmethod
    def set_matrix_transform_for_ops(transform_ops: UsdGeom.Xformable, matrix: Gf.Matrix4d, timecode: Usd.TimeCode):
        # TODO: Should we sanitize the transform ?
        transform = Gf.Transform(matrix)  # Decompose the matrix in translate, rotate
        for op in transform_ops:
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                op.Set(transform.GetTranslation(), timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeScale:
                op.Set(transform.GetScale(), timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateXYZ:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateXZY:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateYXZ:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateYZX:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateZYX:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateZXY:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeRotateAxisAngle:
                rotation = transform.GetRotation().Decompose(Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis())
                op.Set(rotation, timecode)
            elif op.GetOpType() == UsdGeom.XformOp.TypeOrient:
                op.Set(transform.GetRotation(), timecode)
            else:
                # TODO: Support more cases for angles decomposition
                raise Exception("Unsupported transform type")

    @staticmethod
    def set_matrix_transform(dest_xformable: UsdGeom.Xformable, matrix: Gf.Matrix4d, timecode: Usd.TimeCode):
        # We Can't really set the matrix directly because animation curves is sending values directly to fabric
        # And we will get all sorts of warning from hydra about missing transform ops.
        # The only option is to decompose the matrix into translate, rotate and scale and set them  individually.
        transform_ops = dest_xformable.GetOrderedXformOps()
        ClashBakeUtils.set_matrix_transform_for_ops(transform_ops, matrix, timecode)

    @staticmethod
    def flattern_as_matrix(
        cache: UsdGeom.XformCache, src_prim: Usd.Prim, dest_xformable: UsdGeom.Xformable, timecode: Usd.TimeCode
    ):
        """Sets a matrix transform op in dest_xformable as a flatterned transformation of src_prim.

        Args:
        - src_prim (Usd.Prim): Source primitive with some applied XForms
        - dest_xformable (UsdGeom.Xformable): Destination primitive that will receive the matrix transformation
        - timecode (Usd.TimeCode): Usd timecode where to write the transformation.
        """
        source_matrix = Gf.Matrix4d(cache.GetLocalToWorldTransform(src_prim))
        ClashBakeUtils.set_matrix_transform_for_ops(dest_xformable, source_matrix, timecode)

    @staticmethod
    def merge_visibility_range(visible: bool, layer: Sdf.Layer, src_path: str, start_time: float, end_time: float):
        """
        Merge the existing visibility using Sdf api for a prim at src_path with new visibility in the start/end range.
        Args:
        - visible (bool): Whether the prim should be visible or invisible
        - layer (Sdf.Layer): The layer to create the reference in
        - src_path (str): The path to the source prim
        - start_time (float): The start time of the visibility range
        - end_time (float): The end time of the visibility range
        """
        prim_spec = layer.GetPrimAtPath(src_path)
        if not prim_spec:
            prim_spec: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, src_path)
            prim_spec.specifier = Sdf.SpecifierOver  # type: ignore
        if "visibility" in prim_spec.attributes:  # type: ignore
            attr_spec: Sdf.AttributeSpec = prim_spec.attributes["visibility"]  # type: ignore
        else:
            attr_spec: Sdf.AttributeSpec = Sdf.AttributeSpec(prim_spec, "visibility", Sdf.ValueTypeNames.Token)
        start_timecode = ClashBakeUtils.get_frame_time_code(start_time, layer.timeCodesPerSecond).GetValue()
        end_timecode = ClashBakeUtils.get_frame_time_code(end_time, layer.timeCodesPerSecond).GetValue()
        reset_value = UsdGeom.Tokens.invisible if visible else UsdGeom.Tokens.inherited
        set_value = UsdGeom.Tokens.inherited if visible else UsdGeom.Tokens.invisible

        if start_timecode == end_timecode:
            attr_spec.default = set_value  # type: ignore
            return

        if start_timecode > 0:
            # Only set the reset value if there is no pre-existing time sample at 0
            found_start_sample, first_sample, _ = layer.GetBracketingTimeSamplesForPath(attr_spec.path, 0)
            if not found_start_sample and first_sample == 0:
                layer.SetTimeSample(attr_spec.path, 0, reset_value)

        # Here we want to "merge" the visibility range with the existing visibility range

        # Get the bracketing time samples for the start and end timecodes
        # Returns: (<Found sample>, <lower closest sample>, <upper closest sample>)
        start_found, start_before, _ = layer.GetBracketingTimeSamplesForPath(attr_spec.path, start_timecode)

        # Only set the "start" value if it's not already set (and remove the hanging sample if it exists)
        if not start_found or start_timecode >= start_before:
            if start_timecode >= start_before and start_before < start_timecode and start_before > 0:
                layer.EraseTimeSample(attr_spec.path, start_before)
            layer.SetTimeSample(attr_spec.path, start_timecode, set_value)

        end_found, _, end_after = layer.GetBracketingTimeSamplesForPath(attr_spec.path, end_timecode)

        # Only set the "end" value if it's not already set (and remove the hanging sample if it exists)
        if not end_found or end_after <= end_timecode:
            if end_after <= end_timecode and end_after > start_timecode:
                layer.EraseTimeSample(attr_spec.path, end_after)
            layer.SetTimeSample(attr_spec.path, end_timecode, reset_value)

    @staticmethod
    def create_reference_to(layer: Sdf.Layer, src_path: str, dst_path: str, typeName):
        """
        Create a reference using Sdf api to a prim at src_path and add it to the prim at dst_path.
        Args:
        - layer (Sdf.Layer): The layer to create the reference in
        - src_path (str): The path to the source prim
        - dst_path (str): The path to the destination prim
        - typeName (str): The type of the destination prim
        """
        ref = Sdf.Reference(primPath=src_path)
        dst_prim_spec: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, dst_path)
        dst_prim_spec.specifier = Sdf.SpecifierDef  # type: ignore
        # TODO: Find a way to extract typename from root_prim_type
        dst_prim_spec.typeName = "Mesh" if typeName == UsdGeom.Mesh else "Xform"  # type: ignore
        dst_prim_spec.referenceList.explicitItems = [ref]  # type: ignore
        dst_prim_spec.instanceable = False  # type: ignore

    @staticmethod
    def set_instanceable_paths(layer: Sdf.Layer, instanceable_paths: list[str]):
        for path in instanceable_paths:
            dst_prim_spec: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, path)
            dst_prim_spec.specifier = Sdf.SpecifierOver  # type: ignore
            dst_prim_spec.instanceable = False  # type: ignore

    @staticmethod
    def remove_prim_spec(layer: Sdf.Layer, prim_spec_path: str):
        """Removes prim spec from layer."""

        prim_spec = layer.GetPrimAtPath(prim_spec_path)
        if not prim_spec:
            return False

        if prim_spec.nameParent:
            name_parent = prim_spec.nameParent
        else:
            name_parent = layer.pseudoRoot

        if not name_parent:
            return False

        name = prim_spec.name
        if name in name_parent.nameChildren:
            del name_parent.nameChildren[name]

        return True


class CodeTimer:
    """Creates profiler zones with a given name"""

    nesting_level = 0

    def __init__(self, name, options: ClashBakeOptions = ClashBakeOptions()):
        self.name = name
        self.options = options

    def __enter__(self):
        self.start_time = time.time()
        self.__class__.nesting_level += 1
        carb.profiler.begin(1, self.name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        if self.options._debug_mode and self.nesting_level <= self.options._debug_max_level:
            elapsed_time = (self.end_time - self.start_time) * 1000  # in milliseconds
            indentation = "  " * (self.__class__.nesting_level - 1)
            execution_string = f"{indentation}Execution time: {elapsed_time:.2f} ms [[{self.name}]]"
            print(execution_string)
        carb.profiler.end(1)
        self.__class__.nesting_level -= 1
