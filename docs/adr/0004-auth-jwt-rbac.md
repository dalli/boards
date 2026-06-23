# ADR-0004: 자체 인증과 역할 기반 인가 (JWT + RBAC)

- 상태: 승인 대기
- 날짜: 2026-06-23

## 컨텍스트

일반 사용자/관리자 분리가 핵심 요구사항이다. 외부 IdP 없이 자체 구현하기로 했다.

## 결정

- email + password(bcrypt) 자체 인증. 로그인 시 JWT access token 발급(`role` 클레임 포함).
- 인가는 RBAC 2역할(USER/ADMIN) + 소유권 검사로 service 계층에서 집행.
- 토큰의 role을 맹신하지 않고 보호 동작에서 서버가 권한을 재확인.

## 대안

- 세션/쿠키 기반: 서버 상태 필요. SPA + 무상태 API에는 JWT가 단순.
- 외부 OAuth/Clerk: 의존성·설정 증가, 학습/제어 목적에 불리.

## 결과

- 무상태 인증으로 백엔드 단순. refresh token·만료 회전은 향후 phase로 분리(현 범위 access only).
- 시크릿(JWT secret)은 env 보호(§4).
