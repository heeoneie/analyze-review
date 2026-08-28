"""카카오 로그인 · 세션 · 매장 이관."""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Store, User
from backend.dependencies import current_user, require_user
from backend.services import auth_service
from core import config

logger = logging.getLogger(__name__)
router = APIRouter()


def _cookie_secure() -> bool:
    """로컬 개발(http)에서는 secure 쿠키가 브라우저에 저장되지 않는다."""
    return not config.KAKAO_REDIRECT_URI.startswith("http://localhost")


def _require_login_enabled() -> None:
    if not config.KAKAO_LOGIN_ENABLED:
        raise HTTPException(
            503,
            "카카오 로그인이 설정되지 않았습니다. "
            "KAKAO_REST_API_KEY, KAKAO_REDIRECT_URI, SESSION_SECRET 을 확인하세요.",
        )


@router.get("/config")
def auth_config():
    """프론트가 로그인 버튼을 띄울지 판단하는 데 쓴다."""
    return {
        "kakao_login_enabled": config.KAKAO_LOGIN_ENABLED,
        # 이관이 끝났으면 접속코드 입력 화면을 더 보여줄 필요가 없다.
        "access_code_fallback": bool(config.ACCESS_CODE),
    }


@router.get("/kakao/login")
def kakao_login():
    """카카오 로그인 화면으로 보낸다."""
    _require_login_enabled()
    state = auth_service.issue_state()
    resp = RedirectResponse(auth_service.authorize_url(state), status_code=302)
    resp.set_cookie(
        auth_service.STATE_COOKIE, state,
        max_age=600, httponly=True, samesite="lax", secure=_cookie_secure(),
    )
    return resp


@router.get("/kakao/callback")
async def kakao_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    """카카오가 돌려보내는 지점. 세션을 심고 앱으로 되돌린다."""
    _require_login_enabled()

    if error:
        # 사용자가 동의 화면에서 취소한 경우가 대부분이다. 에러 화면 대신 앱으로.
        logger.info("카카오 로그인 취소/실패: %s", error)
        return RedirectResponse("/?login=cancelled", status_code=302)

    if not auth_service.verify_state(
        request.cookies.get(auth_service.STATE_COOKIE, ""), state
    ):
        # state 불일치는 CSRF 이거나 오래된 로그인 시도다. 둘 다 진행하면 안 된다.
        raise HTTPException(400, "로그인 요청이 유효하지 않습니다. 다시 시도해 주세요.")

    if not code:
        raise HTTPException(400, "인가 코드가 없습니다.")

    try:
        token = await auth_service.exchange_code(code)
        kakao_id, nickname = await auth_service.fetch_profile(token)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc

    user = auth_service.upsert_user(db, kakao_id, nickname)

    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        auth_service.SESSION_COOKIE, auth_service.issue_session(user.id),
        max_age=config.SESSION_MAX_AGE_DAYS * 86400,
        httponly=True, samesite="lax", secure=_cookie_secure(),
    )
    resp.delete_cookie(auth_service.STATE_COOKIE)
    return resp


@router.get("/me")
def me(user: User | None = Depends(current_user), db: Session = Depends(get_db)):
    """로그인 상태와 연결된 매장. 로그인 전에도 200 으로 답한다."""
    if user is None:
        return {"authenticated": False, "user": None, "store": None}
    store = db.query(Store).filter(Store.owner_user_id == user.id).first()
    return {
        "authenticated": True,
        "user": {"id": user.id, "nickname": user.nickname},
        "store": {"id": store.id, "name": store.name} if store else None,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(auth_service.SESSION_COOKIE)
    return {"ok": True}


class ClaimStoreRequest(BaseModel):
    access_code: str = Field(min_length=1, max_length=128)


@router.post("/claim-store")
def claim_store(
    body: ClaimStoreRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """기존 접속코드로 매장 소유권을 가져온다 (1회성 이관).

    지금 서비스를 쓰고 계신 사장님은 이미 접속코드를 알고 있다. 카카오
    로그인 후 그 코드를 한 번 넣으면 매장이 계정에 붙는다. 코드를 모르는
    사람이 먼저 로그인해서 매장을 가로채는 것도 이걸로 막힌다.

    한 번 이관되면 같은 이름의 매장은 다시 만들 수 없다.
    """
    if not config.ACCESS_CODE:
        raise HTTPException(409, "이관할 매장이 없습니다.")

    existing = db.query(Store).filter(Store.owner_user_id == user.id).first()
    if existing:
        return {"store": {"id": existing.id, "name": existing.name}}

    # 이름이 같은 매장이 이미 있으면 누군가 먼저 이관한 것이다.
    claimed = db.execute(
        select(Store).where(Store.name == config.STORE_NAME)
    ).scalar_one_or_none()
    if claimed:
        raise HTTPException(409, "이미 다른 계정에 연결된 매장입니다.")

    if not secrets.compare_digest(
        body.access_code.encode("utf-8"), config.ACCESS_CODE.encode("utf-8")
    ):
        raise HTTPException(401, "접속 코드가 맞지 않습니다.")

    store = Store(owner_user_id=user.id, name=config.STORE_NAME)
    db.add(store)
    try:
        db.commit()
    except IntegrityError:
        # 위 조회와 여기 사이에 다른 요청이 먼저 이관했다. 유일 제약이
        # 잡아 준다 — 조회만으로는 동시 요청 둘이 모두 통과한다.
        db.rollback()
        raise HTTPException(409, "이미 다른 계정에 연결된 매장입니다.") from None
    db.refresh(store)
    logger.info("매장 이관 완료: store_id=%s user_id=%s", store.id, user.id)
    return {"store": {"id": store.id, "name": store.name}}
