from modules.model.BaseModel import BaseModel
from modules.util import create
from modules.util.config.TrainConfig import TrainConfig, TrainOptimizerConfig
from modules.util.enum.Optimizer import Optimizer
from modules.util.NamedParameterGroup import NamedParameterGroupCollection
from modules.util.torch_util import optimizer_to_device_

import torch


def change_optimizer(train_config: TrainConfig) -> TrainOptimizerConfig:
    optimizer = train_config.optimizer.optimizer

    optimizer_config = TrainOptimizerConfig.default_values()
    optimizer_config.from_dict(OPTIMIZER_DEFAULT_PARAMETERS[optimizer])
    optimizer_config.optimizer = optimizer

    if str(optimizer) in train_config.optimizer_defaults:
        saved_optimizer_config = train_config.optimizer_defaults[str(optimizer)]
        optimizer_config.from_dict(saved_optimizer_config.to_dict())

    return optimizer_config


def load_optimizer_defaults(train_config: TrainConfig) -> TrainOptimizerConfig:
    optimizer = train_config.optimizer.optimizer

    optimizer_config = TrainOptimizerConfig.default_values()
    optimizer_config.from_dict(OPTIMIZER_DEFAULT_PARAMETERS[optimizer])
    optimizer_config.optimizer = optimizer

    if str(optimizer) in train_config.optimizer_defaults:
        train_config.optimizer_defaults.pop(str(optimizer))

    return optimizer_config


def update_optimizer_config(train_config: TrainConfig):
    optimizer = train_config.optimizer.optimizer

    if str(optimizer) in train_config.optimizer_defaults:
        saved_optimizer_config = train_config.optimizer_defaults[str(optimizer)]
        saved_optimizer_config.from_dict(train_config.optimizer.to_dict())
    else:
        optimizer_donfig = TrainOptimizerConfig.default_values()
        optimizer_donfig.from_dict(train_config.optimizer.to_dict())
        train_config.optimizer_defaults[str(optimizer)] = optimizer_donfig


def init_model_parameters(
        model: BaseModel,
        parameters: NamedParameterGroupCollection,
        train_device: torch.device,
):
    model.parameters = parameters

    model.optimizer = create.create_optimizer(parameters, model.optimizer_state_dict, model.train_config)
    if model.optimizer is not None:
        optimizer_to_device_(model.optimizer, train_device)
    model.optimizer_state_dict = None

    model.ema = create.create_ema(parameters.parameters(), model.ema_state_dict, model.train_config)
    model.ema_state_dict = None

    model.param_group_mapping = parameters.unique_name_mapping


