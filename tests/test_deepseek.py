import json
import unittest
from unittest.mock import patch

import httpx
from agno.exceptions import ModelProviderError
from agno.models.deepseek import DeepSeek
from openai import APITimeoutError, OpenAI

from demo import sample_outline, sample_run
from models import EvidenceBundle, Outline, Selection, TopicBundle
from pipeline import ModelConfig, ResearchError, ask, model_error_message, model_for


class DeepSeekTests(unittest.TestCase):
    def config(self, url="https://api.deepseek.com"):
        return ModelConfig("OpenAI 兼容", "deepseek-chat", "test-key", url)

    def test_adapter_selection_preserves_configuration(self):
        dedicated = model_for(ModelConfig("DeepSeek", "deepseek-chat", "test-key"))
        self.assertIsInstance(dedicated, DeepSeek)
        self.assertEqual(dedicated.base_url, "https://api.deepseek.com")
        self.assertEqual(dedicated.id, "deepseek-chat")
        for url in ["https://api.deepseek.com", "https://api.deepseek.com/", "https://api.deepseek.com/v1"]:
            with self.subTest(url=url):
                model = model_for(self.config(url))
                self.assertIsInstance(model, DeepSeek)
                self.assertEqual(model.id, "deepseek-chat")
                self.assertEqual(model.base_url, url)
        self.assertNotIsInstance(model_for(self.config("https://api.deepseek.com.example.org")), DeepSeek)
        self.assertEqual(model_for(ModelConfig("Gemini", "gemini-2.5-flash", "test-key")).id, "gemini-2.5-flash")

    def test_real_agent_http_protocol_and_all_output_schemas(self):
        sample = sample_run()
        cases = [
            (Selection, Selection(source_ids=["S1", "S2"], rationale="Relevant sources")),
            (EvidenceBundle, EvidenceBundle(evidence=sample.evidence)),
            (TopicBundle, TopicBundle(topics=sample.topics)),
            (Outline, sample_outline(sample.topics[0])),
        ]
        for schema, expected in cases:
            with self.subTest(schema=schema.__name__):
                captured = []

                def respond(request):
                    captured.append(json.loads(request.content))
                    return httpx.Response(200, json={
                        "id": "test-completion", "object": "chat.completion", "created": 1,
                        "model": "deepseek-chat", "choices": [{"index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": expected.model_dump_json()}}],
                    })

                with httpx.Client(transport=httpx.MockTransport(respond)) as http:
                    client = OpenAI(api_key="test-key", base_url=self.config().base_url, http_client=http, max_retries=0)
                    model = model_for(self.config())
                    model.client = client
                    with patch("pipeline.model_for", return_value=model):
                        actual = ask(self.config(), "test", "Analyze supplied sources.", {"sources": []}, schema)
                self.assertEqual(actual, expected)
                self.assertEqual(len(captured), 1)
                body = captured[0]
                self.assertEqual(body["model"], "deepseek-chat")
                self.assertEqual(body["response_format"], {"type": "json_object"})
                self.assertEqual(body["messages"][0]["role"], "system")
                self.assertNotIn("developer", [message["role"] for message in body["messages"]])
                prompt = body["messages"][0]["content"]
                self.assertIn("json", prompt.lower())
                for field in schema.model_fields:
                    self.assertIn(field, prompt)

    def test_http_error_is_actionable_and_does_not_expose_provider_body(self):
        def respond(request):
            return httpx.Response(402, json={"error": {"message": "secret-test-key"}})

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            model = model_for(self.config())
            model.client = OpenAI(api_key="test-key", base_url=self.config().base_url, http_client=http, max_retries=0)
            with patch("pipeline.model_for", return_value=model):
                with self.assertRaises(ResearchError) as caught:
                    ask(self.config(), "test", "Select sources", {}, Selection)
        self.assertIn("余额不足", str(caught.exception))
        self.assertNotIn("secret-test-key", str(caught.exception))

    def test_invalid_json_is_rejected(self):
        from types import SimpleNamespace

        with patch("agno.agent.Agent.run", return_value=SimpleNamespace(content='{"source_ids": []}')):
            with self.assertRaisesRegex(ResearchError, "JSON"):
                ask(self.config(), "test", "Select sources", {}, Selection)

    def test_error_status_and_wrapped_timeout(self):
        for status in [401, 402, 403, 404, 422, 429]:
            message = model_error_message(ModelProviderError("secret-test-key", status_code=status))
            self.assertIn(str(status), message)
            self.assertNotIn("secret-test-key", message)
        wrapped = ModelProviderError("timeout")
        wrapped.__cause__ = APITimeoutError(request=httpx.Request("POST", "https://api.deepseek.com"))
        self.assertIn("超时", model_error_message(wrapped))


if __name__ == "__main__":
    unittest.main()
