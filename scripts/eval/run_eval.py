"""평가 실행 — 라벨링된 표본으로 시스템들을 돌리고 채점한다.

    # 베이스라인만
    python scripts/eval/run_eval.py evaluation/sample_v1.csv --systems batch_fixed

    # 전체 (베이스라인 + 실험 3종)
    python scripts/eval/run_eval.py evaluation/sample_v1.csv --systems all

    # API 없이 배관만 점검
    python scripts/eval/run_eval.py evaluation/sample_v1.csv --dry-run

결과는 results/eval/results_<타임스탬프>.json 에 쌓인다. 리뷰 본문이 들어가는
예측 원본은 predictions_*.jsonl 로 따로 빼고 .gitignore 에 있다.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.eval import runners  # noqa: E402  pylint: disable=wrong-import-position
from core.eval.metrics import (  # noqa: E402  pylint: disable=wrong-import-position
    Item,
    score,
    stratified_bootstrap_ci,
    top3_agreement,
)
from core.eval.taxonomy import (  # noqa: E402  pylint: disable=wrong-import-position
    EXCLUDE,
    LABEL_KEYS,
    TAXONOMY_VERSION,
    is_valid_label,
)

OUT_DIR = "results/eval"

ALL_SYSTEMS = (
    "batch_fixed",       # 대표값 — 닫힌 체계 · 프로덕션 배치 방식
    "single_fixed",      # 대조군 — 배치 효과 분리
    "open_production",   # 프로덕션 프롬프트 그대로 (열린 한국어 어휘)
    "multi_agent",       # 실험 1
    "rag",               # 실험 2
    "prompt_few_shot",   # 실험 3a
    "prompt_cot",        # 실험 3b
)


# ── 표본 로드 ───────────────────────────────────────────────

def load_labeled(path: str) -> tuple[list[dict], dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    kept, excluded, unlabeled, invalid = [], [], [], []
    for row in rows:
        label = (row.get("primary_label") or "").strip()
        if not label:
            unlabeled.append(row)
        elif label == EXCLUDE:
            excluded.append(row)
        elif not is_valid_label(label):
            invalid.append((row.get("sample_id"), label))
        else:
            kept.append(row)

    if invalid:
        raise SystemExit(
            "체계 밖의 주라벨이 있습니다. 라벨 체계는 닫힌 집합입니다.\n"
            + "\n".join(f"  #{sid}: {lbl}" for sid, lbl in invalid[:20])
            + f"\n  허용: {', '.join(LABEL_KEYS)}"
        )
    if unlabeled:
        raise SystemExit(
            f"아직 라벨이 없는 리뷰가 {len(unlabeled)}건 있습니다.\n"
            f"  python scripts/eval/label_tool.py {path}\n"
            "  라벨링을 끝낸 뒤 다시 실행하세요. 부분 라벨로 낸 수치는 표본이 아닙니다."
        )

    # 대체라벨은 검증만 하고 버리지 않는다 — 잘못된 값은 조용히 무시하면
    # lenient 수치가 슬며시 달라진다.
    bad_alt = [
        (r.get("sample_id"), r["alt_label"])
        for r in kept
        if (r.get("alt_label") or "").strip()
        and not is_valid_label(r["alt_label"].strip())
    ]
    if bad_alt:
        raise SystemExit(
            "체계 밖의 대체라벨이 있습니다:\n"
            + "\n".join(f"  #{sid}: {lbl}" for sid, lbl in bad_alt[:20])
        )

    if not kept:
        raise SystemExit(
            f"채점할 행이 없습니다. {len(excluded)}건이 전부 {EXCLUDE} 입니다."
        )

    n_alt = sum(1 for r in kept if (r.get("alt_label") or "").strip())
    meta = {
        "sample_file": os.path.basename(path),
        "rows_total": len(rows),
        "scored": len(kept),
        "excluded_no_body_or_unjudgeable": len(excluded),
        "alt_label_count": n_alt,
        "alt_label_rate": round(n_alt / max(len(kept), 1), 4),
    }
    return kept, meta


def to_items(rows: list[dict], preds: list[str]) -> list[Item]:
    items = []
    for row, pred in zip(rows, preds):
        try:
            weight = float(row.get("weight") or 1.0)
        except ValueError:
            weight = 1.0
        try:
            rating = int(float(row["rating"])) if row.get("rating") else None
        except (ValueError, KeyError):
            rating = None
        items.append(Item(
            review_id=row.get("review_id") or row.get("sample_id", ""),
            gold=row["primary_label"].strip(),
            pred=(pred or "").strip(),
            alt=(row.get("alt_label") or "").strip(),
            weight=weight,
            stratum=row.get("stratum", ""),
            rating=rating,
            text_len=len(row.get("review_text", "")),
        ))
    return items


# ── 실행 ───────────────────────────────────────────────────

def dispatch(system: str, texts: list[str], golds: list[str], args) -> tuple[list[str], dict]:
    # golds 는 rag 만 쓴다 — 나머지 실행기는 정답을 보면 안 된다.
    common = {"model": args.model, "temperature": args.temperature,
              "use_cache": not args.no_cache}
    if system == "batch_fixed":
        return runners.run_batch_fixed(texts, batch_size=args.batch_size, **common)
    if system == "single_fixed":
        return runners.run_single_fixed(texts, **common)
    if system == "open_production":
        return runners.run_open_production(texts, batch_size=args.batch_size, **common)
    if system == "multi_agent":
        return runners.run_multi_agent(texts, consensus=args.consensus, **common)
    if system == "rag":
        return runners.run_rag(texts, golds, k=args.rag_k, **common)
    if system.startswith("prompt_"):
        return runners.run_prompt_variant(
            texts, system[len("prompt_"):], batch_size=args.batch_size, **common
        )
    raise SystemExit(f"알 수 없는 시스템: {system}")


def dispatch_dry(system: str, golds: list[str]) -> tuple[list[str], dict]:
    """API 없이 배관만 점검한다. 70% 는 정답, 30% 는 임의 오답을 낸다."""
    rng = random.Random(f"dry|{system}")
    preds = []
    for gold in golds:
        if rng.random() < 0.70:
            preds.append(gold)
        else:
            preds.append(rng.choice([c for c in LABEL_KEYS if c != gold]))
    return preds, {"system": system, "description": "DRY RUN — 가짜 예측",
                   "calls": 0, "labels_seen": 0, "dry_run": True}


def evaluate_one(rows: list[dict], preds: list[str], meta: dict) -> dict:
    items = to_items(rows, preds)
    strict = score(items, LABEL_KEYS, lenient=False)
    lenient = score(items, LABEL_KEYS, lenient=True)
    return {
        "meta": meta,
        "strict": strict.to_dict(),
        "lenient": lenient.to_dict(),
        "population_estimate_strict": stratified_bootstrap_ci(items, lenient=False),
        "top3": top3_agreement(items),
        "errors": [
            {
                "review_id": it.review_id,
                "gold": it.gold,
                "alt": it.alt,
                "pred": it.pred,
                "rating": it.rating,
                "text_len": it.text_len,
                "stratum": it.stratum,
            }
            for it in items if not it.correct(lenient=False)
        ],
    }


def print_table(results: dict[str, dict]) -> None:
    print("\n" + "=" * 92)
    print("  비교표 — 엄격 채점(주라벨 일치) 기준")
    print("=" * 92)
    head = (f"  {'시스템':<20} {'정확도':>8} {'95% CI':>16} {'macro F1':>9} "
            f"{'관대':>7} {'호출':>6} {'예시':>5}")
    print(head)
    print("  " + "-" * 88)
    for name, res in results.items():
        acc = res["strict"]["overall"]["accuracy"]
        macro = res["strict"]["overall"]["macro"]["f1"]
        len_acc = res["lenient"]["overall"]["accuracy"]["point"]
        calls = res["meta"].get("calls", 0)
        seen = res["meta"].get("labels_seen", 0)
        ci = f"[{acc['ci95_low']*100:.1f}, {acc['ci95_high']*100:.1f}]"
        print(f"  {name:<20} {acc['point']*100:>7.1f}% {ci:>16} "
              f"{(macro or 0)*100:>8.1f}% {(len_acc or 0)*100:>6.1f}% "
              f"{calls:>6} {seen:>5}")
    print("  " + "-" * 88)
    print("  '예시' = 그 시스템이 본 사람 라벨 수. 0 이 아닌 행은 베이스라인과")
    print("  같은 조건이 아니다(0-shot 대 N-shot).")

    widths = [res["strict"]["overall"]["accuracy"]["width"] for res in results.values()]
    if widths and max(widths) > 0.12:
        print("\n  ⚠️  95% 신뢰구간 폭이 최대 "
              f"{max(widths)*100:.0f}%p 다. 표본이 작아서 시스템 간 차이가"
              " 구간 안에 묻힐 수 있다.")
        print("     구간이 겹치는 두 시스템을 '더 낫다' 고 말하면 안 된다.")


def main() -> None:  # pylint: disable=too-many-locals,too-many-statements
    parser = argparse.ArgumentParser(description="분류기 평가 실행")
    parser.add_argument("sample", help="라벨링이 끝난 표본 CSV")
    parser.add_argument("--systems", default="batch_fixed",
                        help=f"쉼표 구분 또는 all. 가능: {', '.join(ALL_SYSTEMS)}")
    parser.add_argument("--model", default=None, help="기본값은 core.config.LLM_MODEL")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--consensus", default="vote", choices=("vote", "weighted"))
    parser.add_argument("--rag-k", type=int, default=5)
    parser.add_argument("--no-cache", action="store_true", help="호출 캐시를 무시한다")
    parser.add_argument("--dry-run", action="store_true",
                        help="API 를 부르지 않고 배관만 점검한다")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.model is None or args.temperature is None:
        from core import config  # pylint: disable=import-outside-toplevel
        args.model = args.model or config.LLM_MODEL
        args.temperature = (
            config.LLM_TEMPERATURE if args.temperature is None else args.temperature
        )

    systems = (list(ALL_SYSTEMS) if args.systems == "all"
               else [s.strip() for s in args.systems.split(",") if s.strip()])

    rows, sample_meta = load_labeled(args.sample)
    texts = [r["review_text"] for r in rows]
    golds = [r["primary_label"].strip() for r in rows]

    print("=" * 92)
    print(f"  평가 — 체계 {TAXONOMY_VERSION} · 모델 {args.model} · T={args.temperature}")
    print("=" * 92)
    print(f"  표본        {sample_meta['sample_file']}")
    print(f"  채점 대상   {sample_meta['scored']}건")
    print(f"  제외        {sample_meta['excluded_no_body_or_unjudgeable']}건 "
          "(본문 없음·판정 불가 — 분류 대상이 아니므로 분모에서 뺌)")
    print(f"  대체라벨    {sample_meta['alt_label_count']}건 "
          f"({sample_meta['alt_label_rate']*100:.0f}%)")
    if sample_meta["alt_label_rate"] > 0.30:
        print("  ⚠️  대체라벨 비율이 30% 를 넘습니다. 관대 채점이 느슨해져 "
              "수치를 부풀릴 수 있습니다.")
    print(f"  시스템      {', '.join(systems)}")
    if args.dry_run:
        print("\n  *** DRY RUN — API 를 부르지 않습니다. 수치는 가짜입니다. ***")

    results: dict[str, dict] = {}
    for system in systems:
        print(f"\n▶ {system} …", end=" ", flush=True)
        started = time.time()
        if args.dry_run:
            preds, meta = dispatch_dry(system, golds)
        else:
            preds, meta = dispatch(system, texts, golds, args)
        meta["elapsed_sec"] = round(time.time() - started, 1)
        meta["model"] = args.model
        meta["temperature"] = args.temperature
        results[system] = evaluate_one(rows, preds, meta)
        acc = results[system]["strict"]["overall"]["accuracy"]["point"]
        print(f"정확도 {acc*100:.1f}%  ({meta['elapsed_sec']}초)")

        os.makedirs(OUT_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, f"predictions_{system}.jsonl"), "w",
                  encoding="utf-8") as f:
            for row, pred in zip(rows, preds):
                f.write(json.dumps({
                    "sample_id": row.get("sample_id"),
                    "review_id": row.get("review_id"),
                    "review_text": row.get("review_text"),
                    "gold": row["primary_label"].strip(),
                    "alt": (row.get("alt_label") or "").strip(),
                    "pred": pred,
                }, ensure_ascii=False) + "\n")

    print_table(results)

    for name, res in results.items():
        for note in res["strict"].get("notes", []):
            print(f"\n  [{name}] {note}")
        if res["meta"].get("caveat"):
            print(f"\n  [{name}] {res['meta']['caveat']}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = args.out or os.path.join(OUT_DIR, f"results_{stamp}.json")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    payload = {
        "taxonomy_version": TAXONOMY_VERSION,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "sample": sample_meta,
        "config": {"model": args.model, "temperature": args.temperature,
                   "batch_size": args.batch_size, "consensus": args.consensus,
                   "rag_k": args.rag_k},
        "systems": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과   {out_path}")
    print(f"💾 예측   {OUT_DIR}/predictions_*.jsonl  (리뷰 원문 포함 — 커밋 금지)")
    print("\n다음:")
    print(f"  python scripts/eval/make_report.py {out_path}")


if __name__ == "__main__":
    main()
