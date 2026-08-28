"""카카오 로그인과 세션 쿠키.

비밀번호를 받지 않는다. 카카오가 인증을 대신하므로 우리 DB 에는 보관할
자격증명이 없고, 유출되어도 사장님의 다른 계정으로 번지지 않는다.
"""

import logging
import secrets

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import User
from core import config

logger = logging.getLogger(__name__)

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"

_SESSION_SALT = "session-v1"
_STATE_SALT = "oauth-state-v1"

# 카카오는 보통 1초 안에 답한다. 무한정 기다리면 uvicorn 워커가 묶인다.
_HTTP_TIMEOUT = 10.0


def _serializer(salt: str) -> URLSafeTimedSerializer:
    if not config.SESSION_SECRET:
        raise RuntimeError("SESSION_SECRET 이 설정되지 않았습니다.")
    return URLSafeTimedSerializer(config.SESSION_SECRET, salt=salt)


def issue_session(user_id: int) -> str:
    """세션 쿠키에 담을 서명된 값."""
    return _serializer(_SESSION_SALT).dumps({"uid": user_id})


def read_session(raw: str) -> int | None:
    """세션 쿠키에서 user_id 를 꺼낸다. 위조·만료면 None."""
    if not raw:
        return None
    try:
        data = _serializer(_SESSION_SALT).loads(
            raw, max_age=config.SESSION_MAX_AGE_DAYS * 86400,
        )
    except SignatureExpired:
        return None
    except BadSignature:
        # 서명이 안 맞는 쿠키는 조작 시도이거나 SESSION_SECRET 이 바뀐 것이다.
        logger.warning("세션 쿠키 서명 불일치")
        return None
    except RuntimeError:
        # SESSION_SECRET 미설정. 로그인 기능 자체가 꺼진 상태다.
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return uid if isinstance(uid, int) else None


def issue_state() -> str:
    """CSRF 방지용 state. 쿠키와 쿼리 양쪽에 실어 보내 대조한다."""
    return _serializer(_STATE_SALT).dumps(secrets.token_urlsafe(16))


def verify_state(cookie_value: str, query_value: str) -> bool:
    """콜백으로 돌아온 state 가 우리가 발급한 것인지 확인한다."""
    if not cookie_value or not query_value:
        return False
    if not secrets.compare_digest(cookie_value, query_value):
        return False
    try:
        # 10분이면 로그인 왕복에 충분하다. 오래된 state 는 재사용 공격으로 본다.
        _serializer(_STATE_SALT).loads(cookie_value, max_age=600)
    except (BadSignature, SignatureExpired, RuntimeError):
        return False
    return True


def authorize_url(state: str) -> str:
    """카카오 로그인 화면 주소."""
    from urllib.parse import urlencode  # pylint: disable=import-outside-toplevel

    params = {
        "client_id": config.KAKAO_REST_API_KEY,
        "redirect_uri": config.KAKAO_REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }
    return f"{KAKAO_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> str:
    """인가 코드를 액세스 토큰으로 바꾼다."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            KAKAO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": config.KAKAO_REST_API_KEY,
                "redirect_uri": config.KAKAO_REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        # 카카오 응답 본문에는 우리 client_id 가 섞여 나올 수 있어 그대로 남기지 않는다.
        logger.warning("카카오 토큰 교환 실패: status=%s", resp.status_code)
        raise RuntimeError("카카오 인증에 실패했습니다.")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("카카오 인증에 실패했습니다.")
    return token


async def fetch_profile(access_token: str) -> tuple[str, str | None]:
    """(kakao_id, nickname) 을 돌려준다."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(
            KAKAO_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        logger.warning("카카오 프로필 조회 실패: status=%s", resp.status_code)
        raise RuntimeError("카카오 사용자 정보를 가져오지 못했습니다.")
    body = resp.json()
    kakao_id = body.get("id")
    if kakao_id is None:
        raise RuntimeError("카카오 사용자 정보를 가져오지 못했습니다.")
    # 닉네임 동의를 안 한 계정도 있다. 없으면 없는 대로 둔다.
    nickname = (body.get("properties") or {}).get("nickname")
    return str(kakao_id), nickname


def upsert_user(db: Session, kakao_id: str, nickname: str | None) -> User:
    """카카오 회원번호로 사용자를 찾거나 만든다."""
    user = db.execute(
        select(User).where(User.kakao_id == kakao_id)
    ).scalar_one_or_none()
    if user is None:
        user = User(kakao_id=kakao_id, nickname=nickname)
        db.add(user)
    elif nickname and user.nickname != nickname:
        # 카카오에서 닉네임을 바꾼 경우 따라간다.
        user.nickname = nickname
    db.commit()
    db.refresh(user)
    return user
