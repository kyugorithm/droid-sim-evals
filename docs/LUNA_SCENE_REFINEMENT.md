# Luna 구현 인계: Appendix G 40개 장면 개선

2026-10-14 작성. 상세한 비교 근거와 task별 수정사항은
[시각 검토 문서](SCENE_FIDELITY_REVIEW_2026-10-14.md)에 있다.

## 목표와 현재 상태

논문 사진의 물체 종류·형태·크기·색·배치·회전·상호 관계를 최대한 보존하는 40개 시뮬레이션 장면을 만든다. 사용자가 새 초기 이미지들을 검토한 뒤 실제 DreamZero rollout으로 진행하는 워크플로다.

현재 v6에는 40개 task의 layout 0 이미지만 있다. 40개 승인 완료 또는 80개 layout 검증 완료가 아니다. 현재 dirty worktree에는 기존 작업이 많이 있으므로 보존한다. 이 인계 작성 중에는 모델 변경·새 rollout·새 scene render를 하지 않았다.

## 실행 체크리스트

### A. 기준 이미지와 명세

- [ ] 상세 검토 문서의 40개 행과 실제 원본/렌더를 읽는다.
- [ ] v6를 보존하고 v7용 별도 USD·render 경로를 만든다.
- [ ] task별 객체 inventory, reference frame, 관계·방향·크기비와 confidence를 저장한다.
- [ ] U10 이미지 매핑은 확인된 것으로 갱신한다. U02의 실제 부채, U09의 upright tray, U15의 눕힌 빵, U20의 열린 상자와 옆면 구멍을 반영한다.
- [ ] group README와 YAML의 stale 설명을 실제 코드·참조 사진에 맞게 갱신한다.

### B. 공통 기반

- [ ] task별 reference camera를 추가하고 기존 policy camera 설정과 구분해 저장한다.
- [ ] GLB 등방 스케일 기본값과 의도적 비등방 스케일 예외를 구현한다.
- [ ] source material의 실제 normal/metallic-roughness 등 지원 채널을 변환·검증한다.
- [ ] 투명 cup과 금속/천/종이의 재질을 대표 물체로 확인한다.
- [ ] 현재 조명과 수정 조명의 동일 camera/geometry A/B 이미지를 만든다.
- [ ] 에셋·설정·USD·PNG hash를 연결해 오래된 출력이 섞이지 않게 한다.

### C. 대표 6개

- [ ] S01: 컵·가위·마커의 비율/방향과 컵의 앞쪽 위치.
- [ ] S03: 수납장 구조·열린 서랍·걸친 어두운 장갑.
- [ ] S10: wicker basket/안감·접힌 타월·성긴 분홍 물체.
- [ ] S16: 서로 접하는 포도송이와 크기·밀도.
- [ ] U09: 세워진 금속 tray·지지물·작은 회색 물체와 빨간 cube의 inventory.
- [ ] U13: 사진에 가까운 toaster·실제 bread 외관·plate·삽입 상태.

각 대표 task에 asset 근접 컷, 원본/새 reference camera/policy camera 1×3, 변경 요약을 남긴다. 한 장면의 외관만 좋아졌다는 이유로 모든 재사용 task를 승인 처리하지 않는다.

### D. 전체 확장

- [ ] 공유 에셋을 나머지 task에 적용한다.
- [ ] 40개 각각의 reference camera·위치·각도·중첩/접촉 관계를 조정한다.
- [ ] 특수 기구(U04/U08/U11/U12/U14/U16/U19/U20)의 보이는 구조와 필요한 상호작용을 구현한다.
- [ ] 40개 layout 0 렌더와 task별 변경 전/후 검토표를 만든다.
- [ ] 사용자 검토 결과를 반영한 뒤 layout 1의 이미지와 reset 상태를 검사한다.
- [ ] interaction/evaluator 미구현 task는 명시적으로 pending으로 남긴다.

### E. 완료 전 확인

- [ ] 컵·용기 내부·구멍·drawer opening을 collider가 막지 않는다.
- [ ] policy-free settling과 반복 reset에서 시작 관계가 유지된다.
- [ ] 각 task의 success predicate가 실제 과업을 측정한다.
- [ ] 실제 policy 해상도에서 task 핵심 물체/부품이 식별된다.
- [ ] 갤러리에서 각 task의 최신 이미지·상태·미해결점을 볼 수 있다.
- [ ] 변경사항과 검증 결과를 이 체크리스트 및 TASK_SUITE_PLAN에 반영한다.

## 병렬화

에셋 묶음별 CPU 작업은 병렬 수행할 수 있다. 공통 builder 수정은 통합 작업자 한 명이 담당한다. Isaac 렌더는 task/layout당 새 프로세스를 기본으로 하며, 2-worker 병렬화는 대표 장면으로 자원·출력 안정성을 먼저 검증한다. 단순히 GPU 2개를 사용한다고 렌더 시간이 절반이 된다고 가정하지 않는다.

## 작업 시작 시 전달할 프롬프트

> `docs/SCENE_FIDELITY_REVIEW_2026-10-14.md`와 이 문서를 읽고 체크리스트 순서대로 구현해줘. 원본 사진의 실루엣·상대 크기·배치·회전·중첩/접촉을 기준으로 삼고, 추정한 것은 기록해줘. v6는 보존하고 v7 경로에 출력해줘. 공유 에셋을 먼저 다듬고 대표 6개를 검증한 뒤 나머지 40개로 확장해줘. 각 task는 실제 Isaac 초기 렌더로 비교하고, 원본/새 reference view/policy view를 1×3으로 보여줘. 완료한 항목만 체크하고 미구현 상호작용은 분리해서 남겨줘. 정책 rollout은 새 장면 이미지에 대한 사용자 검토 후 진행해줘.
