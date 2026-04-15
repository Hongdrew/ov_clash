# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
class ClashMaterialsPaths:
    """Holds paths to materials used for clash meshes generation.

    Attributes:

    - do_clash_solid_materials (tuple[str, str]): Path of solid material for clash mesh
    - no_clash_solid_materials (tuple[str, str]): Path of solid material for non-clashing mesh
    - do_clash_wireframe_materials (tuple[str, str]): Path of material for clash mesh wireframe
    - outlines_material (tuple[str, str]): Path of solid material for outline
    - clash_solid_per_face_materials (tuple[str, str]): Path of material for clash mesh solid
    - clash_wireframe_per_face_materials (tuple[str, str]): Path of material for clash mesh wireframe
    - all_wireframe_per_face_materials (tuple[str, str]): Path of material for all meshes wireframe
    """

    outlines_material: str = ""
    invisible_material: str = ""

    do_clash_solid_materials: tuple[str, str] = ("", "")
    no_clash_solid_materials: tuple[str, str] = ("", "")
    do_clash_wireframe_materials: tuple[str, str] = ("", "")

    clash_solid_per_face_materials: tuple[str, str] = ("", "")
    clash_wireframe_per_face_materials: tuple[str, str] = ("", "")
    all_wireframe_per_face_materials: tuple[str, str] = ("", "")

    def fill_clash_materials(self, stage: Usd.Stage, materials_root: str):
        self.outlines_material = ClashMaterials.create_solid_emissive_outline_material(stage, materials_root)
        self.do_clash_solid_materials = ClashMaterials.create_solid_emissive_two_sided_materials(
            stage,
            materials_root,
            "ObjectEmissiveTwoSided",
            color1=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
            color0=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
        )
        self.no_clash_solid_materials = ClashMaterials.create_solid_diffuse_materials(
            stage, materials_root, "ObjectSolid"
        )
        self.do_clash_wireframe_materials = ClashMaterials.create_wireframe_materials(
            stage, materials_root, "ObjectWireframe"
        )
        self.invisible_material = ClashMaterials.create_invisible_material(stage, materials_root, "Invisible")

        # Display opacity based materials
        dual_material0 = ClashMaterials.create_emissive_two_colors_material(
            stage,
            materials_root,
            "ObjectPerFaceSolid0",
            color0=Gf.Vec3f(0.051, 0.467, 0.706),  # Blue for diffuse (displayOpacity < 0.5)
            color1=Gf.Vec3f(1, 0.478, 0),  # Orange for emissive (displayOpacity >= 0.5)
        )

        dual_material1 = ClashMaterials.create_emissive_two_colors_material(
            stage,
            materials_root,
            "ObjectPerFaceSolid1",
            color1=Gf.Vec3f(0.051, 0.467, 0.706),  # Blue for diffuse (displayOpacity < 0.5)
            color0=Gf.Vec3f(1, 0.478, 0),  # Orange for emissive (displayOpacity >= 0.5)
        )
        self.clash_solid_per_face_materials = (dual_material0, dual_material1)

        self.do_clash_wireframe_per_face_materials = ClashMaterials.create_wireframe_display_opacity_materials(
            stage, materials_root, "ObjectPerFaceWireframe", threshold=0.5
        )
        self.all_wireframe_per_face_materials = ClashMaterials.create_wireframe_display_opacity_materials(
            stage, materials_root, "ObjectPerFaceWireframeAlways", threshold=2.0
        )


