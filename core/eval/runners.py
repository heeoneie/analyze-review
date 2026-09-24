"""평가 대상 시스템들 — 같은 입력을 받아 리뷰별 라벨을 낸다.

각 실행기는 `run(reviews) -> list[str]` 을 지키고, 자기가 무슨 조건으로
돌았는지를 `meta` 에 남긴다. 조건이 안 적힌 수치는 비교할 수 없다.

## 비교 설계에서 주의한 것

**배치 크기를 통제한다.** 프로덕션(core/analyzer.py)은 리뷰 200건을 한
프롬프트에 묶어 1회 호출한다. 반면 멀티에이전트와 RAG 는 건당 호출이다.
배치 채점과 건당 채점은 난이도가 다르므로, 그냥 비교하면 "멀티에이전트의
효과" 와 "건당 호출의 효과" 가 섞인다. 그래서 `single_fixed`(같은 프롬프트,
건당 호출)를 대조군으로 둔다.

    batch_fixed  vs  single_fixed   → 배치로 묶는 비용
    single_fixed vs  multi_agent    → 멀티에이전트의 순수 효과
    single_fixed vs  rag            → 검색 few-shot 의 순수 효과

**RAG 는 공정한 비교가 아니다.** RAG 는 사람이 단 라벨 N-1 개를 예시로
본다. 베이스라인은 0개를 본다. 이건 "시스템 간 비교" 가 아니라 "0-shot 대
(N-1)-shot" 비교다. 리포트에 그대로 적는다.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from core.eval.taxonomy import (
    LABEL_KEYS,
    LABELS,
    build_category_block,
)
from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

UNMAPPED = "__UNMAPPED__"
CACHE_DIR = "results/eval/cache"
MAX_WORKERS = 6


# ── 호출 캐시 ───────────────────────────────────────────────
#
# 실험을 여러 번 돌리게 되는데, 매번 API 비용을 다시 내면 사람이 실험을 덜 하게
# 된다. 프롬프트가 한 글자라도 다르면 키가 달라지므로 낡은 답이 섞이지 않는다.

def _cache_key(model: str, temperature: float, system: str, prompt: str) -> str:
    raw = f"{model}|{temperature}|{system}|{prompt}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _cached_call(prompt: str, system: str, *, model: str, temperature: float,
                 use_cache: bool = True) -> str:
    key = _cache_key(model, temperature, system, prompt)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if use_cache and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["response"]

    content = call_openai_json(
        get_client(), prompt, system_prompt=system, model=model, temperature=temperature
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt, "system": system, "model": model,
                   "temperature": temperature, "response": content}, f,
                  ensure_ascii=False)
    return content


# ── 프롬프트 ───────────────────────────────────────────────

SYSTEM_CLASSIFIER = (
    "You are a Korean food-delivery review classifier. "
    "Always answer with one of the given category keys, exactly as written."
)


def _closed_prompt_batch(reviews: list[str]) -> str:
    """닫힌 13종 + 배치. 사람이 받은 것과 같은 포함 기준을 모델에게도 준다."""
    body = "\n---\n".join(f"{i + 1}. {t[:500]}" for i, t in enumerate(reviews))
    return (
        f"배달앱 고객 리뷰 {len(reviews)}건을 각각 한 개 카테고리로 분류하세요.\n\n"
        "카테고리 (키 이름을 그대로 쓸 것, 번역 금지):\n"
        f"{build_category_block()}\n\n"
        "판정 규칙:\n"
        "- 불만이 여러 개면 가장 강하게 표현된 것 하나만 고른다.\n"
        "- 별점이 높아도 본문에 불만이 있으면 그 불만을 고른다.\n"
        "- 늦어서 식었다는 temperature, 시간만 말하면 delivery_delay.\n"
        "- 불만이 없으면 no_issue.\n\n"
        f"리뷰:\n{body}\n\n"
        "출력 JSON:\n"
        '{"categories": [{"review_number": 1, "category": "taste"}, ...]}\n'
        f"category 는 반드시 다음 중 하나: {', '.join(LABEL_KEYS)}"
    )


def _closed_prompt_single(review: str) -> str:
    return (
        "배달앱 고객 리뷰 하나를 한 개 카테고리로 분류하세요.\n\n"
        "카테고리 (키 이름을 그대로 쓸 것, 번역 금지):\n"
        f"{build_category_block()}\n\n"
        "판정 규칙:\n"
        "- 불만이 여러 개면 가장 강하게 표현된 것 하나만 고른다.\n"
        "- 별점이 높아도 본문에 불만이 있으면 그 불만을 고른다.\n"
        "- 늦어서 식었다는 temperature, 시간만 말하면 delivery_delay.\n"
        "- 불만이 없으면 no_issue.\n\n"
        f'리뷰: "{review[:500]}"\n\n'
        '출력 JSON: {"category": "키이름"}\n'
        f"category 는 반드시 다음 중 하나: {', '.join(LABEL_KEYS)}"
    )


def _parse_batch(content: str, n: int) -> list[str]:
    """배치 응답을 리뷰 순서대로 편다.

    응답에서 빠진 리뷰를 조용히 'other' 로 채우지 않는다. 그렇게 하면
    프롬프트 준수 실패가 정확도로 위장된다(기존 evaluate.py 의 결함).
    빠진 것은 빈 문자열로 남겨 채점에서 오답 + '닫힌 집합 밖' 으로 센다.
    """
    parsed = extract_json_from_text(content) or {}
    out = [""] * n
    for item in parsed.get("categories", []):
        if not isinstance(item, dict):
            continue
        num, cat = item.get("review_number"), item.get("category")
        if isinstance(num, int) and isinstance(cat, str) and 0 <= num - 1 < n:
            out[num - 1] = cat.strip()
    return out


def _map_parallel(fn, items: list) -> list:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(fn, items))


# ── 1. 닫힌 체계 · 배치 (프로덕션 배치 방식 + 고정 라벨) ────────

def run_batch_fixed(reviews: list[str], *, model: str, temperature: float,
                    batch_size: int = 50, use_cache: bool = True) -> tuple[list[str], dict]:
    preds: list[str] = []
    for start in range(0, len(reviews), batch_size):
        chunk = reviews[start:start + batch_size]
        content = _cached_call(
            _closed_prompt_batch(chunk), SYSTEM_CLASSIFIER,
            model=model, temperature=temperature, use_cache=use_cache,
        )
        preds.extend(_parse_batch(content, len(chunk)))
    return preds, {
        "system": "batch_fixed",
        "description": "닫힌 13종 · 배치 프롬프트 (프로덕션과 같은 묶음 방식)",
        "batch_size": batch_size,
        "calls": (len(reviews) + batch_size - 1) // batch_size,
        "labels_seen": 0,
    }


# ── 2. 닫힌 체계 · 건당 (배치 효과를 분리하기 위한 대조군) ──────

def run_single_fixed(reviews: list[str], *, model: str, temperature: float,
                     use_cache: bool = True) -> tuple[list[str], dict]:
    def classify(text: str) -> str:
        content = _cached_call(
            _closed_prompt_single(text), SYSTEM_CLASSIFIER,
            model=model, temperature=temperature, use_cache=use_cache,
        )
        parsed = extract_json_from_text(content) or {}
        return str(parsed.get("category", "")).strip()

    return _map_parallel(classify, reviews), {
        "system": "single_fixed",
        "description": "닫힌 13종 · 건당 호출 (배치 효과 분리용 대조군)",
        "calls": len(reviews),
        "labels_seen": 0,
    }


# ── 3. 프로덕션 프롬프트 그대로 (한국어 열린 어휘) ─────────────

#: 열린 어휘 정규화 규칙. **모델 출력을 보기 전에 확정했다.**
#: 판정은 오직 라벨 문자열만 보고 한다. 그 매핑이 점수를 올리는지 내리는지는
#: 보지 않는다. 매칭되지 않는 문자열은 조용히 other 로 접지 않고 UNMAPPED 로
#: 남겨 "프롬프트가 만들어낸 미지의 라벨" 비율을 그대로 드러낸다.
#
#: 규칙 순서가 곧 우선순위다. 더 구체적인 토큰이 앞에 와야 한다.
#: 예: "오배송" 은 wrong_item 인데, delivery_delay 의 "배송" 이 먼저 오면
#: 배달 지연으로 잘못 접힌다. 아래 순서는 그 충돌들을 정리한 결과다.
OPEN_LABEL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    # 다른 규칙의 토큰을 부분 포함하는 구체어를 먼저 둔다.
    # "양호" 는 portion 의 "양" 을 부분 포함한다 — 문제 없음 계열의 구체어를 맨 앞에.
    ("no_issue", ("양호", "문제없", "이상없", "불만없")),
    ("wrong_item", ("오배송", "잘못", "다른메뉴", "오주문", "바뀜", "다른음식")),
    ("rider", ("라이더", "배달원", "기사")),
    ("temperature", ("온도", "식음", "식어", "식은", "미지근", "차가", "눅눅")),
    ("hygiene", ("위생", "이물", "머리카락", "벌레", "상함", "청결", "냄새")),
    ("packaging", ("포장", "용기", "샘", "누출", "파손", "흘")),
    ("missing_item", ("누락", "빠짐", "미포함", "안옴", "안줌")),
    ("delivery_delay", ("지연", "늦", "배달시간", "배송", "시간", "오래")),
    ("portion", ("양부족", "양적", "양불", "적음", "소량", "건더기", "양")),
    ("price", ("가격", "비쌈", "비싼", "가성비", "비용", "요금")),
    ("store_response", ("응대", "불친절", "서비스", "고객", "환불", "전화")),
    ("taste", ("맛", "품질", "짬", "면")),
    # no_issue 는 마지막에 가깝게 — "불만 없음" 같은 표현이 위 규칙의
    # 부분 문자열에 걸리지 않게 하되, other 보다는 앞에 둔다.
    ("no_issue", ("없음", "만족", "칭찬", "긍정")),
    ("other", ("기타",)),
)


def normalize_open_label(raw: str) -> str:
    """한국어 자유 라벨을 닫힌 13종으로 사상한다 (규칙 고정, LLM 미사용)."""
    if not raw:
        return UNMAPPED

    # 1) 모델이 이미 닫힌 집합의 키를 그대로 냈으면 손대지 않는다.
    #    구분자를 먼저 지우면 "missing_item" 이 "missingitem" 이 되어
    #    정확히 맞는 라벨을 못 알아본다.
    exact = raw.strip()
    if exact in LABELS:
        return exact

    # 2) 한국어 자유 라벨은 띄어쓰기·구분자를 지우고 규칙에 건다.
    text = re.sub(r"[\s·\-_/]", "", exact)
    if text in LABELS:
        return text
    for target, keys in OPEN_LABEL_RULES:
        if any(k in text for k in keys):
            return target
    return UNMAPPED


def run_open_production(reviews: list[str], *, model: str, temperature: float,
                        batch_size: int = 50,
                        use_cache: bool = True) -> tuple[list[str], dict]:
    """core/analyzer.py 가 실제로 쓰는 프롬프트를 그대로 돌린다."""
    # 지연 임포트 — core.analyzer 는 OpenAI 클라이언트를 즉시 만든다.
    from core.utils.prompt_templates import (  # pylint: disable=import-outside-toplevel
        build_zero_shot_prompt,
        format_reviews,
    )

    raw_preds: list[str] = []
    for start in range(0, len(reviews), batch_size):
        chunk = reviews[start:start + batch_size]
        prompt = build_zero_shot_prompt(format_reviews(chunk), len(chunk))
        content = _cached_call(
            prompt,
            "You are an expert at analyzing e-commerce customer "
            "feedback and identifying patterns.",
            model=model, temperature=temperature, use_cache=use_cache,
        )
        raw_preds.extend(_parse_batch(content, len(chunk)))

    mapped = [normalize_open_label(p) for p in raw_preds]
    table = Counter(zip(raw_preds, mapped))
    unmapped = sum(1 for m in mapped if m == UNMAPPED)
    return mapped, {
        "system": "open_production",
        "description": "프로덕션 프롬프트 그대로 (한국어 열린 어휘) + 사전 확정 정규화 규칙",
        "batch_size": batch_size,
        "calls": (len(reviews) + batch_size - 1) // batch_size,
        "labels_seen": 0,
        "distinct_raw_labels": len(set(raw_preds)),
        "unmapped": unmapped,
        "unmapped_rate": round(unmapped / max(len(reviews), 1), 4),
        "mapping_table": [
            {"raw": raw, "mapped": m, "count": c}
            for (raw, m), c in table.most_common()
        ],
        "caveat": "열린 어휘는 정규화 규칙이 점수에 개입한다. 규칙은 모델 출력을 "
                  "보기 전에 확정했고 mapping_table 로 전량 감사할 수 있게 남겼다. "
                  "그래도 고정 체계 수치보다 방어력이 약하다.",
    }


# ── 4. 멀티 에이전트 (3관점 + 합의) ──────────────────────────

AGENT_PERSPECTIVES = {
    "general": "당신은 배달앱 리뷰 분석가입니다. 손님의 전체 경험을 봅니다.",
    "operational": "당신은 배달 운영 담당자입니다. 배달·포장·누락·라이더를 먼저 봅니다.",
    "product": "당신은 주방 책임자입니다. 맛·온도·양·위생을 먼저 봅니다.",
}


def run_multi_agent(reviews: list[str], *, model: str, temperature: float,
                    consensus: str = "vote",
                    use_cache: bool = True) -> tuple[list[str], dict]:
    def classify_one(text: str) -> tuple[str, float]:
        votes: list[tuple[str, float]] = []
        for name, persona in AGENT_PERSPECTIVES.items():
            content = _cached_call(
                _closed_prompt_single(text) +
                '\n신뢰도를 함께 내세요: {"category": "...", "confidence": 0.0~1.0}',
                persona, model=model, temperature=temperature, use_cache=use_cache,
            )
            parsed = extract_json_from_text(content) or {}
            cat = str(parsed.get("category", "")).strip()
            try:
                conf = float(parsed.get("confidence", 1.0))
            except (TypeError, ValueError):
                conf = 1.0
            if cat:
                votes.append((cat, conf))
            else:
                logger.debug("에이전트 %s 응답 파싱 실패", name)

        if not votes:
            return "", 0.0
        if consensus == "weighted":
            scores: dict[str, float] = {}
            for cat, conf in votes:
                scores[cat] = scores.get(cat, 0.0) + conf
            best = max(scores.items(), key=lambda kv: kv[1])[0]
        else:
            best = Counter(c for c, _ in votes).most_common(1)[0][0]
        agree = sum(1 for c, _ in votes if c == best) / len(votes)
        return best, agree

    results = _map_parallel(classify_one, reviews)
    preds = [r[0] for r in results]
    agreements = [r[1] for r in results]
    return preds, {
        "system": f"multi_agent_{consensus}",
        "description": f"3관점 에이전트 + {consensus} 합의 · 건당 호출",
        "consensus": consensus,
        "agents": list(AGENT_PERSPECTIVES),
        "calls": len(reviews) * len(AGENT_PERSPECTIVES),
        "labels_seen": 0,
        "mean_agreement": round(sum(agreements) / max(len(agreements), 1), 4),
        "unanimous_rate": round(
            sum(1 for a in agreements if a == 1.0) / max(len(agreements), 1), 4
        ),
    }


# ── 5. RAG (검색 few-shot, leave-one-out) ────────────────────

class _Retriever:
    """사람이 단 라벨을 예시 풀로 쓰는 검색기.

    원래 실험(core/experiments/rag_system.py)은 ChromaDB + all-MiniLM-L6-v2 를
    썼다. 둘 다 바꿨다:
      * ChromaDB 제거 — 예시가 250건이다. 벡터 DB 서버를 띄울 규모가 아니고,
        CLAUDE.md 도 벡터 DB 를 금지한다. numpy 코사인으로 충분하다.
      * all-MiniLM-L6-v2 는 영어 전용이다. 한국어 리뷰에 쓰면 검색 품질이
        떨어져서 RAG 를 과소평가하게 된다. 다국어 모델을 기본으로 쓰고,
        모델을 못 불러오면 문자 n-gram TF-IDF 로 떨어진다.
    무엇으로 돌았는지는 meta 의 retriever 에 남는다.
    """

    def __init__(self, texts: list[str], model_name: str):
        self.texts = texts
        self.backend = "char_ngram_tfidf"
        self.model_name = None
        self.matrix = None
        try:
            # pylint: disable=import-outside-toplevel
            from sentence_transformers import SentenceTransformer

            encoder = SentenceTransformer(model_name)
            vectors = encoder.encode(texts, normalize_embeddings=True)
            self.matrix = vectors
            self.backend = "sentence_transformers"
            self.model_name = model_name
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("임베딩 모델 로드 실패(%s) — 문자 n-gram 으로 대체", exc)
            self.matrix = self._tfidf(texts)

    @staticmethod
    def _ngrams(text: str, n: int = 3) -> Counter:
        clean = re.sub(r"\s+", "", text)
        return Counter(clean[i:i + n] for i in range(max(0, len(clean) - n + 1)))

    def _tfidf(self, texts: list[str]):
        import numpy as np  # pylint: disable=import-outside-toplevel

        docs = [self._ngrams(t) for t in texts]
        vocab = sorted({g for d in docs for g in d})
        index = {g: i for i, g in enumerate(vocab)}
        df = Counter(g for d in docs for g in d)
        n_docs = len(docs)
        mat = np.zeros((n_docs, len(vocab)), dtype="float32")
        for row, doc in enumerate(docs):
            for gram, count in doc.items():
                import math as _m  # pylint: disable=import-outside-toplevel

                mat[row, index[gram]] = count * _m.log(n_docs / (1 + df[gram]))
        norms = (mat ** 2).sum(axis=1) ** 0.5
        norms[norms == 0] = 1.0
        return mat / norms[:, None]

    def neighbours(self, i: int, k: int) -> list[int]:
        """i 번 리뷰와 가장 비슷한 k 건. **자기 자신은 반드시 뺀다.**

        자기 자신을 예시로 돌려주면 정답이 프롬프트에 그대로 들어가서
        정확도가 100% 에 수렴한다. 그건 측정이 아니다.
        """
        import numpy as np  # pylint: disable=import-outside-toplevel

        # k 가 풀 크기 이상이면 -inf 로 밀어 둔 자기 자신이 맨 뒤에 딸려 나온다.
        k = min(k, len(self.texts) - 1)
        if k <= 0:
            return []
        sims = self.matrix @ self.matrix[i]
        sims = np.asarray(sims).ravel().copy()
        sims[i] = -np.inf  # leave-one-out
        return [int(j) for j in np.argsort(-sims)[:k]]


def run_rag(  # pylint: disable=too-many-arguments
            reviews: list[str], gold_labels: list[str], *, model: str,
            temperature: float, k: int = 5,
            embed_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
            use_cache: bool = True) -> tuple[list[str], dict]:
    retriever = _Retriever(reviews, embed_model)

    def classify(i: int) -> str:
        shots = retriever.neighbours(i, k)
        examples = "\n".join(
            f'- "{reviews[j][:160]}" → {gold_labels[j]}' for j in shots
        )
        prompt = (
            "배달앱 고객 리뷰 하나를 한 개 카테고리로 분류하세요.\n\n"
            "카테고리 (키 이름을 그대로 쓸 것):\n"
            f"{build_category_block()}\n\n"
            "사람이 직접 라벨링한 비슷한 리뷰 예시:\n"
            f"{examples}\n\n"
            f'분류할 리뷰: "{reviews[i][:500]}"\n\n'
            '출력 JSON: {"category": "키이름"}'
        )
        content = _cached_call(prompt, SYSTEM_CLASSIFIER, model=model,
                               temperature=temperature, use_cache=use_cache)
        parsed = extract_json_from_text(content) or {}
        return str(parsed.get("category", "")).strip()

    preds = _map_parallel(classify, list(range(len(reviews))))
    return preds, {
        "system": "rag",
        "description": f"검색 few-shot ({k}-shot, leave-one-out) · 건당 호출",
        "k": k,
        "calls": len(reviews),
        "retriever": retriever.backend,
        "embed_model": retriever.model_name,
        "labels_seen": max(0, len(reviews) - 1),
        "caveat": "⚠️ 이건 시스템 간 공정 비교가 아니다. RAG 는 사람이 단 라벨 "
                  f"{max(0, len(reviews) - 1)}개를 예시로 본다. 베이스라인은 0개를 본다. "
                  "'0-shot 대 (N-1)-shot' 비교로 읽어야 한다. 또한 평가 대상과 예시 풀이 "
                  "같은 표본이므로(transductive) 실제 운영보다 낙관적이다.",
    }


# ── 6. 프롬프트 엔지니어링 변형 ───────────────────────────────

FEW_SHOT_EXAMPLES = """예시:
- "1시간 반 걸렸고 다 식어서 왔어요" → temperature
- "1시간 반이나 걸렸네요" → delivery_delay
- "맛있는데 양이 너무 적어요" → portion
- "머리카락이 나왔어요" → hygiene
- "단무지가 안 왔어요" → missing_item
- "국물이 다 새서 봉투가 젖었어요" → packaging
- "잘 먹었습니다" → no_issue
"""


def run_prompt_variant(  # pylint: disable=too-many-arguments
                       reviews: list[str], variant: str, *, model: str,
                       temperature: float, batch_size: int = 50,
                       use_cache: bool = True) -> tuple[list[str], dict]:
    """few_shot / cot — batch_fixed 와 배치 조건을 동일하게 맞춘 변형."""
    if variant == "few_shot":
        extra_head, extra_tail = FEW_SHOT_EXAMPLES + "\n", ""
    elif variant == "cot":
        extra_head = ""
        extra_tail = (
            "\n각 리뷰마다 단계적으로 생각하세요: (1) 언급된 문제를 모두 적는다 "
            "(2) 가장 강하게 표현된 것을 고른다 (3) 카테고리를 정한다.\n"
            "생각은 reasoning 필드에 짧게 적고, category 는 반드시 키 이름으로 내세요.\n"
            '{"categories": [{"review_number": 1, "reasoning": "...", '
            '"category": "taste"}, ...]}\n'
        )
    else:
        raise ValueError(f"알 수 없는 변형: {variant}")

    preds: list[str] = []
    for start in range(0, len(reviews), batch_size):
        chunk = reviews[start:start + batch_size]
        prompt = extra_head + _closed_prompt_batch(chunk) + extra_tail
        content = _cached_call(prompt, SYSTEM_CLASSIFIER, model=model,
                               temperature=temperature, use_cache=use_cache)
        preds.extend(_parse_batch(content, len(chunk)))

    return preds, {
        "system": f"prompt_{variant}",
        "description": {
            "few_shot": "닫힌 13종 · 배치 · 고정 few-shot 예시 7건",
            "cot": "닫힌 13종 · 배치 · Chain-of-Thought",
        }[variant],
        "batch_size": batch_size,
        "calls": (len(reviews) + batch_size - 1) // batch_size,
        "labels_seen": 0,
    }
