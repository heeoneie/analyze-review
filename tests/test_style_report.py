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

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "style_report.py"
_spec = importlib.util.spec_from_file_location("style_report", _SCRIPT)
style_report = importlib.util.module_from_spec(_spec)
sys.modules["style_report"] = style_report
_spec.loader.exec_module(style_report)


ROWS = [
    # (store_id, origin, rating, generated, final, finalized_at)
    (1, "generated", 5, "가게 초안 하나입니다", "가게 초안 하나입니다", "2026-01-01"),
    (1, "generated", 5, "가게 초안 둘입니다", "사장님이 고쳐 쓴 답글", "2026-01-02"),
    (2, "generated", 5, "다른 가게 초안입니다", "다른 가게 초안입니다", "2026-01-03"),
]


@pytest.fixture(name="db_path")
def _db_path(tmp_path):
    path = tmp_path / "samples.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE reply_samples (id INTEGER PRIMARY KEY, store_id INTEGER, "
        "origin TEXT, rating INTEGER, generated_reply TEXT, final_reply TEXT, "
        "finalized_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO reply_samples (store_id, origin, rating, generated_reply, "
        "final_reply, finalized_at) VALUES (?,?,?,?,?,?)",
        ROWS,
    )
    conn.commit()
    conn.close()
    return str(path)


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


def test_pre_store_rows_group_together(tmp_path):
    """store_id 가 NULL 인 행은 접속코드 시절 데이터다. 그때는 매장이 하나였다."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE reply_samples (id INTEGER PRIMARY KEY, store_id INTEGER, "
        "origin TEXT, rating INTEGER, generated_reply TEXT, final_reply TEXT, "
        "finalized_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO reply_samples (store_id, origin, rating, generated_reply, "
        "final_reply, finalized_at) VALUES (?,?,?,?,?,?)",
        [(None, "generated", 5, "초안입니다", "초안입니다", "2026-01-01"),
         (1, "generated", 5, "다른 초안입니다", "다른 초안입니다", "2026-01-02")],
    )
    conn.commit()
    conn.close()

    groups = style_report.group_by_store(style_report.load_samples(str(path)))
    assert list(groups) == [None, 1]


def test_report_carries_no_reply_text(db_path):
    """리포트를 붙여넣어 공유해도 손님 글도 사장님 글도 따라가면 안 된다."""
    groups = style_report.group_by_store(style_report.load_samples(db_path))
    rendered = "\n".join(
        style_report.render(style_report.build(rows), sid)
        for sid, rows in groups.items()
    )
    for _, _, _, generated, final, _ in ROWS:
        assert generated not in rendered
        assert final not in rendered


def test_empty_database_exits_quietly(tmp_path, capsys, monkeypatch):
    path = tmp_path / "empty.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE reply_samples (id INTEGER PRIMARY KEY, store_id INTEGER, "
        "origin TEXT, rating INTEGER, generated_reply TEXT, final_reply TEXT, "
        "finalized_at TEXT)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(sys, "argv", ["style_report.py", "--db", str(path)])
    assert style_report.main() == 0
    assert "표본이 없습니다" in capsys.readouterr().out


def test_missing_database_returns_one(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["style_report.py", "--db", str(tmp_path / "없는파일.db")])
    assert style_report.main() == 1
    assert "DB 가 없습니다" in capsys.readouterr().err


def test_database_is_opened_read_only(db_path):
    """리포트가 운영 DB 를 건드릴 일은 없다. 실수로도 못 쓰게 막혀 있어야 한다."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM reply_samples")
    conn.close()
