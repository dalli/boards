# 에이전트 지침서 (AGENTS.md)

이 문서는 개발 프로젝트에서 AI 에이전트가 수행해야 할 역할, 규칙, 검증 명령어를 정의하는 **범용 거버넌스 문서**입니다. 특정 언어·프레임워크·도메인에 종속되지 않으며, 어떤 개발 프로젝트에도 적용할 수 있습니다. 에이전트는 작업을 수행하기 전 반드시 이 문서를 숙지해야 합니다.

> **문서 철학**: 모든 규칙은 "약속"이 아니라 **기계가 검증 가능한 명령어**로 환원되어야 합니다. 주관적 판단("잘 됐는지 확인")이 아니라, 복붙 실행 가능한 검증 명령과 그 출력 증거로 완료를 입증합니다.

## 0. 전제 조건 및 프로젝트 선언 (Prerequisites & Project Declaration)

본 지침서는 도메인 비종속적입니다. 각 프로젝트는 자신의 환경을 아래 형태로 **선언**하며, 에이전트는 하드코딩된 가정 대신 이 선언을 참조합니다.

- **버전 관리 전제**: 이 프로젝트는 **git 저장소로 관리**되어야 합니다. (`git rev-parse --is-inside-work-tree` 가 `true`를 반환). 초기화되어 있지 않다면 자의적으로 `git init` 하지 말고 **§4 이스케이프**에 따라 인간에게 확인합니다.
- **작업 스코프 선언**: 프로젝트는 에이전트별 작업 영역(예: 모듈/디렉토리 경계)을 선언합니다. (§5 참조)
- **빌드/테스트/린트 명령 선언**: 프로젝트는 실행·테스트·린트·커버리지 명령을 선언합니다. (§2 참조) 에이전트는 명령을 임의로 추측하지 않습니다.
- **`dev` 브랜치 전제**: phase별 작업 결과는 `dev` 브랜치에 통합됩니다. (§7 참조)

> 프로젝트 선언이 누락되어 검증을 진행할 수 없으면, 추측하지 말고 **§4 이스케이프**로 인간에게 확인합니다.

### 0.1. 본 프로젝트 선언 (Board System Declaration)

이 게시판 프로젝트는 위 전제들을 다음과 같이 구체적으로 선언한다. 에이전트는 하드코딩된 가정 대신 이 선언을 참조한다.

- **버전 관리**: git 저장소. 원격은 `https://github.com/dalli/boards.git`(origin). phase 결과는 `dev` 브랜치에 통합한다(§7).
- **기술 스택**: 백엔드 Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic, DB PostgreSQL 16, 오브젝트 스토리지 MinIO(S3 호환), 이미지 처리 Pillow. 프론트 React 18 + Vite + TypeScript. 인증은 자체 구현(email+password, bcrypt, JWT, role USER/ADMIN).
- **작업 스코프 경계(§5)**: 두 개의 최상위 영역 — `backend/`(API·도메인·영속), `frontend/`(React SPA). 에이전트는 자신에게 할당된 영역 밖을 수정하지 않는다.
- **계층 규칙(§5)**: 백엔드는 `api`(라우터/검증) → `service`(도메인 로직·인가) → `repository/model`(SQLAlchemy 경유 영속) 3계층. 프레젠테이션/라우터 계층은 저장소(DB)에 직접 접근하지 않고 service를 경유한다. Raw SQL은 마이그레이션 외 지양한다.
- **공유/계약 소유권(§5.1)**: API 계약은 OpenAPI. 단일 진실 공급원(SoT)은 backend가 생성하는 `backend/openapi.json`이며 `owner_role=backend`. frontend는 생성된 TS 클라이언트만 소비하고 수동 수정하지 않는다(생성물 드리프트 제어 §5.1).

> 위 선언 슬롯 외 §3·§4·§6의 거버넌스 규칙 본문(완료의 정의, 이스케이프, phase 게이트)은 보호 대상이며 임의로 약화하지 않는다.

