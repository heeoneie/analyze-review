"""채점 — 카테고리별 P/R/F1, micro/macro 평균, 신뢰구간, 재검사 일치도.

sklearn 을 쓰지 않고 직접 센다. 두 가지가 필요해서다:

1. **strict / lenient 두 채점을 같은 코드로 내야 한다.** 대체라벨을 허용한
   채점은 sklearn 의 단일 라벨 API 로 표현되지 않는다.
2. **정의되지 않은 값을 0 으로 적지 않아야 한다.** 예측이 한 번도 안 나온
   카테고리의 정밀도는 0% 가 아니라 "정의되지 않음" 이다. 0 으로 적으면
   macro 평균이 조용히 깎이고, 그걸 모델 성능이라고 말하게 된다.
   (기존 core/experiments/evaluate.py 는 zero_division=0 으로 0 을 적고
   labels=sorted(set(y_true)) 로 y_true 에 없는 예측 클래스를 표에서 누락시킨다.)

단일 라벨 다중클래스에서는 micro-P = micro-R = micro-F1 = accuracy 다.
같은 수를 네 번 적어 놓고 네 가지 증거인 것처럼 보이면 안 되므로,
`micro` 블록은 그 사실을 `equals_accuracy` 로 명시한다.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field

Z_95 = 1.959963984540054


# ── 신뢰구간 ────────────────────────────────────────────────

def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """이항 비율의 Wilson score 구간.

    표본이 작거나 비율이 0/1 에 붙을 때 정규근사(Wald)는 구간이 음수로 가거나
    폭이 0 이 된다. 이 평가는 카테고리당 support 가 한 자리인 경우가 많으므로
    Wald 를 쓰면 안 된다.
    """
    if total <= 0:
        return (0.0, 1.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _fmt_ci(successes: int, total: int) -> dict:
    lo, hi = wilson_interval(successes, total)
    return {
        "point": round(successes / total, 4) if total else None,
        "ci95_low": round(lo, 4),
        "ci95_high": round(hi, 4),
        "n": total,
        "width": round(hi - lo, 4),
    }


# ── 채점 입력 ───────────────────────────────────────────────

@dataclass
class Item:  # pylint: disable=too-many-instance-attributes
    """채점 단위 하나."""

    review_id: str
    gold: str                      # 주라벨
    pred: str                      # 모델 예측
    alt: str = ""                  # 대체라벨 (없으면 "")
    weight: float = 1.0            # 1/π — 모집단 추정용
    stratum: str = ""
    rating: int | None = None
    text_len: int = 0

    def correct(self, lenient: bool) -> bool:
        if self.pred == self.gold:
            return True
        return bool(lenient and self.alt and self.pred == self.alt)

    def effective_gold(self, lenient: bool) -> str:
        """관대 채점에서 대체라벨을 맞혔으면 그 라벨을 정답으로 본다.

        이게 "any-of" 완화의 표준적인 처리다. 대체라벨을 맞힌 건을 주라벨의
        오답으로 세면 lenient 정확도와 per-class 표가 서로 어긋난다.
        """
        if lenient and self.alt and self.pred == self.alt:
            return self.alt
        return self.gold


# ── 카테고리별 집계 ──────────────────────────────────────────

@dataclass
class ClassScore:
    label: str
    support: int = 0        # gold 가 이 라벨인 건수
    n_pred: int = 0         # 모델이 이 라벨로 예측한 건수
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float | None:
        """예측이 하나도 없으면 정의되지 않는다. 0.0 이 아니다."""
        return self.tp / self.n_pred if self.n_pred else None

    @property
    def recall(self) -> float | None:
        return self.tp / self.support if self.support else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None:
            return None
        return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)

    def as_dict(self) -> dict:
        def rnd(v):
            return None if v is None else round(v, 4)

        out = {
            "support": self.support,
            "n_pred": self.n_pred,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": rnd(self.precision),
            "recall": rnd(self.recall),
            "f1": rnd(self.f1),
        }
        # 카테고리별 재현율·정밀도는 이항 비율이다. support 가 한 자리면
        # 구간이 거의 0~1 이 되는데, 그 사실이 숫자 옆에 같이 보여야 한다.
        if self.support:
            lo, hi = wilson_interval(self.tp, self.support)
            out["recall_ci95"] = [round(lo, 4), round(hi, 4)]
        if self.n_pred:
            lo, hi = wilson_interval(self.tp, self.n_pred)
            out["precision_ci95"] = [round(lo, 4), round(hi, 4)]
        return out


@dataclass
class Report:
    mode: str                                  # "strict" | "lenient"
    n: int
    per_class: dict[str, dict] = field(default_factory=dict)
    overall: dict = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "n": self.n,
            "overall": self.overall,
            "per_class": self.per_class,
            "confusion": self.confusion,
            "notes": self.notes,
        }


def score(  # pylint: disable=too-many-locals,too-many-branches
    items: list[Item], labels: tuple[str, ...], *, lenient: bool = False
) -> Report:
    """단일 라벨 다중클래스 채점.

    labels 는 닫힌 집합 전체를 넘긴다. y_true 에 나온 라벨만 넘기면 모델이
    지어낸 라벨이 표에서 사라지고, 없는 오류가 된다.
    """
    classes = {label: ClassScore(label) for label in labels}
    confusion: dict[str, dict[str, int]] = {}
    unknown_preds = Counter()

    n_correct = 0
    w_correct = 0.0
    w_total = 0.0

    for item in items:
        gold = item.effective_gold(lenient)
        pred = item.pred
        ok = item.correct(lenient)

        if gold not in classes:
            classes[gold] = ClassScore(gold)
        if pred not in classes:
            # 모델이 닫힌 집합 밖의 라벨을 냈다. 조용히 'other' 로 접으면
            # 프롬프트 준수 실패가 정확도로 위장된다. 표에 남긴다.
            unknown_preds[pred] += 1
            classes[pred] = ClassScore(pred)

        classes[gold].support += 1
        classes[pred].n_pred += 1
        if ok:
            classes[gold].tp += 1
            n_correct += 1
            w_correct += item.weight
        else:
            classes[gold].fn += 1
            classes[pred].fp += 1
        w_total += item.weight

        confusion.setdefault(gold, {})
        confusion[gold][pred] = confusion[gold].get(pred, 0) + 1

    n = len(items)
    scored = [c for c in classes.values() if c.support or c.n_pred]

    # macro: support 가 있는 카테고리만. 데이터에 한 번도 안 나온 카테고리를
    # 0 점으로 끼워 넣으면 카테고리를 늘리는 것만으로 점수가 떨어진다.
    macro_pool = [c for c in classes.values() if c.support]

    def macro(attr: str) -> float | None:
        if not macro_pool:
            return None
        # 정의되지 않은 정밀도는 0 으로 본다(표준 관행). 몇 개가 그랬는지는
        # notes 에 남긴다.
        vals = [getattr(c, attr) or 0.0 for c in macro_pool]
        return sum(vals) / len(vals)

    def weighted(attr: str) -> float | None:
        total = sum(c.support for c in macro_pool)
        if not total:
            return None
        return sum((getattr(c, attr) or 0.0) * c.support for c in macro_pool) / total

    accuracy = n_correct / n if n else None

    report = Report(mode="lenient" if lenient else "strict", n=n)
    report.per_class = {
        c.label: c.as_dict()
        for c in sorted(scored, key=lambda c: (-c.support, c.label))
    }
    report.overall = {
        "accuracy": _fmt_ci(n_correct, n),
        "micro": {
            "precision": round(accuracy, 4) if accuracy is not None else None,
            "recall": round(accuracy, 4) if accuracy is not None else None,
            "f1": round(accuracy, 4) if accuracy is not None else None,
            "equals_accuracy": True,
            "why": "단일 라벨 다중클래스에서 micro-P/R/F1 은 정확도와 같은 값이다. "
                   "서로 다른 네 개의 증거가 아니다.",
        },
        "macro": {
            "precision": round(macro("precision"), 4) if macro("precision") is not None else None,
            "recall": round(macro("recall"), 4) if macro("recall") is not None else None,
            "f1": round(macro("f1"), 4) if macro("f1") is not None else None,
            "n_classes": len(macro_pool),
        },
        "weighted": {
            "precision": round(weighted("precision"), 4)
            if weighted("precision") is not None else None,
            "recall": round(weighted("recall"), 4)
            if weighted("recall") is not None else None,
            "f1": round(weighted("f1"), 4) if weighted("f1") is not None else None,
        },
        "population_estimate": {
            "accuracy": round(w_correct / w_total, 4) if w_total else None,
            "method": "Horvitz-Thompson (가중치 1/π). 층화 추출이므로 표본 정확도와 "
                      "모집단 정확도는 다르다. 5점 리뷰가 적게 뽑혔다면 표본 정확도가 "
                      "모집단보다 낮게 나온다.",
        },
    }
    report.confusion = confusion

    n_undef_p = sum(1 for c in macro_pool if c.precision is None)
    if n_undef_p:
        report.notes.append(
            f"카테고리 {n_undef_p}개는 모델이 한 번도 예측하지 않아 정밀도가 정의되지 "
            f"않는다. macro 평균에서는 0 으로 셌다(표준 관행). per_class 에는 null 로 "
            f"남겼다."
        )
    thin = [c.label for c in macro_pool if 0 < c.support < 5]
    if thin:
        report.notes.append(
            f"support 5건 미만 카테고리: {', '.join(sorted(thin))}. "
            f"이 카테고리들의 P/R/F1 은 신뢰구간이 사실상 0~100% 다. "
            f"단일 수치로 인용하면 안 된다."
        )
    if unknown_preds:
        top = ", ".join(f"{k or '(빈값)'}×{v}" for k, v in unknown_preds.most_common(5))
        report.notes.append(
            f"닫힌 집합 밖 예측 {sum(unknown_preds.values())}건: {top}. "
            f"프롬프트 준수 실패이며 전부 오답으로 셌다."
        )
    return report


# ── 모집단 추정 부트스트랩 ────────────────────────────────────

def stratified_bootstrap_ci(  # pylint: disable=too-many-locals
    items: list[Item], *, lenient: bool = False, rounds: int = 2000, seed: int = 20260915
) -> dict:
    """층화 부트스트랩으로 모집단 정확도의 95% 구간을 낸다.

    가중 평균의 분산은 Wilson 으로 못 낸다(가중치가 있는 순간 이항이 아니다).
    층 안에서 복원추출을 반복하는 쪽이 표본이 작을 때 더 정직하다.
    """
    by_stratum: dict[str, list[Item]] = {}
    for item in items:
        by_stratum.setdefault(item.stratum or "_", []).append(item)

    rng = random.Random(seed)
    estimates = []
    for _ in range(rounds):
        num = den = 0.0
        for block in by_stratum.values():
            for _ in range(len(block)):
                pick = block[rng.randrange(len(block))]
                den += pick.weight
                if pick.correct(lenient):
                    num += pick.weight
        if den:
            estimates.append(num / den)

    if not estimates:
        return {"point": None, "ci95_low": None, "ci95_high": None, "rounds": 0}
    estimates.sort()
    lo = estimates[int(0.025 * len(estimates))]
    hi = estimates[min(len(estimates) - 1, int(0.975 * len(estimates)))]
    w_num = sum(i.weight for i in items if i.correct(lenient))
    w_den = sum(i.weight for i in items)
    return {
        "point": round(w_num / w_den, 4) if w_den else None,
        "ci95_low": round(lo, 4),
        "ci95_high": round(hi, 4),
        "rounds": len(estimates),
        "method": "층화 복원추출 부트스트랩",
    }


# ── 재검사 일치도 ────────────────────────────────────────────

def cohen_kappa(  # pylint: disable=too-many-locals
    first: list[str], second: list[str]
) -> dict:
    """같은 사람이 같은 건을 두 번 라벨링했을 때의 일치도.

    라벨러가 한 명이면 inter-rater κ 를 낼 수 없다. 대신 intra-rater κ 를 내고,
    그 값을 **분류기 점수의 해석 상한**으로 쓴다. 사람이 자기 자신과 80% 만
    일치하는 기준으로 매긴 라벨에서 분류기가 95% 를 맞혔다면, 그 95% 는
    라벨 잡음을 맞힌 것이지 문제를 맞힌 것이 아니다.
    """
    if len(first) != len(second):
        raise ValueError("두 라벨 목록의 길이가 다르다")
    n = len(first)
    if n == 0:
        return {"kappa": None, "agreement": None, "n": 0}

    agree = sum(1 for a, b in zip(first, second) if a == b)
    po = agree / n

    labels = set(first) | set(second)
    c1, c2 = Counter(first), Counter(second)
    pe = sum((c1[label] / n) * (c2[label] / n) for label in labels)

    kappa = None if pe >= 1.0 else (po - pe) / (1 - pe)
    lo, hi = wilson_interval(agree, n)

    if kappa is None:
        interp = "모든 라벨이 한 카테고리에 몰려 κ 를 정의할 수 없다"
    elif kappa < 0.40:
        interp = "낮음 — 이 라벨로 낸 수치는 신뢰하기 어렵다"
    elif kappa < 0.60:
        interp = "보통"
    elif kappa < 0.80:
        interp = "상당함"
    else:
        interp = "높음"

    return {
        "kappa": round(kappa, 4) if kappa is not None else None,
        "agreement": round(po, 4),
        "agreement_ci95": [round(lo, 4), round(hi, 4)],
        "n": n,
        "interpretation": interp,
        "disagreements": [
            {"first": a, "second": b}
            for a, b in zip(first, second) if a != b
        ],
    }


# ── 제품이 실제로 주장하는 것: TOP 3 ──────────────────────────

def top3_agreement(  # pylint: disable=too-many-locals
    items: list[Item], *, use_weights: bool = True
) -> dict:
    """"부정 리뷰 TOP 3 문제 도출" 자체의 정확도.

    리뷰 단위 P/R/F1 이 주 지표지만, README 가 실제로 약속하는 산출물은
    집계 랭킹이다. 리뷰 단위로 좀 틀려도 TOP 3 집합이 맞으면 제품으로서는
    쓸모가 있고, 반대도 마찬가지다. 둘 다 내는 편이 정직하다.
    """
    def rank(get: str) -> list[tuple[str, float]]:
        counts: dict[str, float] = {}
        for item in items:
            label = item.gold if get == "gold" else item.pred
            if label == "no_issue":
                continue  # 불만 랭킹이다
            counts[label] = counts.get(label, 0.0) + (item.weight if use_weights else 1.0)
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    gold_rank, pred_rank = rank("gold"), rank("pred")
    gold_top3 = [k for k, _ in gold_rank[:3]]
    pred_top3 = [k for k, _ in pred_rank[:3]]
    overlap = set(gold_top3) & set(pred_top3)

    return {
        "gold_top3": gold_top3,
        "pred_top3": pred_top3,
        "overlap": sorted(overlap),
        "overlap_count": len(overlap),
        "exact_order_match": gold_top3 == pred_top3,
        "gold_ranking": [
            {"label": k, "count": round(v, 1)} for k, v in gold_rank[:6]
        ],
        "pred_ranking": [
            {"label": k, "count": round(v, 1)} for k, v in pred_rank[:6]
        ],
        "weighted": use_weights,
    }
