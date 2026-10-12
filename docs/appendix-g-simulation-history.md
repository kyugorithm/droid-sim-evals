# DreamZero Appendix G Task Proxy Simulation

## 목표

DreamZero 논문의 DROID 평가를 Isaac Sim에서 재구성한다.

- Appendix G의 seen 20개 / unseen 20개 task instruction을 이용한 자체 시뮬레이션 비교
- paper protocol의 2 rollouts/task를 참고해 local 위치 variation을 2개 사용
- 이 환경의 결과는 논문 원 수치 재현이 아님 (논문은 exact simulator scene/evaluator를 공개하지 않음)
- DreamZero와 우리 모델을 동일한 초기조건에서 비교
- 동일한 instruction, object 관계, camera view, action interface 사용

## 진행 체크리스트

### 1. 논문 protocol

- [x] Appendix G에서 seen 20개 / unseen 20개 instruction 확인
- [x] Appendix G가 task당 2회 rollout 및 물체 위치 변경을 명시하는 것 확인
- [x] instruction 목록을 manifest에 옮김 (`appendix_g_tasks.yaml`)
- [ ] 논문에서 실제 물체 좌표·에셋·카메라 calibration·DROID task progress 산식 확인 — 공개 부록에는 없음
- [ ] 공식 Appendix G 시뮬레이터 재현 — 논문은 DROID 로봇 평가를 설명하며, TiPToP 공개 sim-evals의 5 scenes / 51 layouts는 별도 DROID policy benchmark

### 2. 에셋 및 라이선스

- [x] YCB 에셋 후보 조사
- [x] Lightwheel SimReady 에셋 후보 조사
- [x] Objaverse 라이선스 조건 확인
- [x] 초기 재현용 proxy 에셋 정책 선정
- [x] DROID Isaac asset bundle 다운로드
- [x] 에셋 출처·라이선스 manifest 초안 작성 (`appendix_g_assets.yaml`)
- [x] S01 가위 visual을 YCB 037 실측 mesh로 교체하고 사진에 맞춰 손잡이만 파란색으로 조정 (cup/marker는 아직 procedural proxy)

### 3. Isaac Sim 환경

- [x] DROID Franka, gripper, 2 external + wrist camera 설정 재사용
- [x] 단순 tabletop 및 procedural object proxy 생성 코드 작성
- [x] S01 proxy cup을 열린 collision proxy로 수정
- [x] USD table/box transform 순서 오류 수정: `.72m` 상판이 `.0576m`로 축소되던 버그
- [x] 테이블 위치·크기를 공개 `sim-evals/assets/scene1.usd` smoke frame에 맞춤 (상판 bounds 약 x=.20~.90m, y=-.48~.52m, z_top=.045m)
- [x] 일반 proxy에는 공개 smoke asset bundle HDRI, S01에는 사진에 맞는 중립 회색 dome 조명 적용
- [x] 사용자가 제공한 Appendix G(a) S01 사진을 참고해 컵·빨간 캡 흰색 마커·파란 손잡이 가위형 물체의 위치/상대 크기와 나무 상판·회색 후면을 반영한 S01 전용 proxy USD 작성
- [x] DreamZero 추론 없이 Isaac 카메라 3장의 PNG/contact sheet를 저장하는 장면 프리뷰 스크립트 구현; 현재 preview는 `assets/previews/S01_candidate_contact_sheet.png`에 보존
- [x] task별 2 layout, 총 80개 proxy USD 생성; deterministic placement preflight에서 상판 이탈/초기 물체 겹침 0건
- [ ] drawer/kitchen/office/assembly를 실제 scene으로 재구성 — 현재는 tabletop proxy라 완료 아님
- [ ] paper의 실제 object locations/camera views 복원 — paper에 수치/calibration이 공개되지 않음
- [ ] 수정 generator로 40 task × 2 local layout scene 생성 및 전부 검증
- [ ] 실제 drawer/oven/toaster/cloth/articulated asset 및 dynamics 교체

### 4. Task evaluator

- [x] S01용 단계별 geometric proxy progress/success 구현 (`move_then_contain`)
- [x] U01 mug에 손잡이 proxy와 local +X orientation evaluator 추가; initial -X에서 target +X로 회전하면 success
- [x] proxy 점수와 각 stage의 원시 수치가 JSON에 남도록 수정
- [x] episode 영상·JSON 로그 저장 runner 구현 (`eval/appendix_g_eval.py`)
- [ ] 논문과 동일한 task progress 산식 복원 — 논문이 DROID 세부 산식을 공개하지 않음
- [ ] 나머지 task별 유효한 geometric/physical evaluator 구현
- [ ] 성공률 및 평균 progress 집계 구현