## 1. 에이전트 역할 및 책임 (Agent Roles)
계획 단계의 완벽성을 기하기 위해 기획 역할은 다중 모델 구조로 분리하여 운영합니다.
- **Primary Planner (초안 설계)**: 요구사항을 분석하고 아키텍처와 작업 단위(phase)로 분해된 최초의 계획을 작성합니다. **모든 Cross-Reviewer의 리뷰를 취합(synthesis)하는 유일한 주체**입니다.
- **Cross-Reviewers (교차 검증자)**: Primary Planner의 계획을 보안, 아키텍처 제약, 엣지 케이스 관점에서 비판적으로 교차 검토합니다. 각 리뷰어는 **서로 독립된 컨텍스트/세션에서 실행**되며, 다른 리뷰어의 산출물을 입력으로 받지 않습니다(§3.1 참조).
- **Implementor (구현)**: 승인된 계획에 따라 phase 단위로 코드를 작성합니다. 할당된 스코프 경계를 엄격히 지킵니다.
- **Tester/Reviewer (코드 검증)**: 코드를 병합하기 전 린터, 테스트, 보안 결함을 기계적으로 검증합니다.

## 2. 빌드 및 테스트 명령 (Build & Test Commands)
코드를 수정하거나 기능을 추가한 후, 에이전트는 스스로 프로젝트가 선언한 명령을 실행하여 결과를 확인해야 합니다. 명령은 프로젝트 스택에 따라 다르므로 **프로젝트 선언(§0)** 을 참조합니다.

선언해야 할 명령은 아래 **플레이스홀더 이름**으로 본 문서 전체(§3.3, §6.2 등)에서 일관되게 참조합니다. 각 프로젝트는 이 플레이스홀더에 자신의 실제 명령을 바인딩합니다.

| 목적 | 플레이스홀더 | 예시(Node) | 예시(Python) |
| --- | --- | --- | --- |
| 실행 | `<PROJECT_DECLARED_RUN_CMD>` | `npm run dev` | `uvicorn app:app` |
| 테스트 | `<PROJECT_DECLARED_TEST_CMD>` | `npm test` | `pytest` |
| 린트/정적분석 | `<PROJECT_DECLARED_LINT_CMD>` | `npm run lint` | `ruff check` |
| 커버리지 게이트 | `<PROJECT_DECLARED_TEST_COVERAGE_CMD>` | `npm run test:coverage` | `pytest --cov --cov-fail-under=80` |

> 위 예시 명령(`npm …`, `pytest …` 등)은 **비규범적 예시**이며, 선언된 명령이 없을 때 이를 기본값으로 사용해서는 안 됩니다.

> **본 프로젝트 바인딩(§0.1)**: 이 게시판 프로젝트는 영역별로 아래 명령을 바인딩한다. 에이전트는 자신이 작업 중인 영역(backend/frontend)의 명령을 실행한다.
>
> | 플레이스홀더 | backend (`backend/`) | frontend (`frontend/`) |
> | --- | --- | --- |
> | `<PROJECT_DECLARED_RUN_CMD>` | `uvicorn app.main:app --reload` | `npm run dev` |
> | `<PROJECT_DECLARED_TEST_CMD>` | `pytest` | `npm test` |
> | `<PROJECT_DECLARED_LINT_CMD>` | `ruff check . && mypy app` | `npm run lint` |
> | `<PROJECT_DECLARED_TEST_COVERAGE_CMD>` | `pytest --cov=app --cov-fail-under=80` | `npm run test:coverage` |
>
> `§3.2`의 스코프 검증에서 `SCOPE`는 작업 영역에 따라 `backend/` 또는 `frontend/`로 설정한다.

> **명령어 존재 확인 (필수 선행 단계)**: 선언된 명령이 실제로 실행 가능한지 먼저 확인합니다. 정의되어 있지 않으면 명령을 임의로 추측·대체하지 말고 **§4 이스케이프**로 인간에게 확인합니다.

## 3. 완료의 정의 (Definition of Done)
에이전트는 자신이 맡은 역할과 단계에 따라 다음의 기계적이고 객관적인 완료 기준을 모두 충족해야 합니다. 각 단계의 완료가 확인되지 않으면 다음 단계로 넘어갈 수 없습니다.

### 3.1. 계획 완료 (Plan Completed)
코드를 수정하기 전, 다음의 **다중 모델 교차 검증 및 인간 승인 절차**를 모두 충족해야만 구현 단계로 넘어갈 수 있습니다.

