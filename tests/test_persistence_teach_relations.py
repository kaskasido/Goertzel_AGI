"""Tests for persistence, the teach mechanism, causal relations and the
demo knowledge pack."""

import tempfile
import unittest
from pathlib import Path

from goertzel_agi import (
    AtomSpace,
    CognitiveKernel,
    ConceptNode,
    EvaluationLink,
    InheritanceLink,
    ListLink,
    PredicateNode,
    TruthValue,
)
from goertzel_agi.core.persistence import load_atomspace, save_atomspace
from goertzel_agi.pln.relations import transitive_closure

DEMO_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "demo"


class PersistenceTests(unittest.TestCase):
    def test_roundtrip_preserves_atoms_and_tv(self):
        space = AtomSpace()
        space.add(InheritanceLink(ConceptNode("socrates"), ConceptNode("human"),
                                  tv=TruthValue(0.9, 0.7)))
        space.add(EvaluationLink(
            PredicateNode("causes"),
            ListLink(ConceptNode("rain"), ConceptNode("mud")),
            tv=TruthValue(0.8, 0.6)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.json"
            save_atomspace(space, path)
            loaded = load_atomspace(path)
        self.assertEqual(len(loaded), len(space))
        link = loaded.get(InheritanceLink(ConceptNode("socrates"), ConceptNode("human")))
        self.assertIsNotNone(link)
        self.assertAlmostEqual(link.tv.strength, 0.9)
        self.assertAlmostEqual(link.tv.confidence, 0.7)

    def test_kernel_save_load(self):
        k = CognitiveKernel()
        k.tell("A dog is a mammal")
        k.run(cycles=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "as.json"
            k.save(path)
            k2 = CognitiveKernel()
            k2.load(path)
        self.assertIsNotNone(
            k2.atomspace.get(InheritanceLink(ConceptNode("dog"), ConceptNode("mammal"))))

    def test_missing_file_returns_empty(self):
        loaded = load_atomspace("/nonexistent/path.json")
        self.assertEqual(len(loaded), 0)


class TeachTests(unittest.TestCase):
    def test_teach_multiline_with_comments(self):
        k = CognitiveKernel()
        n = k.teach("""
            # comments are ignored
            Socrates is a human
            rain causes mud

            mud causes slippery_road
        """)
        self.assertEqual(n, 3)
        self.assertIsNotNone(
            k.atomspace.get(InheritanceLink(ConceptNode("socrates"), ConceptNode("human"))))

    def test_teach_path_dir(self):
        k = CognitiveKernel()
        n = k.teach_path(DEMO_DIR, cycles=1)
        self.assertGreater(n, 20)


class RelationTests(unittest.TestCase):
    def _space_with_chain(self):
        space = AtomSpace()
        tv = TruthValue(0.9, 0.8)
        for a, b in [("a", "b"), ("b", "c"), ("c", "d")]:
            space.add(EvaluationLink(
                PredicateNode("causes"),
                ListLink(ConceptNode(a), ConceptNode(b)), tv=tv))
        return space

    def test_transitive_closure_adds_links(self):
        space = self._space_with_chain()
        added = transitive_closure(space, "causes")
        derived = {
            (l.outgoing[1].outgoing[0].name, l.outgoing[1].outgoing[1].name)
            for l in added
        }
        self.assertIn(("a", "c"), derived)
        self.assertIn(("b", "d"), derived)

    def test_confidence_decreases_along_chain(self):
        space = self._space_with_chain()
        transitive_closure(space, "causes")
        ac = space.get(EvaluationLink(
            PredicateNode("causes"),
            ListLink(ConceptNode("a"), ConceptNode("c"))))
        self.assertIsNotNone(ac)
        self.assertLess(ac.tv.confidence, 0.8)

    def test_kernel_ask_relation(self):
        k = CognitiveKernel()
        k.teach("rain causes mud. mud causes slippery_road.", cycles=3)
        objects = {name for name, _ in k.ask_relation("causes", "rain")}
        self.assertIn("mud", objects)
        self.assertIn("slippery_road", objects)  # derived transitively


class DemoKnowledgeBaseTests(unittest.TestCase):
    def test_all_sentences_parse(self):
        k = CognitiveKernel()
        k.teach_path(DEMO_DIR, cycles=1)
        unparsed = [a for log in k.history for r in log.reports
                    for a in r.actions if a.startswith("unparsed")]
        self.assertEqual(unparsed, [], f"unparsed: {unparsed[:5]}")

    def test_socrates_is_mortal(self):
        k = CognitiveKernel()
        k.teach_path(DEMO_DIR, cycles=2)
        k.run(cycles=4)
        res = k.ask(InheritanceLink(ConceptNode("socrates"),
                                    ConceptNode("mortal_thing")))
        self.assertIsNotNone(res.conclusion)
        self.assertGreater(res.tv.strength, 0.4)

    def test_part_whole_chain_derived(self):
        k = CognitiveKernel()
        k.teach_path(DEMO_DIR, cycles=2)
        k.run(cycles=3)
        hits = dict(k.ask_relation("is_part_of", "a_cell"))
        self.assertIn("an_organism", hits)


class GlossaryTests(unittest.TestCase):
    def test_report_and_duplicate_detection(self):
        from goertzel_agi.glossary import build_report, _likely_duplicates
        k = CognitiveKernel()
        k.teach_path(DEMO_DIR, cycles=1)
        k.run(cycles=2)
        report = build_report(k.atomspace)
        self.assertIn("Glossar", report)
        pairs = _likely_duplicates(["mammal", "mammals", "bird"])
        self.assertIn(("mammal", "mammals"), pairs)


if __name__ == "__main__":
    unittest.main()