### 5. 검증 및 평가

- [x] Seen S01 + unseen U01 proxy pilot 각각 450-step 실행, 영상·JSON·물리 오류 재검증 (둘 다 progress=0/success=false; 정책 성능 통과나 논문 수치가 아님)
- [x] DreamZero WebSocket server 기동 및 port 8000 listen 확인
- [x] B300 `sm_103a`용 CUDA 13.1 `ptxas` 연결
- [x] 합성 3-view observation → DreamZero action 응답 검증
- [x] NVIDIA Vulkan/RTX preflight 추가 — Isaac 초기화 전에 호스트 문제를 진단
- [x] B300 Vulkan에서 `VK_KHR_acceleration_structure` / `VK_KHR_ray_tracing_pipeline` 노출 확인
- [x] Isaac DROID smoke scene observation → DreamZero WebSocket inference 연결 및 450-frame MP4 저장
- [x] 기존 장면에서 DreamZero inference 450-step MP4 저장 (초기 scene은 가림; 평가 유효성 입증은 아님)
- [x] 높은 테이블 가장자리 제거 및 1/20-step 렌더 확인
- [x] static table collider가 잘못된 높이에 생성되어 물체가 낙하하던 근본 원인 수정
- [x] transform 수정 scene에서 CPU 중립 자세 450-step 검사 — 물체 높이 유지, PhysX BroadPhase 오류 미검출
- [x] S01 `move_then_contain` proxy stage evaluator 구현
- [x] DROID-aligned S01에서 DreamZero 450-step rollout 및 세 camera의 object visibility 확인 — PhysX 치명 오류 없음
- [x] U01 손잡이 없는 proxy 결함 수정; 손잡이 geometry와 orientation scoring 구현 및 synthetic direction test 통과
- [x] DROID-aligned U01에서 DreamZero 450-step rollout 및 영상 확인 — mug/handle 가시, PhysX 치명 오류 없음
- [x] S11/S16/S17 directional proxy 진행 방향을 table frame 기준으로 수정하고 positive/negative 방향 synthetic check
- [ ] 우리 모델 inference 연결
- [ ] 전체 40개 task scene 검증
- [ ] DreamZero 80 episode 실행
- [ ] 우리 모델 80 episode 실행
- [ ] 동일 초기조건 paired 비교
- [ ] 최종 결과표 및 실패 분석 작성

## 평가 조건과 재현 한계

- Model input views: exterior 1, exterior 2, wrist
- Action: 기존 DROID sim-evals의 8D joint-position target interface (로컬 구현)
- 논문: task마다 2 rollouts, object location을 변경
- 로컬 proxy: 비교 모델이 같은 2개 위치를 사용하도록 고정; 구체적인 두 위치는 우리 구현의 가정
- paper에는 이 DROID 평가를 위한 exact simulator asset, pose, camera calibration, per-task progress formula가 없음
- 따라서 local 결과는 Appendix G의 공식 재현 수치가 아니라 *자체 proxy 시뮬레이션 비교*로 표기
- 추가 randomization은 고정 위치 결과와 분리

## 상태

현재 단계: **B300에서 Vulkan RGB 렌더 + CPU physics를 사용한 이력이 있다. 초기 proxy table은 카메라에서 작업 물체가 보이지 않았으나, USD transform과 공개 DROID smoke scene의 table frame을 수정해 S01과 U01 물체가 세 카메라에 보이도록 했다. DreamZero rollout은 각각 450 step / 30초였고 둘 다 progress=0, success=false였다. 이 이력은 렌더·통신·물리 안정성 및 일부 local proxy evaluator 확인이지 정책 성능 비교가 아니다. 현재 작업본은 TiPToP의 5-scene/51-layout 기반이며, Appendix G prompt를 이용하는 별도의 근사 확장이다. 논문 exact sim 재현은 아니다.**

최신 S01 candidate는 사용자가 제공한 Appendix G(a) 사진에 맞춰 컵을 중앙, 빨간 캡의 흰색 마커를 한쪽, 파란 손잡이 scissors를 반대쪽에 배치했다. scissors는 YCB 037 Google 16k 스캔 메시를 USD에 포함하고, 사진과 다르게 노란색인 손잡이 면만 파란색으로 바꿨다. cup과 marker는 procedural proxy다. USD는 policy-free preview로 Isaac Lab의 DROID 카메라 3개를 렌더했고 해당 미리보기 실행의 DreamZero inference 호출은 0회다. 아직 사용자 시각 승인을 기다리는 candidate이며, 승인 전에는 이 scene으로 DreamZero rollout을 실행하지 않는다. 원본 논문은 scene 좌표·asset·카메라 calibration을 공개하지 않았으므로 여전히 시각적 재구성이다.

