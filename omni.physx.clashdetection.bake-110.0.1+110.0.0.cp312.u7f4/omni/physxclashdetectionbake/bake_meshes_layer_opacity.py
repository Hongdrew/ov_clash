# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pxr import Sdf, Vt, UsdGeom, Gf
import numpy as np
import numpy.typing as npt

from .bake_utilities import ClashBakeUtils
from .bake_options import ClashBakeOptions
from .bake_globals import ClashInfo
from .bake_materials import ClashMaterialsPaths


class ClashBakeMeshesLayerOpacity:
    """
    This class is used to hide the clashing faces of the no-clash mesh.
    It uses the display opacity primvar to hide the clashing faces.
    It also generates the inverse mesh for the do-clash mesh.
    It uses the low-level Sdf API to write the display opacity primvar.
    """

    @staticmethod
    def hide_clashing_faces_opacity(
        layer: Sdf.Layer,
        options: ClashBakeOptions,
        clash_info: ClashInfo,
        number_of_faces: int,
        prim_path: str,
        materials: ClashMaterialsPaths,
        first: bool,
    ):
        # This code was originally using indexed primvars but it was causing issues with references to instanced prims
        # very likely due to a bug in USD itself, so it has been changed to write display opacity directly.
        index = 0 if first else 1
        prim_spec = Sdf.CreatePrimInLayer(layer, prim_path)
        prim_spec.specifier = Sdf.SpecifierDef
        prim_spec.typeName = "Mesh"
        # Applied Schemas
        applied_apis = []

        # Flat shaded look
        if "subdivisionScheme" not in prim_spec.attributes:
            subdivision_scheme_spec = Sdf.AttributeSpec(prim_spec, "subdivisionScheme", Sdf.ValueTypeNames.Token)
        else:
            subdivision_scheme_spec = prim_spec.attributes["subdivisionScheme"]
        subdivision_scheme_spec.default = "bilinear"  # type: ignore

        # Create MaterialBindingAPI schema
        if prim_spec.relationships.get("material:binding") is None:
            applied_apis.append("MaterialBindingAPI")
            # Create material binding relationship
            material_bind_rel_spec = Sdf.RelationshipSpec(prim_spec, "material:binding")
            paths = [Sdf.Path(materials.clash_solid_per_face_materials[index])]
            material_bind_rel_spec.targetPathList.explicitItems = paths  # type: ignore

        if len(applied_apis) > 0:
            schemas = Sdf.TokenListOp.Create(prependedItems=applied_apis)
            prim_spec.SetInfo("apiSchemas", schemas)

        if not clash_info.clash_frame_info_items:
            return
        if not options.generate_clash_polygons:
            return

        tcps = layer.timeCodesPerSecond

        # Create display opacity primvar
        if "primvars:displayOpacity" in prim_spec.attributes:
            display_opacity_spec = prim_spec.attributes["primvars:displayOpacity"]
        else:
            display_opacity_spec = Sdf.AttributeSpec(
                prim_spec, "primvars:displayOpacity", Sdf.ValueTypeNames.FloatArray
            )
            display_opacity_spec.SetInfo("interpolation", UsdGeom.Tokens.uniform)

        collected_opacities: list[tuple[float, npt.NDArray]] = []
        first_timecode = ClashBakeUtils.get_frame_time_code(time=0, fps=tcps)
        last_frame = clash_info.clash_frame_info_items[-1]
        last_timecode = ClashBakeUtils.get_frame_time_code(time=last_frame.timecode + 0.1, fps=tcps)
        first_timecode_written = False
        last_timecode_written = False
        static_clash = len(clash_info.clash_frame_info_items) == 1
        display_opacity_path = Sdf.Path(f"{prim_path}.primvars:displayOpacity")
        existing_samples = layer.ListTimeSamplesForPath(display_opacity_path)

        for cfi in clash_info.clash_frame_info_items:
            timecode = ClashBakeUtils.get_frame_time_code(time=cfi.timecode, fps=tcps)
            faces = cfi.usd_faces_0 if first else cfi.usd_faces_1

            np_usd_faces = faces.numpy()
            if timecode in existing_samples:
                opacities = np.array(layer.QueryTimeSample(display_opacity_path, timecode.GetValue()))
                # Reconstruct np_existing_opacities set by some previous run of this function for other meshes
                # basically np_existing_opacities is an array of indices in opacities where opacities[index] == 0.0
                np_existing_opacities = np.where(opacities == 0.0)[0]
            else:
                np_existing_opacities = np.array([])

            if len(np_existing_opacities):
                np_faces_to_hide = np.unique(np.concatenate((np_usd_faces, np_existing_opacities)))
            else:
                np_faces_to_hide = np_usd_faces

            # Create an array of 1.0s (fully opaque) and set clashing faces to 0.0 (fully transparent)
            np_opacities = np.ones(number_of_faces, dtype=float)
            np_opacities[np_faces_to_hide] = 0.0

            collected_opacities.append((timecode.GetValue(), np_opacities))

        # Write all opacities
        for timecode_value, np_opacities in collected_opacities:
            if timecode_value == first_timecode.GetValue():
                first_timecode_written = True
            if timecode_value == last_timecode.GetValue():
                last_timecode_written = True
            if static_clash:
                display_opacity_spec.default = Vt.FloatArray.FromNumpy(np_opacities)  # type: ignore
            else:
                layer.SetTimeSample(display_opacity_path, timecode_value, Vt.FloatArray.FromNumpy(np_opacities))

        if not static_clash:
            # Write first frame to reset
            if not first_timecode_written:
                layer.SetTimeSample(
                    display_opacity_path,
                    first_timecode.GetValue(),
                    Vt.FloatArray.FromNumpy(np.ones(number_of_faces, dtype=float)),
                )

            # Write last frame to reset
            if not last_timecode_written:
                layer.SetTimeSample(
                    display_opacity_path,
                    last_timecode.GetValue(),
                    Vt.FloatArray.FromNumpy(np.ones(number_of_faces, dtype=float)),
                )

    @staticmethod
    def remove_duplicated_time_samples(layer: Sdf.Layer, prim_path: str):
        """
        Removes duplicated time samples from the display opacity primvar.
        """
        display_opacity_path = Sdf.Path(f"{prim_path}.primvars:displayOpacity")
        existing_samples = layer.ListTimeSamplesForPath(display_opacity_path)
        if len(existing_samples) <= 1:
            return

        time_samples_to_remove = []
        sample_value = layer.QueryTimeSample(display_opacity_path, existing_samples[0])

        for i in range(len(existing_samples) - 1):
            next_sample_value = layer.QueryTimeSample(display_opacity_path, existing_samples[i + 1])
            if sample_value == next_sample_value:
                time_samples_to_remove.append(existing_samples[i + 1])
            sample_value = next_sample_value

        for time_sample in time_samples_to_remove:
            layer.EraseTimeSample(display_opacity_path, time_sample)
