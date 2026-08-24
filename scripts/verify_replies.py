"""실제 매장 CSV로 답변을 생성하고 첫 문장 중복을 검사한다.

사용법:
    python scripts/verify_replies.py <csv_path> [--positive 10] [--negative 5]

CSV 컬럼: 별점, 주문메뉴, 리뷰내용, 작성일시, 주문유형 (배달앱 리뷰 내보내기 형식)
"""

import argparse
import json
import os
import sys
from itertools import combinations

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config  # noqa: E402  pylint: disable=wrong-import-position
from core.menu_profiles import main_items, parse_menu  # noqa: E402  pylint: disable=wrong-import-position
from core.reply_generator import ReplyGenerator  # noqa: E402  pylint: disable=wrong-import-position
from core.reply_text import openings_collide  # noqa: E402  pylint: disable=wrong-import-position


def menu_signature(menu_text):
    """서비스 품목을 뺀 메인 메뉴 이름 집합. 메뉴가 서로 다른 리뷰를 고르는 데 쓴다."""
    return frozenset(i["name"] for i in main_items(parse_menu(menu_text)))


def pick_positive(df, count):
    """별점 5점 중 주문 메뉴가 서로 겹치지 않는 건을 고른다."""
    rows = df[df["별점"].astype(int) == 5]
    picked, seen = [], set()
    # 본문이 있는 리뷰를 먼저 훑고, 모자라면 본문 없는 리뷰로 채운다.
    for has_body in (True, False):
        for _, row in rows.iterrows():
            if len(picked) >= count:
                break
            body = bool(row["리뷰내용"].strip())
            if body != has_body:
                continue
            sig = menu_signature(row["주문메뉴"])
            if not sig or sig in seen:
                continue
            seen.add(sig)
            picked.append(row)
    return picked


def pick_negative(df, count):
    rows = df[df["별점"].astype(int) <= 3]
    with_body = [r for _, r in rows.iterrows() if r["리뷰내용"].strip()]
    return with_body[:count]


def to_payload(row):
    return {
        "review_text": row["리뷰내용"].strip(),
        "rating": int(row["별점"]),
        "menu": row["주문메뉴"],
        "ordered_at": row["작성일시"],
        "order_type": row["주문유형"],
    }


def report(title, rows, results):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    by_index = {r["review_index"]: r for r in results}
    for i, row in enumerate(rows):
        res = by_index.get(i)
        print(f"\n[{i + 1}] {row['별점']}점 · {row['주문유형']} · {row['작성일시']}")
        print(f"    주문: {', '.join(menu_signature(row['주문메뉴'])) or '(없음)'}")
        print(f"    리뷰: {row['리뷰내용'].strip() or '(본문 없음, 별점만)'}")
        if not res:
            print("    !! 생성 실패")
            continue
        shape = f"도입={res['opening_angle'] or '-'}, 끝맺음={res.get('closing_move') or '-'}"
        print(f"    답변({len(res['reply'])}자, {shape}):")
        for line in res["reply"].split("\n"):
            print(f"      {line}")
        if res.get("menu_mentioned"):
            print(f"    언급 메뉴: {', '.join(res['menu_mentioned'])}")
        if res.get("issues_addressed"):
            print(f"    짚은 불만: {', '.join(res['issues_addressed'])}")
        if res.get("next_action"):
            print(f"    약속한 조치: {res['next_action']}")
        if res["violations"]:
            print(f"    !! 남은 위반: {res['violations']}")


def check_overlap(results, field, label):
    print(f"\n{'-' * 78}\n{label} 중복 검사\n{'-' * 78}")
    sentences = [(r["review_index"], r.get(field, "")) for r in results]
    for idx, sentence in sentences:
        print(f"  [{idx + 1}] {sentence}")

    collisions = [
        (a, b) for (a, sa), (b, sb) in combinations(sentences, 2)
        if openings_collide(sa, sb)
    ]
    if collisions:
        print(f"\n  !! 겹치는 {label} 발견:")
        for a, b in collisions:
            print(f"     [{a + 1}] ↔ [{b + 1}]")
    else:
        print(f"\n  겹치는 {label} 없음")
    return collisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--positive", type=int, default=10)
    parser.add_argument("--negative", type=int, default=5)
    parser.add_argument("--store", default=config.STORE_NAME)
    parser.add_argument("--model", default=None, help="생성 모델 (기본: config.REPLY_LLM_MODEL)")
    parser.add_argument("--out", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path, encoding="utf-8-sig", dtype=str).fillna("")
    generator = ReplyGenerator(store_name=args.store, model=args.model)

    pos_rows = pick_positive(df, args.positive)
    neg_rows = pick_negative(df, args.negative)
    print(f"긍정 {len(pos_rows)}건 / 부정 {len(neg_rows)}건 생성 시작 "
          f"(모델: {generator.model}, 매장: {generator.store_name})")

    pos_results = generator.generate_series([to_payload(r) for r in pos_rows])
    neg_results = generator.generate_series([to_payload(r) for r in neg_rows])

    report(f"별점 5점 {len(pos_rows)}건 — 주문 메뉴가 서로 다른 리뷰", pos_rows, pos_results)
    report(f"별점 3점 이하 {len(neg_rows)}건", neg_rows, neg_results)

    collisions = check_overlap(pos_results, "opening_sentence", "첫 문장")
    collisions += check_overlap(pos_results, "closing_sentence", "끝 문장")
    check_overlap(neg_results, "opening_sentence", "첫 문장")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fp:
            json.dump(
                {"positive": pos_results, "negative": neg_results},
                fp, ensure_ascii=False, indent=2,
            )
        print(f"\n결과 저장: {args.out}")

    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
