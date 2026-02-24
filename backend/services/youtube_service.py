"""YouTube Data API v3 댓글 수집 서비스"""

import logging
from datetime import datetime, timezone

import requests
from requests.exceptions import RequestException

from core import config

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _search_videos(query: str, max_results: int, api_key: str) -> list[dict]:
    """YouTube 검색으로 관련 영상 목록 반환"""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": "ko",
        "key": api_key,
    }
    resp = requests.get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    videos = []
    for item in data.get("items", []):
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel_name": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
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
        top = item["snippet"]["topLevelComment"]["snippet"]
        text = top.get("textOriginal", top.get("textDisplay", "")).strip()
        if not text:
            continue
        comments.append({
            "text": text,
            "likes": int(top.get("likeCount", 0)),
            "replies_count": int(item["snippet"].get("totalReplyCount", 0)),
            "timestamp": top.get("publishedAt", ""),
        })
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


def collect_youtube_signals(
    query: str,
    max_videos: int = 3,
    max_comments_per_video: int = 15,
) -> tuple[list[dict], dict]:
    """
    YouTube Data API v3로 댓글 수집 후 channel_signals 형식으로 반환.

    Args:
        query: 검색어 (브랜드명, 제품명, 이슈 키워드 등)
        max_videos: 수집할 최대 영상 수
        max_comments_per_video: 영상당 최대 댓글 수

    Returns:
        (signals, meta)  — signals는 channel_signal 딕셔너리 목록
    """
    api_key = config.YOUTUBE_API_KEY
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    logger.info("YouTube 검색 시작: query=%s", query)
    candidates = _search_videos(
        query, max_results=max_videos + 3, api_key=api_key
    )

    signals: list[dict] = []
    collected_videos = 0

    for video in candidates:
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
        "collected_videos": collected_videos,
        "total_signals": len(signals),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "youtube_data_api_v3",
    }
    logger.info("YouTube 수집 완료: %d개 시그널 from %d개 영상", len(signals), collected_videos)
    return signals, meta
