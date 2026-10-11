import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from pipeline import ResearchError
from demo import sample_run
from storage import Library


class InterfaceTests(unittest.TestCase):
    def test_live_progress_success_and_failure(self):
        with tempfile.TemporaryDirectory() as data_dir:
            with patch.dict(os.environ, {"TOPIC_STUDIO_DATA_DIR": data_dir, "DEEPSEEK_API_KEY": "test-key"}):
                st.cache_resource.clear()
                self.addCleanup(st.cache_resource.clear)
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15).run()
                next(s for s in app.selectbox if s.label == "服务").set_value("DeepSeek").run()
                next(g for g in app.get("button_group") if g.value == "样例演示").set_value("联网研究").run()
                result = sample_run().model_copy(update={"id": "test-live-progress", "mode": "live"})

                def succeed(*args):
                    report = args[-1]
                    report("资料搜集", "已找到 3 条候选来源。")
                    time.sleep(1.1)
                    report("证据摘要", "证据编号校验通过。")
                    report("选题分析", "已生成 3 个选题。")
                    return result

                with patch("pipeline.research", side_effect=succeed) as research:
                    next(b for b in app.button if b.label == "生成选题").click().run()
                research.assert_called_once()
                self.assertEqual(app.status[0].state, "complete")
                self.assertFalse(app.status[0].proto.expanded)
                self.assertIn("研究完成", app.status[0].label)
                self.assertTrue(any(c.value.startswith("已用 ") and int(c.value.split()[1]) >= 1 for c in app.caption))
                entries = [t.value for t in app.text]
                self.assertTrue(any("资料搜集：已找到 3 条" in t for t in entries))
                self.assertTrue(any("证据摘要：证据编号" in t for t in entries))
                self.assertTrue(any("选题分析：已生成 3 个" in t for t in entries))
                self.assertEqual(app.session_state["run"].id, result.id)

                def fail(*args):
                    args[-1]("资料搜集", "已找到 2 条候选来源。")
                    raise ResearchError("模型请求超时")

                with patch("pipeline.research", side_effect=fail):
                    next(b for b in app.button if b.label == "生成选题").click().run()
                self.assertEqual(app.status[0].state, "error")
                self.assertTrue(app.status[0].proto.expanded)
                self.assertTrue(any("已找到 2 条" in t.value for t in app.text))
                self.assertTrue(any("停止于：资料搜集" in t.value for t in app.text))
                self.assertFalse(any("已找到 3 条" in t.value for t in app.text))
                self.assertTrue(any("超时" in e.value for e in app.error))
                self.assertEqual(app.session_state["run"].id, result.id)
                self.assertEqual(len(Library(Path(data_dir) / "library.sqlite3").runs()), 1)
                self.assertEqual(len(app.exception), 0)

    def test_deepseek_preset_and_credentials(self):
        with tempfile.TemporaryDirectory() as data_dir:
            with patch.dict(os.environ, {
                "TOPIC_STUDIO_DATA_DIR": data_dir,
                "DEEPSEEK_API_KEY": "", "DEEPSEEK_MODEL": "deepseek-chat",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
                "OPENAI_API_KEY": "other-provider-key", "OPENAI_MODEL": "other-model",
                "OPENAI_BASE_URL": "https://example.org/v1",
            }):
                st.cache_resource.clear()
                self.addCleanup(st.cache_resource.clear)
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15).run()
                service = next(s for s in app.selectbox if s.label == "服务")
                self.assertEqual(service.options, ["Gemini", "OpenAI 兼容", "DeepSeek"])
                service.set_value("DeepSeek").run()
                self.assertEqual(app.text_input(key="model_DeepSeek").value, "deepseek-chat")
                self.assertEqual(app.text_input(key="endpoint_DeepSeek").value, "https://api.deepseek.com")
                self.assertEqual(app.text_input(key="key_DeepSeek").value, "")
                next(g for g in app.get("button_group") if g.value == "样例演示").set_value("联网研究").run()
                next(b for b in app.button if b.label == "生成选题").click().run()
                self.assertTrue(any("API Key" in error.value for error in app.error))
                for env_key, input_key, expected_key in [
                    ("deepseek-env-key", "", "deepseek-env-key"),
                    ("deepseek-env-key", "deepseek-input-key", "deepseek-input-key"),
                ]:
                    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": env_key}):
                        app.text_input(key="key_DeepSeek").set_value(input_key)
                        with patch("pipeline.research", side_effect=ResearchError("test-stop")) as research:
                            next(b for b in app.button if b.label == "生成选题").click().run()
                        config = research.call_args.args[4]
                        self.assertEqual(config.provider, "DeepSeek")
                        self.assertEqual(config.api_key, expected_key)
                        self.assertEqual(config.model, "deepseek-chat")
                        self.assertEqual(config.base_url, "https://api.deepseek.com")
                next(s for s in app.selectbox if s.label == "服务").set_value("OpenAI 兼容").run()
                self.assertEqual(app.text_input(key="model_OpenAI 兼容").value, "other-model")
                self.assertEqual(next(t for t in app.text_input if t.label == "API 地址").value, "https://example.org/v1")
                self.assertEqual(app.text_input(key="key_OpenAI 兼容").value, "")
                self.assertEqual(len(app.exception), 0)

    def test_demo_workflow_and_missing_key(self):
        with tempfile.TemporaryDirectory() as data_dir:
            with patch.dict(os.environ, {"TOPIC_STUDIO_DATA_DIR": data_dir, "GOOGLE_API_KEY": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}):
                st.cache_resource.clear()
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15).run()
                self.assertEqual(len(app.exception), 0)
                topic_id = app.session_state["run"].topics[0].id
                app.button(key=f"deepen_{topic_id}").click().run()
                self.assertIn(topic_id, app.session_state["outlines"])
                app.button(key=f"save_{topic_id}").click().run()
                app.button(key=f"feedback_{topic_id}_有价值").click().run()
                app.radio[0].set_value("收藏夹").run()
                self.assertEqual(len(app.subheader), 1)
                app.button(key=f"remove_{topic_id}").click().run()
                self.assertEqual(len(app.subheader), 0)
                app.radio[0].set_value("选题工作台").run()
                next(b for b in app.button if b.label == "载入样例").click().run()
                app.radio[0].set_value("研究记录").run()
                self.assertEqual(len(app.subheader), 1)
                app.radio[0].set_value("选题工作台").run()
                next(g for g in app.get("button_group") if g.value == "样例演示").set_value("联网研究").run()
                next(b for b in app.button if b.label == "生成选题").click().run()
                self.assertTrue(any("API Key" in error.value for error in app.error))
                self.assertEqual(app.session_state["run"].mode, "demo")
                next(s for s in app.selectbox if s.label == "服务").set_value("OpenAI 兼容").run()
                app.text_input(key="key_OpenAI 兼容").set_value("test-key")
                app.text_input(key="model_OpenAI 兼容").set_value("deepseek-chat")
                next(t for t in app.text_input if t.label == "API 地址").set_value("https://api.deepseek.com")
                with patch("pipeline.research", side_effect=ResearchError("模型服务余额不足（402）")):
                    next(b for b in app.button if b.label == "生成选题").click().run()
                self.assertTrue(any("402" in error.value for error in app.error))
                self.assertEqual(app.status[0].label, "研究未完成")
                self.assertEqual(app.status[0].state, "error")
                self.assertEqual(app.session_state["run"].mode, "demo")
                self.assertEqual(app.text_input(key="key_OpenAI 兼容").value, "test-key")
                self.assertEqual(len(app.exception), 0)
                st.cache_resource.clear()


if __name__ == "__main__":
    unittest.main()
