from unittest.mock import MagicMock, patch

from core.utils.openai_client import call_openai_json


class TestCallOpenaiJson:
    def _make_mock_client(self, content="test response"):
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = content
        client.models.generate_content.return_value = mock_response
        return client

    def test_returns_response_text(self):
        client = self._make_mock_client("result content")
        result = call_openai_json(client, "test prompt")
        assert result == "result content"

    def test_passes_correct_default_parameters(self):
        client = self._make_mock_client()
        with patch("core.utils.openai_client.config") as mock_config:
            mock_config.LLM_MODEL = "gemini-2.0-flash"
            mock_config.LLM_TEMPERATURE = 0.3
            call_openai_json(client, "prompt")

        call_kwargs = client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.0-flash"

    def test_custom_model_and_temperature(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt", model="gemini-1.5-flash", temperature=0.7)
        call_kwargs = client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-1.5-flash"

    def test_default_system_prompt(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt")
        call_kwargs = client.models.generate_content.call_args.kwargs
        config_arg = call_kwargs["config"]
        assert "analyzing e-commerce" in config_arg.system_instruction

    def test_custom_system_prompt(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt", system_prompt="Custom system")
        call_kwargs = client.models.generate_content.call_args.kwargs
        config_arg = call_kwargs["config"]
        assert config_arg.system_instruction == "Custom system"
