from modules.model.SanaModel import SanaModel
from modules.modelSaver.BaseModelSaver import BaseModelSaver
from modules.modelSaver.mixin.InternalModelSaverMixin import InternalModelSaverMixin
from modules.modelSaver.sana.SanaEmbeddingSaver import SanaEmbeddingSaver
from modules.modelSaver.sana.SanaModelSaver import SanaModelSaver
from modules.util.enum.ModelFormat import ModelFormat
from modules.util.enum.ModelType import ModelType

import torch


class SanaFineTuneModelSaver(
    BaseModelSaver,
    InternalModelSaverMixin,
):
    def __init__(self):
        super().__init__()

    def save(
            self,
            model: SanaModel,
            model_type: ModelType,
            output_model_format: ModelFormat,
            output_model_destination: str,
            dtype: torch.dtype,
    ):
        base_model_saver = SanaModelSaver()
        embedding_model_saver = SanaEmbeddingSaver()

        base_model_saver.save(model, output_model_format, output_model_destination, dtype)
        embedding_model_saver.save_multiple(model, output_model_format, output_model_destination, dtype)

        if output_model_format == ModelFormat.INTERNAL:
            self._save_internal_data(model, output_model_destination)
