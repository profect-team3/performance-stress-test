# Performance Stress Test

이 프로젝트는 Locust를 사용하여 API 성능 테스트를 수행하는 스크립트입니다. 고객과 소유자의 행동을 시뮬레이션하여 시스템의 부하를 테스트합니다.

## 프로젝트 개요

- **고객 워크플로우**: 주소 추가, 가게 및 메뉴 조회, 장바구니에 아이템 추가, 주문 생성
- **소유자 워크플로우**: 가게 생성

## 요구사항

- Python 3.7 이상
- uv (Python 패키지 관리자)

## 설치 방법

1. uv를 설치합니다 (macOS의 경우):
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   다른 OS의 경우: [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/)를 참고하세요.

2. 프로젝트 디렉토리로 이동합니다.

3. uv를 사용하여 의존성을 설치합니다:
   ```
   uv sync
   ```

## 사용 방법

1. 프로젝트 디렉토리로 이동합니다.

2. Locust를 실행합니다 (기본 포트 8089):
   ```
   uv run locust -f locustfile.py
   ```

3. 특정 포트로 실행하려면 --web-port 옵션을 사용합니다 (예: 포트 9090):
   ```
   uv run locust -f locustfile.py --web-port 9090
   ```

4. 웹 브라우저에서 지정한 포트로 접속하여 테스트를 설정하고 실행합니다 (예: `http://localhost:9090`).

## 워크플로우 설명

### CustomerWorkflow
- `add_address`: 고객이 주소를 추가합니다.
- `get_stores_and_select_menu`: 가게 목록을 조회하고 메뉴를 선택합니다.
- `add_item_to_cart`: 장바구니에 아이템을 추가합니다.
- `create_order`: 주문을 생성합니다.

### OwnerWorkflow
- `create_store`: 소유자가 새로운 가게를 생성합니다.

## 설정

- 고객 사용자: 1-3초 사이의 대기 시간
- 소유자 사용자: 5-10초 사이의 대기 시간
- 글로벌 데이터: 고정된 가게 ID, 메뉴 ID, 가격 사용

## 기여

이슈나 풀 리퀘스트를 통해 기여해주세요.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.