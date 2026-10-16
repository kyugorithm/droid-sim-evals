"""Build opt-in U03 pre-segmented physics scene; never overwrites base USD."""
import argparse
import math
from pathlib import Path
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics
from build_appendix_g_scenes import _define_box, _define_mesh


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    src=Usd.Stage.Open(str(a.source.resolve()))
    # Flatten resolves referenced asset paths before writing to a new directory.
    src.Flatten().Export(str(a.output.resolve()))
    stage=Usd.Stage.Open(str(a.output.resolve()))
    center=stage.GetPrimAtPath('/World/bread_half_a').GetAttribute('xformOp:translate').Get()
    center=Gf.Vec3d(center[0],center[1],0.0676)
    for name,side in [('bread_half_a',-1),('bread_half_b',1)]:
        path=f'/World/{name}'
        stage.RemovePrim(path)
        root=UsdGeom.Xform.Define(stage,path)
        root.AddTranslateOp().Set(center)
        root.AddOrientOp().Set(Gf.Quatf(1))
        UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
        UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(.075)
        points=[]; faces=[]; n=32; rings=13
        for j in range(rings):
            t=(j/(rings-1))*(math.pi/2-.02)
            x=side*.12*math.sin(t)
            for i in range(n):
                theta=2*math.pi*i/n
                points.append((x,.0325*math.cos(t)*math.cos(theta),.0225*math.cos(t)*math.sin(theta)))
        for j in range(rings-1):
            for i in range(n):
                k=(i+1)%n
                f=[j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i]
                faces.append(f if side<0 else f[::-1])
        # Double-sided render; convex-hull physics closes both end caps.
        mesh=_define_mesh(stage,path+'/crust',points,[4]*len(faces),sum(faces,[]),(.62,.28,.065))
        UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)
        UsdPhysics.CollisionAPI.Apply(mesh)
        UsdPhysics.MeshCollisionAPI.Apply(mesh).CreateApproximationAttr('convexHull')
        rim=points[:n]
        cap=_define_mesh(stage,path+'/cut_face',[(0,0,0)]+rim,[3]*n,
                         sum(([0,i+1,(i+1)%n+1] for i in range(n)),[]),(.88,.73,.46))
        UsdGeom.Mesh(cap).CreateDoubleSidedAttr(True)
    joint=UsdPhysics.FixedJoint.Define(stage,'/World/cut_joint')
    joint.CreateBody0Rel().SetTargets(['/World/bread_half_a'])
    joint.CreateBody1Rel().SetTargets(['/World/bread_half_b'])
    joint.CreateLocalPos0Attr(Gf.Vec3f(0)); joint.CreateLocalPos1Attr(Gf.Vec3f(0))
    joint.CreateLocalRot0Attr(Gf.Quatf(1)); joint.CreateLocalRot1Attr(Gf.Quatf(1))
    joint.CreateJointEnabledAttr(True)
    joint.CreateCollisionEnabledAttr(False)
    old=stage.GetPrimAtPath('/World/knife')
    pos=old.GetAttribute('xformOp:translate').Get()
    stage.RemovePrim('/World/knife')
    knife=UsdGeom.Xform.Define(stage,'/World/knife')
    knife.AddTranslateOp().Set(pos); knife.AddOrientOp().Set(Gf.Quatf(1))
    UsdPhysics.RigidBodyAPI.Apply(knife.GetPrim())
    UsdPhysics.MassAPI.Apply(knife.GetPrim()).CreateMassAttr(.08)
    # Rigid bread cannot admit a blade. Explicitly filter these contacts in
    # this approximation; the geometric stroke gate replaces cutting contact.
    # This does NOT simulate cutting forces or material resistance.
    UsdPhysics.FilteredPairsAPI.Apply(knife.GetPrim()).CreateFilteredPairsRel().SetTargets(
        ['/World/bread_half_a','/World/bread_half_b'])
    _define_box(stage,'/World/knife/blade',(.003,.11,.024),(0,0,0),(.65,.67,.7),collision=True)
    _define_box(stage,'/World/knife/handle',(.018,.065,.025),(0,-.0875,.002),(.06,.04,.03),collision=True)
    stage.GetPrimAtPath('/World').CreateAttribute('appendix_g:cutting_prototype',Sdf.ValueTypeNames.Bool).Set(True)
    stage.GetRootLayer().Save()
    print(a.output)

if __name__=='__main__':
    main()
