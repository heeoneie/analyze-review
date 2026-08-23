"""SPA 폴백 라우트 테스트.

/api 를 폴백이 삼키면 라우터가 빠진 슬림 배포에서 index.html 이 200 으로 나가고,
프론트는 성공으로 처리해 엉뚱한 곳에서 터진다. 경로 탈출도 함께 본다.
"""

import os


def _inside(dist, path):
    """backend.main.serve_frontend 의 경계 판정과 같은 로직."""
    candidate = os.path.normpath(os.path.join(dist, path))
    try:
        return os.path.commonpath([dist, candidate]) == dist
    except ValueError:
        return False


class TestPathBoundary:
    def test_allows_normal_asset(self):
        assert _inside("/app/frontend/dist", "assets/index.js")

    def test_blocks_sibling_directory_with_shared_prefix(self):
        # startswith 만 쓰면 dist-backup 이 통과해 버린다
        assert not _inside("/app/frontend/dist", "../dist-backup/secret.env")

    def test_blocks_parent_escape(self):
        assert not _inside("/app/frontend/dist", "../../.env")


class TestApiNotSwallowed:
    def test_api_paths_are_excluded(self):
        from backend.main import serve_frontend
        from fastapi import HTTPException

        for path in ("api", "api/data/reviews", "api/nope"):
            try:
                serve_frontend(path)
            except HTTPException as exc:
                assert exc.status_code == 404
            else:
                raise AssertionError(f"{path} 가 404 를 내지 않았다")
