"""Small task-specific forces and motion helpers for Appendix G scenes."""
import torch
import math


def _step_dt(env):
    value = getattr(env, 'step_dt', None)
    if value is not None:
        return max(float(value), 1e-8)
    cfg = getattr(env, 'cfg', None)
    sim = getattr(cfg, 'sim', None)
    if sim is not None and hasattr(cfg, 'decimation'):
        return max(float(sim.dt) * int(cfg.decimation), 1e-8)
    return 1.0 / 30.0


def fan_reset(env, env_ids=None):
    env._fan_cooling = {
        'initial_temp_c': 55.0,
        'burger_temp_c': 55.0,
        'airflow_time_s': 0.0,
        'alignment': 0.0,
        'distance_m': float('inf'),
    }


def fan_step(env, env_ids=None):
    """Lumped burger-cooling proxy gated by fan distance and front direction.

    The folding panel's authored front is its local +Z axis. This adds a scalar
    food-temperature state; it does not simulate air velocity, pressure, or
    convective flow in space.
    """
    fan = env.scene['folding_fan'].data
    burger = env.scene['burger'].data
    fp = fan.root_pos_w[0]
    bp = burger.root_pos_w[0]
    q = fan.root_quat_w[0]
    w, x, y, z = q.unbind()
    front = torch.stack((2 * (x*z + w*y), 2 * (y*z - w*x), 1 - 2 * (x*x + y*y)))
    delta = bp - fp
    distance = torch.linalg.vector_norm(delta)
    direction = delta / torch.clamp(distance, min=1e-6)
    alignment = torch.clamp(torch.dot(front, direction), min=0.0, max=1.0)
    distance_value = float(distance.item())
    alignment_value = float(alignment.item())
    state = env._fan_cooling
    state['distance_m'] = distance_value
    state['alignment'] = alignment_value
    if distance_value > 0.35 or alignment_value < 0.75:
        return
    dt = _step_dt(env)
    state['airflow_time_s'] += dt
    effectiveness = alignment_value * max(0.0, 1.0 - distance_value / 0.45)
    decay = math.exp(-0.35 * effectiveness * dt)
    ambient_c = 22.0
    state['burger_temp_c'] = ambient_c + (state['burger_temp_c'] - ambient_c) * decay


def _force_buffer(asset):
    device=asset.device
    return (torch.zeros((1,1,3),device=device),torch.zeros((1,1,3),device=device))


def magnet_reset(env, env_ids=None):
    if env.num_envs != 1:
        raise RuntimeError('U09 magnetic proxy currently supports one scene')
    magnet=env.scene['gray_magnet_candidate']
    force,torque=_force_buffer(magnet)
    magnet.set_external_force_and_torque(force,torque,env_ids=[0],is_global=True)
    env._magnet_proxy={'max_force_n':1.5,'range_m':0.22,'active':False}


def magnet_step(env, env_ids=None):
    """Apply a bounded attraction toward the nearest point on the tray shell.

    This is an explicit, approximate magnetic interaction. It is not a field
    solution and does not model material susceptibility or induced currents.
    """
    magnet=env.scene['gray_magnet_candidate']
    tray=env.scene['tray']
    mp=magnet.data.root_pos_w[0]
    tp=tray.data.root_pos_w[0]
    tq=tray.data.root_quat_w[0]
    w,x,y,z=tq.unbind()
    rot=torch.stack((
        torch.stack((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w))),
        torch.stack((2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w))),
        torch.stack((2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y))),
    ))
    local=rot.T@(mp-tp)
    half=torch.tensor([.135,.100,.025],device=mp.device,dtype=mp.dtype)
    closest=torch.maximum(torch.minimum(local,half),-half)
    target=tp+rot@closest
    delta=target-mp
    distance=torch.linalg.vector_norm(delta)
    range_m=float(env._magnet_proxy['range_m'])
    magnitude=1.5*torch.clamp((range_m-distance)/range_m,min=0.0,max=1.0)
    force=(delta/torch.clamp(distance,min=1e-6))*magnitude
    forces=force.reshape(1,1,3)
    torques=torch.zeros_like(forces)
    magnet.set_external_force_and_torque(forces,torques,env_ids=[0],is_global=True)
    env._magnet_proxy['active']=bool(distance.item()<range_m)
    env._magnet_proxy['gap_m']=float(distance.item())


