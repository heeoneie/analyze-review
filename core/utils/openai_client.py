"""
OpenAI API 호출을 위한 공통 유틸리티
중복 코드 제거를 위해 공통 함수로 추출
"""

from openai import OpenAI

from core import config


def get_client():
    """OpenAI 클라이언트 인스턴스 반환"""
    return OpenAI(api_key=config.OPENAI_API_KEY)


def call_openai_json(
    client,
    prompt,
    system_prompt="You are an expert at analyzing e-commerce customer feedback.",
    model=None,
    temperature=None,
):
    """
    OpenAI API를 호출하여 JSON 응답을 반환

    Args:
        client: OpenAI 클라이언트
        prompt: 사용자 프롬프트
        system_prompt: 시스템 프롬프트
        model: 사용할 모델 (기본값: config.LLM_MODEL)
        temperature: 온도 설정 (기본값: config.LLM_TEMPERATURE)

    Returns:
        API 응답의 message content (문자열)
    """
    if model is None:
        model = config.LLM_MODEL
    if temperature is None:
        temperature = config.LLM_TEMPERATURE

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content
