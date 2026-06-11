"""Tests fuer den erweiterten RuleBasedParser und das Claude-Backend (offline,
mit Fake-Client — kein Netz, kein API-Schluessel noetig)."""

import json
import unittest

from goertzel_agi import CognitiveKernel, ConceptNode, EvaluationLink, InheritanceLink
from goertzel_agi.agents.llm_perception import ClaudeLanguageModel
from goertzel_agi.agents.perception import RuleBasedParser, normalize_concept


class RuleBasedParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = RuleBasedParser()

    def test_multiword_subject(self):
        triples = self.parser.extract_triples("Anna Berg ist ein Mensch")
        self.assertEqual(triples, [("anna_berg", "isa", "mensch")])

    def test_article_and_isa(self):
        triples = self.parser.extract_triples("Ein Hund ist ein Tier")
        self.assertEqual(triples, [("hund", "isa", "tier")])

    def test_plural_sind(self):
        triples = self.parser.extract_triples("Hunde sind Tiere")
        self.assertEqual(triples, [("hunde", "isa", "tiere")])

    def test_hat_relation(self):
        triples = self.parser.extract_triples("Ein Hund hat ein Fell")
        self.assertEqual(triples, [("hund", "hat", "fell")])

    def test_kann_relation(self):
        triples = self.parser.extract_triples("Anna Berg kann Zaehne behandeln")
        self.assertEqual(triples, [("anna_berg", "kann", "zaehne_behandeln")])

    def test_common_verb(self):
        triples = self.parser.extract_triples("Der Hund jagt die Katze")
        self.assertEqual(triples, [("hund", "jagt", "katze")])

    def test_english_multiword(self):
        triples = self.parser.extract_triples("A border collie is a dog")
        self.assertEqual(triples, [("border_collie", "isa", "dog")])

    def test_multiple_sentences(self):
        triples = self.parser.extract_triples(
            "Sokrates ist ein Mensch. Anna mag Musik."
        )
        self.assertIn(("sokrates", "isa", "mensch"), triples)
        self.assertIn(("anna", "mag", "musik"), triples)

    def test_normalize(self):
        self.assertEqual(normalize_concept("  Anna   Berg "), "anna_berg")


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessages:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error

        class Response:
            content = [_FakeBlock(json.dumps(self.payload))]

        return Response()


class _FakeClient:
    def __init__(self, payload=None, error=None):
        self.messages = _FakeMessages(payload, error)


class ClaudeLanguageModelTests(unittest.TestCase):
    def test_parses_structured_output(self):
        client = _FakeClient(payload={"triples": [
            {"subject": "Anna Berg", "relation": "isa", "object": "Zahnarzt"},
            {"subject": "zahnarzt", "relation": "behandeln", "object": "patienten"},
        ]})
        model = ClaudeLanguageModel(client=client)
        triples = model.extract_triples("Anna Berg ist Zahnarzt und behandelt Patienten.")
        self.assertEqual(triples, [
            ("anna_berg", "isa", "zahnarzt"),
            ("zahnarzt", "behandeln", "patienten"),
        ])
        self.assertEqual(model.last_status, "ok")

    def test_falls_back_on_error(self):
        client = _FakeClient(error=ConnectionError("offline"))
        model = ClaudeLanguageModel(client=client)
        triples = model.extract_triples("Sokrates ist ein Mensch")
        self.assertEqual(triples, [("sokrates", "isa", "mensch")])  # Regel-Parser
        self.assertIn("Fallback", model.last_status)

    def test_empty_llm_result_uses_fallback(self):
        client = _FakeClient(payload={"triples": []})
        model = ClaudeLanguageModel(client=client)
        triples = model.extract_triples("Ein Hund ist ein Tier")
        self.assertEqual(triples, [("hund", "isa", "tier")])


class KernelIntegrationTests(unittest.TestCase):
    def test_multiword_flows_into_atomspace(self):
        kernel = CognitiveKernel()
        kernel.tell("Anna Berg ist ein Mensch. Anna Berg kann Zaehne behandeln.")
        kernel.run(cycles=1)
        isa = kernel.atomspace.get(
            InheritanceLink(ConceptNode("anna_berg"), ConceptNode("mensch"))
        )
        self.assertIsNotNone(isa)
        evaluations = kernel.atomspace.atoms_of_type(EvaluationLink)
        self.assertTrue(any("kann" in repr(e) for e in evaluations))


if __name__ == "__main__":
    unittest.main()
