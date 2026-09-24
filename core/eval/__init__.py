"""리뷰 분류기 평가 패키지.

라벨 체계(taxonomy), 채점(metrics), 실행기(runners)를 담는다.
여기에는 무거운 의존성(openai, sklearn)을 최상위에서 임포트하지 않는다.
슬림 배포 이미지가 core.eval 을 임포트해도 부팅되어야 한다.
"""