def clip_reset(env, env_ids=None):
    from pxr import UsdPhysics
    import omni.usd
    stage=omni.usd.get_context().get_stage()
    joint=UsdPhysics.FixedJoint.Get(stage,'/World/envs/env_0/scene/clip_paper_release_joint')
    if not joint: raise RuntimeError('U12 scene is missing the paper release joint')
    joint.GetJointEnabledAttr().Set(True)
    env._clip_release_joint=joint
    env._clip_released=False


def clip_step(env, env_ids=None):
    if not hasattr(env,'_clip_release_joint'): clip_reset(env)
    clip=env.scene['binder_clip'].data.root_quat_w[0]
    angles=[]
    for name in ('clip_handle_left','clip_handle_right'):
        q=env.scene[name].data.root_quat_w[0]
        # relative orientation q_clip^-1 * q_handle, Y-axis hinge angle
        cw,cx,cy,cz=clip.unbind(); qw,qx,qy,qz=q.unbind()
        rw=cw*qw+cx*qx+cy*qy+cz*qz
        ry=cw*qy-cx*qz+cy*qw+cz*qx
        angles.append(2.0*torch.atan2(ry,rw))
    env._clip_handle_angles_rad=[float(a.item()) for a in angles]
    if not env._clip_released and all(abs(v)<math.radians(38) for v in env._clip_handle_angles_rad):
        env._clip_release_joint.GetJointEnabledAttr().Set(False)
        env._clip_released=True


def mustard_reset(env, env_ids=None):
    from pxr import UsdPhysics, UsdGeom, Usd
    import omni.usd
    stage=omni.usd.get_context().get_stage()
    env._mustard={'emitted':0,'cooldown':0}
    for i in range(16):
        name=f'mustard_bead_{i:02d}'
        hold=UsdPhysics.FixedJoint.Get(stage,f'/World/envs/env_0/scene/{name}_reset_hold')
        prim=stage.GetPrimAtPath(f'/World/envs/env_0/scene/{name}')
        if not hold or not prim: raise RuntimeError(f'U15 emitter missing bead {name}')
        hold.GetJointEnabledAttr().Set(True)
        UsdGeom.Imageable(prim).VisibilityAttr().Set(UsdGeom.Tokens.invisible)
        child=stage.GetPrimAtPath(f'/World/envs/env_0/scene/{name}/visual')
        UsdPhysics.CollisionAPI(child).CreateCollisionEnabledAttr(False).Set(False)


def mustard_step(env, env_ids=None):
    """Release finite rigid droplets when an inverted nozzle points at bread."""
    if not hasattr(env,'_mustard'): mustard_reset(env)
    env._mustard['cooldown']=max(0,env._mustard['cooldown']-1)
    if env._mustard['emitted']>=16 or env._mustard['cooldown']:
        return
    bottle=env.scene['mustard_bottle'].data
    bread=env.scene['bread'].data.root_pos_w[0]
    p=bottle.root_pos_w[0]; q=bottle.root_quat_w[0]
    w,x,y,z=q.unbind()
    nozzle_axis=torch.stack((2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y)))
    if float(nozzle_axis[2].item())>-.75: return
    nozzle=p+nozzle_axis*.085
    if float(torch.linalg.vector_norm(nozzle[:2]-bread[:2]).item())>.062: return
    index=env._mustard['emitted'];name=f'mustard_bead_{index:02d}'
    bead=env.scene[name]
    from pxr import UsdPhysics, UsdGeom
    import omni.usd
    stage=omni.usd.get_context().get_stage()
    hold=UsdPhysics.FixedJoint.Get(stage,f'/World/envs/env_0/scene/{name}_reset_hold')
    hold.GetJointEnabledAttr().Set(False)
    bead.write_root_pose_to_sim(torch.cat((nozzle.reshape(1,3),torch.tensor([[1.,0.,0.,0.]],device=nozzle.device)),dim=-1))
    bead.write_root_velocity_to_sim(torch.cat((torch.zeros((1,3),device=nozzle.device),torch.tensor([[0.,0.,-.08]],device=nozzle.device)),dim=-1))
    UsdGeom.Imageable(stage.GetPrimAtPath(f'/World/envs/env_0/scene/{name}')).VisibilityAttr().Set(UsdGeom.Tokens.inherited)
    UsdPhysics.CollisionAPI(stage.GetPrimAtPath(f'/World/envs/env_0/scene/{name}/visual')).CreateCollisionEnabledAttr(True).Set(True)
    env._mustard['emitted']+=1;env._mustard['cooldown']=3
