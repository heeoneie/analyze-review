"""YouTube Data API v3 댓글 수집 서비스 — 리스크 트리거 키워드 다중 검색"""

import logging
from datetime import datetime, timezone

import requests
from requests.exceptions import RequestException

from core import config

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# 산업별 리스크 트리거 키워드 (영어 — 글로벌 타겟)
RISK_TRIGGERS: dict[str, list[str]] = {
    "ecommerce": ["defect", "scam", "recall", "fake", "lawsuit", "refund"],
    "hospital":  ["malpractice", "death", "infection", "fraud", "lawsuit"],
    "finance":   ["scam", "data breach", "fraud", "frozen account", "SEC"],
    "gaming":    ["pay to win", "rigged", "dead game", "toxic", "crunch"],
}


def _search_videos(query: str, max_results: int, api_key: str) -> list[dict]:
    """YouTube 검색으로 관련 영상 목록 반환 (영어 콘텐츠 우선)"""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": "en",
        "key": api_key,
    }
    resp = requests.get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    videos = []
    seen_ids: set[str] = set()
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id or not snippet or video_id in seen_ids:
            continue
        seen_ids.add(video_id)
        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_name": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
        })
    return videos


def _get_video_comments(video_id: str, max_results: int, api_key: str) -> list[dict]:
    """YouTube 영상 댓글 수집 (댓글 비활성 영상 예외 처리 포함)"""
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "key": api_key,
    }
    try:
        resp = requests.get(
            f"{YOUTUBE_API_BASE}/commentThreads", params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except RequestException as e:
        logger.warning("댓글 수집 실패 videoId=%s: %s", video_id, e)
        return []

    comments = []
    for item in data.get("items", []):
        try:
            item_snippet = item.get("snippet", {})
            top = item_snippet.get("topLevelComment", {}).get("snippet", {})
            text = top.get("textOriginal", top.get("textDisplay", "")).strip()
            if not text:
                continue
            comments.append({
                "text": text,
                "likes": int(top.get("likeCount") or 0),
                "replies_count": int(item_snippet.get("totalReplyCount") or 0),
                "timestamp": top.get("publishedAt", ""),
            })
        except (KeyError, TypeError, ValueError) as e:
            logger.debug("댓글 파싱 실패 (건너뜀): %s", e)
    return comments


def _to_channel_signal(video: dict, comment: dict) -> dict:
    """댓글 1개를 channel_signal 포맷으로 변환"""
    score = comment["likes"] + comment["replies_count"] * 3
    if score >= 100:
        viral_risk = "높음"
    elif score >= 20:
        viral_risk = "보통"
    else:
        viral_risk = "낮음"

    return {
        "platform": "YouTube",
        "channel_type": "external",
        "data_type": "Video Comment",
        "video_title": video["title"],
        "channel_name": video["channel_name"],
        "content": comment["text"],
        "metadata": {
            "likes": comment["likes"],
            "replies_count": comment["replies_count"],
            "timestamp": comment["timestamp"],
        },
        "risk_indicators": [],  # LLM analyze_youtube_scenario 에서 채움
        "metric_label": "댓글",
        "viral_risk": viral_risk,
        "comment_growth": [],  # 실시간 크롤링이 아니므로 빈 배열
    }


def _build_risk_queries(query: str, industry: str) -> list[str]:
    """기본 쿼리 + 산업별 리스크 트리거 조합 쿼리 목록 생성"""
    triggers = RISK_TRIGGERS.get(industry, RISK_TRIGGERS["ecommerce"])
    queries = [f"{query} {t}" for t in triggers[:4]]  # 상위 4개 트리거
    logger.info("리스크 검색 쿼리 생성: %s", queries)
    return queries


def collect_youtube_signals(  # pylint: disable=too-many-locals
    query: str,
    max_videos: int = 3,
    max_comments_per_video: int = 15,
    industry: str = "ecommerce",
) -> tuple[list[dict], dict]:
    """
    YouTube Data API v3로 리스크 키워드 다중 검색 후 댓글 수집.

    Args:
        query: 검색어 (브랜드명 + 제품명)
        max_videos: 수집할 최대 영상 수
        max_comments_per_video: 영상당 최대 댓글 수
        industry: 산업 컨텍스트 (ecommerce|hospital|finance|gaming)

    Returns:
        (signals, meta)  — signals는 channel_signal 딕셔너리 목록
    """
    api_key = config.YOUTUBE_API_KEY
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    # 산업별 리스크 트리거로 다중 검색
    risk_queries = _build_risk_queries(query, industry)
    logger.info("YouTube 리스크 검색 시작: base=%s, queries=%d개", query, len(risk_queries))

    all_candidates: list[dict] = []
    seen_video_ids: set[str] = set()

    for rq in risk_queries:
        try:
            videos = _search_videos(rq, max_results=3, api_key=api_key)
            for v in videos:
                if v["video_id"] not in seen_video_ids:
                    seen_video_ids.add(v["video_id"])
                    v["search_query"] = rq
                    all_candidates.append(v)
        except RequestException as e:
            logger.warning("검색 실패 query=%s: %s", rq, e)

    logger.info("후보 영상 %d개 (중복 제거 후)", len(all_candidates))

    signals: list[dict] = []
    collected_videos = 0

    for video in all_candidates:
        if collected_videos >= max_videos:
            break

        comments = _get_video_comments(
            video["video_id"],
            max_results=max_comments_per_video,
            api_key=api_key,
        )
        if not comments:
            logger.debug("댓글 없음 또는 비활성: %s", video["title"][:50])
            continue

        for comment in comments:
            signals.append(_to_channel_signal(video, comment))

        collected_videos += 1
        logger.info("  영상 수집: %s (%d개 댓글)", video["title"][:50], len(comments))

    meta = {
        "query": query,
        "risk_queries": risk_queries,
        "collected_videos": collected_videos,
        "total_signals": len(signals),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "youtube_data_api_v3",
    }
    logger.info("YouTube 수집 완료: %d개 시그널 from %d개 영상", len(signals), collected_videos)
    return signals, meta
