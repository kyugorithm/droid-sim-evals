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

현재 단계: **2026-10-12에 B300에서 S01 450-step DreamZero rollout을 완료했다. Vulkan RGB 렌더와 CPU physics가 사용됐고, run은 `progress=0.0`, `success=false`, `approximate=true`를 기록했다. 이는 end-to-end 실행 및 녹화 검증이지 정책 성공이나 논문 수치 재현이 아니다. scene은 Appendix G(a) 사진을 참고한 local reconstruction이며 정식 scene sign-off와 물리/평가기 검증은 남아 있다. 현재 작업본은 TiPToP의 5-scene/51-layout 기반 근사 확장이다.**

최신 S01 candidate는 사용자가 제공한 Appendix G(a) 사진을 참고해 컵, 빨간 캡의 흰색 마커, 파란 손잡이 가위형 물체를 배치했다. scissors는 YCB 037 Google 16k 스캔 메시를 USD에 포함하고, 사진과 다르게 노란색인 손잡이 면만 파란색으로 바꿨다. cup과 marker는 procedural proxy다. Isaac Lab DROID 카메라 3개로 policy-free preview를 만들었고 이후 사용자의 지시에 따라 full rollout도 수행했다. scene 좌표·asset·camera calibration은 논문에 공개되지 않아 공식 장면이 아닌 시각적 재구성이다.

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

### B300 실행 결과 (2026-10-12 full S01 rollout)

- Task: S01 seen; “Move the cup forward then put the marker inside the cup”; layout 0; 450 steps.
- Full-run artifacts: `droid-sim-eval-validation/runs/S01/20261012T150635Z/` 아래 `results.json` 및 450-frame/30-second `episode_00.mp4`.
- Result: `progress=0.0`, `success=false`, `scoring=proxy_geometric_staged`, `approximate=true`; cup displacement 0.0m. 정책이 목표 행동을 성공시키지 못했다.
- 후속 8-step action 진단: `droid-sim-eval-validation/diagnostics/S01/20261012T152422Z/results.json`에 처음 8개 joint target과 전후 joint position을 기록했다. 최대 관절 변화량은 0.131rad로 action이 로봇에 전달되어 움직인 것은 확인했지만 컵은 움직이지 않았다. action-client가 멈춘 문제는 아니며, 물체 접근/contact를 보이기 전에 rollout 수를 늘리지 않는다.
- DreamZero's separate input-view recording: `real_world_eval_gen_20261012_0/molmo2/000003_10_12_15_09_27_n64.mp4` (private data directory); 이 영상은 evaluator MP4와 별개의 server recording이다.
- 첫 full attempt에서는 video/JSON이 없었다. 원인은 evaluator wrapper의 `env -i`가 PATH를 표준 경로로 제한해 `mediapy`가 요구하는 ffmpeg를 찾지 못한 것. DreamZero venv의 `imageio_ffmpeg` binary를 `APPENDIX_G_FFMPEG`로 전달하게 두 source 파일을 수정했고, encode/save check 후 전체 run의 JSON과 MP4를 검증했다.
- 1-step encode/save check 및 실패한 시도의 빈 run directories는 정리했으며, 재현 이력용 stdout logs는 private validation/logs에 남겼다.
- `uv cache clean`으로 `/home/kyuchul-lee/.cache/uv`에서 368,446개 파일(81.5 GiB)을 제거했다. 이는 재생성 가능한 package/build cache이며 Python venv는 유지됐다. 별도 Hugging Face cache의 Wan2.1 auxiliary weights 약 77 GiB는 추론에 필요해 보존했다.
- 오래된 임시 DreamZero project-page clone 3.5 GiB를 제거했다(깨끗한 공개 clone; model/repo working tree는 아님). 종료 후 DreamZero server를 중지했고 두 GPU의 사용량이 0 MiB로 돌아왔다. Home filesystem에는 약 13 GiB가 남아 있다.

## 현재 작업본 상태

2026-10-12 새 checkout에서는 OS graphics library 누락을 해결한 뒤 S01
USD를 Vulkan으로 세 DROID 카메라에서 렌더했고, 실제 DreamZero 450-step
rollout까지 완료했다. 최신 절차와 산출물 위치는 [`reproduction.md`](reproduction.md),
Isaac/B300 복구 및 ffmpeg 저장 문제는 [`b300-isaaclab-history.md`](b300-isaaclab-history.md)에
기록했다. 이전 checkout의 40 task × 2 layout USD 생성 및 초기 placement
preflight는 시각·물리·평가기까지 80개를 검증했다는 뜻이 아니다.

