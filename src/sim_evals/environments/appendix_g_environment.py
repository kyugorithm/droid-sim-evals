"""Task-configured Isaac Lab environment for DreamZero Appendix G.

The original DROID environment remains untouched. This environment reuses the
same Franka, cameras, observations, and joint-position action interface, but
loads a generated task/layout USD selected by the evaluation runner.
"""

import os
import math
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.sensors import CameraCfg
from isaaclab.utils import configclass

from .droid_environment import SceneCfg as DROIDSceneCfg
from .droid_environment import EnvCfg as DROIDEnvCfg


DEFAULT_SCENE_DIR = Path(__file__).resolve().parents[3] / "appendix_g_scenes"


@configclass
class AppendixGSceneCfg(DROIDSceneCfg):
    """DROID camera/robot rig with a task-specific scene asset."""

    # A fixed inspection-only view makes the reconstructed tabletop layout
    # directly comparable to Appendix G photos. It is deliberately separate
    # from the two DROID external cameras and is not part of policy observations.
    review_cam = CameraCfg(
        prim_path="{ENV_REGEX_NS}/review_cam",
        height=900,
        width=1280,
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=5.2,
            focus_distance=1.5,
            horizontal_aperture=5.376,
            vertical_aperture=3.8,
        ),
        offset=CameraCfg.OffsetCfg(
            pos=(0.55, -0.85, 0.95),
            rot=(0.9238795, 0.3826834, 0.0, 0.0),
            convention="opengl",
        ),
    )

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

    def add_reference_camera(self, object_names, elevation_degrees=28.0):
        """Inspection-only object-framed camera; never change policy cameras.

        Framing is inferred, not a calibration of the paper camera. The old
        fixed review view is retained to expose changes in scene scale/poses.
        """
        stage = Usd.Stage.Open(self.scene_path)
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        points = []
        authored_names = [p.GetName() for p in stage.GetPrimAtPath("/World").GetChildren()
                          if p.GetAttribute("appendix_g:semantic_name")]
        for name in authored_names or object_names:
            if name == "table":
                continue
            prim = stage.GetPrimAtPath(f"/World/{name}")
            if prim:
                bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
                if not bounds.IsEmpty():
                    points.extend(tuple(bounds.GetCorner(i)) for i in range(8))
        if not points:
            raise ValueError("Cannot frame reference camera: no task object bounds")
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        center = [(a + b) * .5 for a, b in zip(lo, hi)]
        elevation = math.radians(elevation_degrees)
        sin_e, cos_e = math.sin(elevation), math.cos(elevation)
        tan_h, tan_v = 5.376 / (2 * 6.0), 4.032 / (2 * 6.0)
        distance = .35
        for p in points:
            x, y, z = [p[i] - center[i] for i in range(3)]
            depth = y * cos_e - z * sin_e
            vertical = y * sin_e + z * cos_e
            distance = max(distance, 1.18 * abs(x) / tan_h - depth,
                           1.18 * abs(vertical) / tan_v - depth)
        position = (center[0], center[1] - distance * cos_e, center[2] + distance * sin_e)
        half_angle = (math.pi / 2 - elevation) / 2
        rotation = (math.cos(half_angle), math.sin(half_angle), 0., 0.)
        self.scene.reference_cam = CameraCfg(
            prim_path="{ENV_REGEX_NS}/reference_cam", width=1280, height=960,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(focal_length=6.0, horizontal_aperture=5.376,
                                           vertical_aperture=4.032, focus_distance=distance),
            offset=CameraCfg.OffsetCfg(pos=position, rot=rotation, convention="opengl"),
        )
        return {"kind": "inferred_object_framing_not_paper_calibration", "position": position,
                "rotation_wxyz": rotation, "elevation_degrees": elevation_degrees,
                "bounds_min": lo, "bounds_max": hi, "policy_cameras_changed": False}

    def set_task(self, task_id: str, layout_id: int, scene_dir: str | Path | None = None):
        root = Path(scene_dir or os.environ.get("APPENDIX_G_SCENE_DIR", DEFAULT_SCENE_DIR))
        scene_path = root / f"{task_id.lower()}_layout{layout_id}.usd"
        self.scene.dynamic_scene(scene_path)
        self.task_id = task_id
        self.layout_id = layout_id
        self.scene_path = str(scene_path)
        stage = Usd.Stage.Open(str(scene_path))
        enabled = stage.GetPrimAtPath('/World').GetAttribute('appendix_g:cutting_prototype').Get()
        if enabled:
            from isaaclab.managers import EventTermCfg
            from .cutting_physics import cutting_reset, cutting_step
            self.events.cutting_reset = EventTermCfg(func=cutting_reset, mode='reset')
            self.events.cutting_step = EventTermCfg(
                func=cutting_step, mode='interval', interval_range_s=(0.0, 0.0))
        else:
            self.events.cutting_reset = None
            self.events.cutting_step = None
        if task_id == "U02":
            from isaaclab.managers import EventTermCfg
            from .task_physics import fan_reset, fan_step
            self.events.fan_reset = EventTermCfg(func=fan_reset, mode="reset")
            self.events.fan_step = EventTermCfg(
                func=fan_step, mode="interval", interval_range_s=(0.0, 0.0)
            )
        else:
            self.events.fan_reset = None
            self.events.fan_step = None
        if task_id == "U09":
            from isaaclab.managers import EventTermCfg
            from .task_physics import magnet_reset, magnet_step
            self.events.magnet_reset = EventTermCfg(func=magnet_reset, mode="reset")
            self.events.magnet_step = EventTermCfg(
                func=magnet_step, mode="interval", interval_range_s=(0.0, 0.0))
        else:
            self.events.magnet_reset = None
            self.events.magnet_step = None
        if task_id == "U12":
            from isaaclab.managers import EventTermCfg
            from .task_physics import clip_reset, clip_step
            self.events.clip_reset = EventTermCfg(func=clip_reset,mode="reset")
            self.events.clip_step = EventTermCfg(func=clip_step,mode="interval",interval_range_s=(0.0,0.0))
        else:
            self.events.clip_reset = None
            self.events.clip_step = None
        if task_id == "U15":
            from isaaclab.managers import EventTermCfg
            from .task_physics import mustard_reset, mustard_step
            self.events.mustard_reset = EventTermCfg(func=mustard_reset,mode="reset")
            self.events.mustard_step = EventTermCfg(func=mustard_step,mode="interval",interval_range_s=(0.0,0.0))
        else:
            self.events.mustard_reset = None
            self.events.mustard_step = None


def make_scene_path(task_id: str, layout_id: int, scene_dir: str | Path | None = None) -> Path:
    root = Path(scene_dir or os.environ.get("APPENDIX_G_SCENE_DIR", DEFAULT_SCENE_DIR))
    return root / f"{task_id.lower()}_layout{layout_id}.usd"
