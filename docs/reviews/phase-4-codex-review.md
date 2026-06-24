# Phase 4 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | 1차 agent a8d8f2d7b5cb29503 · 재리뷰 a5174c1b8e0153a0a |
| 검토 대상 | dev staged Phase 4 (storage, file_validation, image_service, attachment_service/repository, api/attachments, deps, tests, openapi) |
| 검토 시각(UTC) | 2026-06-23 |
| 사용 스킬 | code-review (read-only) |
| 결과(1차) | 6건 — blocking 0, **high 2 (RV4-001/002)**, medium 2 (RV4-003/004), low 2 (RV4-005/006) |

## 1차 지적

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| RV4-001 | high | attachment_service.py:115 | S3 업로드 실패가 `AppError`(기본 400)로 반환 — A-03/data.md는 5xx + PENDING 유지 요구. |
| RV4-002 | high | api/attachments.py:40 | 업로드 크기 상한이 파일 전체를 메모리로 읽은 *후*에만 검사 — S-03 위반, 메모리 압박 위험. |
| RV4-003 | medium | file_validation.py:61 | 선언 MIME가 매직바이트 MIME와 일치하도록 강제하지 않음, 확장자 교차검증 부재(S-03). |
| RV4-004 | medium | image_service.py:17 | `MAX_IMAGE_PIXELS`는 Pillow의 2배 임계에서만 에러 — 설정 픽셀 상한이 부분만 강제. |
| RV4-005 | low | api/attachments.py:73 | 중첩 삭제 라우트가 `post_id`를 첨부에 바인딩하지 않음(인가 우회는 아니나 계약 위반). |
| RV4-006 | low | openapi.json:741 | optional-auth 공개 다운로드 엔드포인트가 OpenAPI에 bearer-required로 표기(FastAPI HTTPBearer). |

> 처리·재검증은 [phase-4-codex-resolution.md](phase-4-codex-resolution.md). 1차 판정 `UNRESOLVED BLOCKING FINDINGS: NO`.
