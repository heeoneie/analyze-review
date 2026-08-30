"""답글 이력 기록. 말투 학습의 재료를 모은다.

저장 원칙:

1. 손님 닉네임은 **컬럼 자체를 두지 않는다.** `ReplySample` 에 작성자 필드가
   없으므로 실수로도 들어갈 자리가 없다. 크롤러가 작성자를 주더라도 이
   모듈을 거치면서 버려진다.
2. 리뷰 본문에 섞여 들어오는 연락처·이메일은 지우고 저장한다. 사장님이
   붙여넣는 텍스트라 무엇이 섞여 있을지 통제할 수 없다.
3. 자유 텍스트 안의 닉네임까지 자동으로 걸러낼 수는 없다. "OO님 감사합니다"
   같은 문장은 남는다. 이건 한계로 알고 있어야 하는 부분이고, 보관 기간
   정책으로 보완할 몫이다.
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database.models import ReplySample

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 휴대폰: 010-1234-5678, 01012345678, 010 1234 5678
_MOBILE = re.compile(r"01[016-9][-.\s]?\d{3,4}[-.\s]?\d{4}")
# 유선: 02-123-4567, 031-123-4567, 0212345678. 지역번호는 02 또는 0NN 이다.
# 구분자가 있는 형태는 _LONG_DIGITS(9자리 이상 연속)로는 안 잡힌다.
_LANDLINE = re.compile(r"\b0(?:2|[3-6][1-5])[-.\s]?\d{3,4}[-.\s]?\d{4}\b")
# 주문번호처럼 보이는 긴 숫자열. 별점·금액과 겹치지 않게 9자리 이상만.
_LONG_DIGITS = re.compile(r"\b\d{9,}\b")


def sanitize(text: str) -> str:
    """저장 전에 연락처류를 지운다.

    리뷰 본문만이 아니라 **답글에도 똑같이 적용한다.** 사장님이 답글에
    "010-0000-0000 으로 연락 주세요" 처럼 쓰는 일이 흔하고, 손님이 남긴
    번호를 답글에 옮겨 적는 경우도 있다. 한쪽만 지우면 정책이 반쪽이다.

    휴대폰보다 유선전화를 먼저 지운다. 순서를 바꾸면 겹치는 자리에서
    한쪽이 남는다.
    """
    if not text:
        return ""
    text = _EMAIL.sub("[이메일]", text)
    text = _LANDLINE.sub("[연락처]", text)
    text = _MOBILE.sub("[연락처]", text)
    text = _LONG_DIGITS.sub("[번호]", text)
    return text.strip()


# 예전 이름. 리뷰 본문 전용이 아니게 되면서 sanitize 로 바꿨다.
sanitize_review_body = sanitize


# 인자가 여섯 개지만 전부 키워드 전용이고 각각 다른 컬럼을 가리킨다.
# 값 객체로 묶으면 호출부에서 무엇이 저장되는지 오히려 안 보인다.
def record_generated(  # pylint: disable=too-many-arguments
    db: Session,
    *,
    store_id: int,
    review_body: str,
    rating: int,
    menu: str,
    generated_reply: str,
) -> ReplySample:
    """생성 시점 기록. 아직 사장님이 채택했는지는 모른다."""
    sample = ReplySample(
        store_id=store_id,
        origin="generated",
        review_body=sanitize(review_body),
        rating=rating,
        menu=(menu or "").strip() or None,
        generated_reply=sanitize(generated_reply),
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def finalize(db: Session, sample: ReplySample, final_reply: str) -> ReplySample:
    """사장님이 실제로 게시한 답글을 확정한다.

    생성본과 다르면 `edited` 로 표시한다. 고쳐 쓴 답글은 사장님이 무엇을
    바꾸고 싶어 하는지 알려주므로 말투 학습에서 특히 값지다.
    """
    final = sanitize(final_reply)
    sample.final_reply = final
    sample.was_edited = (final != (sample.generated_reply or "").strip())
    sample.origin = "edited" if sample.was_edited else "generated"
    sample.finalized_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sample)
    return sample


def record_onboarding(
    db: Session,
    *,
    store_id: int,
    review_body: str,
    rating: int,
    owner_reply: str,
) -> ReplySample:
    """가입 때 사장님이 직접 써 넣은 답글.

    생성본이 없으므로 `generated_reply` 는 비고, 처음부터 확정 상태다.
    말투 학습의 콜드스타트를 이 행들이 채운다.
    """
    now = datetime.now(timezone.utc)
    sample = ReplySample(
        store_id=store_id,
        origin="onboarding",
        review_body=sanitize(review_body),
        rating=rating,
        generated_reply=None,
        final_reply=sanitize(owner_reply),
        was_edited=False,
        finalized_at=now,
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def style_examples(db: Session, store_id: int, limit: int = 8) -> list[ReplySample]:
    """말투 few-shot 예시. 사장님이 실제로 게시한 답글만 쓴다.

    생성만 하고 게시하지 않은 답글은 채택 근거가 없어서 제외한다. 그걸
    넣으면 모델이 자기가 만든 문장을 다시 배우는 되먹임이 생긴다.

    고쳐 쓴 답글(`edited`)을 먼저 준다. 사장님이 손을 댔다는 건 생성본이
    본인 말투와 달랐다는 뜻이라 신호가 가장 강하다.
    """
    rows = (
        db.query(ReplySample)
        .filter(
            ReplySample.store_id == store_id,
            ReplySample.final_reply.isnot(None),
        )
        .all()
    )
    priority = {"edited": 0, "onboarding": 1, "generated": 2}
    rows.sort(
        key=lambda r: (
            priority.get(r.origin, 3),
            -(r.finalized_at.timestamp() if r.finalized_at else 0),
        )
    )
    return rows[:limit]
