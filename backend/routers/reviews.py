"""수집한 리뷰의 저장과 조회.

`data.py` 와 나눠 둔 이유는 배포 구성이다. `data.py` 는 CSV 업로드 때문에
pandas 를 최상단에서 임포트해서, 슬림 이미지(requirements-web.txt)에서는
라우터 자체가 빠진다. 대시보드는 사장님이 실제로 쓰는 화면이라 거기서도
살아 있어야 하므로 여기서는 pandas 를 쓰지 않고 DB 만 읽는다.

리뷰는 CSV 임시 파일이 아니라 DB 에 남긴다. 예전 `/api/data/reviews` 는
크롤링 결과를 임시 CSV 로 쓰고 그 경로를 모듈 전역 딕셔너리에 담았다.
재기동하면 사라지고, 워커가 둘이면 서로 다른 것을 보고, 무엇보다
**모든 사장님이 같은 항목 하나를 공유**했다. 매장 사이에 리뷰가 섞이는
구조라 계정 체계가 들어온 지금은 쓸 수 없다 (CLAUDE.md 의 매장 격리).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import ReplySample, Review, Store
from backend.dependencies import store_or_access_code
from backend.services.priority_service import PriorityLevel, score_and_sort

logger = logging.getLogger(__name__)
router = APIRouter()

# pylint 이 SQLAlchemy 의 `func.count()` 를 not-callable 로 오탐한다. func 는
# 런타임에 이름을 만들어 내는 접근자라 정적 분석이 짚어내지 못한다.
# pylint: disable=not-callable

# 이 별점 이하를 부정 리뷰로 본다. 우선순위 큐에 들어가는 기준이다.
NEGATIVE_RATING_THRESHOLD = 3

# 본문 길이 상한. 모델 컬럼이 String(4096) 이라 넘치면 넣을 때 잘린다.
MAX_BODY_CHARS = 4096

# 한 번의 요청에서 답글을 몇 건까지 만들지.
#
# 리뷰 한 건마다 LLM 을 부르고, 규칙에 걸리면 최대 세 번까지 다시 부른다.
# 30건을 한 요청에 몰면 몇 분이 걸려 프록시나 브라우저가 먼저 끊는다.
# 작게 끊어 돌리고 남은 수를 돌려주면, 화면이 이어서 부르며 진행률을
# 보여 줄 수 있다. 사장님도 중간에 멈출 수 있다.
REPLY_BATCH_LIMIT = 5
MAX_REPLY_BATCH = 20


class CollectRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    max_pages: int = Field(default=10, ge=1, le=100)


def _store_id(store: Store | None) -> int | None:
    """조회·저장에 쓸 매장 식별자.

    접속코드 경로에서는 매장이 없어 None 이 된다. 그 값으로 필터하면
    `store_id IS NULL` 인 이행기 행만 걸린다 — 매장이 붙은 리뷰와 섞이지
    않는다.
    """
    return store.id if store is not None else None


def _mine(store: Store | None):
    """이 매장의 리뷰만 고르는 조건.

    한 곳에서만 만든다. 매장 격리가 걸린 조건이라 라우터마다 다시 쓰면
    한 군데만 빠져도 남의 매장 리뷰가 새어 나간다.
    """
    sid = _store_id(store)
    return Review.store_id.is_(None) if sid is None else Review.store_id == sid


def _utc_iso(value: datetime | None) -> str | None:
    """시각을 UTC 오프셋이 붙은 문자열로 만든다.

    컬럼은 DateTime(timezone=True) 지만 SQLite 는 오프셋을 보존하지 않아
    읽을 때 naive 로 돌아온다. 그대로 isoformat 하면 "…T07:17:54" 가 되고,
    브라우저의 `new Date()` 는 오프셋 없는 값을 **현지 시각**으로 읽는다.
    한국이면 9시간 어긋나서 방금 모은 리뷰가 "9시간 전" 으로 표시된다.

    쓸 때 항상 UTC(`_utcnow`) 라서 naive 면 UTC 로 붙여 주면 된다.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _replies_by_review(db: Session, reviews: list[Review]) -> dict[int, ReplySample]:
    """리뷰 id -> 그 리뷰에 만들어 둔 답글. 목록 한 번에 같이 싣는다."""
    ids = [r.id for r in reviews]
    if not ids:
        return {}
    rows = db.scalars(
        select(ReplySample).where(ReplySample.review_id.in_(ids))
        .order_by(
            # 게시한 답글이 먼저다. "다시 만들기" 를 누를 때마다 표본이
            # 새로 쌓이는데, 사장님이 두 번째를 복사해 게시하고 세 번째를
            # 또 만들면 최신순으로는 게시 안 한 세 번째가 이긴다. 그러면
            # 이미 답한 리뷰가 화면에 "만들어 둔 답글" 로 남는다.
            ReplySample.final_reply.is_(None),
            ReplySample.id.desc(),
        )
    )
    best: dict[int, ReplySample] = {}
    for row in rows:
        best.setdefault(row.review_id, row)
    return best


