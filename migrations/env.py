"""Alembic 실행 환경.

접속처는 여기서 정하지 않는다. 앱이 쓰는 backend.database.database 를 그대로
가져다 쓴다. 주소를 두 군데에 적어 두면 언젠가 어긋나고, 그때는 앱과
마이그레이션이 서로 다른 DB 를 보게 된다.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# alembic 은 레포 루트가 아닌 곳에서도 실행될 수 있다. backend 를 import 하려면
# 루트가 sys.path 에 있어야 한다.
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.database import (  # noqa: E402  pylint: disable=wrong-import-position
    DATABASE_URL,
)
from backend.database.models import (  # noqa: E402  pylint: disable=wrong-import-position
    Base,
)

config = context.config

# 호출자가 주소를 명시했으면 그것을 존중한다. 테스트가 임시 DB 를 지정하거나,
# 일회성으로 다른 DB 에 돌릴 때 필요하다. 예전에는 무조건 덮어써서 어떤
# 주소를 넘겨도 앱 DB 로 흘러갔다 — 테스트가 실제 DB 를 건드렸다.
# 지정이 없으면 앱이 쓰는 주소를 그대로 가져온다. 주소를 두 군데 적어 두면
# 언젠가 어긋나고, 그때는 앱과 마이그레이션이 다른 DB 를 보게 된다.
# %는 configparser 의 보간 문자라 이스케이프해야 한다 (경로에 % 가 있을 수 있다).
_configured_url = config.get_main_option("sqlalchemy.url", "")
DB_URL = _configured_url or DATABASE_URL
if not _configured_url:
    config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))

if config.config_file_name is not None:
    # disable_existing_loggers 기본값(True)은 이미 만들어진 로거를 전부 끈다.
    # 앱 안에서 마이그레이션을 돌리면 앱 로거가 조용히 죽는다 — 실제로
    # graph_store 의 경고 로그가 사라져 테스트가 순서에 따라 실패했다.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# SQLite 는 ALTER TABLE 이 거의 없다. batch 모드가 임시 테이블을 만들어
# 복사·교체하는 식으로 대신한다. 컬럼 삭제·타입 변경·CHECK 추가에 필수다.
RENDER_AS_BATCH = DB_URL.startswith("sqlite")


def run_migrations_offline() -> None:
    """SQL 파일만 뽑는 오프라인 모드 (`alembic upgrade head --sql`)."""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=RENDER_AS_BATCH,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """실제 DB 에 붙어서 실행하는 온라인 모드."""
    # FastAPI 기동 중 프로그램적으로 부를 때는 이미 열린 커넥션을 넘겨받는다.
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    if hasattr(connectable, "connect"):
        with connectable.connect() as connection:
            _run(connection)
    else:  # 이미 Connection 인 경우
        _run(connectable)


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=RENDER_AS_BATCH,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
