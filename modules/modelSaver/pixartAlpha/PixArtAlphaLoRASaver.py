
from modules.model.PixArtAlphaModel import PixArtAlphaModel
from modules.modelSaver.mixin.LoRASaverMixin import LoRASaverMixin
from modules.util.convert.convert_lora_util import LoraConversionKeySet
from modules.util.convert.lora.convert_pixart_lora import convert_pixart_lora_key_sets
from modules.util.enum.ModelFormat import ModelFormat

import torch
from torch import Tensor


class PixArtAlphaLoRASaver(
    LoRASaverMixin,
):
    def __init__(self):
        super().__init__()

    def _get_convert_key_sets(self, model: PixArtAlphaModel) -> list[LoraConversionKeySet] | None:
        return convert_pixart_lora_key_sets()

    def _get_state_dict(
            self,
            model: PixArtAlphaModel,
    ) -> dict[str, Tensor]:
        state_dict = {}
        if model.text_encoder_lora is not None:
            state_dict |= model.text_encoder_lora.state_dict()
        if model.transformer_lora is not None:
            state_dict |= model.transformer_lora.state_dict()
        if model.lora_state_dict is not None:
            state_dict |= model.lora_state_dict

        if model.additional_embeddings and model.train_config.bundle_additional_embeddings:
            for embedding in model.additional_embeddings:
                placeholder = embedding.text_encoder_embedding.placeholder

                if embedding.text_encoder_embedding.vector is not None:
                    state_dict[f"bundle_emb.{placeholder}.t5"] = embedding.text_encoder_embedding.vector
                if embedding.text_encoder_embedding.output_vector is not None:
                    state_dict[f"bundle_emb.{placeholder}.t5_out"] = embedding.text_encoder_embedding.output_vector

        return state_dict

    def save(
            self,
            model: PixArtAlphaModel,
            output_model_format: ModelFormat,
            output_model_destination: str,
            dtype: torch.dtype | None,
    ):
        self._save(model, output_model_format, output_model_destination, dtype)
