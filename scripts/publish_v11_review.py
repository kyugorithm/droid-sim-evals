"""Publish immutable existing-render comparisons; never renders or runs policy."""
from pathlib import Path
import html

root = Path.home() / '.local/share/.private/runs/scene_previews'
out = root / 'corrections_v11'
out.mkdir(exist_ok=True)
notes = {
    'S08': '모자를 서랍 상판 위로 이동하고 상판 충돌 추가. 주의: 중력 검사에서는 모자가 상판 위에 남지만 기울기가 펴짐. 비스듬히 걸쳐진 상태의 물리 재현은 미완료.',
    'S15': '둥근 대체 물체를 기존 CC0 크로아상 에셋으로 교체. 레몬과 겹침을 줄이도록 방향 재조정.',
    'U03': '절반 폭에 압축되던 빵을 가로로 긴 빵으로 수정. 절단 물리는 아직 미구현.',
    'U19': '선반과 환기구를 정면으로 회전. 가려진 노란 블록을 앞에 배치하고 크로아상 교체. 선반 내부 충돌은 아직 미검증.',
}
cards=[]
for task,note in notes.items():
    ref = 'paper_refs' if task.startswith('S') else 'paper_refs_task_mapped'
    old = 'physical_review_u_v10' if task=='U03' else 'assets_quality_v9'
    new = 'fixes_v11b' if task=='S15' else 'fixes_v11'
    paths = [root/ref/f'{task}.png', root/old/task/'layout0/reference_cam.png', root/new/task/'layout0/reference_cam.png']
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    panels = ''.join(f'<div><h3>{label}</h3><a href="../{p.relative_to(root)}"><img src="../{p.relative_to(root)}"></a></div>' for label,p in zip(['논문','수정 전','실제 새 렌더'],paths))
    settle = '<p><a href="../s08_settle_v11b/S08/layout0/reference_cam.png">S08 중력 적용 후 실제 이미지 — 기울기가 펴짐</a> · <a href="../s08_settle_v11b/S08/layout0/physics_settle.json">물체 위치 측정값</a></p>' if task=='S08' else ''
    cards.append(f'<section id="{task}"><h2>{task}</h2><p>{html.escape(note)}</p><main>{panels}</main><a href="../{new}/{task}/layout0/contact_sheet.png">정책 카메라 보기</a>{settle}</section>')
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>실제 수정본 v11</title><style>body{font:16px system-ui;background:#eee;margin:24px}section{background:white;padding:18px;margin:20px 0}main{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}img{width:100%;height:340px;object-fit:contain}h3{font-size:15px}@media(max-width:700px){main{grid-template-columns:1fr}}</style><h1>실제 수정본 — 4개 태스크</h1><p>왼쪽부터 논문 / 이전 렌더 / 새 렌더. 클릭하면 원본 크기. 40개 전체 수정 완료가 아닙니다. 카메라는 논문 보정값이 아닌 추정 구도입니다. DreamZero 추론은 실행하지 않았습니다.</p>'''+''.join(cards)+'</html>'
(out/'index.html').write_text(page)
print(out/'index.html')
