# 회고: Phase 6 (프론트 통합 마감 + 전체 AC 회귀)

## 한 일과 결과

- React 18 + Vite + TS SPA: 로그인/회원가입, 게시판 목록·상세, 게시물 작성(첨부/이미지 포함)·조회·삭제,
  댓글 작성·삭제, 이미지 썸네일 카드 그리드 + 라이트박스(AC6), 관리자 게시판 생성.
- §5.1: `openapi.json`에서 TS 타입 생성(`npm run gen:api`) 후 소비(수기 타입 금지, 생성물 drift 무).
- S-01(인메모리 토큰)·S-04(React 이스케이프, `dangerouslySetInnerHTML` 미사용) 준수. 라이트박스 a11y(Escape/포커스).

### 검증 증거 (콘솔)

```text
frontend: tsc clean · eslint clean · vitest 10 passed · vite build OK (175KB/gzip 57KB)
backend 회귀: ruff/mypy clean · pytest 104 passed · coverage 93.83%
codex 4라운드 리뷰: 최종 UNRESOLVED BLOCKING: NO · UNRESOLVED HIGH: NO
```

## 수락 기준 추적표 (§3.2-1, AC↔코드/테스트 1:1 매핑)

| AC | 대응 구현 | 대응 테스트(증거) |
| --- | --- | --- |
| AC1 인증/role | backend auth_service·deps·api/auth; frontend AuthContext | backend `tests/test_auth.py`(signup 201/login 200·401/role 403), `test_security.py`; frontend `endpoints.test.ts` |
| AC2 게시판 생성 | board_service·api/boards; CreateBoardPage | `tests/test_boards.py`(ADMIN 201/비ADMIN 403/enum 422/dup 409) |
| AC3 NOTICE 쓰기·PUBLIC 읽기 | permissions.ensure_can_write/read_board | `test_boards.py`, `test_posts.py`(NOTICE 403/201, PUBLIC 비인증 200) |
| AC4 GENERAL 첨부 업로드/다운로드 | attachment_service(A-02)·presigned GET | `tests/test_attachments.py`(업로드 201·presigned·401/403) |
| AC5 IMAGE 0개 422·썸네일·마지막삭제 422 | attachment_service IMAGE 경로·E-01 | `tests/test_image_board.py`(0개 422·thumbnail_key·마지막삭제 422) |
| AC6 썸네일 배열·original-url | PostDetailResponse.attachments·original-url; ImageGallery | `test_image_board.py`(그리드 배열·라이트박스 원본); frontend `ImageGallery.test.tsx` |
| AC7 작성자/ADMIN 수정·삭제·409 | post/comment service·낙관적 잠금 | `tests/test_posts.py`(403/2xx·stale 409) |
| AC8 §3.4 산출물 + ADR | docs/architecture/**, docs/adr/** | AGENTS.md §3.4 점검 스크립트(아래) |
| AC9 페이지네이션 계약 | pagination·post_repository keyset | `tests/test_pagination.py`(경계 전수) |

> **AC 체크박스(plan.md)는 §4 보호 대상**이므로 본 추적표로 충족을 입증하고, plan.md 체크 표기는 인간 승인 후 반영(아래 HCI-1).

## 잘된 점

- 백엔드 계약(OpenAPI)을 SoT로 둔 덕에 프론트가 타입 안전하게 소비, 수기 드리프트 0.
- codex가 상태 위생(로그아웃 후 잔존)·토큰 위생·a11y(포커스/Escape)까지 4라운드로 끌어올림.

## 어려웠던 점

- 인메모리 토큰 모델에서 로그인 실패/재로그인 경로의 토큰·user 상태 위생이 미묘 → 시작 시 클리어 + 실패 시 클리어로 정리.

## codex 리뷰 지적과 그 처리 결과

- 누적 9건(high 5/med 4) **전건 Fixed**, 최종 재검증 blocking·high 0.
- 상세: [phase-6-codex-review.md](../reviews/phase-6-codex-review.md), [phase-6-codex-resolution.md](../reviews/phase-6-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Scope | plan.md의 AC 체크박스(§4 보호 대상)에 충족 표기 필요. 본 phase에서 전체 AC를 추적표+테스트로 입증함. | plan.md AC 체크박스를 [x]로 갱신하는 것을 승인(보호 파일 변경). | **차단**(보호 파일 — 인간 승인 전 변경 불가) |
| HCI-2 | Security | CSP 헤더(security.md S-04 line 61)는 SPA 빌드가 아닌 서빙 계층(nginx/Vite) 책임 — 현재 미설정. | CSP 헤더 적용 위치/시점(배포 nginx) 결정. | 비차단 |
| HCI-3 | Risk | 브라우저 기반 E2E(Playwright)는 docker 스택 필요 — 현재 통합검증은 backend TestClient(엔드투엔드) + frontend Testing Library로 대체. | 실 브라우저 E2E 도입 시점 확인(HCI: Postgres/MinIO 통합 테스트와 함께). | 비차단 |
| HCI-4 | Architecture | 조정/orphan 정리 잡(E-02)·Postgres 통합 테스트는 누적 미구현(Phase 4/5 HCI 연속). | 운영 전 구현 계획 확정. | 비차단 |