1. **최초 초안 작성 (Drafting)**: Primary Planner가 요구사항, 수락 기준(Acceptance Criteria), §3.4의 아키텍처 산출물, §6의 phase 분해를 포함한 계획 초안을 작성합니다.
2. **독립적 교차 검증 (Independent Cross-Review)**: 초안은 최소 1개 이상의 다른 모델 기반 Cross-Reviewer에게 전달되어 검토를 받습니다.
   - **독립성 보장 방식**: 각 Cross-Reviewer는 Primary Planner와 **다른 모델 또는 독립 실행 주체**여야 하며, 별도의 서브에이전트/세션으로 호출합니다. 입력으로는 *계획 초안만* 받고, 다른 리뷰어의 결과를 컨텍스트에 포함하지 않습니다.
   - **감사 가능성(Auditability)**: 각 리뷰는 `plan.md`(또는 계획 문서)에 `reviewer_id`, `model_id`, `session_id`, **검토 대상 draft의 해시(예: SHA-256)**, 검토 시각을 기록합니다. **동일 agent/session/model 조합의 자기 검토는 무효**입니다.
   - **신선도(Freshness) 바인딩**: 각 리뷰는 검토 시점 draft 해시와 함께 저장되며, **draft 내용이 바뀌면 기존 리뷰는 자동 무효화**됩니다. 구버전 draft 리뷰를 재활용할 수 없습니다.
   - **단방향 정보 흐름**: 리뷰 결과는 오직 Primary Planner에게만 모입니다. 리뷰어끼리는 서로의 결과를 보지 못합니다(group-think 방지).
3. **피드백 통합 및 파일 저장 (Synthesis & Save)**: Primary Planner는 지적 사항을 분석·반영하여 최종 계획서를 작성하고 **계획 문서(`plan.md`)로 저장**합니다.
   - **이의 처리 명시(Adjudication)**: 각 지적 사항을 **Accepted / Rejected / Escalated** 중 하나로 분류해 기록하며, **Rejected 항목은 근거를 반드시 명시**합니다(보안·아키텍처 지적이 조용히 사라지는 것 방지).
   - **차단성 지적의 우선권**: Security 또는 architecture blocking 지적은 인간 승인자가 명시적으로 판정하기 전까지 구현으로 넘어갈 수 없습니다.
4. **인간 검토 및 승인 (Human Review & Judgment)**: 저장된 계획 문서에 대해 인간 개발자에게 검토를 요청하고 대기 모드로 전환(Plan Mode)합니다.
   - **수정 및 추가 판단**: 인간 피드백을 반영해 계획 문서를 수정합니다.
   - **구현 단계 승인**: 인간 개발자의 **명시적 승인 전까지는 절대 구현 단계로 넘어가서는 안 됩니다.**

### 3.2. 구현 완료 (Implementation Completed)
Implementor는 코드 작성을 마친 후 다음을 **검증 명령**으로 입증합니다.

1. **스펙 충족**: 승인된 계획의 수락 기준과 아키텍처 제약을 정확히 반영합니다.
   - 검증: 각 수락 기준 체크박스를 **대응 코드/테스트 경로와 1:1 매핑한 추적표**로 제시합니다. 미매핑 기준이 하나라도 있으면 미완료입니다.
   - 보조 점검 (계획 문서에 미충족 체크박스가 남아 있으면 출력 — **비어 있어야** 완료):
     ```bash
     grep -nE '^\s*- \[ \]' plan.md && echo "❌ 미충족 수락 기준 존재" || echo "✅ 모든 수락 기준 체크 완료"
     ```
