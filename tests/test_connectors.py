"""Tests for the tabular/DB connector (facts + MOSES cases) and folder learning."""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from goertzel_agi import CognitiveKernel, ConceptNode, InheritanceLink
from goertzel_agi.connect import tabular
from goertzel_agi.connect.ingest import IngestEngine

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "inbox_examples"


class TabularFactsTests(unittest.TestCase):
    def test_facts_csv_with_relation_column(self):
        k = CognitiveKernel()
        n = tabular.import_facts_csv(
            k, EXAMPLES / "facts_example.csv",
            {"subject_col": "subject", "relation_col": "relation", "object_col": "object"})
        self.assertEqual(n, 3)
        self.assertIn("inflammation",
                      [o for o, _ in k.ask_relation("reduces", "ozone")])

    def test_facts_csv_fixed_relation(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "f.csv"
            csv.write_text("agent;effect\nsmoking;disease\n")
            k = CognitiveKernel()
            n = tabular.import_facts_csv(k, csv, {
                "subject_col": "agent", "relation": "causes", "object_col": "effect"})
            self.assertEqual(n, 1)
            self.assertIn("disease",
                          [o for o, _ in k.ask_relation("causes", "smoking")])

    def test_facts_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "k.db"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE t (s TEXT, o TEXT)")
            con.execute("INSERT INTO t VALUES ('exercise', 'health')")
            con.commit(); con.close()
            k = CognitiveKernel()
            n = tabular.import_facts_sqlite(
                k, db, "SELECT s AS subject, o AS object FROM t",
                {"subject_col": "subject", "relation": "improves", "object_col": "object"})
            self.assertEqual(n, 1)
            self.assertIn("health", [o for o, _ in k.ask_relation("improves", "exercise")])


class MosesCaseTests(unittest.TestCase):
    def test_cases_learn_readable_rule(self):
        k = CognitiveKernel(seed=1)
        n = tabular.import_cases_csv(
            k, EXAMPLES / "cases_example.csv",
            label_col="outcome", positive_label="flu",
            feature_cols=["has_fever", "has_cough", "has_rash", "short_breath"],
            concept="flu_suspected")
        self.assertEqual(n, 8)
        k.run(cycles=2)
        res = k.learning.learned.get("flu_suspected")
        self.assertIsNotNone(res)
        self.assertGreaterEqual(res.accuracy, 0.9)

    def test_bool_of(self):
        self.assertTrue(tabular.bool_of("yes"))
        self.assertTrue(tabular.bool_of("X"))
        self.assertFalse(tabular.bool_of("no"))
        self.assertFalse(tabular.bool_of(""))


class IngestEngineTests(unittest.TestCase):
    def _inbox_with_examples(self, tmp):
        inbox = Path(tmp) / "inbox"
        inbox.mkdir()
        for f in EXAMPLES.iterdir():
            if f.is_file():
                shutil.copy(f, inbox / f.name)
        return inbox

    def test_process_folder_moves_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = self._inbox_with_examples(tmp)
            k = CognitiveKernel(seed=1)
            report = IngestEngine(k, inbox=str(inbox)).process_folder()
            self.assertGreaterEqual(len(report.files_done), 2)
            self.assertEqual([], report.files_failed)
            left = [p.name for p in inbox.iterdir() if p.is_file()]
            self.assertEqual(left, [])
            processed = sorted(p.name for p in (inbox / "processed").iterdir())
            self.assertIn("facts_example.csv", processed)
            self.assertIn("cases_example.csv", processed)

    def test_text_file_learned(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox"
            inbox.mkdir()
            (inbox / "lesson.nico").write_text(
                "Socrates is a human\nrain causes mud\n")
            k = CognitiveKernel()
            IngestEngine(k, inbox=str(inbox)).process_folder()
            self.assertIsNotNone(
                k.atomspace.get(InheritanceLink(ConceptNode("socrates"),
                                                ConceptNode("human"))))

    def test_failed_file_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox"
            inbox.mkdir()
            (inbox / "broken.csv").write_text("a;b\n1;2\n")
            (inbox / "broken.csv.json").write_text('{"mode":"cases"}')  # label_col missing
            k = CognitiveKernel()
            report = IngestEngine(k, inbox=str(inbox)).process_folder()
            self.assertTrue(report.files_failed)
            self.assertTrue((inbox / "failed" / "broken.csv").exists())


if __name__ == "__main__":
    unittest.main()
