"""Tests fuer TruthValues, Atomspace, PLN, ECAN, MOSES und den Kernel."""

import unittest

from goertzel_agi import (
    AtomSpace,
    CognitiveKernel,
    ConceptNode,
    InheritanceLink,
    SimilarityLink,
    TruthValue,
    VariableNode,
)
from goertzel_agi.agents.goals import Demand
from goertzel_agi.bridge.metta_bridge import export_metta
from goertzel_agi.ecan.attention import AttentionBank
from goertzel_agi.moses.evolution import MosesLearner
from goertzel_agi.pln import rules
from goertzel_agi.pln.engine import BackwardChainer, ForwardChainer


class TruthValueTests(unittest.TestCase):
    def test_evidence_roundtrip(self):
        tv = TruthValue.from_evidence(8, 10)
        self.assertAlmostEqual(tv.strength, 0.8)
        self.assertAlmostEqual(tv.to_count(), 10.0, places=5)

    def test_revision_weighted_mean(self):
        a = TruthValue.from_evidence(9, 10)   # s=0.9, n=10
        b = TruthValue.from_evidence(1, 10)   # s=0.1, n=10
        merged = a.revise(b)
        self.assertAlmostEqual(merged.strength, 0.5, places=5)
        self.assertGreater(merged.confidence, a.confidence)

    def test_validation(self):
        with self.assertRaises(ValueError):
            TruthValue(1.5, 0.5)


class PLNRuleTests(unittest.TestCase):
    def test_deduction_formula(self):
        # sAC = sAB*sBC + (1-sAB)*(sC - sB*sBC)/(1-sB)
        tv = rules.deduction(
            TruthValue(0.8, 0.9), TruthValue(0.9, 0.9),
            TruthValue(0.5, 0.9), TruthValue(0.4, 0.9), TruthValue(0.5, 0.9),
        )
        expected = 0.8 * 0.9 + 0.2 * (0.5 - 0.4 * 0.9) / 0.6
        self.assertAlmostEqual(tv.strength, expected, places=6)

    def test_inversion_bayes(self):
        tv = rules.inversion(TruthValue(0.8, 0.9), TruthValue(0.2, 0.9), TruthValue(0.4, 0.9))
        self.assertAlmostEqual(tv.strength, 0.8 * 0.2 / 0.4, places=6)

    def test_negation(self):
        tv = rules.negation(TruthValue(0.3, 0.7))
        self.assertAlmostEqual(tv.strength, 0.7)
        self.assertAlmostEqual(tv.confidence, 0.7)


class AtomSpaceTests(unittest.TestCase):
    def setUp(self):
        self.space = AtomSpace()
        self.tv = TruthValue(0.9, 0.8)
        self.space.add(InheritanceLink(ConceptNode("hund"), ConceptNode("tier"), tv=self.tv))
        self.space.add(InheritanceLink(ConceptNode("katze"), ConceptNode("tier"), tv=self.tv))

    def test_deduplication_and_revision(self):
        before = len(self.space)
        self.space.add(InheritanceLink(ConceptNode("hund"), ConceptNode("tier"),
                                       tv=TruthValue(0.9, 0.5)))
        self.assertEqual(len(self.space), before)  # kein Duplikat
        link = self.space.get(InheritanceLink(ConceptNode("hund"), ConceptNode("tier")))
        self.assertGreater(link.tv.confidence, 0.8)  # Evidenz akkumuliert

    def test_pattern_matching(self):
        pattern = InheritanceLink(VariableNode("$x"), ConceptNode("tier"))
        matches = self.space.match(pattern)
        names = {b.get("$x").name for b in matches}
        self.assertEqual(names, {"hund", "katze"})


class ChainerTests(unittest.TestCase):
    def test_forward_deduction(self):
        space = AtomSpace()
        tv = TruthValue(0.95, 0.9)
        space.add(InheritanceLink(ConceptNode("sokrates"), ConceptNode("mensch"), tv=tv))
        space.add(InheritanceLink(ConceptNode("mensch"), ConceptNode("sterblich"), tv=tv))
        ForwardChainer(space).run()
        conclusion = space.get(InheritanceLink(ConceptNode("sokrates"), ConceptNode("sterblich")))
        self.assertIsNotNone(conclusion)
        self.assertGreater(conclusion.tv.strength, 0.8)
        self.assertGreater(conclusion.tv.confidence, 0.5)

    def test_backward_chaining_multi_hop(self):
        space = AtomSpace()
        tv = TruthValue(0.95, 0.9)
        chain = ["a", "b", "c", "d"]
        for x, y in zip(chain, chain[1:]):
            space.add(InheritanceLink(ConceptNode(x), ConceptNode(y), tv=tv))
        goal = InheritanceLink(ConceptNode("a"), ConceptNode("d"))
        result = BackwardChainer(space).prove(goal)
        self.assertIsNotNone(result.conclusion)
        self.assertGreater(result.tv.confidence, 0.1)
        self.assertTrue(result.trace)


class EcanTests(unittest.TestCase):
    def test_focus_and_rent(self):
        space = AtomSpace()
        bank = AttentionBank(space, focus_size=2, sti_rent=1.0)
        hot = space.add(ConceptNode("wichtig"))
        space.add(ConceptNode("egal"))
        bank.stimulate(hot, 50.0)
        bank.step()
        focus = bank.focus()
        self.assertIn(hot, focus)
        self.assertLess(hot.av.sti, 50.0)  # Spreading + Rent reduzieren STI


class MosesTests(unittest.TestCase):
    def test_learns_conjunction(self):
        # Ziel: gefaehrlich = hat_zaehne AND NOT ist_zahm
        examples = [
            ({"hat_zaehne": True, "ist_zahm": False}, True),
            ({"hat_zaehne": True, "ist_zahm": True}, False),
            ({"hat_zaehne": False, "ist_zahm": False}, False),
            ({"hat_zaehne": False, "ist_zahm": True}, False),
        ]
        result = MosesLearner(["hat_zaehne", "ist_zahm"], seed=7).learn(examples)
        self.assertEqual(result.accuracy, 1.0)


class KernelTests(unittest.TestCase):
    def test_full_cycle_socrates(self):
        kernel = CognitiveKernel(seed=1)
        kernel.goals.add_demand(Demand("neugier", level=0.3))
        kernel.tell("Sokrates ist ein mensch. Ein mensch ist ein sterbliches.")
        kernel.run(cycles=2)
        result = kernel.ask(
            InheritanceLink(ConceptNode("sokrates"), ConceptNode("sterbliches"))
        )
        self.assertIsNotNone(result.conclusion)
        self.assertGreater(result.tv.strength, 0.5)

    def test_similarity_mining(self):
        kernel = CognitiveKernel(seed=1)
        kernel.tell("Ein hund ist ein tier. Eine katze ist ein tier. "
                    "Ein hund ist ein haustier. Eine katze ist ein haustier.")
        kernel.run(cycles=2)
        sim = kernel.atomspace.get(SimilarityLink(ConceptNode("hund"), ConceptNode("katze")))
        sim_rev = kernel.atomspace.get(SimilarityLink(ConceptNode("katze"), ConceptNode("hund")))
        self.assertTrue(sim is not None or sim_rev is not None)

    def test_metta_export(self):
        kernel = CognitiveKernel()
        kernel.tell("Ein hund ist ein tier")
        kernel.run(cycles=1)
        metta = export_metta(kernel.atomspace)
        self.assertIn("(Inheritance hund tier)", metta)
        self.assertIn("(stv", metta)


if __name__ == "__main__":
    unittest.main()
