"""별점 값 파싱 단일 창구.

CSV 는 ``.fillna("")`` 로 읽히므로 pandas 가 ``object`` 로 파싱한 컬럼
(타입이 섞였거나, 따옴표 붙은 숫자, 중간에 낀 헤더 행)은 ``"3.0"``,
``""``, ``"5 out of 5"`` 처럼 전부 문자열로 도착한다.

호출부마다 다르게 파싱하면 한쪽 필터는 통과시킨 값에서 다음 단계가
``ValueError`` 로 터진다. 파싱을 이 함수 하나로 모은다.
"""

DEFAULT_RATING = 3


def parse_rating(value, default=None):
    """별점을 정수로 변환한다.

    Args:
        value: 별점 값 (int/float/str/None 등 무엇이든).
        default: 숫자로 읽히지 않을 때 돌려줄 값. 기본은 ``None``.

    Returns:
        정수 별점, 실패하면 ``default``.

    >>> parse_rating("3.0")
    3
    >>> parse_rating("") is None
    True
    >>> parse_rating("5 out of 5", DEFAULT_RATING)
    3
    """
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
