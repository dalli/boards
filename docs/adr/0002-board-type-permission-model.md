# ADR-0002: 게시판 종류와 권한 모델 (Board.type enum)

- 상태: 승인 대기
- 날짜: 2026-06-23

## 컨텍스트

공지(관리자만 쓰기), 일반(모두 읽기/쓰기), 이미지(이미지 첨부 강제)의 세 게시판이 서로 다른 권한·동작을 가진다.

## 결정

- 단일 `Board` 테이블 + `type` enum(NOTICE/GENERAL/IMAGE)으로 **쓰기 권한·첨부 규칙**을 구분한다.
- **읽기 가시성은 별도 `read_visibility` enum(PUBLIC/AUTHENTICATED)으로 분리(E-04 결정)**. ADMIN이 게시판 생성 시 지정한다. PUBLIC=누구나 읽기, AUTHENTICATED=인증 사용자만 읽기.
- 따라서 두 축이 독립: 쓰기=`type` 분기(NOTICE는 ADMIN, GENERAL/IMAGE는 인증 사용자), 읽기=`read_visibility` 분기. 모두 service 계층에서 집행.

## 대안

- 게시판별 read_role/write_role 컬럼으로 세분화: 더 유연하나 현 요구(3종 고정)에는 과설계(YAGNI).
- 종류별 테이블 분리: 중복·조인 복잡도 증가.

## 결과

- 단순하고 마이그레이션 쉬움. 권한 분기가 한 곳(service)에 모임.
- 읽기(공개/인증)와 쓰기(type) 축이 분리되어 "공개 일반 게시판"·"인증 전용 공지" 같은 조합이 가능.
- 향후 커스텀 권한이 필요해지면 ADR을 갱신해 role 컬럼 모델로 확장(확장 가능).
