import re
from collections.abc import Callable

from modules.util import path_util
from modules.util.config.TrainConfig import TrainConfig
from modules.util.enum.DataType import DataType

from mgds.OutputPipelineModule import OutputPipelineModule
from mgds.pipelineModules.AspectBatchSorting import AspectBatchSorting
from mgds.pipelineModules.AspectBucketing import AspectBucketing
from mgds.pipelineModules.CalcAspect import CalcAspect
from mgds.pipelineModules.CapitalizeTags import CapitalizeTags
from mgds.pipelineModules.CollectPaths import CollectPaths
from mgds.pipelineModules.DownloadHuggingfaceDatasets import DownloadHuggingfaceDatasets
from mgds.pipelineModules.DropTags import DropTags
from mgds.pipelineModules.GenerateImageLike import GenerateImageLike
from mgds.pipelineModules.GenerateMaskedConditioningImage import GenerateMaskedConditioningImage
from mgds.pipelineModules.GetFilename import GetFilename
from mgds.pipelineModules.ImageToVideo import ImageToVideo
from mgds.pipelineModules.InlineAspectBatchSorting import InlineAspectBatchSorting
from mgds.pipelineModules.LoadImage import LoadImage
from mgds.pipelineModules.LoadMultipleTexts import LoadMultipleTexts
from mgds.pipelineModules.LoadVideo import LoadVideo
from mgds.pipelineModules.ModifyPath import ModifyPath
from mgds.pipelineModules.RandomBrightness import RandomBrightness
from mgds.pipelineModules.RandomCircularMaskShrink import RandomCircularMaskShrink
from mgds.pipelineModules.RandomContrast import RandomContrast
from mgds.pipelineModules.RandomFlip import RandomFlip
from mgds.pipelineModules.RandomHue import RandomHue
from mgds.pipelineModules.RandomLatentMaskRemove import RandomLatentMaskRemove
from mgds.pipelineModules.RandomMaskRotateCrop import RandomMaskRotateCrop
from mgds.pipelineModules.RandomRotate import RandomRotate
from mgds.pipelineModules.RandomSaturation import RandomSaturation
from mgds.pipelineModules.ScaleCropImage import ScaleCropImage
from mgds.pipelineModules.SelectFirstInput import SelectFirstInput
from mgds.pipelineModules.SelectInput import SelectInput
from mgds.pipelineModules.SelectRandomText import SelectRandomText
from mgds.pipelineModules.ShuffleTags import ShuffleTags
from mgds.pipelineModules.SingleAspectCalculation import SingleAspectCalculation

import torch

from diffusers import AutoencoderKL


