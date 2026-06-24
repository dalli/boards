# Phase 4 codex 리뷰 처리 (§6.2-4)

원본 리뷰: [phase-4-codex-review.md](phase-4-codex-review.md).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| RV4-001 | high | **Fixed** | `StorageError`(502) 신설(errors.py), `attachment_service`가 PENDING commit 후 raise. 테스트 `test_storage_failure_returns_502_and_keeps_pending`. |
| RV4-002 | high | **Fixed** | `api/attachments._read_capped`가 `UploadFile.size`+cap+1 bounded read로 전체 버퍼링 전 거부(413). 테스트 `test_oversized_upload_rejected_413`. |
| RV4-003 | medium | **Fixed** | `validate_upload`가 선언 MIME↔매직바이트 불일치 및 확장자 불일치 거부. 테스트 `test_validate_rejects_declared_mime_mismatch`, `test_validate_rejects_extension_mismatch`. |
| RV4-004 | medium | **Fixed** | `image_service`가 `width*height > max_image_pixels` 명시 검사 후 거부(Pillow 2배 임계 의존 제거). |
| RV4-005 | low | **Fixed** | `delete_attachment(post_id=...)`가 `attachment.post_id != post_id`면 404. 테스트 `test_delete_with_wrong_post_id_404`. |
| RV4-006 | low | **Accepted(known)** | FastAPI `HTTPBearer(auto_error=False)`가 optional-auth 엔드포인트를 OpenAPI에 bearer-required로 표기하는 알려진 표현 한계. 런타임 인가(`_readable_post`)는 정상. 생성 클라이언트는 토큰 없이도 호출 가능. 회고 HCI에 기록. |

## codex 재검증 (§6.2-4)

재리뷰(thread a5174c1b8e0153a0a): RV4-001~005 전부 **RESOLVED**, 신규 blocking/high 없음.

> **재리뷰 최종 판정: `UNRESOLVED BLOCKING FINDINGS: NO` · `UNRESOLVED HIGH FINDINGS: NO`** → §6.2-4 게이트 충족.

## 수정 후 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (36 files)
pytest 96 passed · coverage 92.84% (>=80)
```
