"""말투 적합도 리포트 — 답글이 사장님께 맞는지, 그리고 매크로가 아닌지.

    python scripts/style_report.py                 # DATABASE_URL 의 DB
    python scripts/style_report.py --db data/ontology.db
    python scripts/style_report.py --store 1 --json

## 왜 이 두 개를 같이 내는가

편집률만 보면 "사장님이 고치지 않는 답글" 로 수렴한다. 그런데 이 매장
사장님의 기존 답변 441건 중 131건(31%)이 같은 인사말로 시작했고, 손님에게
매크로로 읽히는 것이 애초에 이 도구를 만든 이유였다. 말투를 완벽히 따라
하면 그 매크로를 복제한다. 그래서 반복률을 나란히 놓는다.

## 화면에 안 띄우고 CLI 로 두는 이유

사장님이 볼 숫자가 아니다. 우리가 말투 학습을 고칠 때 보는 숫자다. 대시보드에
올리면 사장님이 "편집률 40%" 를 자기 성적표로 읽게 되는데, 이건 우리 성적표다.

## 매장을 섞지 않는다

매장이 여럿이면 **매장마다 따로** 낸다. 합산값은 만들지 않는다. 두 가지
이유가 겹친다.

법적으로, 여러 매장 데이터를 합쳐 보는 것은 수탁자가 위탁사무 대가 외의
독자적 이익을 갖는 쪽으로 읽힌다 (CLAUDE.md 의 매장 격리). 내부용 품질
지표라도 합산 파일을 만드는 순간 그게 존재하게 된다.

수치로도 틀린다. 학습 곡선의 x축은 "이 답글을 만들 때 **이 매장의** 표본이
몇 건 있었나" 다. 매장을 넘어 세면 A매장 20건 뒤에 가입한 B매장의 첫 답글이
'표본 20건' 구간에 들어간다. 그 매장 프롬프트에는 0건이 들어갔는데도.

## 개인정보

리뷰 본문도 답글 본문도 출력하지 않는다. 집계 수치와 건수만 낸다.
리포트를 붙여넣어 공유해도 손님 글이 따라가지 않아야 한다.
"""

import argparse
import json
import os
import sqlite3
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config, style_fit  # noqa: E402  pylint: disable=wrong-import-position

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 앱이 DATABASE_URL 을 못 찾았을 때 쓰는 경로와 같아야 한다
# (`backend/database/database.py`). 여기서만 다르게 두면 조용히 다른 DB 를 읽는다.
_FALLBACK_DB = os.path.join(_ROOT, "data", "ontology.db")


def default_db() -> str | None:
    """앱이 실제로 쓰는 SQLite 경로. 알아낼 수 없으면 None.

    `DATABASE_URL` 을 먼저 본다. 이걸 안 보고 `data/ontology.db` 를 박아 두면
    배포 환경에서 두 가지로 틀린다. docker-compose 는
    `sqlite:////app/var/app.db` 를 넣고, `data/ontology.db` 는 마이그레이션
    기록상 **옛 경로**다. 앱이 임포트될 때마다 그 디렉터리를 만들어 두므로
    빈 파일이나 낡은 파일이 남아 있기 쉽고, 그러면 죽은 데이터로 리포트가
    멀쩡히 나온다. 틀린 숫자를 조용히 내는 쪽이 못 찾는 쪽보다 나쁘다.

    sqlite 파일이 아니면(postgres, `sqlite://` 메모리 DB, 못 읽는 URL) None 을
    돌려준다. 이 스크립트는 sqlite 파일만 읽는다.

    상대경로는 **현재 작업 디렉터리** 기준으로 푼다. SQLAlchemy 가
    `sqlite:///var/app.db` 를 그렇게 열기 때문이다. 저장소 루트 기준으로
    풀면 앱이 쓴 파일과 다른 파일을 조용히 읽는다 — 이 함수가 막으려는 바로
    그 일이다. URL 해석은 앱과 같은 `make_url` 에 맡긴다.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        return _FALLBACK_DB
    try:
        parsed = make_url(url)
    except ArgumentError:
        return None
    if parsed.get_backend_name() != "sqlite" or not parsed.database:
        return None
    return os.path.abspath(parsed.database)


def load_samples(db_path: str, store_id: int | None = None) -> list[dict]:
    """`reply_samples` 를 읽어 순수 dict 로 바꾼다.

    SQLAlchemy 를 거치지 않고 sqlite3 으로 직접 읽는다. 이 스크립트는 읽기만
    하고 모델도 라우터도 건드리지 않으므로, 앱을 임포트해서 설정과 마이그레이션이
    딸려 오게 만들 이유가 없다.

    `created_at`·`finalized_at` 은 문자열 그대로 둔다. ISO 형식이라 문자열
    비교가 곧 시간 비교이고, 학습 곡선은 앞뒤 관계만 쓴다. 둘 다 읽어야
    한다 — 곡선은 답글을 **만든** 시각으로 세고, 그 시점의 표본 수는
    **게시된** 시각으로 센다.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT store_id, origin, rating, generated_reply, final_reply, "
            "created_at, finalized_at FROM reply_samples"
        )
        params: tuple = ()
        if store_id is not None:
            sql += " WHERE store_id = ?"
            params = (store_id,)
        # ORDER BY 를 빼면 같은 DB 를 두 번 읽어도 다른 반복률이 나온다.
        # 행 순서는 계약이 아니다 — VACUUM 이나 batch_alter_table 로 테이블이
        # 다시 만들어지면 바뀐다. 마이그레이션이 실제로 batch_alter_table 을 쓴다.
        sql += " ORDER BY id"
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _edit_line(label: str, stats: style_fit.EditStats, indent: str = "  ") -> str:
    if stats.total == 0:
        return f"{indent}{label:<10} 표본 없음"
    band = f"[{_pct(stats.ci_low)} ~ {_pct(stats.ci_high)}]"
    # 표본이 적으면 비율 자리를 비워 둔다. 옆에 주석으로 "인용 금지" 를 달면
    # 눈이 앞의 숫자만 가져가고 주석은 장식이 된다. 아예 안 보여 주는 편이 낫다.
    if not stats.citable:
        return f"{indent}{label:<10} {'':>7}   {stats.edited}/{stats.total}건  구간 {band}"
    return (
        f"{indent}{label:<10} {_pct(stats.rate):>7}"
        f"   {stats.edited}/{stats.total}건  구간 {band}"
    )


