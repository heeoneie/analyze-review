"""
LLM API 호출 공통 유틸리티
OpenAI 우선 호출, 실패 시 Google Gemini 폴백
"""

import logging

from google import genai
from google.genai import types
from openai import OpenAI

from core import config

logger = logging.getLogger(__name__)

_openai_client = None  # pylint: disable=invalid-name
_gemini_client = None  # pylint: disable=invalid-name


def get_client():
    """OpenAI 클라이언트 반환 (기본)"""
    global _openai_client  # pylint: disable=global-statement
    if _openai_client is None:
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def _get_fallback_client():
    """Gemini 클라이언트 반환 (폴백)"""
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
    """Gemini API 폴백 호출"""
    fallback = _get_fallback_client()
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
    LLM API를 호출하여 JSON 응답을 반환
    OpenAI 우선, 실패 시 Gemini 폴백

    Args:
        client: OpenAI 클라이언트 (get_client() 반환값)
        prompt: 사용자 프롬프트
        system_prompt: 시스템 프롬프트
        model: 사용할 모델 (기본값: config.LLM_MODEL)
        temperature: 온도 설정 (기본값: config.LLM_TEMPERATURE)

    Returns:
        API 응답의 text content (문자열)
    """
    if model is None:
        model = config.LLM_MODEL
    if temperature is None:
        temperature = config.LLM_TEMPERATURE

    try:
        return _call_openai(client, prompt, system_prompt, model, temperature)
    except Exception:  # pylint: disable=broad-except
        logger.warning("OpenAI 호출 실패, Gemini 폴백 시도", exc_info=True)
        return _call_gemini(prompt, system_prompt, temperature)