### S02 scene preview (2026-10-13; no policy inference)

- Source task: Appendix G(a), seen task 2, “Put the marker in the blue box.”
- The paper image was used to map a turquoise open box, white/red marker,
  blue-handled scissors, wooden tabletop, and gray equipment backdrop. The
  scissors are a visible distractor; the task evaluator target remains the box.
- Added an image-guided S02 layout to the USD builder and manifest. The first
  version used a procedural box and marker; scissors use the already included
  YCB 037 scan with blue handles. Dimensions and coordinates are local
  assumptions, not paper-published data.
- Candidate USD: `assets/appendix_g/s02_candidate/s02_layout0.usd` (about
  555 KiB). Three-camera, policy-free preview:
  `assets/previews/S02_candidate/S02/layout0/contact_sheet.png`.
- Render initialized Isaac Lab with CPU physics and Vulkan RGB. This step made
  zero DreamZero inference calls and did not run a rollout. Visual approval is
  pending before any S02 inference.

### S02 public box asset candidate (2026-10-13; no policy inference)

- Replaced the latest candidate's hand-built box visual with the public
  Innerscene “Stack Bin - Storage Bin” GLB (CC0). The 150 KiB source file and
  license/source record are included under `assets/third_party/innerscene/`.
- The source model is resized and recolored blue; its original front access
  cutout remains a visible difference from the paper photograph. The object
  uses a simple open-container collision proxy so the visual mesh does not
  introduce unstable concave collision behavior.
- New candidate USD: `assets/appendix_g/s02_public_asset_candidate/`.
  Rendered preview: `assets/previews/S02_public_asset_candidate_contact_sheet.png`.
- This remains a visual candidate, not an official or paper-exact asset.
  Scene review is pending; no DreamZero inference or rollout has been run.

### S02 rollout with the containment proxy (2026-10-13)

- Re-ran the reviewed public-bin layout for 450 policy steps with the current
  oriented box-footprint/interior check. The result was `success=false`,
  `progress=0.0`, reason `item_not_fully_inside_container_proxy`; measured
  marker footprint margins were negative in the container frame.
- Video:
  `/home/kyuchul-lee/.local/share/.private/runs/s02_public_asset_candidate/S02/20261013T085809Z/S02/layout0/episode_00.mp4`.
  Machine-readable result:
  `/home/kyuchul-lee/.local/share/.private/runs/s02_public_asset_candidate/S02/20261013T085809Z/results.json`.
- This differs from the earlier human-reviewed episode, whose final wrist
  frame was judged successful. Preserve both results; do not rewrite the old
  record or claim a stable S02 success rate from these two local runs.
- Every completed policy episode now requires a non-empty MP4. Each run has an
  `index.html` video gallery, and the private archive catalog at
  `/home/kyuchul-lee/.local/share/.private/runs/index.html` links the run
  galleries. Scene-only previews remain PNG contact sheets.

### U13 CC0 scene and paired rollout pilot (2026-10-13)

- Added the public-domain Innerscene toaster and CC0 Kenney bread/plate visuals,
  with local asset source/license records. The toaster's hidden collision shell
  includes a slot ledge so bread does not fall through under gravity. A
  policy-free 60-step settle check passed for both layouts before inference.
- The first U13 run used the pre-ledge scene and is excluded from valid outcome
  counts. With the corrected scene, layout 0 failed (`progress≈0.000011`) and
  layout 1 passed the project's approximate geometry/stability proxy
  (`progress≈0.8485`, `success=true`). This is one success in two paired local
  layouts, not a paper score.
- Videos:
  `/home/kyuchul-lee/.local/share/.private/runs/appendix_g_u13_pilot/U13/20261013T084235Z/U13/layout0/episode_00.mp4`
  and
  `/home/kyuchul-lee/.local/share/.private/runs/appendix_g_u13_pilot/U13/20261013T084737Z/U13/layout1/episode_00.mp4`.
- Scene review contact sheets and settle JSON are under
  `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/u13_cc0_v1/U13/`.
  The evaluator uses an approximate oriented-AABB toaster-clearance proxy; it
  should not be presented as the undisclosed Appendix G metric.
