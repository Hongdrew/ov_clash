# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from dataclasses import dataclass

import carb
import carb.tokens
from pxr import Gf, Sdf, Usd, UsdShade

__all__ = []


@dataclass
class ClashViewportMaterialPaths:
    """Holds paths to materials used for clash meshes generation.

    Attributes:

    - do_clash_emissive_materials (tuple[str, str]): Path of emissive material for clash mesh
    - no_clash_translucent_materials (tuple[str, str]): Path of translucent material for non-clashing mesh
    - do_clash_wireframe_materials (tuple[str, str]): Path of material for clash mesh wireframe
    - no_clash_wireframe_materials (tuple[str, str]): Path of material for non-clashing mesh wireframe
    - no_clash_diffuse_materials (tuple[str, str]): Path of diffuse material for non-clashing mesh
    - do_clash_diffuse_materials (tuple[str, str]): Path of diffuse material for clash mesh
    - outlines_material (tuple[str, str]): Path of solid material for outline
    - invisible_material (str): Path of invisible material
    """

    do_clash_emissive_materials: tuple[str, str] = ("", "")
    no_clash_translucent_materials: tuple[str, str] = ("", "")
    do_clash_wireframe_materials: tuple[str, str] = ("", "")
    no_clash_wireframe_materials: tuple[str, str] = ("", "")
    no_clash_diffuse_materials: tuple[str, str] = ("", "")
    do_clash_diffuse_materials: tuple[str, str] = ("", "")
    outlines_material = ""
    invisible_material = ""

    def fill_standard_materials(self, stage: Usd.Stage, materials_root: str):
        """Fills the given stage under materials_root with standard selection of clash viewport material"""
        self.do_clash_emissive_materials = ClashViewportMaterials.create_solid_emissive_two_sided_materials(
            stage, materials_root
        )
        self.outlines_material = ClashViewportMaterials.create_solid_emissive_outline_material(stage, materials_root)
        self.no_clash_translucent_materials = ClashViewportMaterials.create_translucent_materials(stage, materials_root)
        self.do_clash_wireframe_materials = ClashViewportMaterials.create_wireframe_materials(stage, materials_root)
        self.no_clash_wireframe_materials = self.do_clash_wireframe_materials
        self.no_clash_diffuse_materials = ClashViewportMaterials.create_solid_diffuse_materials(stage, materials_root)
        self.do_clash_diffuse_materials = (self.no_clash_diffuse_materials[1], self.no_clash_diffuse_materials[0])
        self.invisible_material = ClashViewportMaterials.create_invisible_material(stage, materials_root, "Invisible")


