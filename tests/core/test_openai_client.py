from unittest.mock import MagicMock, patch

from core.utils.openai_client import call_openai_json


class TestCallOpenaiJson:
    def _make_mock_client(self, content="test response"):
        client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        client.chat.completions.create.return_value = mock_response
        return client

    def test_returns_message_content(self):
        client = self._make_mock_client("result content")
        result = call_openai_json(client, "test prompt")
        assert result == "result content"

    def test_passes_correct_default_parameters(self):
        client = self._make_mock_client()
        with patch("core.utils.openai_client.config") as mock_config:
            mock_config.LLM_MODEL = "gpt-4o-mini"
            mock_config.LLM_TEMPERATURE = 0.3
            call_openai_json(client, "prompt")

        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs.kwargs["temperature"] == 0.3
        assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}

    def test_custom_model_and_temperature(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt", model="gpt-4", temperature=0.7)
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4"
        assert call_kwargs.kwargs["temperature"] == 0.7

    def test_default_system_prompt(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt")
        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "analyzing e-commerce" in messages[0]["content"]

    def test_custom_system_prompt(self):
        client = self._make_mock_client()
        call_openai_json(client, "prompt", system_prompt="Custom system")
        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["content"] == "Custom system"