def build(samples: list[dict]) -> dict:
    """리포트에 들어갈 수치 전부. --json 이 그대로 내보낸다."""
    posted = [s for s in samples if (s.get("final_reply") or "").strip()]
    # 게시 여부와 무관하게 우리가 만든 초안 **전부**를 센다. 게시된 것만 세면
    # 사장님이 버린 초안이 빠지는데, 매크로처럼 읽히는 초안이야말로 버려질
    # 가능성이 높다. 그러면 "우리가 매크로를 만들었나" 라는 바로 그 질문에
    # 유리한 쪽으로 표본이 걸러진다.
    drafted = [s for s in samples if (s.get("generated_reply") or "").strip()]

    def _pol(rows, positive):
        return [
            r for r in rows
            if (r["rating"] >= config.POSITIVE_RATING_THRESHOLD) == positive
        ]

    return {
        "counts": {
            "전체": len(samples),
            "게시됨": len(posted),
            "미게시": len(samples) - len(posted),
            "온보딩": sum(1 for s in samples if s["origin"] == "onboarding"),
        },
        "edit": {
            "전체": style_fit.edit_stats(samples),
            "긍정": style_fit.edit_stats(_pol(samples, True)),
            "부정": style_fit.edit_stats(_pol(samples, False)),
        },
        "curve": {
            "긍정": style_fit.learning_curve(samples, positive=True),
            "부정": style_fit.learning_curve(samples, positive=False),
        },
        "repetition": {
            # 사장님이 이 도구 없이 쓴 글. **이 매장의** 매크로 기준선이다.
            # 다른 매장 수치나 손으로 센 값을 기준선으로 두지 않는다 — 세는
            # 방법이 다르면 비교가 안 되고, 매장을 넘는 순간 격리가 깨진다.
            "온보딩": style_fit.repetition([
                s["final_reply"] for s in posted if s["origin"] == "onboarding"
            ]),
            # 사장님이 실제로 올린 글 전부 (온보딩 포함).
            "게시본": style_fit.repetition([s["final_reply"] for s in posted]),
            # 우리가 만든 초안 전량. 온보딩보다 이쪽이 더 반복적이면 우리 문제다.
            "생성본": style_fit.repetition([s["generated_reply"] for s in drafted]),
        },
    }


def group_by_store(samples: list[dict]) -> dict:
    """매장별로 가른다. 합치지 않는다 — 모듈 최상단의 설명 참고.

    `reply_samples.store_id` 는 NOT NULL 이다 (모델과 baseline 마이그레이션
    양쪽에서). `Review` 쪽과 달리 접속코드 시절의 NULL 행이 존재하지 않으므로
    없는 경우를 다루지 않는다.
    """
    groups: dict = {}
    for sample in samples:
        groups.setdefault(sample["store_id"], []).append(sample)
    return dict(sorted(groups.items()))


