"""마이그레이션 회귀 테스트.

`create_all` 은 없는 테이블만 만들고 있는 테이블은 손대지 않는다. 그래서
모델에 컬럼이나 제약을 더해도 배포된 DB 에는 영원히 반영되지 않고, 코드와
DB 가 조용히 갈라진다. 실제로 nodes/reviews 의 CHECK 제약 두 개가 그렇게
빠져 있었다.

여기서 고정하는 것:
  1. 모델과 마이그레이션이 어긋나면 CI 가 잡는다 (드리프트 재발 방지)
  2. 신규 DB 든 create_all 로 만들어진 기존 DB 든 upgrade 한 줄로 끝난다
  3. batch 마이그레이션이 데이터를 잃지 않는다
"""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

from backend.database.models import Base, Review

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _config(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture(name="db_url")
def fixture_db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


class TestFreshDatabase:
    def test_upgrade_creates_every_table(self, db_url):
        command.upgrade(_config(db_url), "head")
        tables = set(sa.inspect(sa.create_engine(db_url)).get_table_names())
        assert {"users", "stores", "reply_samples", "reviews"} <= tables

    def test_ontology_tables_are_gone(self, db_url):
        """b7c4e9f21a08 이 nodes·edges 를 지운다. 베이스라인이 만든 뒤 지운다."""
        command.upgrade(_config(db_url), "head")
        tables = set(sa.inspect(sa.create_engine(db_url)).get_table_names())
        assert "nodes" not in tables
        assert "edges" not in tables

    def test_upgrade_is_idempotent(self, db_url):
        """이미 head 면 두 번 돌려도 아무 일도 없어야 한다. 기동 때마다 돈다."""
        command.upgrade(_config(db_url), "head")
        command.upgrade(_config(db_url), "head")


class TestNoModelDrift:
    """모델을 고치고 마이그레이션을 안 만들면 여기서 걸린다."""

    def test_models_match_migrations(self, db_url):
        command.upgrade(_config(db_url), "head")
        engine = sa.create_engine(db_url)
        with engine.connect() as conn:
            diff = compare_metadata(
                MigrationContext.configure(conn), Base.metadata,
            )
        assert diff == [], (
            "모델과 마이그레이션이 어긋납니다. "
            "`alembic revision --autogenerate -m '...'` 로 리비전을 만드세요.\n"
            f"차이: {diff}"
        )


class TestLegacyDatabase:
    """create_all 로 만들어진 기존 DB 도 그대로 받아야 한다."""

    def test_upgrade_absorbs_create_all_schema(self, db_url):
        engine = sa.create_engine(db_url)
        Base.metadata.create_all(engine)   # 옛 방식
        command.upgrade(_config(db_url), "head")
        version = sa.inspect(engine).get_table_names()
        assert "alembic_version" in version

    def test_batch_migration_preserves_data(self, db_url):
        """CHECK 제약 추가는 테이블을 새로 만들어 옮긴다. 데이터가 남아야 한다."""
        engine = sa.create_engine(db_url)
        Base.metadata.create_all(engine)
        with Session(engine) as s:
            s.add_all([
                Review(source="coupang", rating=5, body="맛있어요"),
                Review(source="naver", rating=2, body="배송이 늦었어요", severity=0.8),
            ])
            s.commit()

        command.upgrade(_config(db_url), "head")

        with Session(engine) as s:
            bodies = {r.body for r in s.query(Review).all()}
            assert bodies == {"맛있어요", "배송이 늦었어요"}
            # 옮겨진 테이블에 컬럼 값이 그대로 남아야 한다.
            naver = s.query(Review).filter_by(source="naver").one()
            assert naver.severity == 0.8


class TestConstraintsAreEnforced:
    """모델에만 있고 DB 에는 없던 제약이 실제로 걸리는지."""

    @pytest.fixture(name="engine")
    def fixture_engine(self, db_url):
        command.upgrade(_config(db_url), "head")
        return sa.create_engine(db_url)

    @pytest.mark.parametrize("table,names", [
        ("reviews", {"ck_reviews_rating_1_5"}),
        ("reply_samples", {"ck_reply_samples_rating_1_5", "ck_reply_samples_origin"}),
    ])
    def test_check_constraints_exist(self, engine, table, names):
        found = {
            c["name"]
            for c in sa.inspect(engine).get_check_constraints(table)
            if c.get("name")
        }
        assert names <= found

    def test_rating_out_of_range_rejected(self, engine):
        with engine.begin() as conn:
            with pytest.raises(sa.exc.IntegrityError):
                conn.execute(sa.text(
                    "INSERT INTO reviews (source,rating,body,severity,ingested_at) "
                    "VALUES ('x',9,'b',0,'2026-01-01')"
                ))

    def test_unknown_origin_rejected(self, engine):
        """origin 은 onboarding/generated/edited 셋뿐이다."""
        with engine.begin() as conn:
            with pytest.raises(sa.exc.IntegrityError):
                conn.execute(sa.text(
                    "INSERT INTO reply_samples "
                    "(store_id,origin,review_body,rating,was_edited,created_at) "
                    "VALUES (1,'bogus','b',5,0,'2026-01-01')"
                ))


class TestRevisionChain:
    def test_single_head(self):
        """head 가 둘이면 브랜치가 갈라진 것이고 upgrade 가 실패한다."""
        script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
        assert len(script.get_heads()) == 1

    def test_revisions_above_baseline_downgrade(self, db_url):
        """baseline 위 리비전은 왕복할 수 있어야 한다.

        baseline 자체는 되돌리지 않는다 (TestBaselineDowngradeIsRefused 참고).
        """
        cfg = _config(db_url)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "d0effa13eb85")
        command.upgrade(cfg, "head")


