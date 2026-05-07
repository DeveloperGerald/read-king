from __future__ import annotations

import unittest

try:
    from app.agents.workflow import _select_snippets_with_coverage
except Exception:
    _select_snippets_with_coverage = None


class TestRetrievalCoverage(unittest.TestCase):
    @unittest.skipIf(_select_snippets_with_coverage is None, "dependencies are not installed")
    def test_per_section_limit(self) -> None:
        items = []
        for i in range(10):
            items.append((f"a{i}", {"section_title": "第1章"}))
        for i in range(10):
            items.append((f"b{i}", {"section_title": "第2章"}))

        out = _select_snippets_with_coverage(items, max_total=10, per_section_max=2)
        self.assertEqual(len(out), 4)
        s1 = sum(1 for _, md in out if md.get("section_title") == "第1章")
        s2 = sum(1 for _, md in out if md.get("section_title") == "第2章")
        self.assertEqual(s1, 2)
        self.assertEqual(s2, 2)


if __name__ == "__main__":
    unittest.main()

