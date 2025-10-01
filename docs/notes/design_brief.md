# Saturn V (외형 고정) × 내부 커스텀 고효율 추진체 설계 브리프

## 핵심 원칙
- 외형: 실제 Saturn V 형상 유지(비율/실루엣).
- 내부: 간소화 + 고추진·고효율 + 제작 용이성 우선(배관/밸브/벨로즈/매니폴드 정리).
- 엔진: 다중 인젝터·혼합제 프로펠런트(변칙 조합 A/B, 중앙 혼합 A+B도 고려).
- 파트명: 계층형 GLB 그룹과 일관된 파트명(Shell, Tanks, Intertank, ThrustStruct, Engines, Plumbing, Fins…).

## 단계
1) 1단(S-IC): LOX/RP-1 매니폴드, 밸브·벨로즈, 피드, 엘보, 드롭 파이프까지 완전 연결(히트쉴드 간섭 없음).
2) 2단(S-II): 공용 벌크헤드·J-2군, LH2/LOX 매니폴드·GG/덕트 반영.
3) 3단(S-IVB + IU/CSM/LES): 탱크·배플·APS·IU 링 및 최종 스택.
4) 발사대/고정대: 최종 스택 뷰 제공.

## 출력/폴더 정책
- 정밀: data/geometry/cad/exports/rocket/saturn_v/<stamp>
- 프린트(예: 1:200): .../rocket/saturn_v/print/1_200/<stamp>
- J58 커스텀: .../pencil_engine/J58_custom/<stamp>
- 각 폴더에 index.json과 계층 GLB(S-IC_named.glb 등) 포함.

## 프린트 가이드(예시)
- 스케일: 1:200(=0.005). 커플러: peg Ø6, L12, 간극 0.25mm.
- 부품 분할: 스커트/탱크/추력구조/엔진·배관 모듈화.

## Git
- GitHub Desktop 내장 git 우선 사용, 변경 시 자동 커밋/푸시.