def _to_row(review: Review) -> dict:
    """프론트가 쓰는 모양으로 변환.

    화면 컴포넌트와 `priority_service` 가 CSV 시절의 `Ratings`/`Reviews`
    키를 그대로 쓴다. 여기서 한 번만 맞춰 주면 양쪽을 건드리지 않아도 된다.
    """
    return {
        "id": review.id,
        "Ratings": review.rating,
        "Reviews": review.body,
        "title": review.title or "",
        "source": review.source,
        "product_url": review.product_url or "",
        "created_at": _utc_iso(review.ingested_at),
    }


def _paginate(rows: list[dict], page: int, page_size: int) -> dict:
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "reviews": rows[start:start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/collect")
async def collect_reviews(
    request: CollectRequest,
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """상품 URL 에서 리뷰를 긁어 이 매장 앞으로 저장한다."""
    # curl_cffi 는 슬림 이미지에 들어 있지만, 없는 구성에서도 목록 조회는
    # 계속 되도록 여기서만 불러온다.
    try:
        from backend.services.crawler_service import (  # pylint: disable=import-outside-toplevel
            crawl_reviews,
        )
    except ImportError:
        logger.exception("크롤러를 불러오지 못했습니다")
        raise HTTPException(
            503, "이 서버에는 수집 기능이 설치돼 있지 않습니다."
        ) from None

    try:
        platform, result = await crawl_reviews(request.url.strip(), request.max_pages)
    except ValueError as exc:
        # 지원하지 않는 플랫폼, 상품 ID 추출 실패 — 사장님이 고칠 수 있다.
        raise HTTPException(400, str(exc)) from exc
    except Exception:
        logger.exception("리뷰 수집 실패")
        raise HTTPException(
            502, "리뷰를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요."
        ) from None

    saved, skipped = _persist(
        db, store, platform, request.url.strip(), result.get("reviews", []),
    )

    return {
        "platform": platform,
        "saved": saved,
        "skipped": skipped,
        "total_count": result.get("total_count", 0),
        "rating_average": result.get("rating_average", 0.0),
    }


def _existing_keys(db: Session, store: Store | None, url: str) -> set[tuple[int, str]]:
    """이 매장이 이 상품에서 이미 담아 둔 (별점, 본문) 짝."""
    stmt = (
        select(Review.rating, Review.body)
        .where(_mine(store))
        .where(Review.product_url == url[:1024])
    )
    return set(db.execute(stmt).all())


def _persist(
    db: Session, store: Store | None, platform: str, url: str, reviews: list[dict],
) -> tuple[int, int]:
    """수집 결과를 Review 행으로 남기고 (담은 수, 건너뛴 수) 를 돌려준다.

    별점이 1~5 를 벗어나거나 본문이 빈 항목은 건너뛴다. CHECK 제약에
    걸려 트랜잭션 전체가 깨지면 멀쩡한 리뷰까지 통째로 버려진다.

    이미 담은 리뷰도 건너뛴다. 사장님은 새 리뷰를 보려고 같은 상품을
    다시 수집한다. 막지 않으면 누를 때마다 목록이 두 배가 된다.

    무엇이 "같은 리뷰"인지는 (별점, 본문) 으로 본다. 수집기가 리뷰
    식별자도 작성자도 날짜도 주지 않아서 이것 말고 쓸 게 없다. 손님
    둘이 똑같이 "맛있어요" 5점을 남겼다면 한 건으로 합쳐진다 — 매번
    전부를 두 배로 늘리는 것보다는 이쪽이 낫다.
    """
    seen = _existing_keys(db, store, url)
    rows = []
    skipped = 0

    for item in reviews:
        body = str(item.get("Reviews") or "").strip()
        if not body:
            continue
        try:
            rating = int(item.get("Ratings"))
        except (TypeError, ValueError):
            continue
        if not 1 <= rating <= 5:
            continue

        body = body[:MAX_BODY_CHARS]
        key = (rating, body)
        # 같은 수집 안에 똑같은 항목이 두 번 올 수도 있다. seen 에 바로
        # 넣어 두면 DB 를 다시 읽지 않고 그것까지 걸러진다.
        if key in seen:
            skipped += 1
            continue
        seen.add(key)

        rows.append(Review(
            store_id=_store_id(store),
            source=platform,
            product_url=url[:1024],
            rating=rating,
            title=(str(item.get("title") or "").strip() or None),
            body=body,
        ))

    if rows:
        db.add_all(rows)
        db.commit()
    return len(rows), skipped


@router.get("")
def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """수집한 리뷰 목록. 최근 것부터."""
    where = _mine(store)
    total = db.scalar(select(func.count()).select_from(Review).where(where)) or 0

    stmt = (
        select(Review)
        .where(where)
        .order_by(Review.ingested_at.desc(), Review.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    found = list(db.scalars(stmt))
    replies = _replies_by_review(db, found)
    rows = []
    for review in found:
        row = _to_row(review)
        sample = replies.get(review.id)
        if sample:
            row["reply"] = sample.final_reply or sample.generated_reply or ""
            row["sample_id"] = sample.id
            row["reply_posted"] = sample.final_reply is not None
        rows.append(row)

    return {
        "reviews": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/prioritized")
def list_prioritized(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: PriorityLevel = Query(None, description="critical/high/medium/low"),
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """먼저 답해야 할 부정 리뷰부터 정렬해서 돌려준다.

    점수를 매기려면 후보 전체를 봐야 해서 부정 리뷰는 한 번에 읽는다.
    한 매장의 부정 리뷰 규모에서는 문제가 되지 않는다. 페이지네이션은
    정렬이 끝난 뒤에 자른다.
    """
    stmt = (
        select(Review)
        .where(_mine(store))
        .where(Review.rating <= NEGATIVE_RATING_THRESHOLD)
    )
    scored = score_and_sort([_to_row(r) for r in db.scalars(stmt)])

    if level:
        scored = [r for r in scored if r["priority"]["level"] == level.value]

    return _paginate(scored, page, page_size)


@router.get("/summary")
def summary(
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """대시보드 상단에 쓰는 숫자 몇 개. 분석 파이프라인 없이 셀 수 있는 것만."""
    where = _mine(store)

    total = db.scalar(select(func.count()).select_from(Review).where(where)) or 0
    negative = db.scalar(
        select(func.count()).select_from(Review)
        .where(where).where(Review.rating <= NEGATIVE_RATING_THRESHOLD)
    ) or 0
    average = db.scalar(select(func.avg(Review.rating)).where(where))
    latest = db.scalar(select(func.max(Review.ingested_at)).where(where))

    return {
        "total": total,
        "negative": negative,
        "negative_rate": round(negative / total, 3) if total else 0.0,
        "rating_average": round(float(average), 2) if average is not None else 0.0,
        "last_collected_at": _utc_iso(latest),
    }