class ClashViewportMaterials:

    @staticmethod
    def create_material_from_asset(
        stage: Usd.Stage,
        material_path: str,
        material_name: str,
        material_file_path: str,
    ) -> tuple[UsdShade.Material, UsdShade.Shader]:
        """Creates a material from a given MDL asset path.

        Args:
        - stage (Usd.Stage): Stage where to create materials
        - material_path (str): Usd path where material should be created
        - material_name (str): Name of sub-identifier used in the MDL shader
        - material_file_path (str): File path where the MDL material script can be located
        """

        material: UsdShade.Material = UsdShade.Material.Define(stage, material_path)
        shader: UsdShade.Shader = UsdShade.Shader.Define(stage, f"{material_path}/Shader")

        shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "out")
        material.CreateVolumeOutput().ConnectToSource(shader.ConnectableAPI(), "out")
        shader.SetSourceAsset(material_file_path, "mdl")
        shader.SetSourceAssetSubIdentifier(material_name)
        shader.GetImplementationSourceAttr().Set(UsdShade.Tokens.sourceAsset)

        return material, shader

    @staticmethod
    def create_solid_diffuse_materials(stage: Usd.Stage, material_root_path: str) -> tuple[str, str]:
        """Creates a pair of solid diffuse materials on the given stage, under material_root_path with default clash colors (Blue / Orange)"""

        material_paths = (
            f"{material_root_path}/ObjectSolid0",
            f"{material_root_path}/ObjectSolid1",
        )
        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[0], "OmniPBR", "OmniPBR.mdl"
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        mat_0.GetPrim().SetMetadata("hide_in_stage_window", True)
        # COLOR_CLASH_A = cl("0D77B4")  # Blue
        shader_prim_0.CreateAttribute("inputs:diffuse_tint", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.051, 0.467, 0.706)
        )
        mat_1, shader_1 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[1], "OmniPBR", "OmniPBR.mdl"
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        mat_1.GetPrim().SetMetadata("hide_in_stage_window", True)
        # COLOR_CLASH_B = cl("#FF7A00")  # Orange
        shader_prim_1.CreateAttribute("inputs:diffuse_tint", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1, 0.478, 0))
        return material_paths

    @staticmethod
    def create_solid_emissive_two_sided_materials(stage: Usd.Stage, material_root_path: str) -> tuple[str, str]:
        """Creates a pair of solid two sided emissive materials on the given stage, under material_root_path with default clash colors (Blue / Orange)"""

        token = carb.tokens.get_tokens_interface()
        material_path = token.resolve("${omni.physx.clashdetection.viewport}/assets/emissive_two_sided.mdl")
        material_paths = (
            f"{material_root_path}/ObjectEmissiveTwoSided0",
            f"{material_root_path}/ObjectEmissiveTwoSided1",
        )

        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[0], "emissive_two_sided", material_path
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        mat_0.GetPrim().SetMetadata("hide_in_stage_window", True)
        # COLOR_CLASH_A = cl("0D77B4")  # Blue
        shader_prim_0.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.051, 0.467, 0.706)
        )
        shader_prim_0.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.051, 0.467, 0.706)
        )
        shader_prim_0.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_0.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(400)

        mat_1, shader_1 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[1], "emissive_two_sided", material_path
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        mat_1.GetPrim().SetMetadata("hide_in_stage_window", True)
        # COLOR_CLASH_B = cl("#FF7A00")  # Orange
        shader_prim_1.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(1, 0.478, 0)
        )
        shader_prim_1.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(1, 0.478, 0)
        )
        shader_prim_1.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_1.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(400)

        return material_paths

    @staticmethod
    def create_solid_emissive_outline_material(stage: Usd.Stage, material_root_path: str) -> str:
        """Creates a single emissive material to be used for outlines on the given stage, under material_root_path of Magenta color"""

        token = carb.tokens.get_tokens_interface()
        material_path = token.resolve("${omni.physx.clashdetection.viewport}/assets/emissive_two_sided.mdl")
        material_paths = f"{material_root_path}/ObjectEmissiveOutlines"

        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage,
            f"{material_root_path}/ObjectEmissiveOutlines",
            "emissive_two_sided",
            material_path,
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        mat_0.GetPrim().SetMetadata("hide_in_stage_window", True)
        shader_prim_0.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(1.0, 0.0, 1.0)
        )
        shader_prim_0.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(1.0, 0.0, 1.0)
        )
        shader_prim_0.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(10000)
        shader_prim_0.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(1000)
        return material_paths

    @staticmethod
    def create_wireframe_materials(stage: Usd.Stage, material_root_path: str) -> tuple[str, str]:
        """Creates a pair of materials to be used as black wireframe materials on meshes with RTX wireframe primvar set"""

        material_paths = (
            f"{material_root_path}/ObjectWireframe",
            f"{material_root_path}/ObjectWireframe",
        )
        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[0], "SimPBR_Translucent", "SimPBR_Translucent.mdl"
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        mat_0.GetPrim().SetMetadata("hide_in_stage_window", True)
        # Setting transmittance instead of emissive otherwise we will be able to see through
        # Setting transmittance_measurement_distance == 0 makes the object opaque by all means
        # Setting enable_thin_walled == true fixes inside faces
        shader_prim_0.CreateAttribute("inputs:transmittance_color", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.0, 0.0, 0.0)
        )
        shader_prim_0.CreateAttribute("inputs:transmittance_measurement_distance", Sdf.ValueTypeNames.Float).Set(0.0)
        shader_prim_0.CreateAttribute("inputs:ior_constant", Sdf.ValueTypeNames.Float).Set(1.0)
        shader_prim_0.CreateAttribute("inputs:enable_thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        return material_paths

    @staticmethod
    def create_translucent_materials(stage: Usd.Stage, material_root_path: str) -> tuple[str, str]:
        """Creates translucent materials allowing to see through them."""

        material_paths = (
            f"{material_root_path}/ObjectTranslucent0",
            f"{material_root_path}/ObjectTranslucent1",
        )
        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[0], "SimPBR_Translucent", "SimPBR_Translucent.mdl"
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        mat_0.GetPrim().SetMetadata("hide_in_stage_window", True)
        transparency0 = 0.1
        shader_prim_0.CreateAttribute("inputs:emissive_color", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.051, 0.467, 0.706) * transparency0
        )
        shader_prim_0.CreateAttribute("inputs:ior_constant", Sdf.ValueTypeNames.Float).Set(1.0)
        shader_prim_0.CreateAttribute("inputs:enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:enable_thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:emissive_intensity", Sdf.ValueTypeNames.Float).Set(5000)
        # Partial Workaround for OMPE-67526
        shader_prim_0.CreateAttribute("inputs:reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.0)

        mat_1, shader_1 = ClashViewportMaterials.create_material_from_asset(
            stage, material_paths[1], "SimPBR_Translucent", "SimPBR_Translucent.mdl"
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        mat_1.GetPrim().SetMetadata("hide_in_stage_window", True)
        transparency1 = 0.1
        shader_prim_1.CreateAttribute("inputs:emissive_color", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(1, 0.478, 0) * transparency1
        )
        shader_prim_1.CreateAttribute("inputs:ior_constant", Sdf.ValueTypeNames.Float).Set(1.0)
        shader_prim_1.CreateAttribute("inputs:enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_1.CreateAttribute("inputs:enable_thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_1.CreateAttribute("inputs:emissive_intensity", Sdf.ValueTypeNames.Float).Set(5000)
        # Partial Workaround for OMPE-67526
        shader_prim_1.CreateAttribute("inputs:reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.0)
        return material_paths

    @staticmethod
    def create_invisible_material(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
    ):
        material_path = f"{material_root_path}/{base_name}"
        mat_0, shader_0 = ClashViewportMaterials.create_material_from_asset(
            stage, material_path, "OmniPBR", "OmniPBR.mdl"
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:opacity_constant", Sdf.ValueTypeNames.Float).Set(0)
        return material_path
