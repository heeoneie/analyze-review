"""재검사 신뢰도 — 같은 사람이 같은 리뷰를 다시 라벨링했을 때의 일치도.

    python scripts/eval/reliability.py evaluation/sample_v1.csv

라벨러가 한 명이므로 rater 간 일치도(inter-rater κ)를 낼 수 없다. 대신
intra-rater κ 를 낸다. 이 값은 **분류기 점수의 해석 상한**이다. 사람이 자기
자신과 75% 만 일치하는 기준으로 매긴 라벨에서 분류기가 90% 를 맞혔다면,
그 90% 중 상당 부분은 문제를 맞힌 게 아니라 라벨 잡음을 맞힌 것이다.

κ 가 낮게 나와도 수치를 고치지 않는다. 그건 결과이지 실패가 아니다.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.eval.metrics import cohen_kappa  # noqa: E402  pylint: disable=wrong-import-position


def _read(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def main() -> None:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    parser = argparse.ArgumentParser(description="재검사 신뢰도 (intra-rater κ)")
    parser.add_argument("sample", help="최초 라벨링 표본 CSV")
    parser.add_argument("--retest", default=None,
                        help="재검사 CSV (기본: <sample>.retest.csv)")
    parser.add_argument("--out", default="results/eval/reliability.json")
    args = parser.parse_args()

    retest_path = args.retest or os.path.splitext(args.sample)[0] + ".retest.csv"
    if not os.path.exists(retest_path):
        raise SystemExit(
            f"재검사 파일이 없습니다: {retest_path}\n"
            f"  python scripts/eval/label_tool.py {args.sample} --mode retest"
        )

    first, second = _read(args.sample), _read(retest_path)

    pairs = []
    pending = 0
    for sid, row in second.items():
        b = (row.get("primary_label") or "").strip()
        a = (first.get(sid, {}).get("primary_label") or "").strip()
        if not b:
            pending += 1
            continue
        if a:
            pairs.append((sid, a, b))

    if not pairs:
        raise SystemExit(
            f"비교할 쌍이 없습니다. 재검사 라벨이 {pending}건 남았습니다."
        )

    result = cohen_kappa([a for _, a, _ in pairs], [b for _, _, b in pairs])

    # 최초 라벨링 시각과 재검사 시각 사이 간격 — 너무 짧으면 기억으로 맞힌다.
    gaps = []
    for sid, _, _ in pairs:
        t1 = first.get(sid, {}).get("labeled_at", "")
        t2 = second.get(sid, {}).get("labeled_at", "")
        if t1 and t2:
            try:
                gaps.append(
                    (datetime.fromisoformat(t2) - datetime.fromisoformat(t1)).days
                )
            except ValueError:
                pass
    min_gap = min(gaps) if gaps else None

    print("=" * 74)
    print("  재검사 신뢰도 (intra-rater)")
    print("=" * 74)
    print(f"  비교 건수      {result['n']}")
    print(f"  단순 일치율    {result['agreement']*100:.1f}%  "
          f"[{result['agreement_ci95'][0]*100:.1f}, {result['agreement_ci95'][1]*100:.1f}]")
    kappa = result["kappa"]
    print(f"  Cohen's κ      {kappa if kappa is not None else 'n/a'}  "
          f"— {result['interpretation']}")
    if min_gap is not None:
        print(f"  최소 간격      {min_gap}일")
        if min_gap < 3:
            print("  ⚠️  간격이 3일 미만입니다. 기억으로 맞힌 부분이 섞여 κ 가 "
                  "실제보다 높게 나옵니다. 리포트에 간격을 함께 적으세요.")
    if pending:
        print(f"  아직 재검사 안 한 건  {pending}")

    if result["disagreements"]:
        print(f"\n  불일치 {len(result['disagreements'])}건 — 경계가 흔들리는 쌍:")
        pairs_count = Counter(
            (d["first"], d["second"]) for d in result["disagreements"]
        )
        for (a, b), n in pairs_count.most_common(10):
            print(f"    {a:<18} ↔ {b:<18} {n}건")
        print("\n  같은 쌍이 반복되면 그 두 카테고리의 경계가 가이드에서 덜 갈린 것입니다.")
        print("  ⚠️  지금 가이드를 고치지 마세요. v1 수치를 낸 뒤 v2 에 반영하고,")
        print("     두 수치를 모두 남기는 것이 원칙입니다 (taxonomy-changelog.md).")

    if kappa is not None:
        print("\n" + "=" * 74)
        print("  이 값이 뜻하는 것")
        print("=" * 74)
        print(f"  라벨 자체가 완벽하지 않습니다. 단순 일치율 {result['agreement']*100:.0f}% 는")
        print("  분류기 정확도를 해석할 때의 현실적인 천장으로 봐야 합니다.")
        print("  분류기가 이 값을 크게 넘으면 성능이 아니라 라벨 잡음을 맞힌 것입니다.")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_file": os.path.basename(args.sample),
        "retest_file": os.path.basename(retest_path),
        "min_gap_days": min_gap,
        "pending": pending,
        **result,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n💾 {args.out}")


if __name__ == "__main__":
    main()
