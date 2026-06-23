# Phase 0+1 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | codex thread 019ef435-40f3-7222-85f4-ecbc4c4e233a |
| 검토 대상 | dev 브랜치 staged Phase 0+1 (backend 스캐폴딩·auth·User 모델·0001 마이그레이션·frontend Phase 0) |
| 검토 시각(UTC) | 2026-06-23T11:19Z |
| 사용 스킬 | code-review (read-only) |
| 결과 | 총 12건 — blocking 0, high 3, medium 8, low 1 |

> 리뷰는 alembic upgrade/downgrade SQL 오프라인 생성 및 JWT 클레임 검증을 직접 실행해 확인함(증거 기반).

## SECURITY

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| SEC-001 | high | backend/app/security.py:52-56 | `decode_access_token`가 `exp`/`iat` 필수 클레임 검증 옵션 없이 `jwt.decode` 호출 → 만료 검증 누락 가능(security.md S-02). |
| SEC-002 | high | docker-compose.yml:45-49 | DB/S3/JWT 시크릿 폴백 기본값 존재 → env 주입 누락 시 공개 자격증명으로 기동(§4, deployment.md). |
| SEC-003 | medium | backend/app/service/auth_service.py:22-30 | signup이 중복 이메일에 `Email already registered` 반환 → 가입 경로 계정 열거(S-05). |
| SEC-004 | medium | backend/app/service/auth_service.py:34-40 | login이 미지의 이메일에서 bcrypt 검증을 단락(short-circuit)으로 건너뜀 → 타이밍 사이드채널(계정 열거). |
| SEC-005 | medium | backend/app/service/auth_service.py:34-40 | login 경로에 rate-limit·감사 로그 없음(security.md S-05 미구현). |
| SEC-006 | medium | backend/app/config.py:23 | `bcrypt_rounds`가 하한 검증 없이 env 설정 가능 → cost≥12 요건(S-02) 미강제. |

## 3-TIER LAYERING

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| LAY-001 | medium | backend/app/service/auth_service.py:42-48 | `promote_to_admin`이 `UserRepository`를 거치지 않고 세션으로 직접 `User.role` 변경·commit(§5 계층). |

## AUTH/AUTHZ DEPENDENCY DESIGN

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| AUTH-001 | high | backend/app/service/auth_service.py:42-49 | `promote_to_admin`이 actor/role 검사 없이 `target_user_id`만 받음 → 라우터 의존성이 유일한 ADMIN 게이트(서비스 계층 방어 부재). |
| AUTH-002 | medium | backend/app/deps.py:30-34 | `get_current_user`가 `int(sub)`를 auth-error 처리 밖에서 캐스팅 → 비정수 sub 토큰이 처리되지 않은 `ValueError`로 누출 가능. |

## SQLALCHEMY MODELS vs DB-SCHEMA

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| MOD-001 | medium | backend/app/models.py:62-147 | `role`/`status`/`version`/`is_image`의 ORM 기본값이 Python-side 전용 → db-schema.md·마이그레이션의 DB server default와 불일치. |

## MIGRATION

(지적 없음)

## OTHER

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| OTH-001 | low | (plan.md 경로) | 리뷰 프롬프트가 `docs/architecture/plan.md`를 참조했으나 실제 문서는 저장소 루트 `plan.md`. (프롬프트 오기, 산출물 결함 아님) |
| OTH-002 | medium | frontend/src/api/client.ts:1-22 | Phase 0 프론트가 수기 API 클라이언트를 추가 — §5.1 계약은 생성물 `frontend/src/api/generated/**`를 소비 경로로 선언. |

## 총계

총 12건; blocking 0, high 3, medium 8, low 1.
