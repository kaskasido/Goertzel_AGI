"""Tests fuer SelfUpdateAgent (mit Fake-Quellen, ohne Netz) und die Web-API."""

import json
import tempfile
import unittest
from pathlib import Path

from goertzel_agi import AtomSpace, CognitiveKernel, ConceptNode, InheritanceLink
from goertzel_agi.agents.goals import GoalAgent
from goertzel_agi.ecan.attention import AttentionBank
from goertzel_agi.selfupdate.agent import COOLDOWN_CYCLES, SelfUpdateAgent
from goertzel_agi.selfupdate.sources import Finding


class FakeSource:
    """Deterministische Quelle fuer Tests (ersetzt arXiv/Substack)."""

    name = "fake"

    def __init__(self, findings, reachable=True):
        self.findings = findings
        self.reachable = reachable
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return self.findings if self.reachable else []


def make_agent(tmpdir, source):
    space = AtomSpace()
    attention = AttentionBank(space)
    goals = GoalAgent(space, attention)
    agent = SelfUpdateAgent(
        space, attention, goals,
        sources=[source],
        state_file=Path(tmpdir) / "state.json",
        log_file=Path(tmpdir) / "auto-updates.md",
    )
    return space, goals, agent


FINDING = Finding(
    source="arxiv",
    uid="http://arxiv.org/abs/2606.05411",
    title="A Motivational Architecture for Conversational AGI",
    summary="Applies the MetaMo/OpenPsi framework to dialogue agents.",
    url="http://arxiv.org/abs/2606.05411",
    published="2026-06-04",
)


class SelfUpdateTests(unittest.TestCase):
    def test_ingests_new_findings_as_atoms(self):
        with tempfile.TemporaryDirectory() as tmp:
            space, goals, agent = make_agent(tmp, FakeSource([FINDING]))
            goals.demands["aktualitaet"].level = 0.0  # voller Urge
            report = agent.step()
            self.assertEqual(report.data.get("new"), 1)
            work = space.node(ConceptNode, "werk:a_motivational_architecture_for_conversational_agi")
            self.assertIsNotNone(work)
            self.assertTrue(work.av.vlti)  # Vordenker-Wissen wird nie vergessen
            link = space.get(InheritanceLink(work, ConceptNode("publikation")))
            self.assertIsNotNone(link)

    def test_deduplication_via_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeSource([FINDING])
            _, goals, agent = make_agent(tmp, source)
            agent.check_now()
            # Zweiter Agent mit gleichem State-File kennt das Werk schon
            _, _, agent2 = make_agent(tmp, FakeSource([FINDING]))
            report = agent2.check_now()
            self.assertEqual(report.data.get("new"), 0)
            state = json.loads((Path(tmp) / "state.json").read_text())
            self.assertEqual(len(state["known_uids"]), 1)

    def test_urge_persists_when_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, goals, agent = make_agent(tmp, FakeSource([], reachable=False))
            goals.demands["aktualitaet"].level = 0.0
            agent.check_now()
            # Offline: Demand wurde NICHT gesaettigt -> System will es wieder versuchen
            self.assertGreater(goals.demands["aktualitaet"].urge, 0.4)

    def test_cooldown_prevents_hammering(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeSource([FINDING])
            _, goals, agent = make_agent(tmp, source)
            goals.demands["aktualitaet"].level = 0.0
            agent.step()                 # erster Lauf: fragt Quelle ab
            calls_after_first = source.calls
            goals.demands["aktualitaet"].level = 0.0
            agent.step()                 # direkt danach: Cooldown greift
            self.assertEqual(source.calls, calls_after_first)

    def test_log_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, agent = make_agent(tmp, FakeSource([FINDING]))
            agent.check_now()
            log = (Path(tmp) / "auto-updates.md").read_text()
            self.assertIn("Motivational Architecture", log)


class WebApiTests(unittest.TestCase):
    """Testet den KernelService direkt (ohne Socket)."""

    def setUp(self):
        from webui.server import KernelService

        self.service = KernelService(self_update=False)

    def test_tell_and_snapshot(self):
        state = self.service.tell("Ein hund ist ein tier")
        self.assertGreater(state["atom_count"], 0)
        labels = {n["label"] for n in state["graph"]["nodes"]}
        self.assertIn("hund", labels)
        self.assertIn("tier", labels)
        edge_types = {e["type"] for e in state["graph"]["edges"]}
        self.assertIn("Inheritance", edge_types)

    def test_ask_with_trace(self):
        self.service.tell("Sokrates ist ein mensch")
        self.service.tell("Ein mensch ist ein sterbliches")
        result = self.service.ask("sokrates", "sterbliches")
        self.assertTrue(result["answer"]["proven"])
        self.assertGreater(result["answer"]["strength"], 0.5)
        # trace darf leer sein, wenn der Forward Chainer den Fakt schon
        # waehrend tell() abgeleitet hat (dann ist er direkt im Atomspace)

    def test_selfupdate_disabled_reports_error(self):
        result = self.service.self_update_now()
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