### B300 실행 결과 (2026-10-11)

- NVIDIA ICD: 호스트의 `libGLX_nvidia.so.0`; `vkCreateInstance` 검사 통과. 현재 호스트 전용 manifest는 `configs/nvidia_icd.local.json`이며 Git에는 포함하지 않는다.
- `vulkaninfo`: B300 2개 인식, 두 장치 모두 Vulkan ray-tracing pipeline 및 acceleration-structure extension 보고.
- Isaac Sim 5.0 headless app과 RGB camera는 시작·렌더됨. GLFW/GLInterop 및 helper-process fork 경고는 남지만 이 실행에서 종료 원인은 아님.
- PyTorch CUDA physics는 `sm_103` 커널 부재로 실패. `--device cpu`에서는 환경 초기화와 camera rendering 가능.
- NVIDIA 문서는 RT Core가 없는 GPU(A100/H100 등)를 지원하지 않는다고 명시하고 RTX sensor도 ray-tracing 지원 RTX GPU를 요구한다. B300에 대한 Isaac Sim 5.0 공식 인증 여부와 현재 pod driver 조합은 별도 확인이 필요하며, Vulkan extension 노출만으로 공식 지원을 단정하지 않는다.
- 공개 `scene1.usd` 좌표 검사: table bounds x=[0.1986, 0.8986], y=[-0.4779, 0.5221], z_top=0.0451m; smoke Rubik cube center≈(0.360, -0.081, 0.103)m. Appendix G의 좌표라는 뜻은 아니다.
- 정렬된 S01 DreamZero rollout: 450 steps, 30초 H.264, `progress=0.0`, `success=false`, cup 전진량 0.0m, marker-cup 거리≈0.22m. 카메라에서 물체가 보이고 PhysX broad-phase/orthonormalize 오류가 없음을 확인했다.
- S01 영상·결과 JSON은 당시 임시 NVMe에 기록됐다. 해당 scratch 경로를 정리해 현재 파일은 보존되어 있지 않다.
- unseen U01 DreamZero rollout: 450 steps, 30초 H.264, `progress=0.0`, `success=false`; handle orientation stayed at the initial -X. 손잡이 가시성 및 PhysX broad-phase/orthonormalize 오류 미검출을 확인했다.
- U01 영상·결과 JSON도 당시 임시 NVMe에 기록됐으며 현재 파일은 보존되어 있지 않다.
- 당시 40 task × 2 layouts = 80 USD를 생성하고 초기 배치 기하 검사를 통과했다. 생성물은 재생성 가능한 출력이며 현재 checkout에는 포함하지 않는다. 물리·시각·평가까지 80개 모두 검증한 것은 아니다.

## 현재 작업본 상태

앞선 로컬 checkout에서는 S01과 U01을 대상으로 policy-free camera preview 및
450-step DreamZero pilot을 실행한 적이 있다. 두 pilot 모두 task success는
false였고 논문 정량 결과를 재현하지 않았다. 당시 영상/JSON은 보존되지
않았으며, 미리보기 contact sheet만 `assets/previews/`에 남아 있다.

2026-10-12 새 checkout에서는 Appendix G S01 USD authoring과 외부 asset
준비까지 확인했다. 하지만 실제 Vulkan loader를 통한 `vkCreateInstance`가
`VK_ERROR_INCOMPATIBLE_DRIVER`로 실패해 새 카메라 렌더를 진행하지 않았다.
현재 환경 상태와 진단 결과는
[`b300-isaaclab-history.md`](b300-isaaclab-history.md)에 기록했다.

이전 체크아웃에서 40 task × 2 layouts의 USD 80개를 만들고 초기 배치의
기하 검사를 통과시킨 기록은 있지만, 그 장면들은 대부분 tabletop proxy였고
물리 안정성·시각·평가기를 모두 검증한 건 아니다. 이전 문서에 있던
`--task all --layout 2` 예시는 현재 CLI와 맞지 않아 제거했다. 지금은
[`reproduction.md`](reproduction.md)의 S01 단일 scene 절차만 기준으로 삼고,
Vulkan 문제가 해결되고 S01 시각 승인을 받은 뒤 다음 rollout을 진행한다.