def render(report: dict, store_id: int) -> str:
    counts = report["counts"]
    title = f"  말투 적합도 — 매장 {store_id}"
    lines = [
        "",
        "═" * 68,
        title,
        "═" * 68,
        "",
        f"표본 {counts['전체']}건 "
        f"(게시 {counts['게시됨']} · 미게시 {counts['미게시']} · 온보딩 {counts['온보딩']})",
        "",
        "── 편집률 — 낮을수록 사장님 말투에 가깝다 ──",
        f"  (비율 칸이 비었으면 표본 {style_fit.MIN_SAMPLES_TO_CITE}건 미만이다."
        " 건수와 구간만 본다.)",
    ]
    for label, stats in report["edit"].items():
        lines.append(_edit_line(label, stats))

    similarity = report["edit"]["전체"].median_similarity_when_edited
    if similarity is not None:
        lines += [
            "",
            f"  고쳐 쓴 답글에서 생성본이 남은 정도 (중앙값): {_pct(similarity)}",
            "  낮을수록 통째로 다시 썼다는 뜻이다.",
        ]

    lines += [
        "",
        "── 학습 곡선 — 표본이 쌓이면 덜 고치는가 ──",
        "  표본 0 은 말투 학습이 전혀 안 걸린 구간이다. 이게 기준선이다.",
        "  (1건부터 예시와 인사말이 프롬프트에 들어간다. 길이 기준만 2건부터다.)",
    ]
    for polarity, points in report["curve"].items():
        lines.append(f"  [{polarity}]")
        for point in points:
            lines.append(_edit_line(f"표본 {point.label}", point.stats, indent="    "))

    lines += ["", "── 반복률 — 높을수록 매크로로 읽힌다 ──"]
    for label, rep in report["repetition"].items():
        if rep.total == 0:
            lines.append(f"  {label:<8} 표본 없음")
            continue
        lines.append(
            f"  {label:<8} 첫 문장 최다 군집 {_pct(rep.top_opening_share):>7}"
            f"  ({rep.distinct_openings}종/{rep.total}건)"
        )
        lines.append(
            f"  {'':<8} 끝 문장 최다 군집 {_pct(rep.top_closing_share):>7}"
            f"  ({rep.distinct_closings}종/{rep.total}건)"
        )
    lines += [
        "",
        "  온보딩은 사장님이 이 도구 없이 쓴 글이라 이 매장의 매크로 기준선이다.",
        "  생성본이 그보다 높으면 매크로를 줄인 게 아니라 늘린 것이다.",
    ]

    lines += [
        "",
        "── 이 숫자가 증명하지 못하는 것 ──",
        "  편집률은 대리 지표다. 바빠서 그냥 게시했을 수도 있으므로 낮은 편집률이",
        "  '맞았다' 를 증명하지 않는다. 높은 편집률이 '안 맞았다' 는 쪽이 더 믿을 만하다.",
        "  학습 곡선은 관측이지 실험이 아니다. 표본이 쌓이는 동안 프롬프트도 바뀌었다면",
        "  원인을 가를 수 없다. 프롬프트를 바꾼 날짜를 따로 적어 두고 곡선과 같이 본다.",
        "  반복률은 첫 문장의 앞 두 어절, 끝 문장의 뒤 두 어절만 본다. 세 번째 어절부터",
        "  같은 문장은 다른 계열로 세므로 반복을 덜 잡을 수는 있어도 지어내지는 않는다.",
        "  게시본 반복률에는 사장님이 직접 쓴 온보딩 답글이 섞여 있다. 우리가 만든",
        "  글만 보려면 생성본 쪽을 본다 — 그쪽은 버린 초안까지 전부 센다.",
        "",
    ]
    return "\n".join(lines)


def _jsonable(report: dict) -> dict:
    """dataclass 를 dict 로 편다. 수치를 다른 도구로 넘길 때 쓴다."""
    return {
        "counts": report["counts"],
        "edit": {k: vars(v) | {"citable": v.citable} for k, v in report["edit"].items()},
        "curve": {
            polarity: [
                {"bucket": p.label, **vars(p.stats), "citable": p.stats.citable}
                for p in points
            ]
            for polarity, points in report["curve"].items()
        },
        "repetition": {k: vars(v) for k, v in report["repetition"].items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="말투 적합도 리포트")
    parser.add_argument(
        "--db", default=None, help="SQLite 경로 (기본: DATABASE_URL 에서 찾는다)",
    )
    parser.add_argument("--store", type=int, default=None, help="매장 id (기본: 전체)")
    parser.add_argument("--json", action="store_true", help="수치만 JSON 으로")
    args = parser.parse_args()

    db = args.db or default_db()
    if db is None:
        print(
            "DATABASE_URL 에서 sqlite 파일 경로를 알 수 없습니다 "
            "(sqlite 파일이 아니거나 메모리 DB). --db 로 지정해 주십시오.",
            file=sys.stderr,
        )
        return 1
    if not os.path.exists(db):
        print(f"DB 가 없습니다: {db}", file=sys.stderr)
        return 1

    samples = load_samples(db, args.store)
    if not samples:
        where = f"store_id={args.store} " if args.store else ""
        print(f"{where}답글 표본이 없습니다. 답글을 게시한 뒤에 다시 보십시오.")
        return 0

    groups = group_by_store(samples)
    if args.json:
        # 매장 id 를 키로 둔다. 합산 항목은 만들지 않는다.
        print(json.dumps(
            {str(sid): _jsonable(build(rows)) for sid, rows in groups.items()},
            ensure_ascii=False, indent=2,
        ))
    else:
        for store_id, rows in groups.items():
            print(render(build(rows), store_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