class ClashMaterials:

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
    def create_invisible_material(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
    ):
        material_path = f"{material_root_path}/{base_name}"
        mat_0, shader_0 = ClashMaterials.create_material_from_asset(stage, material_path, "OmniPBR", "OmniPBR.mdl")
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:opacity_constant", Sdf.ValueTypeNames.Float).Set(0)
        return material_path

    @staticmethod
    def create_emissive_two_colors_material(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue for diffuse
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange for emissive
    ) -> str:
        """Creates a material that switches between two colors based on displayOpacity value.

        Args:
            stage: The USD stage to create materials on
            material_root_path: Base path for creating materials
            base_name: Base name for the material
            color0: Color to use for the diffuse material (displayOpacity < 0.5)
            color1: Color to use for the emissive material (displayOpacity >= 0.5)

        Returns:
            The path to the created material
        """
        token = carb.tokens.get_tokens_interface()
        mdl_path = token.resolve("./ClashMaterials.mdl")
        material_path = f"{material_root_path}/{base_name}"

        mat, shader = ClashMaterials.create_material_from_asset(
            stage, material_path, "ClashPerFaceEmissiveTwoColors", mdl_path
        )
        shader_prim: Usd.Prim = shader.GetPrim()

        # Set material parameters
        shader_prim.CreateAttribute("inputs:defaultColor0", Sdf.ValueTypeNames.Color3f).Set(color0)
        shader_prim.CreateAttribute("inputs:defaultColor1", Sdf.ValueTypeNames.Color3f).Set(color1)
        shader_prim.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(10000)
        shader_prim.CreateAttribute("inputs:useDisplayColor", Sdf.ValueTypeNames.Bool).Set(False)

        return material_path

    @staticmethod
    def create_solid_diffuse_materials(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
    ) -> tuple[str, str]:
        """Creates a pair of solid diffuse materials on the given stage, under material_root_path with default clash colors (Blue / Orange)"""

        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )
        mat_0, shader_0 = ClashMaterials.create_material_from_asset(stage, material_paths[0], "OmniPBR", "OmniPBR.mdl")
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:diffuse_tint", Sdf.ValueTypeNames.Color3f).Set(color0)
        mat_1, shader_1 = ClashMaterials.create_material_from_asset(stage, material_paths[1], "OmniPBR", "OmniPBR.mdl")
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        shader_prim_1.CreateAttribute("inputs:diffuse_tint", Sdf.ValueTypeNames.Color3f).Set(color1)
        return material_paths

    @staticmethod
    def create_solid_emissive_two_sided_materials(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
    ) -> tuple[str, str]:
        """Creates a pair of solid two sided emissive materials on the given stage, under material_root_path with default clash colors (Blue / Orange)"""

        token = carb.tokens.get_tokens_interface()
        material_path = token.resolve("./ClashMaterials.mdl")
        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )

        mat_0, shader_0 = ClashMaterials.create_material_from_asset(
            stage, material_paths[0], "emissive_two_sided", material_path
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(color0)
        shader_prim_0.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(color0)
        shader_prim_0.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_0.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(400)

        mat_1, shader_1 = ClashMaterials.create_material_from_asset(
            stage, material_paths[1], "emissive_two_sided", material_path
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        shader_prim_1.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(color1)
        shader_prim_1.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(color1)
        shader_prim_1.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_1.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(400)

        return material_paths

    @staticmethod
    def create_solid_emissive_outline_material(
        stage: Usd.Stage, material_root_path: str, color=Gf.Vec3f(1.0, 0.0, 1.0)
    ) -> str:
        """Creates a single emissive material to be used for outlines on the given stage, under material_root_path of Magenta color"""

        token = carb.tokens.get_tokens_interface()
        # TODO: Figure out how this can be embedded in the USD itself
        material_path = token.resolve("./ClashMaterials.mdl")
        material_paths = f"{material_root_path}/ObjectEmissiveOutlines"

        mat_0, shader_0 = ClashMaterials.create_material_from_asset(
            stage,
            f"{material_root_path}/ObjectEmissiveOutlines",
            "emissive_two_sided",
            material_path,
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:parIntensityTintFront", Sdf.ValueTypeNames.Color3f).Set(color)
        shader_prim_0.CreateAttribute("inputs:parIntensityTintBack", Sdf.ValueTypeNames.Color3f).Set(color)
        shader_prim_0.CreateAttribute("inputs:parIntensityFront", Sdf.ValueTypeNames.Float).Set(10000)
        shader_prim_0.CreateAttribute("inputs:parIntensityBack", Sdf.ValueTypeNames.Float).Set(1000)
        return material_paths

    @staticmethod
    def create_wireframe_materials(
        stage: Usd.Stage, material_root_path: str, base_name: str, color=Gf.Vec3f(0.0, 0.0, 0.0)
    ) -> tuple[str, str]:
        """Creates a pair of simple black diffuse materials for wireframes (now that they're offset in Z)"""
        return ClashMaterials.create_solid_diffuse_materials(
            stage, material_root_path, base_name, color0=color, color1=color
        )

    @staticmethod
    def create_translucent_materials(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
        transparency0=0.1,
        transparency1=0.1,
    ) -> tuple[str, str]:
        """Creates translucent materials allowing to see through them."""

        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )
        mat_0, shader_0 = ClashMaterials.create_material_from_asset(
            stage, material_paths[0], "SimPBR_Translucent", "SimPBR_Translucent.mdl"
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:emissive_color", Sdf.ValueTypeNames.Color3f).Set(color0 * transparency0)
        shader_prim_0.CreateAttribute("inputs:ior_constant", Sdf.ValueTypeNames.Float).Set(1.0)
        shader_prim_0.CreateAttribute("inputs:enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:enable_thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_0.CreateAttribute("inputs:emissive_intensity", Sdf.ValueTypeNames.Float).Set(5000)
        mat_1, shader_1 = ClashMaterials.create_material_from_asset(
            stage, material_paths[1], "SimPBR_Translucent", "SimPBR_Translucent.mdl"
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()

        shader_prim_1.CreateAttribute("inputs:emissive_color", Sdf.ValueTypeNames.Color3f).Set(color1 * transparency1)
        shader_prim_1.CreateAttribute("inputs:ior_constant", Sdf.ValueTypeNames.Float).Set(1.0)
        shader_prim_1.CreateAttribute("inputs:enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_1.CreateAttribute("inputs:enable_thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        shader_prim_1.CreateAttribute("inputs:emissive_intensity", Sdf.ValueTypeNames.Float).Set(5000)
        return material_paths

    @staticmethod
    def create_per_face_solid_diffuse_materials(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
    ) -> tuple[str, str]:
        """Creates a pair of solid diffuse materials on the given stage, under material_root_path with default clash colors (Blue / Orange)"""
        token = carb.tokens.get_tokens_interface()
        mdl_path = token.resolve("./ClashMaterials.mdl")

        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )
        _, shader_0 = ClashMaterials.create_material_from_asset(
            stage, material_paths[0], "ClashPerFaceDiffuse", mdl_path
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color0)
        _, shader_1 = ClashMaterials.create_material_from_asset(
            stage, material_paths[1], "ClashPerFaceDiffuse", mdl_path
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        shader_prim_1.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color1)
        return material_paths

    @staticmethod
    def create_per_face_emissive_material(
        stage: Usd.Stage,
        material_root_path: str,
        base_name: str,
        color0=Gf.Vec3f(0.051, 0.467, 0.706),  # cl("0D77B4")  # Blue
        color1=Gf.Vec3f(1, 0.478, 0),  # cl("#FF7A00")  # Orange
    ) -> tuple[str, str]:
        """Creates a pair of solid two sided emissive materials using per-face displayColor on the given stage"""

        token = carb.tokens.get_tokens_interface()
        mdl_path = token.resolve("./ClashMaterials.mdl")
        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )

        _, shader_0 = ClashMaterials.create_material_from_asset(
            stage, material_paths[0], "ClashPerFaceEmissive", mdl_path
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color0)
        shader_prim_0.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_0.CreateAttribute("inputs:useDisplayColor", Sdf.ValueTypeNames.Bool).Set(False)

        _, shader_1 = ClashMaterials.create_material_from_asset(
            stage, material_paths[1], "ClashPerFaceEmissive", mdl_path
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        shader_prim_1.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color1)
        shader_prim_1.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1600)
        shader_prim_1.CreateAttribute("inputs:useDisplayColor", Sdf.ValueTypeNames.Bool).Set(False)

        return material_paths

    @staticmethod
    def create_wireframe_display_opacity_materials(
        stage: Usd.Stage, material_root_path: str, base_name: str, color=Gf.Vec3f(0.0, 0.0, 0.0), threshold=0.5
    ) -> tuple[str, str]:
        """Creates a pair of black diffuse materials for wireframes that hide faces based on displayOpacity threshold"""
        token = carb.tokens.get_tokens_interface()
        mdl_path = token.resolve("./ClashMaterials.mdl")
        material_paths = (
            f"{material_root_path}/{base_name}0",
            f"{material_root_path}/{base_name}1",
        )
        mat_0, shader_0 = ClashMaterials.create_material_from_asset(
            stage, material_paths[0], "ClashPerFaceDiffuse", mdl_path
        )
        shader_prim_0: Usd.Prim = shader_0.GetPrim()
        shader_prim_0.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color)
        shader_prim_0.CreateAttribute("inputs:useDisplayColor", Sdf.ValueTypeNames.Bool).Set(False)
        shader_prim_0.CreateAttribute("inputs:threshold", Sdf.ValueTypeNames.Float).Set(threshold)

        mat_1, shader_1 = ClashMaterials.create_material_from_asset(
            stage, material_paths[1], "ClashPerFaceDiffuse", mdl_path
        )
        shader_prim_1: Usd.Prim = shader_1.GetPrim()
        shader_prim_1.CreateAttribute("inputs:defaultColor", Sdf.ValueTypeNames.Color3f).Set(color)
        shader_prim_1.CreateAttribute("inputs:useDisplayColor", Sdf.ValueTypeNames.Bool).Set(False)
        shader_prim_1.CreateAttribute("inputs:threshold", Sdf.ValueTypeNames.Float).Set(threshold)
        return material_paths
