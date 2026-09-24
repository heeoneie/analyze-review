"""말투 적합도 리포트 스크립트 테스트.

주로 고정하려는 성질은 **매장 격리**다. 이 리포트가 매장을 합치면 크로스-머천트
분석이 되고(CLAUDE.md), 학습 곡선의 x축도 틀린다. 합치지 않는다는 것을
테스트로 박아 둔다.

답글 문장은 전부 지어낸 것이다.
"""

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from backend.database.models import ReplySample

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "style_report.py"
_spec = importlib.util.spec_from_file_location("style_report", _SCRIPT)
style_report = importlib.util.module_from_spec(_spec)
sys.modules["style_report"] = style_report
_spec.loader.exec_module(style_report)


ROWS = [
    # (store_id, origin, rating, generated, final, created_at, finalized_at)
    (1, "generated", 5, "가게 초안 하나입니다", "가게 초안 하나입니다",
     "2026-01-01T00:00", "2026-01-01T01:00"),
    (1, "generated", 5, "가게 초안 둘입니다", "사장님이 고쳐 쓴 답글",
     "2026-01-02T00:00", "2026-01-02T01:00"),
    (2, "generated", 5, "다른 가게 초안입니다", "다른 가게 초안입니다",
     "2026-01-03T00:00", "2026-01-03T01:00"),
]


def _make_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE reply_samples (id INTEGER PRIMARY KEY, "
        "store_id INTEGER NOT NULL, origin TEXT, rating INTEGER, "
        "generated_reply TEXT, final_reply TEXT, created_at TEXT, finalized_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO reply_samples (store_id, origin, rating, generated_reply, "
        "final_reply, created_at, finalized_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture(name="db_path")
def _db_path(tmp_path):
    return _make_db(tmp_path / "samples.db", ROWS)


def test_samples_are_split_per_store(db_path):
    groups = style_report.group_by_store(style_report.load_samples(db_path))
    assert set(groups) == {1, 2}
    assert len(groups[1]) == 2
    assert len(groups[2]) == 1


def test_no_combined_entry_is_produced(db_path, capsys, monkeypatch):
    """JSON 출력에 '전체' 나 매장을 합친 키가 있으면 안 된다.

    있으면 누군가 그 값을 인용하게 되고, 그게 곧 크로스-머천트 분석이다.
    """
    monkeypatch.setattr(sys, "argv", ["style_report.py", "--db", db_path, "--json"])
    assert style_report.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"1", "2"}


def test_a_single_store_can_be_read(db_path):
    samples = style_report.load_samples(db_path, store_id=2)
    assert len(samples) == 1
    assert {s["store_id"] for s in samples} == {2}


def test_edit_rate_is_computed_per_store(db_path):
    groups = style_report.group_by_store(style_report.load_samples(db_path))
    assert style_report.build(groups[1])["edit"]["전체"].rate == 0.5
    assert style_report.build(groups[2])["edit"]["전체"].rate == 0.0


def test_reply_samples_store_id_is_not_nullable():
    """매장 없는 행을 다루는 분기를 두지 않는 근거.

    `Review.store_id` 와 달리 `ReplySample.store_id` 는 NOT NULL 이다. 모델과
    baseline 마이그레이션 양쪽에 걸려 있으므로 접속코드 시절의 NULL 행이
    존재하지 않는다. 이게 뒤집히면 `group_by_store` 가 KeyError 로 먼저
    깨져야 한다 — 조용히 "None" 매장을 만들어 내는 것보다 낫다.
    """
    assert ReplySample.__table__.c.store_id.nullable is False


def test_report_carries_no_reply_text(db_path):
    """리포트를 붙여넣어 공유해도 손님 글도 사장님 글도 따라가면 안 된다."""
    groups = style_report.group_by_store(style_report.load_samples(db_path))
    rendered = "\n".join(
        style_report.render(style_report.build(rows), sid)
        for sid, rows in groups.items()
    )
    for _, _, _, generated, final, _, _ in ROWS:
        assert generated not in rendered
        assert final not in rendered


def test_empty_database_exits_quietly(tmp_path, capsys, monkeypatch):
    path = _make_db(tmp_path / "empty.db", [])
    monkeypatch.setattr(sys, "argv", ["style_report.py", "--db", path])
    assert style_report.main() == 0
    assert "표본이 없습니다" in capsys.readouterr().out


