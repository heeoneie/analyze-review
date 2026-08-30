"""라우터가 공유하는 인증 의존성."""

import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Store, User
from backend.services import auth_service
from core import config


def current_user(
    request: Request, db: Session = Depends(get_db),
) -> User | None:
    """세션 쿠키가 가리키는 사용자. 없으면 None."""
    uid = auth_service.read_session(request.cookies.get(auth_service.SESSION_COOKIE, ""))
    if uid is None:
        return None
    return db.get(User, uid)


def require_user(user: User | None = Depends(current_user)) -> User:
    """로그인을 강제한다."""
    if user is None:
        raise HTTPException(401, "로그인이 필요합니다.")
    return user


def require_store(
    user: User = Depends(require_user), db: Session = Depends(get_db),
) -> Store:
    """로그인한 사장님의 매장.

    매장이 없으면 409 를 낸다. 401 이 아닌 이유는, 다시 로그인해도 해결되지
    않고 매장을 만들거나 이관받아야 하는 상태이기 때문이다. 프론트가 두
    경우를 구분해서 다른 화면을 띄운다.
    """
    store = db.query(Store).filter(Store.owner_user_id == user.id).first()
    if store is None:
        raise HTTPException(409, "연결된 매장이 없습니다.")
    return store


def store_or_access_code(
    request: Request, db: Session = Depends(get_db),
) -> Store | None:
    """이행기용 인증. 계정 체계와 기존 접속코드를 설정으로 가른다.

    카카오 로그인이 설정돼 있으면 로그인을 요구하고 매장을 돌려준다.
    아직 설정 전이면 기존 ACCESS_CODE 헤더 방식을 그대로 받는다. 이렇게
    해 두면 카카오 앱 심사가 끝나기 전에 이 코드를 배포해도 지금 쓰고
    계신 사장님의 서비스가 끊기지 않는다.

    None 을 돌려주는 것은 "접속코드로 통과했고 연결된 매장이 없다" 는
    뜻이다. 그 경우 답글 이력을 남길 곳이 없으므로 저장하지 않는다.
    """
    if config.KAKAO_LOGIN_ENABLED:
        user = current_user(request, db)
        if user is None:
            raise HTTPException(401, "로그인이 필요합니다.")
        store = db.query(Store).filter(Store.owner_user_id == user.id).first()
        if store is None:
            raise HTTPException(409, "연결된 매장이 없습니다.")
        return store

    verify_access_code(request.headers.get("x-access-code", ""))
    return None


def verify_access_code(supplied: str) -> None:
    """기존 접속코드 검증. 카카오 로그인 설정 전까지만 쓰인다."""
    if not config.ACCESS_CODE:
        return
    if not secrets.compare_digest(
        supplied.encode("utf-8"), config.ACCESS_CODE.encode("utf-8")
    ):
        raise HTTPException(401, "접속 코드가 맞지 않습니다.")
