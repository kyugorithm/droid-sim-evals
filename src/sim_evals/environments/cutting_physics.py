"""Experimental fixed-seam cutting. Geometry gate, NOT material fracture.

No force/contact-sensor claim: blade overlap and a continuous downward stroke
gate a real PhysX fixed-joint release. Disabled unless the USD opts in.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class CutGate:
    armed: bool = False
    cut: bool = False
    previous_z: float | None = None
    start_z: float = 0.0
    max_step: float = 0.020

    def update(self, edge_center, edge_direction):
        p = np.asarray(edge_center, dtype=float)
        axis = np.asarray(edge_direction, dtype=float)
        if self.cut:
            return False
        norm = np.linalg.norm(axis)
        valid = (np.isfinite(p).all() and np.isfinite(axis).all()
                 and norm > 1e-8 and abs(p[0]) <= 0.008
                 and abs(p[1]) <= 0.012
                 and abs(axis[1]) / max(norm, 1e-8) >= 0.95)
        if not valid:
            self.armed = False
            self.previous_z = None
            return False
        z = float(p[2])
        if self.previous_z is not None:
            dz = z - self.previous_z
            if abs(dz) > self.max_step or dz > 0.004:
                self.armed = False
        self.previous_z = z
        if not self.armed and 0.024 <= z <= 0.045:
            self.armed = True
            self.start_z = z
        if self.armed and z <= -0.020 and self.start_z - z >= 0.044:
            self.cut = True
            return True
        return False


def rotation(q):
    w, x, y, z = np.asarray(q, dtype=float)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def cutting_reset(env, env_ids=None):
    from pxr import UsdPhysics
    import omni.usd
    if env.num_envs != 1:
        raise RuntimeError('Experimental cutting currently supports one environment only')
    stage = omni.usd.get_context().get_stage()
    joint = UsdPhysics.FixedJoint.Get(stage, '/World/envs/env_0/scene/cut_joint')
    if not joint:
        raise RuntimeError('Opt-in cutting scene has no cut_joint')
    joint.GetJointEnabledAttr().Set(True)
    env._cut_gate = CutGate()
    env._cut_joint = joint
    env._cut_events = []


def cutting_step(env, env_ids=None):
    if not hasattr(env, '_cut_gate'):
        cutting_reset(env)
    knife = env.scene['knife'].data
    bread = env.scene['bread_half_a'].data
    kp = knife.root_pos_w[0].detach().cpu().numpy()
    bp = bread.root_pos_w[0].detach().cpu().numpy()
    kr = rotation(knife.root_quat_w[0].detach().cpu().numpy())
    br = rotation(bread.root_quat_w[0].detach().cpu().numpy())
    # Authored knife blade edge extends along local Y at z=-0.012 m.
    center = br.T @ (kp + kr @ np.array([0., 0., -0.012]) - bp)
    direction = br.T @ kr[:, 1]
    env._cut_last_sample = {'center':center.tolist(),'direction':direction.tolist()}
    if env._cut_gate.update(center, direction):
        env._cut_joint.GetJointEnabledAttr().Set(False)
        env._cut_events.append({'event':'fixed_seam_released',
                                'blade_edge_in_bread_frame_m':center.tolist(),
                                'model':'geometric_stroke_gate_not_force_fracture'})
