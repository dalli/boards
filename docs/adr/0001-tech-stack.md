# ADR-0001: 기술 스택 선택 (FastAPI + React + PostgreSQL + MinIO)

- 상태: 승인 대기
- 날짜: 2026-06-23

## 컨텍스트

일반/관리자 분리, 다중 게시판, 첨부·이미지 처리를 갖춘 게시판 시스템을 개발한다. 백/프론트 분리, 자체 인증, 이미지 썸네일이 필요하다.

## 결정

- 백엔드: Python 3.12 + FastAPI (pydantic 검증, OpenAPI 자동 생성).
- ORM: SQLAlchemy 2.x + Alembic.
- DB: PostgreSQL 16.
- 파일: MinIO(S3 호환), 이미지 처리: Pillow.
- 프론트: React 18 + Vite + TypeScript.

## 대안

- Next.js 풀스택: 단일 앱이나 백/프론트 경계·스코프 분리(§5)가 흐려짐.
- Node/Nest 백엔드: 가능하나 이미지 처리·자체 인증 학습 목적에서 Python 생태계 선택.

## 결과

- 백/프론트 스코프 경계가 명확(§5), OpenAPI가 공유 계약 SoT(§5.1).
- Python/JS 두 툴체인을 운영해야 함(명령은 §0.1/§2에 영역별 바인딩).