2. **임시 코드 제거**: 커밋 대상 Diff에 `TODO`, `FIXME`, `HACK` 등 임시 주석·데드 코드가 없어야 합니다.
   - 검증 명령 (스테이징된 변경의 **추가된 본문 줄만** 검사. 파일명에 `TODO`가 든 신규 파일의 `+++` diff 헤더를 오탐하지 않도록 `awk` 헝크 필터 사용. 매칭이 없어야 통과):
     ```bash
     git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "❌ git 저장소 아님 → §4 이스케이프"; exit 2; }
     diff_output=$(git diff --cached --unified=0 --no-ext-diff) || { echo "❌ git diff 실패 → §4 이스케이프"; exit 2; }
     if printf '%s\n' "$diff_output" | awk '
       /^diff --git / { in_hunk = 0 }
       /^@@ /         { in_hunk = 1; next }
       in_hunk && /^\+/ && !/^\+\+\+ / && /(TODO|FIXME|HACK|XXX)/ { print NR ":" $0; found = 1 }
       END { exit(found ? 0 : 1) }'; then
       echo "❌ 임시 코드 발견"; else echo "✅ 임시 코드 없음"; fi
     ```
3. **영역 준수**: 할당된 스코프를 위반한 파일 수정이 없어야 합니다.
   - 검증 명령 (`SCOPE`를 자신의 할당 스코프로 설정. 스코프 밖 경로가 출력되면 **위반**. `--name-status -M`으로 rename의 *양쪽 경로*를 모두 검사하여, 스코프 밖 파일을 스코프 안으로 옮기며 삭제를 숨기는 사각지대를 막음):
     ```bash
     SCOPE='<PROJECT_DECLARED_SCOPE_PREFIX>'   # ← 프로젝트 선언(§0)의 할당 스코프로 교체
     git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "❌ git 저장소 아님 → §4 이스케이프"; exit 2; }
     name_status=$(git diff --cached --name-status -M) || { echo "❌ git diff 실패 → §4 이스케이프"; exit 2; }
     violations=$(printf '%s\n' "$name_status" | awk -v scope="$SCOPE" '
       $1 ~ /^[RC][0-9]+$/ { if (index($2, scope) != 1) print $2; if (index($3, scope) != 1) print $3; next }
       NF >= 2 && index($2, scope) != 1 { print $2 }')
     [ -z "$violations" ] && echo "✅ 스코프 준수" || { echo "❌ 스코프 위반:"; echo "$violations"; }
     ```
   - 공유/계약 파일(§5.1 참조) 변경이 포함된 경우, 그 변경이 계획 문서에 명시·승인되었는지 추가 확인합니다.

### 3.3. 테스트 완료 (Test Completed)
Tester/Reviewer는 다음을 만족해야 합니다.
1. **결정론적 테스트 통과**: 선언된 `<PROJECT_DECLARED_TEST_CMD>` 결과 실패(Fail)가 0건이어야 합니다.
2. **정적 분석 통과**: 선언된 `<PROJECT_DECLARED_LINT_CMD>` 결과 경고·타입 에러가 0건이어야 합니다.
3. **신규 로직의 테스트 존재**: "실패 0건"만으로는 테스트 0개로도 통과할 수 있으므로, **이번 변경의 신규/변경 로직에는 대응 테스트가 반드시 존재**해야 합니다.
   - 커버리지 하한선의 **기본값은 신규/변경 코드 라인 기준 80%** 이며, 이는 권장이 아니라 **강제 기준**입니다. 낮춰야 할 합당한 사유가 있을 때만 계획 문서에 명시적으로 예외 기록합니다.
   - 검증은 정보성 리포트가 아니라 **종료 코드로 통과/실패가 판정**되어야 합니다. 임계값을 테스트 설정에 박아 미달 시 0이 아닌 종료 코드로 실패하는 `test:coverage` 명령으로 게이트합니다.
     ```bash
     # 프로젝트가 선언한 커버리지 명령을 실행. 미달 시 non-zero exit.
     <PROJECT_DECLARED_TEST_COVERAGE_CMD> || { echo "❌ 커버리지 기준 미달 → §4 이스케이프"; exit 1; }
     ```
4. **증거(Evidence) 제시**: 테스트 통과 로그, 린트 결과, 커버리지 요약을 **실제 콘솔 출력 그대로** 제출합니다("통과했다"는 서술 금지).

### 3.4. 계획 단계 아키텍처 산출물 (Planning Architecture Artifacts)
계획 단계에서는 코드 작성 전 다음 산출물을 **모두 작성**해야 하며, 모든 문서는 **`docs/` 폴더**에 둡니다. 다이어그램은 **mermaid**로 작성합니다.

