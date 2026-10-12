import gymnasium as gym
from .droid_environment import EnvCfg as DroidEnvCfg
from .appendix_g_environment import AppendixGEnvCfg
from isaaclab.envs import ManagerBasedRLEnv

gym.register(
    id="DROID",
    entry_point=ManagerBasedRLEnv,
    kwargs={
        "env_cfg_entry_point": DroidEnvCfg,
    },
    disable_env_checker=True,
)

gym.register(
    id="APPENDIX_G",
    entry_point=ManagerBasedRLEnv,
    kwargs={"env_cfg_entry_point": AppendixGEnvCfg},
    disable_env_checker=True,
)
