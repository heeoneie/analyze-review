"""
LLM API 호출 공통 유틸리티
LLM_PROVIDER=google  → Gemini 우선, 429시 backoff 재시도 후 OpenAI 폴백 (로컬 개발)
LLM_PROVIDER=openai  → OpenAI 우선, Gemini 폴백 (배포 환경, 기본값)
"""

import logging
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError as GeminiClientError
from openai import OpenAI

from core import config

logger = logging.getLogger(__name__)

# Gemini 429 재시도 설정
_GEMINI_RETRY_DELAYS = [10, 30]  # 1차: 10초 대기, 2차: 30초 대기 후 OpenAI 폴백

_openai_client = None  # pylint: disable=invalid-name
_gemini_client = None  # pylint: disable=invalid-name


def get_client():
    """OpenAI 클라이언트 반환 (기본)"""
    global _openai_client  # pylint: disable=global-statement
    if _openai_client is None:
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def _get_gemini_client():
    """Gemini 클라이언트 반환"""
    global _gemini_client  # pylint: disable=global-statement
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _gemini_client


def _call_openai(client, prompt, system_prompt, model, temperature):
    """OpenAI API 호출"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_gemini(prompt, system_prompt, temperature):
    """Gemini API 호출"""
    fallback = _get_gemini_client()
    response = fallback.models.generate_content(
        model=config.FALLBACK_LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return response.text


def call_openai_json(
    client,
    prompt,
    system_prompt="You are an expert at analyzing e-commerce customer feedback.",
    model=None,
    temperature=None,
):
    """
    LLM API를 호출하여 JSON 응답을 반환.
    LLM_PROVIDER 환경변수에 따라 primary/fallback 순서가 바뀜:
      - "google" : Gemini 우선 → OpenAI 폴백  (로컬 개발)
      - "openai" : OpenAI 우선 → Gemini 폴백  (배포, 기본값)
    """
    if model is None:
        model = config.LLM_MODEL
    if temperature is None:
        temperature = config.LLM_TEMPERATURE

    if config.LLM_PROVIDER == "google":
        # 429 시 backoff 재시도 → 최종 실패 시 OpenAI 폴백
        last_exc = None
        for attempt, delay in enumerate([0, *_GEMINI_RETRY_DELAYS]):
            if delay:
                logger.warning("Gemini 429 — %d초 대기 후 재시도 (attempt %d)", delay, attempt + 1)
                time.sleep(delay)
            try:
                return _call_gemini(prompt, system_prompt, temperature)
            except GeminiClientError as e:
                if getattr(e, "status_code", None) == 429:
                    last_exc = e
                    continue  # 재시도
                break  # 429 외 에러는 바로 OpenAI 폴백
            except Exception:  # pylint: disable=broad-except
                break  # 비 429 예외는 바로 OpenAI 폴백

        logger.warning("Gemini 재시도 소진, OpenAI 폴백 (last_exc=%s)", last_exc)
        return _call_openai(client, prompt, system_prompt, model, temperature)

    try:
        return _call_openai(client, prompt, system_prompt, model, temperature)
    except Exception:  # pylint: disable=broad-except
        logger.warning("OpenAI 호출 실패, Gemini 폴백 시도", exc_info=True)
        return _call_gemini(prompt, system_prompt, temperature)
