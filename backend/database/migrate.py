"""기동 시 스키마를 최신 리비전까지 올린다.

지금까지는 `Base.metadata.create_all()` 이 이 일을 했다. create_all 은 없는
테이블만 만들고 이미 있는 테이블은 손대지 않는다. 그래서 모델에 컬럼이나
제약을 더해도 기존 DB 에는 영원히 반영되지 않고, 코드와 DB 가 조용히 갈라진다.
실제로 nodes 의 `ck_node_estimated_loss_nonneg` 와 reviews 의
`ck_reviews_rating_1_5` 가 그렇게 빠져 있었다 — 모델에는 있는데 DB 에는 없었다.

SQLite 한 파일짜리 앱이라 배포 훅을 따로 두지 않고 기동 때 올린다. 이미 head 면
SQL 이 한 줄도 나가지 않으므로 재기동 비용은 사실상 0 이다. Postgres 같은
공유 DB 로 옮기는 날에는 이 호출을 빼고 배포 파이프라인에서
`alembic upgrade head` 를 돌려야 한다. 여러 인스턴스가 동시에 기동하면서
같은 마이그레이션을 밀면 서로 밟는다.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.database.database import engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def upgrade_database() -> None:
    """DB 를 head 까지 올린다. 이미 최신이면 아무 일도 하지 않는다."""
    config = Config(str(ALEMBIC_INI))

    with engine.begin() as connection:
        # 이미 열린 커넥션을 넘겨 env.py 가 엔진을 새로 만들지 않게 한다.
        # SQLite 파일을 두 커넥션이 동시에 잡으면 잠금으로 막힌다.
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