class TestBaselineDowngradeIsRefused:
    """baseline downgrade 가 기존 DB 를 날리던 버그의 회귀 테스트.

    upgrade() 는 create_all 로 이미 만들어진 테이블을 건너뛴다. 그런데 예전
    downgrade() 는 그 테이블까지 drop 해서, 기존 DB 에서 upgrade 후
    downgrade 하면 이 리비전과 무관한 nodes·reviews·edges 가 사라졌다.
    """

    def test_downgrade_to_base_is_refused(self, db_url):
        cfg = _config(db_url)
        command.upgrade(cfg, "head")
        with pytest.raises(NotImplementedError):
            command.downgrade(cfg, "base")

    def test_legacy_data_survives_downgrade_attempt(self, db_url):
        engine = sa.create_engine(db_url)
        Base.metadata.create_all(engine)          # 옛 create_all DB
        with Session(engine) as s:
            s.add(Review(source="coupang", rating=5, body="소중한 데이터"))
            s.commit()

        cfg = _config(db_url)
        command.upgrade(cfg, "head")
        with pytest.raises(NotImplementedError):
            command.downgrade(cfg, "base")

        with Session(sa.create_engine(db_url)) as s:
            assert [r.body for r in s.query(Review).all()] == ["소중한 데이터"]


class TestStoreNameIsUnique:
    """이관을 원자적으로 1회로 만드는 제약."""

    def test_duplicate_store_name_rejected(self, db_url):
        command.upgrade(_config(db_url), "head")
        engine = sa.create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "INSERT INTO users (id, kakao_id, created_at, last_login_at) "
                "VALUES (1,'a','2026-01-01','2026-01-01'), "
                "(2,'b','2026-01-01','2026-01-01')"
            ))
            conn.execute(sa.text(
                "INSERT INTO stores (owner_user_id, name, created_at) "
                "VALUES (1,'도야짬뽕','2026-01-01')"
            ))
        with engine.begin() as conn:
            with pytest.raises(sa.exc.IntegrityError):
                conn.execute(sa.text(
                    "INSERT INTO stores (owner_user_id, name, created_at) "
                    "VALUES (2,'도야짬뽕','2026-01-01')"
                ))
