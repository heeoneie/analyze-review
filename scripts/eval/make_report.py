"""결과 JSON → 마크다운 리포트 초안.

    python scripts/eval/make_report.py results/eval/results_<ts>.json

개인정보: 기본값은 리뷰 원문을 한 글자도 싣지 않는다. 실패 유형에 예시가
필요하면 --examples N 으로 명시적으로 켜야 하고, 그때도 40자로 자른다.
이 레포는 공개다. 기본값이 안전한 쪽이어야 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.eval.taxonomy import (  # noqa: E402  pylint: disable=wrong-import-position
    LABELS,
    TAXONOMY_VERSION,
)

HEADLINE = "batch_fixed"  # 이력서·README 에 쓰는 대표 시스템


def pct(value, digits=1):
    return "—" if value is None else f"{value * 100:.{digits}f}%"


def _ci(block):
    return f"[{block['ci95_low'] * 100:.1f}, {block['ci95_high'] * 100:.1f}]"


def per_class_table(report: dict) -> str:
    lines = [
        "| 카테고리 | 이름 | support | P | R | F1 | R 95% CI |",
        "|---|---|---:|---:|---:|---:|:---:|",
    ]
    for key, row in report["per_class"].items():
        if not row["support"] and not row["n_pred"]:
            continue
        ko = LABELS.get(key, {}).get("ko", "—")
        ci = row.get("recall_ci95")
        ci_txt = f"[{ci[0]*100:.0f}, {ci[1]*100:.0f}]" if ci else "—"
        flag = " ⚠️" if 0 < row["support"] < 5 else ""
        lines.append(
            f"| `{key}` | {ko}{flag} | {row['support']} | {pct(row['precision'])} | "
            f"{pct(row['recall'])} | {pct(row['f1'])} | {ci_txt} |"
        )
    lines.append("")
    lines.append("⚠️ = support 5건 미만. 이 행의 P/R/F1 은 단일 수치로 인용하면 안 된다.")
    return "\n".join(lines)


def comparison_table(systems: dict) -> str:
    lines = [
        "| 시스템 | 설명 | 정확도 | 95% CI | macro F1 | 관대 채점 | API 호출 | 본 사람라벨 |",
        "|---|---|---:|:---:|---:|---:|---:|---:|",
    ]
    for name, res in systems.items():
        acc = res["strict"]["overall"]["accuracy"]
        macro = res["strict"]["overall"]["macro"]["f1"]
        lenient = res["lenient"]["overall"]["accuracy"]["point"]
        meta = res["meta"]
        mark = " **(대표)**" if name == HEADLINE else ""
        lines.append(
            f"| `{name}`{mark} | {meta.get('description', '')} | "
            f"**{pct(acc['point'])}** | {_ci(acc)} | {pct(macro)} | "
            f"{pct(lenient)} | {meta.get('calls', 0)} | {meta.get('labels_seen', 0)} |"
        )
    return "\n".join(lines)


def failure_types(  # pylint: disable=too-many-locals
    res: dict, examples: int, preds_path: str | None
) -> str:
    errors = res["errors"]
    if not errors:
        return "오분류가 없습니다."

    out = [f"오분류 **{len(errors)}건** / 채점 {res['strict']['n']}건.", ""]

    pairs = Counter((e["gold"], e["pred"]) for e in errors)
    out += ["### 혼동 쌍 (정답 → 예측)", "",
            "| 정답 | 예측 | 건수 | 비중 |", "|---|---|---:|---:|"]
    for (gold, pred), n in pairs.most_common(12):
        ko_g = LABELS.get(gold, {}).get("ko", gold)
        ko_p = LABELS.get(pred, {}).get("ko", pred) if pred else "(응답 누락)"
        out.append(f"| `{gold}` {ko_g} | `{pred or '—'}` {ko_p} | {n} | "
                   f"{n / len(errors) * 100:.0f}% |")
    out.append("")

    # 대체라벨을 맞힌 오답 — 사람 기준으로도 갈릴 만한 건
    soft = [e for e in errors if e["alt"] and e["pred"] == e["alt"]]
    if soft:
        out += [
            f"### 대체라벨을 맞힌 오답 — {len(soft)}건 "
            f"({len(soft) / len(errors) * 100:.0f}%)", "",
            "주라벨은 틀렸지만 라벨링 때 '이것도 맞다고 하기 어렵지 않다' 고 표시해 둔 "
            "라벨을 골랐다. 사람 기준으로도 갈리는 다중 이슈 리뷰이며, 엄격 채점이 "
            "과소평가하는 부분의 크기가 곧 이 숫자다.", "",
        ]

    out += ["### 별점별 오분류율", "", "| 별점 | 오분류 | 비중 |", "|---:|---:|---:|"]
    by_rating = Counter(e["rating"] for e in errors)
    for rating, n in sorted(by_rating.items(), key=lambda kv: (kv[0] is None, kv[0])):
        out.append(f"| {rating if rating is not None else '—'} | {n} | "
                   f"{n / len(errors) * 100:.0f}% |")
    out.append("")

    buckets = {"~20자": 0, "21~60자": 0, "61~150자": 0, "151자~": 0}
    for e in errors:
        n = e["text_len"]
        key = ("~20자" if n <= 20 else "21~60자" if n <= 60
               else "61~150자" if n <= 150 else "151자~")
        buckets[key] += 1
    out += ["### 본문 길이별 오분류", "", "| 길이 | 건수 |", "|---|---:|"]
    out += [f"| {k} | {v} |" for k, v in buckets.items()]
    out.append("")

    missing = sum(1 for e in errors if not e["pred"])
    if missing:
        out += [
            f"### 응답 누락 {missing}건", "",
            "모델이 해당 리뷰 번호를 아예 반환하지 않았다. 배치 프롬프트에서 "
            "생기는 실패이며, 전부 오답으로 셌다. 기존 `core/experiments/evaluate.py` "
            "는 이걸 조용히 `other` 로 채웠는데, 그러면 프롬프트 준수 실패가 "
            "정확도로 위장된다.", "",
        ]

    if examples and preds_path and os.path.exists(preds_path):
        out += [f"### 오분류 예시 {examples}건 (원문 40자로 절단)", ""]
        wrong = {e["review_id"] for e in errors}
        shown = 0
        with open(preds_path, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if row.get("review_id") not in wrong or shown >= examples:
                    continue
                text = (row.get("review_text") or "").replace("\n", " ")[:40]
                out.append(f"- `{row['gold']}` → `{row['pred'] or '—'}` … \"{text}…\"")
                shown += 1
        out.append("")
    return "\n".join(out)


def build(  # pylint: disable=too-many-locals
    data: dict, examples: int, preds_dir: str
) -> str:
    systems = data["systems"]
    head = systems.get(HEADLINE) or next(iter(systems.values()))
    head_name = HEADLINE if HEADLINE in systems else next(iter(systems))
    acc = head["strict"]["overall"]["accuracy"]
    macro = head["strict"]["overall"]["macro"]
    sample = data["sample"]

    parts = [
        "# 리뷰 분류기 정확도 측정 결과",
        "",
        "| | |", "|---|---|",
        f"| 라벨 체계 | `{data['taxonomy_version']}` |",
        f"| 측정 시각 | {data['evaluated_at']} |",
        f"| 모델 | `{data['config']['model']}` (T={data['config']['temperature']}) |",
        f"| 채점 대상 | {sample['scored']}건 |",
        f"| 제외 | {sample['excluded_no_body_or_unjudgeable']}건 (본문 없음·판정 불가) |",
        f"| 대체라벨 | {sample['alt_label_count']}건 ({pct(sample['alt_label_rate'], 0)}) |",
        "",
    ]
    if data.get("dry_run"):
        parts += ["> ⚠️ **DRY RUN 결과입니다. 아래 수치는 전부 가짜입니다.**", ""]

    parts += [
        "## 요약",
        "",
        f"대표 시스템 `{head_name}` — 정확도 **{pct(acc['point'])}** "
        f"(95% CI {_ci(acc)}), macro F1 **{pct(macro['f1'])}**, "
        f"n={acc['n']}.",
        "",
        "신뢰구간을 함께 읽어야 한다. 표본이 작으면 점추정은 구간 안 어디든 될 수 "
        f"있고, 이 측정의 구간 폭은 {acc['width'] * 100:.0f}%p 다.",
        "",
        "## 카테고리별 (엄격 채점 — 주라벨 일치)",
        "",
        per_class_table(head["strict"]),
        "",
        "### 평균",
        "",
        "| 평균 방식 | Precision | Recall | F1 |", "|---|---:|---:|---:|",
    ]
    ov = head["strict"]["overall"]
    parts += [
        f"| micro | {pct(ov['micro']['precision'])} | {pct(ov['micro']['recall'])} | "
        f"{pct(ov['micro']['f1'])} |",
        f"| macro | {pct(macro['precision'])} | {pct(macro['recall'])} | "
        f"{pct(macro['f1'])} |",
        f"| weighted | {pct(ov['weighted']['precision'])} | "
        f"{pct(ov['weighted']['recall'])} | {pct(ov['weighted']['f1'])} |",
        "",
        "> micro 평균은 단일 라벨 다중클래스에서 정확도와 같은 값이다. "
        "서로 다른 세 개의 증거가 아니다.",
        "",
    ]

    pop = head.get("population_estimate_strict", {})
    if pop.get("point") is not None:
        parts += [
            "### 모집단 추정치",
            "",
            f"층화 가중(1/π)을 적용한 전체 리뷰 기준 정확도 **{pct(pop['point'])}** "
            f"(95% CI [{pop['ci95_low']*100:.1f}, {pop['ci95_high']*100:.1f}], "
            f"{pop.get('method', '')}).",
            "",
            "표본은 불만이 실릴 만한 층을 일부러 과대추출했으므로, 표본 정확도와 "
            "모집단 정확도는 다르다. 실제 운영에서 기대할 값은 이쪽이다.",
            "",
        ]

    if head.get("top3"):
        t3 = head["top3"]
        parts += [
            "### TOP 3 문제 도출 (제품이 실제로 주장하는 산출물)",
            "",
            f"- 사람 기준 TOP 3: {', '.join(f'`{x}`' for x in t3['gold_top3'])}",
            f"- 모델 기준 TOP 3: {', '.join(f'`{x}`' for x in t3['pred_top3'])}",
            f"- 일치: **{t3['overlap_count']}/3**"
            f"{' (순서까지 일치)' if t3['exact_order_match'] else ''}",
            "",
            "리뷰 단위로 틀려도 집계 랭킹이 맞으면 제품으로서는 쓸모가 있고, 반대도 "
            "마찬가지다. 그래서 둘 다 낸다.",
            "",
        ]

    if len(systems) > 1:
        parts += [
            "## 시스템 비교", "", comparison_table(systems), "",
            "**읽는 법**",
            "",
            "- `batch_fixed` vs `single_fixed` = 리뷰를 배치로 묶는 데 드는 비용",
            "- `single_fixed` vs `multi_agent` / `rag` = 그 기법의 순수 효과 "
            "(둘 다 건당 호출이므로 조건이 같다)",
            "- **'본 사람라벨' 이 0 이 아닌 행은 베이스라인과 같은 조건이 아니다.** "
            "RAG 는 사람이 단 라벨을 예시로 보고, 베이스라인은 아무것도 보지 않는다. "
            "'0-shot 대 N-shot' 비교로 읽어야 한다.",
            "- 두 시스템의 95% CI 가 겹치면 '더 낫다' 고 말할 수 없다.",
            "",
        ]
        for name, res in systems.items():
            if res["meta"].get("caveat"):
                parts += [f"> **`{name}`** — {res['meta']['caveat']}", ""]

    parts += [
        "## 실패 유형",
        "",
        failure_types(head, examples, os.path.join(preds_dir,
                                                   f"predictions_{head_name}.jsonl")),
        "",
        "## 한계",
        "",
        f"- 표본 {acc['n']}건. 95% 신뢰구간 폭 {acc['width'] * 100:.0f}%p.",
        "- 카테고리별 support 가 한 자리인 클래스가 있다. 그 P/R/F1 은 단일 수치로 "
        "인용할 수 없다.",
        f"- 본문 없는 리뷰 {sample['excluded_no_body_or_unjudgeable']}건은 분류 대상이 "
        "아니므로 분모에서 뺐다. 전체 리뷰 대비 커버리지와 혼동하면 안 된다.",
        "- 한 매장·한 업종(중식 배달) 데이터다. 다른 업종으로 일반화되지 않는다.",
        "- 라벨러가 한 명이다. 재검사 신뢰도(intra-rater κ)를 함께 보고, 그 값을 "
        "정확도 해석의 천장으로 삼아야 한다 (`results/eval/reliability.json`).",
        "",
    ]

    notes = head["strict"].get("notes", [])
    if notes:
        parts += ["### 측정 중 기록된 주의사항", ""]
        parts += [f"- {note}" for note in notes]
        parts.append("")

    parts += [
        "## README 대체 표 초안",
        "",
        "```markdown",
        "### 분류 정확도",
        "",
        "| 지표 | 값 |",
        "|---|---|",
        f"| 정확도 | {pct(acc['point'])} (95% CI {_ci(acc)}) |",
        f"| macro F1 | {pct(macro['f1'])} |",
        f"| macro Precision / Recall | {pct(macro['precision'])} / "
        f"{pct(macro['recall'])} |",
        f"| 표본 | 사람이 직접 라벨링한 {acc['n']}건 (층화 추출) |",
        f"| 라벨 체계 | {TAXONOMY_VERSION} · 13종 닫힌 집합 |",
        f"| 모델 | {data['config']['model']} |",
        "",
        "라벨은 LLM 이 아니라 사람이 직접 달았습니다. 표본이 작아 신뢰구간이 넓으며,",
        "카테고리별 수치와 한계는 [평가 리포트](docs/evaluation/RESULTS.md)에 있습니다.",
        "```",
        "",
        "## 이력서 한 줄 초안",
        "",
        "```",
        f"배달앱 리뷰 분류기 정확도 {pct(acc['point'], 0)} · macro F1 "
        f"{pct(macro['f1'], 0)} — 직접 라벨링한 {acc['n']}건 층화 표본 기준 "
        f"(95% CI {_ci(acc)})",
        "```",
        "",
        "> 신뢰구간을 빼고 점추정만 쓰지 말 것. 면접에서 표본 크기를 물으면 "
        "구간을 같이 말할 수 있어야 한다.",
        "",
    ]
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="결과 JSON → 마크다운 리포트")
    parser.add_argument("results", help="run_eval.py 가 만든 results_*.json")
    parser.add_argument("--out", default="docs/evaluation/RESULTS.md")
    parser.add_argument("--examples", type=int, default=0,
                        help="오분류 예시 건수. 0 이면 리뷰 원문을 한 글자도 싣지 않는다")
    args = parser.parse_args()

    with open(args.results, encoding="utf-8") as f:
        data = json.load(f)

    if args.examples:
        print(f"⚠️  리뷰 원문 {args.examples}건이 40자로 잘려 리포트에 들어갑니다.")
        print("   이 레포는 공개입니다. 커밋 전에 직접 읽어 보고 개인 식별 정보를 지우세요.")

    markdown = build(data, args.examples, os.path.dirname(args.results))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"💾 {args.out}")


if __name__ == "__main__":
    main()
