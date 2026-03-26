import unittest

from core import nodes
from core.state import PaperWriterState


class SearchNodeTests(unittest.TestCase):
    def test_extract_openalex_abstract_from_inverted_index(self):
        item = {
            "abstract_inverted_index": {
                "Adaptive": [0],
                "control": [1],
                "for": [2],
                "traffic": [3],
            }
        }
        abstract = nodes._extract_openalex_abstract(item)
        self.assertEqual(abstract, "Adaptive control for traffic")

    def test_fetch_openalex_papers_respects_total_limit(self):
        original_openalex = nodes._search_openalex
        try:
            def fake_openalex(query, limit=8, api_key=""):
                return [
                    {
                        "title": f"O-{query}-{i}",
                        "abstract": "b",
                        "url": f"https://openalex.org/W{query}{i}",
                    }
                    for i in range(limit)
                ]

            nodes._search_openalex = fake_openalex

            papers = nodes._fetch_openalex_papers_by_queries(
                queries=["q1", "q2"],
                total_limit=5,
                openalex_api_key="demo-key",
            )
            self.assertEqual(len(papers), 5)
        finally:
            nodes._search_openalex = original_openalex

    def test_dedupe_queries(self):
        queries = nodes._dedupe_queries([
            "  traffic signal reinforcement learning  ",
            "traffic signal reinforcement learning",
            "multi agent traffic control",
        ])
        self.assertEqual(len(queries), 2)

    def test_format_related_works_markdown_contains_abstract(self):
        md = nodes._format_related_works_markdown([
            {
                "title": "Paper A",
                "authors": "Alice",
                "year": "2025",
                "source": "OpenAlex",
                "venue": "Test Venue",
                "url": "https://openalex.org/W1",
                "abstract": "This is an abstract.",
            }
        ])
        self.assertIn("- Abstract: This is an abstract.", md)

    def test_state_reads_paper_search_limit_from_inputs(self):
        state = PaperWriterState(
            {
                "topic": "t",
                "language": "English",
                "model": "gpt-5.2",
                "paper_search_limit": 7,
                "openalex_api_key": "demo-key",
                "writing_guidance_library": {"overall_guidance": "ok"},
                "review_guidance_library": {"overall_review": "ok"},
            },
            input_from_md=False,
        )
        self.assertEqual(state.paper_search_limit, 7)
        self.assertEqual(state.openalex_api_key, "demo-key")


if __name__ == "__main__":
    unittest.main()
