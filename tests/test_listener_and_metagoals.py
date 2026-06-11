"""Tests fuer ListenerAgent (Denker-Agenten), Metagoals-Waechter und
Feed-Konfiguration — offline mit Fake-Quellen."""

import json
import tempfile
import unittest
from pathlib import Path

from goertzel_agi import AtomSpace, ConceptNode, EvaluationLink, InheritanceLink
from goertzel_agi.agents.goals import Demand, GoalAgent
from goertzel_agi.agents.perception import PerceptionAgent
from goertzel_agi.ecan.attention import AttentionBank
from goertzel_agi.selfupdate.listener import ListenerAgent
from goertzel_agi.selfupdate.sources import Finding
from goertzel_agi.selfupdate.thinkers import load_thinker_sources


class FakeSource:
    name = "lex_fridman"

    def __init__(self, findings):
        self.findings = findings

    def fetch(self):
        return self.findings


EPISODE = Finding(
    source="lex_fridman",
    uid="https://lexfridman.com/david-deutsch",
    title="David Deutsch: Knowledge Creation",
    summary="David Deutsch ist ein physiker. Ein physiker ist ein wissenschaftler.",
    url="https://lexfridman.com/david-deutsch",
    published="2026-01-01",
)


def make_listener(tmp, findings):
    space = AtomSpace()
    attention = AttentionBank(space)
    goals = GoalAgent(space, attention)
    perception = PerceptionAgent(space, attention)
    listener = ListenerAgent(
        space, attention, goals, perception,
        sources=[FakeSource(findings)],
        state_file=Path(tmp) / "state.json",
        log_file=Path(tmp) / "log.md",
        corpus_dir=Path(tmp) / "corpus",
    )
    return space, goals, listener


class ListenerTests(unittest.TestCase):
    def test_ingests_episode_and_grows_knowledge(self):
        with tempfile.TemporaryDirectory() as tmp:
            space, goals, listener = make_listener(tmp, [EPISODE])
            report = listener.check_now()
            self.assertEqual(report.data.get("new"), 1)
            # Denker + Werk verankert
            self.assertIsNotNone(space.node(ConceptNode, "denker:lex_fridman"))
            self.assertTrue(space.atoms_of_type(EvaluationLink))
            # Beschreibung wurde zu Wissen: david_deutsch -> physiker
            isa = space.get(InheritanceLink(
                ConceptNode("david_deutsch"), ConceptNode("physiker")))
            self.assertIsNotNone(isa)

    def test_corpus_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, listener = make_listener(tmp, [EPISODE])
            listener.check_now()
            self.assertEqual(listener.corpus_size(), 1)
            record = json.loads(
                (Path(tmp) / "corpus" / "lex_fridman.jsonl").read_text())
            self.assertIn("Knowledge Creation", record["title"])

    def test_own_demand_separate_from_selfupdate(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, goals, _ = make_listener(tmp, [EPISODE])
            self.assertIn("horizont", goals.demands)
            self.assertTrue(goals.demands["horizont"].protected)


class MetagoalTests(unittest.TestCase):
    def setUp(self):
        space = AtomSpace()
        self.goals = GoalAgent(space, AttentionBank(space))
        self.goals.add_demand(Demand("kern", weight=1.0, target=1.0, protected=True))
        self.goals.add_demand(Demand("nebensache", weight=1.0, protected=False))

    def test_protected_demand_cannot_be_removed(self):
        self.assertFalse(self.goals.remove_demand("kern"))
        self.assertIn("kern", self.goals.demands)
        self.assertTrue(any("VETO" in e for e in self.goals.metagoal_log))

    def test_unprotected_demand_can_be_removed(self):
        self.assertTrue(self.goals.remove_demand("nebensache"))
        self.assertNotIn("nebensache", self.goals.demands)

    def test_change_is_drift_limited(self):
        # Versuch, das Gewicht schlagartig auf 0 zu setzen -> auf -20% gedaempft
        self.goals.request_change("kern", weight=0.0)
        self.assertAlmostEqual(self.goals.demands["kern"].weight, 0.8)
        self.assertTrue(any("GEDAEMPFT" in e for e in self.goals.metagoal_log))

    def test_gradual_change_allowed(self):
        changed = self.goals.request_change("kern", weight=0.9)
        self.assertTrue(changed)
        self.assertAlmostEqual(self.goals.demands["kern"].weight, 0.9)


class FeedConfigTests(unittest.TestCase):
    def test_default_sources(self):
        sources = load_thinker_sources(config_file="/nonexistent/feeds.json")
        names = {s.name for s in sources}
        self.assertEqual(names, {"lex_fridman", "ted_talks", "david_deutsch"})

    def test_custom_feed_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "feeds.json"
            cfg.write_text(json.dumps([
                {"name": "mindscape", "kind": "rss", "url": "https://example.org/rss"}
            ]))
            names = {s.name for s in load_thinker_sources(cfg)}
            self.assertIn("mindscape", names)
            self.assertIn("lex_fridman", names)  # Defaults bleiben


if __name__ == "__main__":
    unittest.main()
