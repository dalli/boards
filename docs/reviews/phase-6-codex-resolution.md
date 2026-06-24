# Phase 6 codex 리뷰 처리 (§6.2-4)

원본 리뷰: [phase-6-codex-review.md](phase-6-codex-review.md).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| F-001 | high | **Fixed** | `login`이 `/auth/me` 실패 시 `setAccessToken(null)` 후 rethrow. 테스트 `endpoints.test.ts`(실패 시 토큰 null). |
| F-002 | high | **Fixed** | `BoardDetailPage` effect가 board/posts/cursor/error 초기화 + `active` 경합 가드 + 에러 시 비움 + reloadKey 재조회. |
| F-003 | high | **Fixed** | `PostDetailPage` effect가 post/comments 초기화 + `active` 가드 + 에러 시 비움. |
| F-004 | medium | **Fixed** | `BoardListPage`가 auth 변경 시 boards 비우고 `active` 가드. |
| F-005 | medium | **Fixed** | 댓글 변경 후 `await refreshComments()`(try/catch)로 갱신. |
| NF-001 | high | **Fixed** | `login` 시작 시 `setAccessToken(null)` → 실패한 재로그인이 이전 토큰을 남기지 않음. 테스트(stale 토큰+401→null). |
| FE-AC6-001 | high | **Fixed** | 라이트박스 open 시 close 버튼 포커스(ref+useEffect), Escape로 닫힘(window keydown+cleanup). 테스트(Escape 닫힘). |
| FE-AC6-002 | medium | **Fixed** | 썸네일 그리드를 `<ul>/<li>` + 네이티브 `<button>`으로 변경(role 오버라이드 제거). |
| AUTH-001 | medium | **Fixed** | `AuthContext.login`이 실패 시 `setUser(null)` 후 rethrow. |

## codex 재검증 (§6.2-4)

- 라운드 2: F-001~F-005 RESOLVED, 신규 NF-001(high).
- 라운드 3: NF-001 RESOLVED, 신규 FE-AC6-001(high)·FE-AC6-002·AUTH-001(med).
- 라운드 4(최종): FE-AC6-001/FE-AC6-002/AUTH-001 **전부 RESOLVED**.

> **최종 재리뷰 판정: `UNRESOLVED BLOCKING FINDINGS: NO` · `UNRESOLVED HIGH FINDINGS: NO`** → §6.2-4 게이트 충족.

## AC 체크박스 / §3.2-2 보조 점검 관련 (인간 결정)

- **인간 결정(2026-06-24)**: plan.md의 AC 체크박스(§4 보호 대상)는 **변경하지 않고**, 충족은
  Phase 6 회고의 **AC 추적표(§3.2-1)** + 통과 테스트로 입증한다.
- 따라서 AGENTS.md §3.2-2의 보조 grep(`^\s*- \[ \] plan.md`)은 미충족 체크박스를 계속 출력한다 —
  이는 보호 파일 미변경(인간 결정)에 따른 **의도된 상태**이며, 권위 있는 완료 증거는 추적표다.

## 수정 후 검증 증거 (콘솔)

```text
frontend: tsc clean · eslint clean · vitest 10 passed · vite build OK
backend (회귀): ruff/mypy clean · pytest 104 passed · coverage 93.83%
§5.1 drift: backend/openapi.json current · generated client matches (regen no-diff)
```
