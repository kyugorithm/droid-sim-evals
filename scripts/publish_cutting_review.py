"""Publish only completed scripted physics probes, with explicit limitations."""
import json
from pathlib import Path
root=Path.home()/'.local/share/.private/runs/scene_previews'
out=root/'cutting_physics_review'
out.mkdir(exist_ok=True)
cards=[]
for kind,label in [('valid','정상 절단 경로'),('miss','절단면을 빗나간 경로')]:
    folder=root/f'cutting_p2_{kind}'/'U03/layout0'
    result=json.loads((folder/'cutting_probe.json').read_text())
    if not result['passed'] or not (folder/'cutting_probe.mp4').is_file():
        raise RuntimeError(f'{kind} not successfully validated')
    url='../'+str(folder.relative_to(root))
    cards.append(f'<section><h2>{label}</h2><p>검사 통과 · 연결 해제: {result["released"]} · 분리 거리: {result["root_separation_m"]*100:.3f} cm</p><video controls preload="metadata" src="{url}/cutting_probe.mp4"></video><p><a href="{url}/cutting_probe.mp4">MP4 직접 열기</a> · <a href="{url}/cutting_probe.json">측정 기록</a></p></section>')
(out/'index.html').write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>U03 절단 물리 실험</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:16px;background:#eee}section{background:white;padding:20px;margin:20px 0}video{width:100%}</style><h1>U03 — 고정 절단면 분리 프로토타입</h1><p>로봇 정책 성공 영상이 아닙니다. 칼은 스크립트로 움직입니다. 칼날-빵 충돌을 필터링하고 기하학적 절단 경로로 연결 해제를 판정하는 근사 모델입니다. 재료의 절단 저항·자유 절단은 구현하지 않았습니다.</p><p>영상 뒤쪽에서는 칼을 치운 뒤 빵 양쪽에 반대 방향 속도를 줘서 실제 연결 해제 여부를 검사합니다. 이는 검사용 자극이지 절단에 의한 힘이 아닙니다. 외형은 별도의 단순 실험용 빵/칼이며 기존 외형 개선 장면을 덮어쓰지 않았습니다.</p>'''+''.join(cards)+'</html>')
print(out/'index.html')
