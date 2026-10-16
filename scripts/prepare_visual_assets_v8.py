"""Derive green grapes and a posed CC0 glove pair; not a cloth simulation."""
from pathlib import Path
import io
import json
import hashlib
import shutil
import zipfile
from urllib.request import urlopen
import numpy as np
from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[1]
food = ROOT / 'assets/third_party/food_v8'
scene = trimesh.load(food / 'grapes.glb', force='scene')
changed = set()
for name, mesh in scene.geometry.items():
    material = mesh.visual.material
    if 'berry' not in name.lower() or 'pedicel' in name.lower():
        continue
    if id(material) in changed:
        continue
    changed.add(id(material))
    texture = material.baseColorTexture
    if texture is not None:
        # Preserve fine luminance variation; change only berry hue/saturation
        # to match the reference's green bunch. Keep brown stems untouched.
        hsv = np.array(texture.convert('HSV')).copy()
        hsv[...,0] = 62
        hsv[...,1] = np.clip(hsv[...,1].astype(float)*.65, 65, 145).astype('uint8')
        hsv[...,2] = np.clip(hsv[...,2].astype(float)*1.25,0,255).astype('uint8')
        material.baseColorTexture = Image.fromarray(hsv, 'HSV').convert('RGB')
scene.export(food / 'grapes-green.glb')

out = ROOT / 'assets/third_party/gloves_v8'
out.mkdir(parents=True, exist_ok=True)
archive = out / 'gloves01_cc0.zip'
if not archive.is_file():
    source_url = 'https://files2.makehumancommunity.org/asset_packs/gloves01/gloves01_cc0.zip'
    with urlopen(source_url, timeout=60) as response, archive.open('wb') as destination:
        shutil.copyfileobj(response, destination)
with zipfile.ZipFile(archive) as z:
    source_name = 'clothes/toigo_gloves_short/gloves_hand.obj'
    source = z.read(source_name)
    (out/'source.obj').write_bytes(source)
    (out/'source.mhclo').write_bytes(z.read('clothes/toigo_gloves_short/toigo_gloves_short.mhclo'))
mesh = trimesh.load(io.BytesIO(source),file_type='obj',force='mesh',process=False)
parts = sorted(mesh.split(only_watertight=False), key=lambda m: m.centroid[0])
result = trimesh.Scene()
for i, part in enumerate(parts):
    p = part.vertices - part.vertices.mean(axis=0)
    _, _, axes = np.linalg.svd(p, full_matrices=False)
    q = p @ axes.T
    q -= (q.min(axis=0)+q.max(axis=0))/2
    q /= np.ptp(q,axis=0)
    # Local Z-up: width X, finger/cuff length Y, thin glove thickness Z.
    x = q[:,1]*.065 + (-.038 if i==0 else .038)
    y = q[:,0]*.12
    z = q[:,2]*.018 + .014 - np.maximum(-y,0)*.65
    # The rest pose is bent over a lip; this is a static visual adaptation.
    part.vertices = np.column_stack((x,z,-y))  # export Y-up
    part.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        # The source is an untextured clothing mesh. Keep it near-black under
        # the bright inspection lighting; 32/255 rendered as a conspicuous gray.
        baseColorFactor=[9,8,7,255], metallicFactor=0., roughnessFactor=.92))
    result.add_geometry(part, geom_name=f'glove_{i}')
result.export(out/'glove-pair-draped.glb')
(out/'provenance.json').write_text(json.dumps({
    'source':'https://static.makehumancommunity.org/assets/assetpacks/gloves01.html',
    'download':'https://files2.makehumancommunity.org/asset_packs/gloves01/gloves01_cc0.zip',
    'author':'MargaretToigo / MRT', 'license':'CC0',
    'source_obj_sha256':hashlib.sha256(source).hexdigest(),
    'modifications':'PCA alignment, tabletop scaling, paired placement, bent rest pose, near-black matte material',
    'cloth_physics':False,'bounds_y_up_m':result.bounds.tolist(),
},indent=2)+'\n')
print('green berry materials:',len(changed),'glove meshes:',len(parts))