def test_missing_database_returns_one(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["style_report.py", "--db", str(tmp_path / "없는파일.db")])
    assert style_report.main() == 1
    assert "DB 가 없습니다" in capsys.readouterr().err


def test_database_is_opened_read_only(db_path, monkeypatch):
    """리포트가 운영 DB 를 건드릴 일은 없다. 실수로도 못 쓰게 막혀 있어야 한다.

    URI 를 테스트가 다시 조립하면 `load_samples` 를 읽기·쓰기로 바꿔도 통과한다.
    실제로 `load_samples` 가 연 연결을 잡아서 본다.
    """
    opened = {}
    real_connect = sqlite3.connect

    def spy(target, *args, **kwargs):
        opened["target"] = target
        opened["uri"] = kwargs.get("uri", False)
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr(style_report.sqlite3, "connect", spy)
    style_report.load_samples(db_path)

    assert opened["uri"] is True
    assert opened["target"].endswith("?mode=ro")

    conn = real_connect(opened["target"], uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM reply_samples")
    conn.close()


def test_default_db_follows_database_url(monkeypatch):
    """배포는 DATABASE_URL 로 경로를 준다. 여기를 안 보면 옛 DB 를 읽는다."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/var/app.db")
    assert style_report.default_db() == "/app/var/app.db"


def test_default_db_resolves_a_relative_sqlite_url_like_the_app(tmp_path, monkeypatch):
    """SQLAlchemy 는 상대경로를 작업 디렉터리 기준으로 연다. 여기도 같아야 한다.

    저장소 루트 기준으로 풀면 `cd /srv && uvicorn ...` 으로 띄운 앱이 쓴 파일과
    다른 파일을 조용히 읽는다.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///var/app.db")
    assert style_report.default_db() == str(tmp_path / "var" / "app.db")


@pytest.mark.parametrize("url", [
    "postgresql://user@host/db",   # 이 스크립트는 sqlite 만 읽는다
    "sqlite://",                   # 메모리 DB 는 파일이 없다
    "not a url",
])
def test_default_db_gives_up_when_there_is_no_sqlite_file(url, monkeypatch):
    """읽을 파일을 모르면 None. 조용히 다른 파일을 읽지 않는다."""
    monkeypatch.setenv("DATABASE_URL", url)
    assert style_report.default_db() is None


def test_baseline_repetition_comes_from_this_stores_onboarding_rows(tmp_path):
    """매크로 기준선은 같은 매장 사장님이 도구 없이 쓴 글(온보딩)에서 센다.

    다른 매장 수치나 손으로 센 상수를 기준선으로 찍으면 매장 격리가 깨지고,
    세는 방법이 달라 비교도 안 된다.
    """
    rows = [
        (1, "onboarding", 5, None, "감사합니다 고객님. 또 오세요.", "2026-01-01T00:00", "2026-01-01T00:00"),
        (1, "onboarding", 5, None, "감사합니다 고객님. 좋은 하루요.", "2026-01-01T00:00", "2026-01-01T00:00"),
        (1, "generated", 5, "짬뽕 맛있으셨군요. 또 오세요.", "짬뽕 맛있으셨군요. 또 오세요.",
         "2026-01-02T00:00", "2026-01-02T01:00"),
    ]
    samples = style_report.load_samples(_make_db(tmp_path / "b.db", rows))
    report = style_report.build(samples)
    assert report["repetition"]["온보딩"].total == 2
    assert report["repetition"]["온보딩"].top_opening_share == 1.0
    assert report["repetition"]["게시본"].total == 3
    rendered = style_report.render(report, 1)
    assert "441" not in rendered and "31%" not in rendered


def test_unposted_drafts_count_toward_generated_repetition(tmp_path):
    """버린 초안도 센다. 살아남은 것만 세면 매크로 판정이 유리하게 걸러진다."""
    rows = list(ROWS[:1]) + [
        (1, "generated", 5, "버려진 초안입니다", None, "2026-01-05T00:00", None),
    ]
    samples = style_report.load_samples(_make_db(tmp_path / "d.db", rows))
    report = style_report.build(samples)
    assert report["repetition"]["생성본"].total == 2
    assert report["repetition"]["게시본"].total == 1
