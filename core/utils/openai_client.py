"""
Google Gemini API 호출을 위한 공통 유틸리티
기존 OpenAI에서 Gemini로 전환. 함수 시그니처는 호환성을 위해 유지.
"""

from google import genai
from google.genai import types

from core import config

_client = None  # pylint: disable=invalid-name


def get_client():
    """Gemini API 클라이언트 반환"""
    global _client  # pylint: disable=global-statement
    if _client is None:
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


def call_openai_json(
    client,
    prompt,
    system_prompt="You are an expert at analyzing e-commerce customer feedback.",
    model=None,
    temperature=None,
):
    """
    Gemini API를 호출하여 JSON 응답을 반환

    Args:
        client: genai.Client (get_client() 반환값)
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

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )

    return response.text
