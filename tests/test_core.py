import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demo import sample_run
from models import EvidenceBundle, Selection, TopicBundle
from pipeline import ModelConfig, ResearchError, export_markdown, public_url, research, search_sources, validate_citations
from storage import Library


class CoreTests(unittest.TestCase):
    def test_demo_citations_and_export_provenance(self):
        run = sample_run()
        validate_citations(run.topics + run.evidence, {s.id for s in run.sources})
        markdown = export_markdown(run)
        self.assertIn("固定样例，未联网生成", markdown)
        self.assertIn(run.sources[0].url, markdown)
        self.assertEqual(len(run.topics), 3)
        self.assertEqual(run.subject, "羽毛球")

    def test_invalid_or_empty_reference_rejected(self):
        topic = sample_run().topics[0]
        for ids in ([], ["S999"]):
            with self.subTest(ids=ids):
                topic.source_ids = ids
                with self.assertRaises(ResearchError):
                    validate_citations([topic], {"S1"})

    def test_private_source_urls_rejected(self):
        for url in ["file:///etc/passwd", "http://127.0.0.1", "http://[::1]", "https://user:password@example.com", "http://localhost:8501"]:
            self.assertFalse(public_url(url))

    def test_library_roundtrip_and_idempotent_save(self):
        with tempfile.TemporaryDirectory() as folder:
            library = Library(Path(folder) / "db.sqlite3")
            run = sample_run()
            library.add_run(run)
            library.save(run, run.topics[0].id)
            library.save(run, run.topics[0].id)
            library.feedback(run.topics[0].id, "有价值")
            self.assertEqual(len(library.saved()), 1)
            self.assertEqual(library.runs()[0].model_dump(), run.model_dump())
            self.assertEqual(library.verdicts()[run.topics[0].id], "有价值")
            library.remove(run.topics[0].id)
            self.assertEqual(library.saved(), [])

    def test_three_stage_flow_with_mocked_model(self):
        sample = sample_run()
        responses = [Selection(source_ids=[s.id for s in sample.sources], rationale="按相关性选择"), EvidenceBundle(evidence=sample.evidence), TopicBundle(topics=sample.topics)]
        steps = []
        events = []
        def progress(stage, detail):
            steps.append(stage)
            events.append(detail)
        with patch("pipeline.model_for"), patch("pipeline.search_sources", return_value=sample.sources), patch("pipeline.read_page", return_value=""), patch("pipeline.ask", side_effect=responses) as ask:
            run = research("AI", "产品经理", "原型", "不限时间", ModelConfig("Gemini", "test", "test-key"), progress)
        self.assertEqual(ask.call_count, 3)
        self.assertEqual(run.mode, "live")
        self.assertEqual(len(run.trace), 3)
        self.assertTrue(all(s.basis == "仅搜索摘要，正文未能读取" for s in run.sources))
        self.assertNotIn("test-key", run.model_dump_json())
        self.assertTrue(all(t.id.startswith(run.id) for t in run.topics))
        self.assertEqual(list(dict.fromkeys(steps)), ["资料搜集", "证据摘要", "选题分析"])
        self.assertTrue(any(f"已找到 {len(sample.sources)} 条" in event for event in events))
        self.assertTrue(any("0 份正文" in event for event in events))
        self.assertTrue(any(f"已整理 {len(sample.evidence)} 条证据" in event for event in events))
        self.assertTrue(any(f"已生成 {len(sample.topics)} 个选题" in event for event in events))

    def test_failed_search_does_not_produce_run(self):
        with patch("pipeline.model_for"), patch("pipeline.search_sources", side_effect=ResearchError("search failed")), patch("pipeline.ask") as ask:
            with self.assertRaises(ResearchError):
                research("AI", "PM", "", "不限时间", ModelConfig("Gemini", "test", "key"), lambda *args: None)
            ask.assert_not_called()

    def test_search_fallback_preserves_date_constraint_and_filters_ads(self):
        results = [{"title": "Ad", "href": "https://www.bing.com/aclick?x=1", "body": "ad"}, {"title": "Source one", "href": "https://example.com/one", "body": "one"}, {"title": "Source two", "href": "https://example.org/two", "body": "two"}]
        with patch("ddgs.DDGS") as searcher, patch("pipeline.bing_rss_results", return_value=results) as fallback:
            searcher.return_value.text.side_effect = RuntimeError("timeout")
            sources = search_sources("AI", "", "不限时间")
            self.assertEqual(len(sources), 2)
            self.assertEqual([s.id for s in sources], ["S1", "S2"])
            fallback.assert_called_once()
            with self.assertRaises(ResearchError):
                search_sources("AI", "", "近一个月")
            self.assertEqual(fallback.call_count, 1)


if __name__ == "__main__":
    unittest.main()
