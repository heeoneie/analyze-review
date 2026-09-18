"""말투 적합도 리포트 — 답글이 사장님께 맞는지, 그리고 매크로가 아닌지.

    python scripts/style_report.py                 # 기본 DB
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config, style_fit  # noqa: E402  pylint: disable=wrong-import-position

DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ontology.db"
)


def load_samples(db_path: str, store_id: int | None = None) -> list[dict]:
    """`reply_samples` 를 읽어 순수 dict 로 바꾼다.

    SQLAlchemy 를 거치지 않고 sqlite3 으로 직접 읽는다. 이 스크립트는 읽기만
    하고 모델도 라우터도 건드리지 않으므로, 앱을 임포트해서 설정과 마이그레이션이
    딸려 오게 만들 이유가 없다.

    `finalized_at` 은 문자열 그대로 둔다. ISO 형식이라 문자열 정렬이 곧
    시간순이고, 학습 곡선은 순서만 쓴다.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT store_id, origin, rating, generated_reply, final_reply, "
            "finalized_at FROM reply_samples"
        )
        params: tuple = ()
        if store_id is not None:
            sql += " WHERE store_id = ?"
            params = (store_id,)
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
    generated_posted = [s for s in posted if (s.get("generated_reply") or "").strip()]

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
            # 사장님이 실제로 올린 글 전부. 매크로 기준선이다.
            "게시본": style_fit.repetition([s["final_reply"] for s in posted]),
            # 우리가 만든 초안. 게시본보다 이쪽이 더 반복적이면 우리가 만든 문제다.
            "생성본": style_fit.repetition(
                [s["generated_reply"] for s in generated_posted]
            ),
        },
    }


def group_by_store(samples: list[dict]) -> dict:
    """매장별로 가른다. 합치지 않는다 — 모듈 최상단의 설명 참고.

    `store_id` 가 NULL 인 행은 카카오 로그인 이전의 접속코드 시절 데이터다.
    매장이 하나뿐이던 시기라 한 덩어리로 묶어도 섞이지 않는다.
    """
    groups: dict = {}
    for sample in samples:
        groups.setdefault(sample.get("store_id"), []).append(sample)
    return dict(sorted(groups.items(), key=lambda kv: (kv[0] is not None, kv[0])))


def render(report: dict, store_id: int | None = None) -> str:
    counts = report["counts"]
    title = "  말투 적합도" + (
        f" — 매장 {store_id}" if store_id is not None else " — 매장 연결 전 데이터"
    )
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
        "  표본 0-1 은 길이 학습이 아직 안 걸리는 구간이다. 이게 기준선이다.",
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
        "  이 매장 사장님의 기존 답변 441건 기준선은 31% 였다 (README).",
        "  생성본이 그보다 높으면 매크로를 줄인 게 아니라 늘린 것이다.",
    ]

    lines += [
        "",
        "── 이 숫자가 증명하지 못하는 것 ──",
        "  편집률은 대리 지표다. 바빠서 그냥 게시했을 수도 있으므로 낮은 편집률이",
        "  '맞았다' 를 증명하지 않는다. 높은 편집률이 '안 맞았다' 는 쪽이 더 믿을 만하다.",
        "  학습 곡선은 관측이지 실험이 아니다. 표본이 쌓이는 동안 프롬프트도 바뀌었다면",
        "  원인을 가를 수 없다. 바꾼 것은 evaluation/public/tuning_log.json 에 남긴다.",
        "  반복률은 구두점 없이 이어 쓴 답글에서 반복을 덜 잡는다 (과소평가 방향).",
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
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite 경로")
    parser.add_argument("--store", type=int, default=None, help="매장 id (기본: 전체)")
    parser.add_argument("--json", action="store_true", help="수치만 JSON 으로")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"DB 가 없습니다: {args.db}", file=sys.stderr)
        return 1

    samples = load_samples(args.db, args.store)
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
