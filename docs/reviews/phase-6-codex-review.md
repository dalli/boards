# Phase 6 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | 1차 ac3b9fb1b8e213044 · 재리뷰 aa4150fc8b0f89d63 · 최종 aa4d4f0c13293dca1 / a1cba7342bb2ac478 |
| 검토 대상 | dev staged Phase 6 (프론트 SPA: api client/endpoints/types, AuthContext, ImageGallery, pages, App, app.css) |
| 검토 시각(UTC) | 2026-06-23 |
| 사용 스킬 | code-review (read-only) |
| 결과(라운드 합산) | blocking 0 · high(F-001/002/003, NF-001, FE-AC6-001) · medium(F-004/005, FE-AC6-002, AUTH-001) |

> 생성물 `frontend/src/api/generated/schema.ts`는 리뷰 대상 제외(§5.1 자동 생성, openapi.json SoT).

## 라운드별 지적

### 1차

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| F-001 | high | endpoints.ts:24 | login이 `/auth/me` 실패 시에도 토큰을 메모리에 남김. |
| F-002 | high | BoardDetailPage.tsx | 재조회 실패 시 기존 board/posts를 비우지 않아 로그아웃/가시성 실패 후에도 보호 콘텐츠 잔존. |
| F-003 | high | PostDetailPage.tsx | 동일 — post/comments 잔존. |
| F-004 | medium | BoardListPage.tsx | auth 변경 시 stale 비우지 않음 + 경합 미가드 → 익명 뷰에 AUTHENTICATED 메타 잔존 가능. |
| F-005 | medium | PostDetailPage.tsx | 댓글 갱신 미await/미catch. |

### 재리뷰 신규

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| NF-001 | high | endpoints.ts:25 | login 시작 시 기존 토큰 미클리어 → `/auth/login` 실패 시 이전 세션 토큰 잔존. |

### 최종 a11y/상태 신규

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| FE-AC6-001 | high | ImageGallery.tsx:41 | 라이트박스 modal에 포커스 트랩·Escape 키 처리 없음(접근성). |
| FE-AC6-002 | medium | ImageGallery.tsx:28 | 썸네일 button이 `role="listitem"`로 시맨틱 오버라이드 → 보조기술 오인. |
| AUTH-001 | medium | AuthContext.tsx:18 | 로그인 실패가 setUser 전에 reject → 이전 user 상태 잔존(토큰만 클리어). |

> 처리·재검증은 [phase-6-codex-resolution.md](phase-6-codex-resolution.md).

## 확인 사항

- **XSS(S-04)**: `dangerouslySetInnerHTML` 사용 0건, 사용자 콘텐츠는 React 기본 이스케이프 — 지적 없음(확인).
- **토큰(S-01)**: localStorage/sessionStorage/cookie 미사용, 인메모리 보관 — 확인.
- **CSP(security.md:61)**: SPA 파일만으로는 확인 불가(서빙 계층 헤더) → out-of-scope, 회고 HCI 기록.
