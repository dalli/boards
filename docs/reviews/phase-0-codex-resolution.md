# Phase 0+1 codex 리뷰 처리 (§6.2-4)

각 지적을 **Fixed / Rejected / Escalated**로 기록한다. Fixed는 대응 파일·테스트 증거를 연결한다.
원본 리뷰: [phase-0-codex-review.md](phase-0-codex-review.md) (codex thread 019ef435-40f3-7222-85f4-ecbc4c4e233a).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| SEC-001 | high | **Fixed** | `decode_access_token`가 `exp`/`iat`/`sub` 필수 클레임을 명시 검증(python-jose는 require 옵션 미강제). [security.py](../../backend/app/security.py) · 테스트 `test_decode_rejects_token_without_exp`, `test_decode_rejects_expired_token`. |
| SEC-002 | high | **Fixed** | docker-compose에서 시크릿 폴백 제거 → `${VAR:?...}`로 미주입 시 기동 실패. [docker-compose.yml](../../docker-compose.yml). |
| SEC-003 | medium | **Accepted-deferred** | signup 중복 409는 표준 UX. 가입 경로 완전 비열거화는 이메일 인증(범위 밖, spec §10) 전제 → MVP 보류. 회고 Human Check Item에 기록(HCI). |
| SEC-004 | medium | **Fixed** | 미지의 사용자도 더미 해시(`DUMMY_PASSWORD_HASH`)로 bcrypt 검증 수행 → 타이밍 사이드채널 완화. [auth_service.py](../../backend/app/service/auth_service.py)·[security.py](../../backend/app/security.py) · 테스트 `test_login_unknown_user_runs_verification`. |
| SEC-005 | medium | **Accepted-deferred** | rate-limit·인증 감사 로그는 미들웨어성 횡단 관심사. security.md S-05에 설계 존재. 전용 슬라이스로 보류(회고 HCI). |
| SEC-006 | high | **Fixed** | `Settings.bcrypt_rounds`에 `>=12` field_validator 추가. [config.py](../../backend/app/config.py) · 테스트 `test_config_rejects_weak_bcrypt_cost`. |
| LAY-001 | medium | **Fixed** | `promote_to_admin`이 `UserRepository.set_role`로 쓰기 경로 일원화. [auth_service.py](../../backend/app/service/auth_service.py)·[user_repository.py](../../backend/app/repository/user_repository.py). |
| AUTH-001 | high | **Fixed** | `promote_to_admin(actor=...)`가 service 계층에서 ADMIN 재검사(라우터 외 방어). 테스트 `test_promote_requires_admin_at_service_layer`. |
| AUTH-002 | medium | **Fixed** | `_parse_subject`가 비정수 sub를 `AuthenticationError`로 변환(unhandled ValueError 제거). [deps.py](../../backend/app/deps.py) · 테스트 `test_token_with_noninteger_sub_rejected`. |
| MOD-001 | medium | **Fixed** | `role`/`status`/`version`/`is_image`에 `server_default` 추가 → 모델·마이그레이션 정합. [models.py](../../backend/app/models.py). |
| OTH-001 | low | **Rejected** | 근거: 리뷰 *프롬프트*가 `docs/architecture/plan.md`로 오기한 것이며 실제 문서는 루트 `plan.md`로 정상 존재. 산출물 결함 아님(경로 정합 유지). |
| OTH-002 | medium | **Accepted-clarified** | `apiFetch`는 인증 헤더·base URL을 다루는 **전송 래퍼**이지 계약 타입이 아니다. §5.1 생성물(`frontend/src/api/generated/**`)은 OpenAPI에서 생성되며 수기 수정 금지 — Phase 2+에서 `npm run gen:api`로 생성. 전송 래퍼와 생성 타입은 공존(생성 타입을 `apiFetch`가 소비). README §API 계약에 절차 명시. |

## 미해결 blocking finding 여부

- blocking: 0건(원래 없음). high 3건(SEC-001/SEC-002/SEC-006/AUTH-001) **전부 Fixed**.
- Accepted-deferred 2건(SEC-003, SEC-005) 및 Accepted-clarified 1건(OTH-002), Rejected 1건(OTH-001)은 회고 §Human Check Items에 인간 확인용으로 기재.

## 수정 후 검증 증거 (콘솔)

```
ruff check .   → All checks passed!
mypy app       → Success: no issues found in 22 source files
pytest --cov   → 25 passed; TOTAL coverage 93.32% (>=80% gate)
alembic up/down → migration OK
```

## codex 재리뷰 (§6.2-4 미해결 blocking 부재 확인)

Fixed 항목 적용 후 staged 코드에 대해 codex 재리뷰 수행(동일 독립 모델, 새 thread).

| ID | sev | 파일/라인 | 상태 |
| --- | --- | --- | --- |
| SEC-001 | HIGH | backend/app/security.py:63-74 | **RESOLVED** — 고정 알고리즘 + exp/iat/sub 누락 토큰 거부 확인. |
| SEC-002 | HIGH | docker-compose.yml:9,26-27,47,50-52 | **RESOLVED** — Postgres/MinIO/JWT 시크릿 `${VAR:?...}` 폴백 없음 확인. |
| SEC-004 | HIGH | auth_service.py:40-46; security.py:40-44 | **RESOLVED** — 미지 사용자도 DUMMY_PASSWORD_HASH로 검증 후 일반화 실패. |
| AUTH-001 | HIGH | api/auth.py:35-38; auth_service.py:49-56 | **RESOLVED** — actor 전달 + service 계층 ADMIN 재검사 확인. |
| AUTH-002 | HIGH | deps.py:38-45 | **RESOLVED** — 비정수 sub → AuthenticationError 변환 확인. |

> **재리뷰 최종 판정: `BLOCKING FINDINGS REMAINING: NO`.** high 전건 RESOLVED, 신규 blocking/high 도입 없음 → §6.2-4 게이트(미해결 blocking 부재) 충족.
