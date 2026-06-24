# 회고: Phase 4 (첨부파일 — 일반 게시판)

## 한 일과 결과 (완료된 수락 기준)

- **AC4**: 인증 사용자가 일반 게시판에 글+첨부 업로드(백엔드 경유, A-02)→201(COMMITTED).
  PENDING→COMMITTED 생명주기(ADR-0005), 실패 시 PENDING 유지(data.md 4단계, 보상 롤백 없음).
  다운로드는 read_visibility 검사 후 presigned GET(S-06, TTL 5분) 반환, 비인가 읽기→401.
- **검증(S-03)**: 매직바이트 + 선언 Content-Type + 확장자 교차검증, 크기 상한(버퍼링 전 거부),
  이미지 Pillow 디코딩·재인코딩·픽셀 상한·압축폭탄 방어, 서버 생성 storage_key.
- **삭제(NV2-002)**: S3 객체 선삭제 → DB 행 삭제(단일 트랜잭션), 작성자/ADMIN만.

### 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (36 files)
pytest 96 passed · coverage 92.84% (>=80)
codex 재검증: RV4-001~005 RESOLVED · UNRESOLVED BLOCKING: NO · UNRESOLVED HIGH: NO
```

## 잘된 점

- `StorageClient` 프로토콜 + 인메모리 페이크로 도커 없이 업로드/다운로드/삭제 경로를 고속 검증.
- codex가 5xx 매핑 오류·메모리 압박·MIME/확장자 교차검증·픽셀 상한·중첩 라우트 바인딩을 잡아 S-03 강화.

## 어려웠던 점

- FastAPI `HTTPBearer(auto_error=False)`가 optional-auth 엔드포인트를 OpenAPI에 bearer-required로 표기(RV4-006).
  런타임 인가는 정상이라 알려진 표현 한계로 수용.

## 다음 phase 개선점 (Phase 5 입력)

- 이미지 게시판은 본 첨부 파이프라인을 재사용하되 E-01(1개 이상 이미지) 전구간 강제 + 썸네일 그리드/라이트박스(프론트).
- 조정/orphan 정리 잡(E-02)은 설계만 존재 — 실제 스케줄드 잡 구현 시점은 인간 확인 필요(HCI).

## codex 리뷰 지적과 그 처리 결과

- 6건(high 2/med 2/low 2). high·med 전건 + low 1건 **Fixed**, low 1건(RV4-006) Accepted(known). 재검증 blocking·high 0.
- 상세: [phase-4-codex-review.md](../reviews/phase-4-codex-review.md), [phase-4-codex-resolution.md](../reviews/phase-4-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Architecture | 조정/orphan 정리 잡(E-02)은 data.md 설계만 있고 실제 스케줄드 잡 미구현. PENDING 행/고아 객체가 즉시 정리되지 않음(eventual). | 정리 잡 구현 phase/방식(주기적 태스크 vs 외부 스케줄러) 결정. | 비차단(계획된 후속) |
| HCI-2 | Other | RV4-006: OpenAPI가 optional-auth 공개 다운로드 엔드포인트를 bearer-required로 표기(FastAPI 한계). 런타임 인가는 정상. | 생성 클라이언트 영향 수용 여부 / 별도 보안스킴 분리 필요성 확인. | 비차단(known) |
| HCI-3 | Security | 업로드 크기/픽셀 상한은 설정값(이미지 10MB, 일반 25MB, 5천만 픽셀). 운영 환경 적정값 검토 필요. | prod 상한값 승인. | 비차단 |
| HCI-4 | Risk | S3StorageClient(boto3) 경로는 실 MinIO 대상이라 단위테스트 커버리지 낮음(인메모리 페이크로 로직 검증). | MinIO 통합 테스트 도입 시점 확인. | 비차단 |
