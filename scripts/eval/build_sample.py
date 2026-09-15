"""평가 표본 추출 — 층화 무작위 추출 + 포함확률 기록.

왜 "3점 이하 전량 + 4~5점 무작위" 가 아니라 층화인가:

    배달앱 리뷰는 별점 인플레이션이 심하다. 실측(REPLY_GENERATOR.md)으로
    441건 중 5점이 405건(92%), 3점 이하는 17건(4%)이다. 3점 이하를 전량
    가져와도 부정 카테고리 12종에 17건이 흩어져 클래스당 support 가 1~2건이
    된다. 그 상태의 per-class F1 은 신뢰구간이 0~100% 에 걸쳐 숫자가 아니다.

    그리고 실제 불만의 상당수가 5점 리뷰 본문에 숨어 있다
    ("맛있는데 양이 너무 적어요"). 별점만으로 자르면 그걸 통째로 놓친다.

층 구성:

    S1  별점 ≤3, 본문 있음                     전수 (π=1)
    S2  별점 4,  본문 있음                     전수 (π=1)
    S3  별점 5,  본문 있음, 불만어휘 검출       높은 비율
    S4  별점 5,  본문 있음, 불만어휘 미검출     낮은 비율 — 그러나 반드시 포함
    --  본문 없음                              제외 (분류 대상이 아님)

S4 를 넣는 이유가 이 설계의 핵심이다. 어휘 사전으로 거른 것만 라벨링하면
사전이 놓친 불만은 영원히 보이지 않고, 재현율 추정이 구조적으로 불가능해진다.
S4 가 있어야 "사전이 불만의 몇 %를 놓치는가"를 숫자로 말할 수 있다.

어휘 사전은 규칙 기반이다. 표본 구성에 LLM 을 개입시키지 않는다.

포함확률 π 를 행마다 남기므로 채점 때 두 가지를 낼 수 있다:
    - 표본 기준 지표 (불균형이 완화된 조건부 추정)
    - 모집단 추정치 (가중치 1/π, Horvitz-Thompson)

사용법:
    python scripts/eval/build_sample.py --csv <리뷰CSV> --out evaluation/sample_v1.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.eval.taxonomy import (  # noqa: E402  pylint: disable=wrong-import-position
    TAXONOMY_VERSION,
    has_complaint_signal,
)

# 배달앱 리뷰 내보내기 형식 ↔ 표준 컬럼명
COLUMN_ALIASES = {
    "review_text": ("리뷰내용", "리뷰", "review_text", "Reviews", "content"),
    "rating": ("별점", "평점", "rating", "Ratings", "score"),
    "ordered_at": ("작성일시", "작성일", "created_at", "date"),
    "menu": ("주문메뉴", "메뉴", "menu"),
    "order_type": ("주문유형", "order_type"),
}

STRATUM_LABELS = {
    "S1": "별점 ≤3, 본문 있음",
    "S2": "별점 4, 본문 있음",
    "S3": "별점 5, 불만어휘 검출",
    "S4": "별점 5, 불만어휘 미검출",
}

SAMPLE_COLUMNS = [
    "sample_id",
    "review_id",
    "review_text",
    "rating",
    "ordered_at",
    "menu",
    "stratum",
    "inclusion_prob",
    "weight",
    "primary_label",
    "alt_label",
    "notes",
    "labeled_at",
]


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """CSV 의 실제 컬럼명을 표준 이름에 대응시킨다."""
    resolved = {}
    for standard, candidates in COLUMN_ALIASES.items():
        for candidate in candidates:
            if candidate in df.columns:
                resolved[standard] = candidate
                break
    missing = {"review_text", "rating"} - set(resolved)
    if missing:
        raise SystemExit(
            f"필수 컬럼을 찾지 못했습니다: {sorted(missing)}\n"
            f"  CSV 컬럼: {list(df.columns)}\n"
            f"  허용 이름: {json.dumps(COLUMN_ALIASES, ensure_ascii=False, indent=2)}"
        )
    return resolved


def _assign_stratum(rating: int, text: str) -> str:
    if not text.strip():
        return "EMPTY"
    if rating <= 3:
        return "S1"
    if rating == 4:
        return "S2"
    return "S3" if has_complaint_signal(text) else "S4"


def _review_id(text: str, rating: int, ordered_at: str) -> str:
    """원문 해시 기반 안정 ID. 원문을 다시 노출하지 않으면서 건을 지목할 수 있다."""
    raw = f"{rating}|{ordered_at}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def load_and_stratify(
    csv_path: str, dedup: bool = True
) -> tuple[pd.DataFrame, dict[str, str], int]:
    df = pd.read_csv(csv_path)
    cols = _resolve_columns(df)

    out = pd.DataFrame()
    out["review_text"] = df[cols["review_text"]].fillna("").astype(str).str.strip()
    out["rating"] = pd.to_numeric(df[cols["rating"]], errors="coerce")
    out["ordered_at"] = (
        df[cols["ordered_at"]].fillna("").astype(str) if "ordered_at" in cols else ""
    )
    out["menu"] = df[cols["menu"]].fillna("").astype(str) if "menu" in cols else ""

    bad_rating = out["rating"].isna().sum()
    if bad_rating:
        print(f"⚠️  별점을 숫자로 읽을 수 없는 행 {bad_rating}건을 버립니다.")
        out = out[out["rating"].notna()]
    out["rating"] = out["rating"].astype(int)

    before = len(out)
    if dedup:
        out = out.drop_duplicates(subset=["review_text", "rating", "ordered_at"])
    removed = before - len(out)
    if removed:
        rate = removed / before
        print(f"ℹ️  중복 {removed}건 제거 (본문+별점+작성일시 동일)")
        if rate > 0.10:
            print(
                f"⚠️  중복 비율이 {rate:.0%} 로 높습니다. 배달앱 리뷰는 '맛있어요' 같은\n"
                "     짧은 본문이 서로 다른 손님에게서 실제로 반복됩니다. 작성일시에\n"
                "     시각(HH:MM)이 없으면 서로 다른 리뷰가 중복으로 잘려 모집단이\n"
                "     줄어듭니다. 원본 CSV 의 작성일시 정밀도를 확인하고, 실제 중복이\n"
                "     아니라면 --no-dedup 으로 다시 뽑으세요."
            )

    out["review_id"] = [
        _review_id(r.review_text, r.rating, r.ordered_at) for r in out.itertuples()
    ]
    out["stratum"] = [
        _assign_stratum(r.rating, r.review_text) for r in out.itertuples()
    ]
    return out.reset_index(drop=True), cols, removed


def allocate(pop: pd.DataFrame, target: int, min_s4: int) -> dict[str, int]:
    """층별 추출 건수 결정.

    S1·S2 는 전수. 남는 몫을 S3 에 우선 주되, S4 에 최소 인원을 확보한다.
    S4 가 없으면 어휘 사전의 누락률을 추정할 수 없다 — 이건 협상 대상이 아니다.
    """
    sizes = pop["stratum"].value_counts().to_dict()
    take = {
        "S1": sizes.get("S1", 0),
        "S2": sizes.get("S2", 0),
    }
    remaining = max(0, target - take["S1"] - take["S2"])

    s3_pop, s4_pop = sizes.get("S3", 0), sizes.get("S4", 0)
    s4_take = min(s4_pop, max(min_s4, 0))
    s3_take = min(s3_pop, max(0, remaining - s4_take))
    # S3 를 다 담고도 자리가 남으면 S4 를 더 채운다.
    leftover = remaining - s3_take - s4_take
    if leftover > 0:
        s4_take = min(s4_pop, s4_take + leftover)

    take["S3"] = s3_take
    take["S4"] = s4_take
    return take


def draw(pop: pd.DataFrame, take: dict[str, int], seed: int) -> pd.DataFrame:
    parts = []
    for stratum, n in take.items():
        block = pop[pop["stratum"] == stratum]
        if block.empty or n <= 0:
            continue
        picked = block if n >= len(block) else block.sample(n=n, random_state=seed)
        pi = len(picked) / len(block)
        picked = picked.copy()
        picked["inclusion_prob"] = round(pi, 6)
        picked["weight"] = round(1 / pi, 6)
        parts.append(picked)

    if not parts:
        raise SystemExit("표본이 비었습니다. 본문 있는 리뷰가 하나도 없습니다.")

    sample = pd.concat(parts, ignore_index=True)
    # 라벨링 순서를 섞는다. 층 순서대로 두면 라벨러가 "지금은 5점 구간" 을
    # 알아채고 기준이 그쪽으로 끌려간다.
    sample = sample.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    sample.insert(0, "sample_id", range(1, len(sample) + 1))
    for col in ("primary_label", "alt_label", "notes", "labeled_at"):
        sample[col] = ""
    return sample[SAMPLE_COLUMNS]


def report(  # pylint: disable=too-many-locals
    pop: pd.DataFrame, sample: pd.DataFrame, take: dict[str, int]
) -> None:
    sizes = pop["stratum"].value_counts().to_dict()
    body = len(pop) - sizes.get("EMPTY", 0)

    print("\n" + "=" * 72)
    print("  모집단")
    print("=" * 72)
    print(f"  전체 리뷰            {len(pop):>6}")
    print(f"  본문 없음 (제외)     {sizes.get('EMPTY', 0):>6}"
          f"  ({sizes.get('EMPTY', 0) / max(len(pop), 1) * 100:.1f}%)")
    print(f"  분류 대상 (본문 있음) {body:>6}")

    print("\n" + "=" * 72)
    print("  층화 추출")
    print("=" * 72)
    print(f"  {'층':<4} {'정의':<28} {'모집단':>7} {'추출':>6} {'π':>8} {'가중치':>8}")
    print("  " + "-" * 68)
    for stratum in ("S1", "S2", "S3", "S4"):
        n_pop, n_take = sizes.get(stratum, 0), take.get(stratum, 0)
        pi = n_take / n_pop if n_pop else 0.0
        w = 1 / pi if pi else 0.0
        print(f"  {stratum:<4} {STRATUM_LABELS[stratum]:<28} {n_pop:>7} {n_take:>6} "
              f"{pi:>8.3f} {w:>8.2f}")
    print("  " + "-" * 68)
    print(f"  {'합계':<33} {body:>7} {len(sample):>6}")

    print("\n  별점 분포(표본):")
    for rating, cnt in sorted(sample["rating"].value_counts().items()):
        print(f"    {rating}점  {cnt:>4}")

    # ── 솔직한 한계 경고 ──────────────────────────────────────
    warnings = []
    likely_complaints = take.get("S1", 0) + take.get("S2", 0) + take.get("S3", 0)
    if likely_complaints < 60:
        warnings.append(
            f"불만이 실릴 가능성이 있는 표본이 {likely_complaints}건뿐입니다. "
            "불만 카테고리 12종에 나누면 클래스당 5건 미만이 되어\n"
            "     per-class F1 의 신뢰구간이 사실상 0~100% 가 됩니다. "
            "기간을 넓히거나 다른 지점 데이터를 합치는 것을 권합니다."
        )
    if take.get("S4", 0) < 40:
        warnings.append(
            f"S4 가 {take.get('S4', 0)}건입니다. 어휘 사전 누락률 추정의 "
            "신뢰구간이 매우 넓어집니다 (--min-s4 로 늘리세요)."
        )
    if sizes.get("EMPTY", 0) / max(len(pop), 1) > 0.2:
        warnings.append(
            f"본문 없는 리뷰가 {sizes.get('EMPTY', 0) / len(pop) * 100:.0f}% 입니다. "
            "이 건들은 분류 대상이 아니므로 분모에서 빠졌다는 사실을\n"
            "     리포트에 반드시 적으세요. 빼놓고 말하면 커버리지를 부풀리는 것이 됩니다."
        )
    if warnings:
        print("\n" + "=" * 72)
        print("  ⚠️  한계 — 리포트에 그대로 옮겨 적을 것")
        print("=" * 72)
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}")


def main() -> None:
    parser = argparse.ArgumentParser(description="평가 표본 층화 추출")
    parser.add_argument("--csv", required=True, help="원본 리뷰 CSV 경로")
    parser.add_argument("--out", default="evaluation/sample_v1.csv", help="표본 출력 경로")
    parser.add_argument("--target", type=int, default=250, help="목표 표본 크기")
    parser.add_argument("--min-s4", type=int, default=60,
                        help="S4(사전 미검출 5점) 최소 건수. 사전 누락률 추정에 필요")
    parser.add_argument("--seed", type=int, default=20260915, help="난수 시드")
    parser.add_argument("--no-dedup", action="store_true",
                        help="동일 본문+별점+작성일시 중복 제거를 건너뛴다")
    args = parser.parse_args()

    if os.path.exists(args.out):
        raise SystemExit(
            f"{args.out} 이 이미 있습니다. 덮어쓰면 라벨이 날아갑니다.\n"
            "  다른 --out 을 쓰거나, 라벨이 없는 것이 확실하면 직접 지우세요."
        )

    pop, cols, deduped = load_and_stratify(args.csv, dedup=not args.no_dedup)
    take = allocate(pop, args.target, args.min_s4)
    sample = draw(pop, take, args.seed)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    sample.to_csv(args.out, index=False, encoding="utf-8-sig")

    meta = {
        "taxonomy_version": TAXONOMY_VERSION,
        "source_csv": os.path.basename(args.csv),
        "source_columns": cols,
        "deduplicated_rows": int(deduped),
        "dedup_enabled": not args.no_dedup,
        "seed": args.seed,
        "target": args.target,
        "min_s4": args.min_s4,
        "population_total": int(len(pop)),
        "population_by_stratum": {
            k: int(v) for k, v in pop["stratum"].value_counts().items()
        },
        "taken_by_stratum": {k: int(v) for k, v in take.items()},
        "sample_size": int(len(sample)),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = os.path.splitext(args.out)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    report(pop, sample, take)
    print(f"\n💾 표본   {args.out}  ({len(sample)}건)")
    print(f"💾 메타   {meta_path}")
    print("\n다음:")
    print(f"  python scripts/eval/label_tool.py {args.out}")
    print("\n⚠️  표본 파일에는 손님 리뷰 원문이 들어 있습니다. 커밋하지 마세요.")


if __name__ == "__main__":
    main()