1. **시스템 아키텍처 (System Architecture)**: 전체 컴포넌트와 그 관계를 mermaid로 작성합니다. (`docs/architecture/system.md`)
2. **핵심 시퀀스 다이어그램 (Sequence Diagrams)**: 핵심 유스케이스/플로우에 대해 mermaid `sequenceDiagram`을 작성합니다. (`docs/architecture/sequences/*.md`)
3. **데이터 아키텍처 (Data Architecture)**: 어떤 데이터가 **어떤 저장소(DB/캐시/큐/오브젝트 스토리지 등)에 저장되는지** 매핑을 작성합니다. 엔티티-저장소 매핑과 보존/일관성 특성을 포함합니다. (`docs/architecture/data.md`)
4. **DB 스키마 정의서 (Database Schema Definition)**: 데이터 아키텍처가 *저장소 선택*이라면, 스키마 정의서는 *구체적 구조*입니다. 각 영속 저장소에 대해 **테이블/컬렉션·필드명·타입·제약(PK/FK/UNIQUE/NOT NULL)·인덱스·엔티티 간 관계**를 정의합니다. 관계는 mermaid `erDiagram`으로 시각화하고, 마이그레이션/버전 전략을 함께 기술합니다. (`docs/architecture/db-schema.md`)
   - **조건부 면제**: 영속 데이터 저장소가 없는 프로젝트(예: 순수 CLI 도구, 라이브러리, 정적 사이트)는 이 산출물 대신 `docs/architecture/db-schema.md`에 **"해당 없음(N/A)"과 그 근거**를 기록합니다(누락과 면제를 구분하기 위해 문서 자체는 존재해야 함).
