"""Fetch the original CC0 Poly Haven croissant, keeping its 2K PBR maps."""
from pathlib import Path
import hashlib
import json
import requests

root = Path(__file__).resolve().parents[1] / 'assets/third_party/food_v8/croissant_scan'
root.mkdir(parents=True, exist_ok=True)
response = requests.get('https://api.polyhaven.com/files/croissant', timeout=30)
response.raise_for_status()
entry = response.json()['gltf']['2k']['gltf']
files = {'croissant_2k.gltf': entry} | entry['include']
record = {}
for name, meta in files.items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = requests.get(meta['url'], timeout=60)
    data.raise_for_status()
    if hashlib.md5(data.content).hexdigest() != meta['md5']:
        raise ValueError(f'Hash mismatch: {name}')
    path.write_bytes(data.content)
    record[name] = {'url':meta['url'], 'sha256':hashlib.sha256(data.content).hexdigest()}
(root/'provenance.json').write_text(json.dumps({
    'source':'https://polyhaven.com/a/croissant','license':'CC0-1.0',
    'files':record,'modifications':'None; scene importer changes axes/scale only',
},indent=2)+'\n')
print('Fetched',len(files),'original files with checksum verification')
