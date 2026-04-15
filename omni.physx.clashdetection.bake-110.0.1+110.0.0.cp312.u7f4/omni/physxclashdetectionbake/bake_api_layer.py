# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import carb
import carb.tokens
from pxr import Usd, UsdGeom, Sdf

from .bake_materials import ClashMaterialsPaths
from .bake_options import ClashBakeOptions
from .bake_utilities import CodeTimer
from .bake_globals import ClashInfo
from .bake_info import ClashBakeInfo
from .bake_generator_layer import ClashBakeGeneratorLayer, ClashBakeOptimizeLayer


class ClashBakeLayer:
    """A class to bake clash meshes to a USD layer.
    All methods of this class are ``@staticmethod`` so this class doesn't need to be instantiated.

    The API enables baking a list of :any:`ClashInfo` objects from :any:`Clash_Detection_Core` extension to OpenUSD meshes.

    The general usage workflow is:

    Setup (when a new stage is loaded):
        - :any:`get_support_files_paths` obtains support files that must be copied where the result of clash bake will be
        - Set an edit target where clash materials need to be written
        - :any:`bake_clash_materials` creates materials in the current edit target for a given stage
        - Potentially create an additional layer to contain only the clash meshes
        - Attach the layer containing the material and the clash meshes one as sublayers of current session layer

    Runtime:
        - :any:`prepare_clash_bake_infos` transforms a [:any:`ClashInfo`] (with :any:`clash_frame_info_items` filled) in a :any:`[ClashBakeInfo]`
        - Set an edit target where clash meshes need to be written
        - :any:`bake_clash_meshes` takes a [:any:`ClashBakeInfo`] and a stage + materials and writes the meshes in the stage.
        - Finally :any:`finalize_clash_meshes` will finalize meshes, doing merging and / or keyframe semplifications.

    Note:
        - Use the [:any:`ClashBakeOptions`] to specify different ways to bake the meshes.
    """

    @staticmethod
    def remove_baked_meshes(
        stage: Usd.Stage, layer: Sdf.Layer, paths: list[tuple[str, str]], options: ClashBakeOptions = ClashBakeOptions()
    ) -> list[str]:
        """Removes additional clash prims baked for prims at given paths.

        Args:
            stage (Usd.Stage): The USD Stage.
            layer (Sdf.Layer): The USD Layer containing previous bake results.
            paths (list[tuple[str, str]]): List of tuples containing the paths of the prims to remove.
            options (ClashBakeOptions): Options for the bake.

        Returns:
            list[str]: List of paths of the prims that failed to be removed.
        """
        failed_paths: list[str] = []
        for clash_info in paths:
            if not ClashBakeInfo._remove_baked_meshes(stage, layer, clash_info[0], options):
                failed_paths.append(clash_info[0])
            if not ClashBakeInfo._remove_baked_meshes(stage, layer, clash_info[1], options):
                failed_paths.append(clash_info[1])
        return failed_paths

    @staticmethod
    def prepare_clash_bake_infos(
        stage: Usd.Stage, clash_infos: list[ClashInfo], options: ClashBakeOptions = ClashBakeOptions()
    ) -> list[ClashBakeInfo]:
        """Prepare ClashBakeInfo objects that are needed to bake meshes for a given list of clashes.

        Note: The passed in clash_infos must have their `clash_frame_info_items` filled.

        Args:
           stage (Usd.Stage): The USD Stage.
           clash_infos (list[ClashInfo]): List of ClashInfo objects from omni.physx.clashdetection.core.
           options (ClashBakeOptions): Options for the bake.

        Returns:
           list[ClashBakeInfo]: List of ClashBakeInfo objects that can be used with `bake_clash_meshes`.
        """
        options.validate(layer_mode=True)
        bake_infos = []
        for clash_info in clash_infos:
            bake_info = ClashBakeInfo(clash_info)
            if not bake_info._prepare_bake(stage=stage, first=True, options=options):
                continue
            if not bake_info._prepare_bake(stage=stage, first=False, options=options):
                continue
            bake_infos.append(bake_info)
        return bake_infos

    @staticmethod
    def get_support_files_paths(options: ClashBakeOptions = ClashBakeOptions()):
        """Obtain a list of paths to support files needed by `bake_clash_meshes`.

        For example it contains the path to material file used by the baked meshes materials.
        Copy these files in the target directory where the clash layer is saved.

        Args:
            options (ClashBakeOptions): Options for the bake.

        Returns:
            list[str]: List of file paths to support files needed by `bake_clash_meshes`.

        """
        if options.use_selection_groups:
            return []
        token = carb.tokens.get_tokens_interface()
        material_path = token.resolve("${omni.physx.clashdetection.bake}/assets/ClashMaterials.mdl")
        return [material_path]

    @staticmethod
    def bake_clash_materials(layer: Sdf.Layer, options: ClashBakeOptions = ClashBakeOptions()):
        """Write materials used by `bake_clash_meshes` to current stage.

        Note: Before calling this function you can change the edit layer to save the materials to.

        Args:
            layer (Sdf.Layer): The USD Layer where to bake the clash meshes.
            options (ClashBakeOptions): Options for the bake.
        Returns:
            ClashMaterialsPaths: The materials created (to be passed in to `bake_clash_meshes`)
        """
        materials_root = "/ClashMaterials"
        materials = ClashMaterialsPaths()
        stage: Usd.Stage = Usd.Stage.Open(layer.identifier)
        UsdGeom.Scope.Define(stage, materials_root)
        materials.fill_clash_materials(stage, materials_root)
        del stage
        return materials

    @staticmethod
    def bake_clash_meshes(
        layer: Sdf.Layer,
        bake_infos: list[ClashBakeInfo],
        materials: ClashMaterialsPaths | None,
        options: ClashBakeOptions = ClashBakeOptions(),
    ):
        """Bakes meshes prepared with `prepare_clash_bake_infos` applying the materials created with `bake_clash_materials`.

        Note: Before calling this function you can change the edit layer to save the clash mesh USD overs to.

        Args:
            layer (Sdf.Layer): The USD Layer where to bake the clash meshes.
            bake_infos (list[ClashBakeInfo]): List of ClashBakeInfo objects prepared with `prepare_clash_bake_infos`.
            materials (ClashMaterialsPaths | None): Materials created with `bake_clash_materials`.
            options (ClashBakeOptions): Options for the bake.
        """
        for bi in bake_infos:
            gen = ClashBakeGeneratorLayer(bake_info=bi, layer=layer, materials=materials, options=options)
            with CodeTimer("BAKE", options):
                gen.generate()

    @staticmethod
    def finalize_clash_meshes(
        layer: Sdf.Layer, bake_infos: list[ClashBakeInfo], options: ClashBakeOptions = ClashBakeOptions()
    ):
        """Opmizes and merges multiple clash pairs at paths previously baked with `bake_clash_meshes`

        Args:
            layer (Sdf.Layer): The USD Layer where to bake the clash meshes.
            bake_infos (list[ClashBakeInfo]): List of ClashBakeInfo objects prepared with `prepare_clash_bake_infos`.
            options (ClashBakeOptions): Options for the bake.
        """
        with CodeTimer("FINALIZE", options):
            clash_optimizer = ClashBakeOptimizeLayer(layer=layer, options=options)
            clash_optimizer.optimize(bake_infos)