5. **보안 아키텍처 (Security Architecture)**: 인증/인가, 신뢰 경계, 민감 데이터 흐름, 위협 모델 요약을 작성합니다. (`docs/architecture/security.md`)
6. **배포 아키텍처 (Deployment Architecture)**: 런타임 토폴로지, 환경(dev/staging/prod), CI/CD, 롤백 전략을 작성합니다. (`docs/architecture/deployment.md`)
7. **ADR (Architecture Decision Records)**: 위 각 아키텍처의 **주요 결정마다 ADR 문서**를 작성합니다. ADR은 컨텍스트·결정·대안·결과를 담으며 `docs/adr/NNNN-title.md` 형식으로 번호를 매깁니다.

   - 산출물 존재 점검 (모든 항목이 존재해야 통과. zsh `nomatch`로 glob 확장 에러가 새지 않도록 `ls *.md` 대신 `find` 사용):
     ```bash
     missing=""
     for f in docs/architecture/system.md docs/architecture/data.md docs/architecture/db-schema.md \
              docs/architecture/security.md docs/architecture/deployment.md; do
       [ -f "$f" ] || missing="${missing:+$missing }$f"
     done
     find docs/architecture/sequences -type f -name '*.md' -print -quit 2>/dev/null | grep -q . \
       || missing="${missing:+$missing }docs/architecture/sequences/*.md"
     find docs/adr -type f -name '*.md' -print -quit 2>/dev/null | grep -q . \
       || missing="${missing:+$missing }docs/adr/*.md"
     [ -z "$missing" ] && echo "✅ 아키텍처 산출물 완비" || { echo "❌ 누락:$missing → §4 이스케이프"; exit 1; }
     ```
   - mermaid 블록 존재 점검 (시스템 문서 + **모든** 시퀀스 문서에 mermaid가 있어야 함. `grep -rlq`는 "하나라도 있으면 통과"하므로 전수 검사로 교체):
     ```bash
     grep -q '```mermaid' docs/architecture/system.md \
       && echo "✅ system mermaid 존재" || { echo "❌ system mermaid 누락"; exit 1; }
     sequence_missing=$(find docs/architecture/sequences -type f -name '*.md' \
       ! -exec grep -q '```mermaid' {} \; -print 2>/dev/null)
     [ -z "$sequence_missing" ] && echo "✅ 모든 시퀀스 mermaid 존재" \
       || { echo "❌ mermaid 누락 시퀀스 문서:"; echo "$sequence_missing"; exit 1; }
     ```
   - DB 스키마 점검 (영속 저장소가 있으면 `erDiagram`이 있어야 하고, 없으면 N/A 근거가 있어야 함. 둘 중 하나는 충족해야 통과):
     ```bash
     if grep -q 'erDiagram' docs/architecture/db-schema.md; then
       echo "✅ DB 스키마 erDiagram 존재"
     elif grep -qiE 'N/A|해당 없음' docs/architecture/db-schema.md; then
       echo "✅ DB 스키마 면제(N/A) 근거 기재됨"
     else
       echo "❌ db-schema.md에 erDiagram도 N/A 근거도 없음 → §4 이스케이프"; exit 1
     fi
     ```

## 4. 에스컬레이션 및 이스케이프 밸브 (Escalation Rules)
에이전트는 다음 상황에 직면하면 자의적으로 추측하지 말고 **즉시 작업을 중단하고 인간 개발자에게 질문**해야 합니다.
1. **무한 루프 방지**: 동일한 테스트 실패나 빌드 에러가 3번 이상 반복되어 해결되지 않을 때.
2. **권한 및 보안**: 시크릿/자격증명(`.env` 등), DB 마이그레이션 핵심 설정, CI/CD 파이프라인 설정을 수정해야 할 때.
3. **모호성**: 권한 처리, 암호화 방식 등 명확히 정의되지 않은 요구사항이나 승인된 계획과 어긋나는 상황을 만났을 때.
4. **환경 미비**: 저장소가 git으로 초기화되어 있지 않거나(§0), 선언된 빌드/테스트 명령이 실제로 존재하지 않을 때. 임의로 초기화하거나 명령을 지어내지 말 것.
5. **보호 파일 변경**: 본 `AGENTS.md`, 승인된 계획 문서의 수락 기준, 또는 위 2항의 보호 대상 파일을 수정해야 할 때.

**에스컬레이션 해소 규칙 (교착·자기승인 방지)**: 막연히 "인간에게 질문"으로 끝나면 인간 부재·이해상충 시 무한 대기하거나, 검토 대상 에이전트가 조정자를 겸하면 우회 자기승인이 발생합니다.
- 에스컬레이션은 **지정된 인간 승인자(owner)만** 해소할 수 있습니다.
- 승인자가 **합의된 시한(기본 24시간) 내 응답하지 않으면** 작업 상태를 `BLOCKED`로 기록하고 중단합니다(임의 진행 금지).
- **에이전트·서브에이전트, 또는 검토 대상 산출물의 작성자는 인간 승인자를 대체할 수 없습니다.**

## 5. 스코핑 및 코드 소유권 (Scoping & Ownership)
에이전트는 현재 할당된 작업 영역의 경계를 넘어서는 코드를 수정해서는 안 됩니다. 경계는 프로젝트 선언(§0)을 따릅니다. (예: 계층/모듈/디렉토리 단위)

- 프로젝트가 데이터 계층 또는 프레젠테이션 계층 같은 **계층 구조를 선언한 경우에만**, 계층 간 접근 규칙과 허용된 통신 방식(예: ORM/Typed SDK 경유, Raw 쿼리 지양; 프레젠테이션 계층의 저장소 직접 접근 금지)을 프로젝트 선언에 명시하고 그에 따릅니다.
- 선언된 계층 경계가 없으면(예: CLI 도구, 라이브러리, 정적 사이트, 인프라 저장소 등) 에이전트는 임의로 계층 구조를 가정하지 않습니다.

### 5.1. 공유/계약 코드의 단일 소유권 (Single Ownership of Shared Contracts)
경계 사이에 공유되는 **계약**(API 스펙/스키마, 공유 타입 정의 등)은 소유권이 불분명하면 "둘 다 남의 영역이라 아무도 못 고치는" 교착(deadlock)이 발생합니다.

- **계약의 단일 소유자(owner)를 계획 단계에서 명시**합니다. 계약의 단일 진실 공급원(Single Source of Truth)은 그 소유자가 정의합니다.
- **소비 측은 계약을 소비(consume)만** 하며, 생성된 타입/클라이언트를 사용합니다.
- **계약 변경은 반드시 계획 문서를 통해서만** 이뤄집니다. 변경은 계획 단계에서 합의되고, 소비 측은 승인된 변경에 맞춰 갱신합니다.
- **기계 검증 가능한 소유권 기록**: 계약마다 계획 문서에 `contract_id`, `source_of_truth_path`, `owner_role`, `owner_human_approver`, `producer_paths`, `consumer_paths`, `regen_command`, `drift_check_command`를 표로 기록합니다.
  - 제공 측이 없거나 외부 계약인 경우 `owner_role`을 `external` 또는 `shared-governance`로 표시하고, 변경 가능 범위와 승인자를 명시합니다.
  - **소유자가 하나로 결정되지 않는 계약 변경**(제공 측 부재, 다중 제공자, peer 소유 스키마 등)은 §4 이스케이프로 `Escalated` 상태가 되며 그 전까지 구현할 수 없습니다.
- **생성물 드리프트 제어**: **생성 파일은 수동 수정 금지**이며, 소비 측 diff에 생성 파일이 포함되면 `regen_command` 실행 증거와 `drift_check_command` 통과 증거를 함께 제출합니다.

## 6. Phase 분해 및 구현 워크플로우 (Phase Workflow)
계획과 구현은 **phase 단위**로 진행합니다. 큰 작업을 한 번에 처리하지 않고, 검증 가능한 작은 단위로 나눕니다.

### 6.1. 계획 단계의 Phase 분해
계획 문서에는 **각 phase에서 어떤 작업을 진행할지**를 명시해야 합니다. 각 phase 항목은 다음을 포함합니다.
- phase 번호와 목표(무엇을 완성하는가)
- 포함 작업 목록과 산출물
- 해당 phase의 수락 기준(Acceptance Criteria)
- 의존성(선행 phase)

### 6.2. Phase별 구현 절차 (닫힌 게이트)
구현에 들어가면 각 phase를 다음 순서로 진행하며, **모든 게이트를 통과해야 해당 phase가 종료**됩니다.

1. **구현 (Implement)**: 해당 phase의 작업을 구현합니다. 할당 스코프(§5)를 준수합니다.
2. **테스트 (Test)**: 해당 phase의 구현에 대해 §3.3의 테스트·린트·커버리지 게이트를 모두 통과합니다. **구현과 테스트를 모두 마쳐야** 다음 단계로 갑니다.
3. **codex 플러그인 리뷰 (Review)**: 해당 phase의 작업 결과를 **codex 플러그인으로 리뷰**받습니다. 리뷰 결과는 `docs/reviews/phase-<N>-codex-review.md`에 저장하며, 각 지적은 **고유 ID, severity, 파일/라인, 원문 요약**을 포함해야 합니다.
4. **리뷰 지적 수정 (Fix)**: 리뷰에서 지적된 문제는 **모두 수정 완료**해야 합니다. "모두 수정했다"는 자기 신고로는 검증되지 않으므로, 감사 추적을 남깁니다.
   - 각 지적 ID별 처리 상태를 `docs/reviews/phase-<N>-codex-resolution.md`에 **Fixed / Rejected / Escalated**로 기록합니다. `Fixed`는 대응 커밋/파일/테스트 증거를 연결합니다.
   - **Rejected 또는 Escalated 항목은 인간 승인자 판정 전까지 phase 종료 불가**입니다.
   - 수정 후 **codex 리뷰를 재실행**하여 미해결 blocking finding이 없다는 출력 증거를 첨부합니다. **미해결 지적이 하나라도 남아 있으면 phase는 끝나지 않습니다.**
5. **회고 작성 (Retrospective)**: 아래 §6.3에 따라 회고를 작성합니다.
6. **dev 브랜치 통합 (Commit & Push)**: 해당 phase의 작업 결과를 **`dev` 브랜치에 commit & push** 합니다. 커밋은 §7 규칙을 따릅니다.

   - phase 종료 게이트 점검 예시 (각 게이트는 실패 시 0이 아닌 종료 코드로 멈춰야 함):
     ```bash
     N=1   # phase 번호로 치환
     # 1) 테스트/커버리지 게이트
     <PROJECT_DECLARED_TEST_COVERAGE_CMD> || { echo "❌ 테스트/커버리지 미통과"; exit 1; }
     # 2) codex 리뷰·처리 기록 존재 (§6.2-3,4)
     [ -f "docs/reviews/phase-${N}-codex-review.md" ] && [ -f "docs/reviews/phase-${N}-codex-resolution.md" ] \
       && echo "✅ 리뷰·처리 기록 존재" || { echo "❌ phase $N 리뷰/처리 기록 누락 → §6.2"; exit 1; }
     # 3) 회고 문서 존재 (zsh nomatch 회피 위해 find 사용)
     find docs/retrospectives -type f -name "phase-${N}-*.md" -print -quit 2>/dev/null | grep -q . \
       && echo "✅ 회고 존재" || { echo "❌ phase $N 회고 누락 → §6.3"; exit 1; }
     # 4) 현재 브랜치가 dev 인지 확인 (detached HEAD는 HEAD를 반환하므로 symbolic-ref로 판정 — warn-only 금지)
     git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "❌ git 저장소 아님 → §4 이스케이프"; exit 2; }
     current_branch=$(git symbolic-ref --quiet --short HEAD) || { echo "❌ detached HEAD 상태 → §7 확인"; exit 1; }
     [ "$current_branch" = "dev" ] && echo "✅ dev 브랜치" \
       || { echo "❌ dev 브랜치가 아님: $current_branch → §7 확인"; exit 1; }
     ```

### 6.3. Phase 회고 (Retrospective)
각 phase가 끝나면 **회고**를 작성합니다. 회고 문서는 `docs/retrospectives/phase-<N>-<slug>.md`에 둡니다. 회고에는 다음을 포함합니다.
- 한 일과 결과(완료된 수락 기준)
- 잘된 점 / 어려웠던 점 / 다음 phase에 반영할 개선점
- codex 리뷰 지적과 그 처리 결과
- **인간이 확인해야 할 항목(Human Check Items)**: 에이전트가 자의로 판단하면 안 되는 사항(아키텍처 트레이드오프, 보안 결정, 범위 변경, 미해결 리스크 등)을 인간 확인용으로 명시합니다.
  - 회고에는 정확히 `## Human Check Items` 제목을 포함해야 하며, 그 아래에 표로 `ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부`를 기록합니다.
  - **이 섹션은 비어 있으면 안 됩니다.** 확인 항목이 없다고 판단하는 경우에도 `ID=HCI-0`, `분류=None`, `확인 필요 사항=없음`, `근거=<보안/아키텍처/범위 변경/미해결 리뷰 지적이 없음을 확인한 검증 증거>` 행을 적어야 합니다.
  - **단, Rejected/Escalated 리뷰 지적, 범위 변경, 보호 파일 변경, 보안/아키텍처 트레이드오프가 하나라도 있으면 `없음(HCI-0)`을 사용할 수 없습니다.** 해당 항목을 반드시 행으로 나열합니다.

## 7. 커밋 및 브랜치 규칙 (Commit & Branch Rules)
- **원자적 커밋**: 하나의 커밋은 하나의 논리적 변경 단위만 담습니다. 무관한 변경을 섞지 않습니다.
- **커밋 메시지**: 명령형 현재 시제로 변경의 *이유*를 설명합니다. (예: `fix: 입력 검증에서 누락된 경계값 처리 추가`)
- **검증 통과 후 커밋**: §3.2, §3.3의 모든 검증 명령이 통과하고 증거가 확보된 후에만 커밋합니다.
- **phase 단위 통합**: 각 phase 종료 시 결과를 **`dev` 브랜치에 commit & push** 합니다(§6.2-6).
- **보호 파일**: `AGENTS.md`, 승인된 계획 문서의 수락 기준, 시크릿/CI 설정은 §4에 따라 인간 승인 없이 커밋하지 않습니다.
- **자동 커밋·푸시 금지(예외)**: 일반적으로 인간이 명시적으로 요청하기 전까지 임의 커밋/푸시하지 않습니다. 단, **§6.2의 phase 종료 절차에 따른 `dev` 커밋·푸시는 승인된 워크플로우의 일부**로 허용됩니다.