# Optimizer Key map with defaults
OPTIMIZER_DEFAULT_PARAMETERS = {
    Optimizer.ADAFACTOR: {
        "eps": 1e-30,
        "eps2": 1e-3,
        "clip_threshold": 1.0,
        "decay_rate": -0.8,
        "beta1": None,
        "weight_decay": 0.0,
        "scale_parameter": False,
        "relative_step": False,
        "warmup_init": False,
        "stochastic_rounding": True,
        "fused_back_pass": False,
    },
    Optimizer.ADAGRAD: {
        "lr_decay": 0,
        "weight_decay": 0,
        "initial_accumulator_value": 0,
        "eps": 1e-10,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
    },
    Optimizer.ADAGRAD_8BIT: {
        "lr_decay": 0,
        "weight_decay": 0,
        "initial_accumulator_value": 0,
        "eps": 1e-10,
        "optim_bits": 8,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
        "fused_back_pass": False,
    },
    Optimizer.ADAM_8BIT: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 0,
        "amsgrad": False,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
        "is_paged": False,
    },
    Optimizer.ADAMW_8BIT: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 1e-2,
        "amsgrad": False,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
        "is_paged": False,
    },
    Optimizer.AdEMAMix_8BIT: {
        "beta1": 0.9,
        "beta2": 0.999,
        "beta3": 0.9999,
        "eps": 1e-8,
        "alpha": 5,
        "weight_decay": 1e-2,
        "min_8bit_size": 4096,
        "is_paged": False,
    },
    Optimizer.AdEMAMix: {
        "beta1": 0.9,
        "beta2": 0.999,
        "beta3": 0.9999,
        "eps": 1e-8,
        "alpha": 5,
        "weight_decay": 1e-2,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "is_paged": False,
    },
    Optimizer.ADOPT: {
        "beta1": 0.9,
        "beta2": 0.9999,
        "weight_decay": 0.0,
        "decoupled_decay": False,
        "fixed_decay": False,
        "cautious": False,
        "eps": 1e-6,
    },
    Optimizer.LAMB: {
        "bias_correction": True,
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 0,
        "amsgrad": False,
        "adam_w_mode": True,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": False,
        "max_unorm": 1.0,
    },
    Optimizer.LAMB_8BIT: {
        "bias_correction": True,
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 0,
        "amsgrad": False,
        "adam_w_mode": True,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": False,
        "max_unorm": 1.0,
    },
    Optimizer.LARS: {
        "momentum": 0,
        "dampening": 0,
        "weight_decay": 0,
        "nesterov": False,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "max_unorm": 0.02,
    },
    Optimizer.LARS_8BIT: {
        "momentum": 0,
        "dampening": 0,
        "weight_decay": 0,
        "nesterov": False,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "max_unorm": 0.02,
    },
    Optimizer.LION_8BIT: {
        "beta1": 0.9,
        "beta2": 0.999,
        "weight_decay": 0,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
        "is_paged": False,
    },
    Optimizer.RMSPROP: {
        "alpha": 0.99,
        "eps": 1e-8,
        "weight_decay": 0,
        "momentum": 0,
        "centered": False,
        "optim_bits": 32,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
    },
    Optimizer.RMSPROP_8BIT: {
        "alpha": 0.99,
        "eps": 1e-8,
        "weight_decay": 0,
        "momentum": 0,
        "centered": False,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
    },
    Optimizer.SGD_8BIT: {
        "momentum": 0,
        "dampening": 0,
        "weight_decay": 0,
        "nesterov": False,
        "min_8bit_size": 4096,
        "percentile_clipping": 100,
        "block_wise": True,
    },
    Optimizer.SCHEDULE_FREE_ADAMW: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 1e-2,
        "r": 0.0,
        "weight_lr_power": 2.0,
        "foreach": False,
    },
    Optimizer.SCHEDULE_FREE_SGD: {
        "momentum": 0,
        "weight_decay": 1e-2,
        "r": 0.0,
        "weight_lr_power": 2.0,
        "foreach": False,
    },
    Optimizer.PRODIGY: {
        "beta1": 0.9,
        "beta2": 0.999,
        "beta3": None,
        "eps": 1e-8,
        "weight_decay": 0,
        "decouple": True,
        "use_bias_correction": False,
        "safeguard_warmup": False,
        "d0": 1e-6,
        "d_coef": 1.0,
        "growth_rate": float('inf'),
        "fsdp_in_use": False,
        "slice_p": 11,
    },
    Optimizer.PRODIGY_PLUS_SCHEDULE_FREE: {
        "beta1": 0.9,
        "beta2": 0.99,
        "beta3": None,
        "weight_decay": 0.0,
        "weight_decay_by_lr": True,
        "use_bias_correction": False,
        "d0": 1e-6,
        "d_coef": 1.0,
        "prodigy_steps": 0,
        "use_speed": False,
        "eps": 1e-8,
        "split_groups": True,
        "split_groups_mean": True,
        "factored": True,
        "factored_fp32": True,
        "fused_back_pass": False,
        "use_stableadamw": True,
        "use_muon_pp": False,
        "use_cautious": False,
        "use_grams": False,
        "use_adopt": False,
        "use_focus": False,
        "stochastic_rounding": True,
    },
    Optimizer.DADAPT_ADA_GRAD: {
        "momentum": 0,
        "log_every": 0,
        "weight_decay": 0.0,
        "eps": 0.0,
        "d0": 1e-6,
        "growth_rate": float('inf'),
    },
    Optimizer.DADAPT_ADAN: {
        "beta1": 0.98,
        "beta2": 0.92,
        "beta3": 0.99,
        "eps": 1e-8,
        "weight_decay": 0.02,
        "no_prox": False,
        "log_every": 0,
        "d0": 1e-6,
        "growth_rate": float('inf'),
    },
    Optimizer.DADAPT_ADAM: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 0,
        "log_every": 0,
        "decouple": False,
        "use_bias_correction": False,
        "d0": 1e-6,
        "growth_rate": float('inf'),
        "fsdp_in_use": False,
    },
    Optimizer.DADAPT_SGD: {
        "momentum": 0.0,
        "weight_decay": 0,
        "log_every": 0,
        "d0": 1e-6,
        "growth_rate": float('inf'),
        "fsdp_in_use": False,
    },
    Optimizer.DADAPT_LION: {
        "beta1": 0.9,
        "beta2": 0.999,
        "weight_decay": 0.0,
        "log_every": 0,
        "d0": 1e-6,
        "fsdp_in_use": False,
    },
    Optimizer.ADAM: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 0,
        "amsgrad": False,
        "foreach": False,
        "maximize": False,
        "capturable": False,
        "differentiable": False,
        "fused": True,
        "stochastic_rounding": False,
        "fused_back_pass": False,
    },
    Optimizer.ADAMW: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-8,
        "weight_decay": 1e-2,
        "amsgrad": False,
        "foreach": False,
        "maximize": False,
        "capturable": False,
        "differentiable": False,
        "fused": True,
        "stochastic_rounding": False,
        "fused_back_pass": False,
    },
    Optimizer.SGD: {
        "momentum": 0,
        "dampening": 0,
        "weight_decay": 0,
        "nesterov": False,
        "foreach": False,
        "maximize": False,
        "differentiable": False,
    },
    Optimizer.LION: {
        "beta1": 0.9,
        "beta2": 0.99,
        "weight_decay": 0.0,
        "use_triton": False,
    },
    Optimizer.CAME: {
        "beta1": 0.9,
        "beta2": 0.999,
        "beta3": 0.9999,
        "eps": 1e-30,
        "eps2": 1e-16,
        "weight_decay": 1e-2,
        "stochastic_rounding": False,
        "use_cautious": False,
        "fused_back_pass": False,
    },
    Optimizer.CAME_8BIT: {
        "beta1": 0.9,
        "beta2": 0.999,
        "beta3": 0.9999,
        "eps": 1e-30,
        "eps2": 1e-16,
        "weight_decay": 1e-2,
        "stochastic_rounding": False,
        "fused_back_pass": False,
        "min_8bit_size": 16384,
        "quant_block_size": 2048
    },
    Optimizer.ADABELIEF: {
        "beta1": 0.9,
        "beta2": 0.999,
        "eps": 1e-16,
        "weight_decay": 0,
        "amsgrad": False,
        "decoupled_decay": True,
        "fixed_decay": False,
        "rectify": True,
        "degenerated_to_sgd": True,
    },
    Optimizer.TIGER: {
        "beta1": 0.965,
        "weight_decay": 0.01,
        "decoupled_decay": True,
        "fixed_decay": False,
    },
    Optimizer.AIDA: {
        "beta1": 0.9,
        "beta2": 0.999,
        "k": 2,
        "xi": 1e-20,
        "weight_decay": 0.0,
        "decoupled_decay": False,
        "fixed_decay": False,
        "rectify": False,
        "n_sma_threshold": 5,
        "degenerated_to_sgd": True,
        "ams_bound": False,
        "r": 0.95,
        "adanorm": False,
        "adam_debias": False,
        "eps": 1e-8,
    },
    Optimizer.YOGI: {
        "beta1": 0.9,
        "beta2": 0.999,
        "weight_decay": 0.0,
        "decoupled_decay": True,
        "fixed_decay": False,
        "r": 0.95,
        "adanorm": False,
        "adam_debias": False,
        "initial_accumulator": 1e-6,
        "eps": 1e-3,
    },
}
