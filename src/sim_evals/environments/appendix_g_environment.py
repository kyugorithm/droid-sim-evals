"""Task-configured Isaac Lab environment for DreamZero Appendix G.

The original DROID environment remains untouched. This environment reuses the
same Franka, cameras, observations, and joint-position action interface, but
loads a generated task/layout USD selected by the evaluation runner.
"""

import os
from pathlib import Path

from pxr import Usd, UsdPhysics

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.utils import configclass

from .droid_environment import SceneCfg as DROIDSceneCfg
from .droid_environment import EnvCfg as DROIDEnvCfg


DEFAULT_SCENE_DIR = Path(__file__).resolve().parents[3] / "appendix_g_scenes"


@configclass
class AppendixGSceneCfg(DROIDSceneCfg):
    """DROID camera/robot rig with a task-specific scene asset."""

    def dynamic_scene(self, scene_path: str | Path):
        scene_path = Path(scene_path).resolve()
        if not scene_path.exists():
            raise FileNotFoundError(
                f"Appendix G scene does not exist: {scene_path}. "
                "Run scripts/build_appendix_g_scenes.py first."
            )

        scene = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/scene",
            spawn=sim_utils.UsdFileCfg(usd_path=str(scene_path)),
        )
        self.scene = scene

        stage = Usd.Stage.Open(str(scene_path))
        world = stage.GetPrimAtPath("/World")
        if not world:
            raise ValueError(f"Appendix G scene has no /World prim: {scene_path}")

        # Register top-level rigid bodies so Isaac Lab exposes their state to
        # evaluators. The USD scene itself owns the visual/physics geometry.
        for child in world.GetChildren():
            if not UsdPhysics.RigidBodyAPI(child):
                continue
            name = child.GetName()
            translate = child.GetAttribute("xformOp:translate").Get()
            orient = child.GetAttribute("xformOp:orient").Get()
            if orient is None:
                rotation = (1.0, 0.0, 0.0, 0.0)
            else:
                rotation = (
                    orient.GetReal(),
                    orient.GetImaginary()[0],
                    orient.GetImaginary()[1],
                    orient.GetImaginary()[2],
                )
            setattr(
                self,
                name,
                RigidObjectCfg(
                    prim_path=f"{{ENV_REGEX_NS}}/scene/{name}",
                    spawn=None,
                    init_state=RigidObjectCfg.InitialStateCfg(
                        pos=translate,
                        rot=rotation,
                    ),
                ),
            )


@configclass
class AppendixGEnvCfg(DROIDEnvCfg):
    scene = AppendixGSceneCfg(num_envs=1, env_spacing=7.0)

    def set_task(self, task_id: str, layout_id: int, scene_dir: str | Path | None = None):
        root = Path(scene_dir or os.environ.get("APPENDIX_G_SCENE_DIR", DEFAULT_SCENE_DIR))
        scene_path = root / f"{task_id.lower()}_layout{layout_id}.usd"
        self.scene.dynamic_scene(scene_path)
        self.task_id = task_id
        self.layout_id = layout_id
        self.scene_path = str(scene_path)


def make_scene_path(task_id: str, layout_id: int, scene_dir: str | Path | None = None) -> Path:
    root = Path(scene_dir or os.environ.get("APPENDIX_G_SCENE_DIR", DEFAULT_SCENE_DIR))
    return root / f"{task_id.lower()}_layout{layout_id}.usd"