class DataLoaderText2ImageMixin:
    def __init__(self):
        pass

    def _enumerate_input_modules(self, config: TrainConfig, allow_videos: bool = False) -> list:
        supported_extensions = set()
        supported_extensions |= path_util.supported_image_extensions()

        if allow_videos:
            supported_extensions |= path_util.supported_video_extensions()

        download_datasets = DownloadHuggingfaceDatasets(
            concept_in_name='concept', path_in_name='path', enabled_in_name='enabled',
            concept_out_name='concept',
        )

        collect_paths = CollectPaths(
            concept_in_name='concept', path_in_name='path', include_subdirectories_in_name='concept.include_subdirectories', enabled_in_name='enabled',
            path_out_name='image_path', concept_out_name='concept',
            extensions=supported_extensions, include_postfix=None, exclude_postfix=['-masklabel','-condlabel']
        )

        mask_path = ModifyPath(in_name='image_path', out_name='mask_path', postfix='-masklabel', extension='.png')
        cond_path = ModifyPath(in_name='image_path', out_name='cond_path', postfix='-condlabel', extension='.png')
        sample_prompt_path = ModifyPath(in_name='image_path', out_name='sample_prompt_path', postfix='', extension='.txt')

        modules = [download_datasets, collect_paths, sample_prompt_path]

        if config.masked_training:
            modules.append(mask_path)
        if config.custom_conditioning_image:
            modules.append(cond_path)

        return modules

    def _load_input_modules(
            self,
            config: TrainConfig,
            train_dtype: DataType,
            allow_video: bool = False,
    ) -> list:
        load_image = LoadImage(path_in_name='image_path', image_out_name='image', range_min=0, range_max=1, supported_extensions=path_util.supported_image_extensions(), dtype=train_dtype.torch_dtype())
        load_video = LoadVideo(path_in_name='image_path', target_frame_count_in_name='settings.target_frames', video_out_name='image', range_min=0, range_max=1, target_frame_rate=24, supported_extensions=path_util.supported_video_extensions(), dtype=train_dtype.torch_dtype())
        image_to_video = ImageToVideo(in_name='image', out_name='image')

        generate_mask = GenerateImageLike(image_in_name='image', image_out_name='mask', color=255, range_min=0, range_max=1)
        load_mask = LoadImage(path_in_name='mask_path', image_out_name='mask', range_min=0, range_max=1, channels=1, supported_extensions={".png"}, dtype=train_dtype.torch_dtype())
        mask_to_video = ImageToVideo(in_name='mask', out_name='mask')

        load_cond_image = LoadImage(path_in_name='cond_path', image_out_name='custom_conditioning_image', range_min=0, range_max=1, supported_extensions=path_util.supported_image_extensions(), dtype=train_dtype.torch_dtype())

        load_sample_prompts = LoadMultipleTexts(path_in_name='sample_prompt_path', texts_out_name='sample_prompts')
        load_concept_prompts = LoadMultipleTexts(path_in_name='concept.text.prompt_path', texts_out_name='concept_prompts')
        filename_prompt = GetFilename(path_in_name='image_path', filename_out_name='filename_prompt', include_extension=False)
        select_prompt_input = SelectInput(setting_name='concept.text.prompt_source', out_name='prompts', setting_to_in_name_map={
            'sample': 'sample_prompts',
            'concept': 'concept_prompts',
            'filename': 'filename_prompt',
        }, default_in_name='sample_prompts')
        select_random_text = SelectRandomText(texts_in_name='prompts', text_out_name='prompt')

        modules = [load_image, load_video]

        if allow_video:
            modules.append(image_to_video)

        modules.extend([load_sample_prompts, load_concept_prompts, filename_prompt, select_prompt_input, select_random_text])

        if config.masked_training:
            modules.append(generate_mask)
            modules.append(load_mask)
        elif config.model_type.has_mask_input():
            modules.append(generate_mask)

        if config.custom_conditioning_image:
            modules.append(load_cond_image)

        if allow_video:
            modules.append(mask_to_video)

        return modules

    def _mask_augmentation_modules(self, config: TrainConfig) -> list:
        inputs = ['image']

        lowest_resolution = min([int(x.strip()) for x in re.split(r'\D', config.resolution) if x.strip() != ''])
        circular_mask_shrink = RandomCircularMaskShrink(mask_name='mask', shrink_probability=1.0, shrink_factor_min=0.2, shrink_factor_max=1.0, enabled_in_name='concept.image.enable_random_circular_mask_shrink')
        random_mask_rotate_crop = RandomMaskRotateCrop(mask_name='mask', additional_names=inputs, min_size=lowest_resolution, min_padding_percent=10, max_padding_percent=30, max_rotate_angle=20, enabled_in_name='concept.image.enable_random_mask_rotate_crop')

        modules = []

        if config.masked_training or config.model_type.has_mask_input():
            modules.append(circular_mask_shrink)

        if config.masked_training or config.model_type.has_mask_input():
            modules.append(random_mask_rotate_crop)

        return modules

    def _aspect_bucketing_in(self, config: TrainConfig, aspect_bucketing_quantization: int, frame_dim_enabled:bool=False):
        calc_aspect = CalcAspect(image_in_name='image', resolution_out_name='original_resolution')

        aspect_bucketing_quantization = AspectBucketing(
            quantization=aspect_bucketing_quantization,
            resolution_in_name='original_resolution',
            target_resolution_in_name='settings.target_resolution',
            enable_target_resolutions_override_in_name='concept.image.enable_resolution_override',
            target_resolutions_override_in_name='concept.image.resolution_override',
            target_frames_in_name='settings.target_frames',
            frame_dim_enabled=frame_dim_enabled,
            scale_resolution_out_name='scale_resolution',
            crop_resolution_out_name='crop_resolution',
            possible_resolutions_out_name='possible_resolutions'
        )

        single_aspect_calculation = SingleAspectCalculation(
            resolution_in_name='original_resolution',
            target_resolution_in_name='settings.target_resolution',
            enable_target_resolutions_override_in_name='concept.image.enable_resolution_override',
            target_resolutions_override_in_name='concept.image.resolution_override',
            scale_resolution_out_name='scale_resolution',
            crop_resolution_out_name='crop_resolution',
            possible_resolutions_out_name='possible_resolutions'
        )

        modules = [calc_aspect]

        if config.aspect_ratio_bucketing:
            modules.append(aspect_bucketing_quantization)
        else:
            modules.append(single_aspect_calculation)

        return modules

    def _crop_modules(self, config: TrainConfig):
        inputs = ['image']

        if config.masked_training or config.model_type.has_mask_input():
            inputs.append('mask')

        if config.model_type.has_depth_input():
            inputs.append('depth')

        if config.custom_conditioning_image:
            inputs.append('custom_conditioning_image')

        scale_crop = ScaleCropImage(names=inputs, scale_resolution_in_name='scale_resolution', crop_resolution_in_name='crop_resolution', enable_crop_jitter_in_name='concept.image.enable_crop_jitter', crop_offset_out_name='crop_offset')

        modules = [scale_crop]

        return modules

    def _augmentation_modules(self, config: TrainConfig):
        inputs = ['image']
        image_inputs = ['image']

        if config.masked_training or config.model_type.has_mask_input():
            inputs.append('mask')

        if config.model_type.has_depth_input():
            inputs.append('depth')

        if config.custom_conditioning_image:
            inputs.append('custom_conditioning_image')
            image_inputs.append('custom_conditioning_image')

        # image augmentations
        random_flip = RandomFlip(names=inputs, enabled_in_name='concept.image.enable_random_flip', fixed_enabled_in_name='concept.image.enable_fixed_flip')
        random_rotate = RandomRotate(names=inputs, enabled_in_name='concept.image.enable_random_rotate', fixed_enabled_in_name='concept.image.enable_fixed_rotate', max_angle_in_name='concept.image.random_rotate_max_angle')
        random_brightness = RandomBrightness(names=image_inputs, enabled_in_name='concept.image.enable_random_brightness', fixed_enabled_in_name='concept.image.enable_fixed_brightness', max_strength_in_name='concept.image.random_brightness_max_strength')
        random_contrast = RandomContrast(names=image_inputs, enabled_in_name='concept.image.enable_random_contrast', fixed_enabled_in_name='concept.image.enable_fixed_contrast', max_strength_in_name='concept.image.random_contrast_max_strength')
        random_saturation = RandomSaturation(names=image_inputs, enabled_in_name='concept.image.enable_random_saturation', fixed_enabled_in_name='concept.image.enable_fixed_saturation', max_strength_in_name='concept.image.random_saturation_max_strength')
        random_hue = RandomHue(names=image_inputs, enabled_in_name='concept.image.enable_random_hue', fixed_enabled_in_name='concept.image.enable_fixed_hue', max_strength_in_name='concept.image.random_hue_max_strength')

        # text augmentations
        drop_tags = DropTags(text_in_name='prompt', enabled_in_name='concept.text.tag_dropout_enable', probability_in_name='concept.text.tag_dropout_probability', dropout_mode_in_name='concept.text.tag_dropout_mode',
                             special_tags_in_name='concept.text.tag_dropout_special_tags', special_tag_mode_in_name='concept.text.tag_dropout_special_tags_mode', delimiter_in_name='concept.text.tag_delimiter',
                             keep_tags_count_in_name='concept.text.keep_tags_count', text_out_name='prompt', regex_enabled_in_name='concept.text.tag_dropout_special_tags_regex')
        caps_randomize = CapitalizeTags(text_in_name='prompt', enabled_in_name='concept.text.caps_randomize_enable', probability_in_name='concept.text.caps_randomize_probability',
                                        capitalize_mode_in_name='concept.text.caps_randomize_mode', delimiter_in_name='concept.text.tag_delimiter', convert_lowercase_in_name='concept.text.caps_randomize_lowercase', text_out_name='prompt')
        shuffle_tags = ShuffleTags(text_in_name='prompt', enabled_in_name='concept.text.enable_tag_shuffling', delimiter_in_name='concept.text.tag_delimiter', keep_tags_count_in_name='concept.text.keep_tags_count', text_out_name='prompt')

        modules = [
            random_flip,
            random_rotate,
            random_brightness,
            random_contrast,
            random_saturation,
            random_hue,
            drop_tags,
            caps_randomize,
            shuffle_tags,
        ]

        return modules

    def _inpainting_modules(self, config: TrainConfig):
        conditioning_image = GenerateMaskedConditioningImage(image_in_name='image', mask_in_name='mask', image_out_name='conditioning_image', image_range_min=0, image_range_max=1)
        select_conditioning_image = SelectFirstInput(in_names=['custom_conditioning_image', 'conditioning_image'], out_name='conditioning_image')

        modules = []

        if config.model_type.has_conditioning_image_input():
            modules.append(conditioning_image)
            modules.append(select_conditioning_image)

        return modules

    def _output_modules_from_out_names(
            self,
            output_names: list[str | tuple[str, str]],
            config: TrainConfig,
            before_cache_image_fun: Callable[[], None] | None = None,
            use_conditioning_image: bool = False,
            vae: AutoencoderKL | None = None,
            autocast_context: list[torch.autocast | None] = None,
            train_dtype: DataType | None = None,
    ):
        sort_names = output_names + ['concept']

        output_names = output_names + [
            ('concept.loss_weight', 'loss_weight'),
            ('concept.type', 'concept_type'),
        ]

        if config.validation:
            output_names.append(('concept.name', 'concept_name'))
            output_names.append(('concept.path', 'concept_path'))
            output_names.append(('concept.seed', 'concept_seed'))

        mask_remove = RandomLatentMaskRemove(
            latent_mask_name='latent_mask', latent_conditioning_image_name='latent_conditioning_image' if use_conditioning_image else None,
            replace_probability=config.unmasked_probability, vae=vae,
            possible_resolutions_in_name='possible_resolutions',
            autocast_contexts=autocast_context, dtype=train_dtype.torch_dtype(),
            before_cache_fun=before_cache_image_fun,
        )

        if config.latent_caching:
            batch_sorting = AspectBatchSorting(resolution_in_name='crop_resolution', names=sort_names, batch_size=config.batch_size)
        else:
            batch_sorting = InlineAspectBatchSorting(resolution_in_name='crop_resolution', names=sort_names, batch_size=config.batch_size)

        output = OutputPipelineModule(names=output_names)

        modules = []

        if config.model_type.has_mask_input():
            modules.append(mask_remove)

        modules.append(batch_sorting)

        modules.append(output)

        return modules
