"""Web-UI-Server fuer die Goertzel-AGI — reine Python-Stdlib.

Start:   python3 -m webui.server  [--port 8000] [--no-self-update]

Endpunkte (JSON):
  GET  /api/state        kompletter Introspektions-Snapshot:
                         Graph (Atome+Links), Attentional Focus, Demands,
                         Zyklus-Historie, Self-Update-Status
  POST /api/tell         {"text": "..."}    Wahrnehmung einspeisen + 1 Zyklus
  POST /api/ask          {"subject": "...", "object": "..."}
                         Backward Chaining mit Beweisspur
  POST /api/step         {"cycles": n}      n kognitive Zyklen laufen lassen
  POST /api/selfupdate   sofortige Vordenker-Pruefung (arXiv/Substack)

Ein Lock serialisiert alle Kernel-Zugriffe (der Kern ist single-threaded —
wie ein Atomspace ohne DAS; echtes Hyperon loest das verteilt).
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from goertzel_agi import CognitiveKernel, ConceptNode, InheritanceLink
from goertzel_agi.agents.goals import Demand
from goertzel_agi.core.atom import Link, Node

STATIC_DIR = Path(__file__).parent / "static"

MAX_GRAPH_ATOMS = 120  # UI-Schutz: nur die wichtigsten Atome zeichnen


def _detect_language_model():
    """Claude-Wahrnehmung aktivieren, wenn SDK + API-Schluessel vorhanden sind."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, "Regel-Parser (offline)"
    try:
        from goertzel_agi.agents.llm_perception import ClaudeLanguageModel

        model = ClaudeLanguageModel()
        return model, f"Claude ({model.model})"
    except RuntimeError as exc:  # SDK fehlt
        return None, f"Regel-Parser ({exc})"


class KernelService:
    """Haelt den Kernel und liefert JSON-serialisierbare Sichten darauf."""

    def __init__(self, self_update: bool = True,
                 store: str = "data/atomspace.json") -> None:
        self.lock = threading.Lock()
        self.store = store
        language_model, self.perception_backend = _detect_language_model()
        self.kernel = CognitiveKernel(language_model=language_model,
                                      self_update=self_update,
                                      listen=self_update)
        self.kernel.goals.add_demand(
            Demand("wissensdurst", level=0.3, decay=0.02, protected=True)
        )
        # Persistenz: gespeicherten Wissensstand laden (Tag-und-Nacht-Lernen)
        self.kernel.load(self.store)

    def _persist(self) -> None:
        try:
            self.kernel.save(self.store)
        except OSError:
            pass  # Speichern darf den Betrieb nie blockieren

    # ---- Kommandos ------------------------------------------------------------
    def tell(self, text: str) -> dict:
        with self.lock:
            self.kernel.tell(text)
            self.kernel.run(cycles=1)
            self._persist()
            return self.snapshot()

    def teach(self, text: str, cycles: int = 2) -> dict:
        """Ganze Lektion (mehrzeilig) auf einmal einspeisen."""
        with self.lock:
            taught = self.kernel.teach(text, cycles=cycles)
            self._persist()
            return {"taught": taught, "state": self.snapshot()}

    def ingest_inbox(self) -> dict:
        """Posteingang (inbox/) verarbeiten: Dateien lernen, dann aufraeumen."""
        with self.lock:
            from goertzel_agi.connect.ingest import IngestEngine

            engine = IngestEngine(self.kernel, inbox="inbox", cycles=2)
            report = engine.process_folder()
            self.kernel.run(cycles=2)
            self._persist()
            result = (f"{len(report.files_done)} Datei(en), "
                      f"{report.learned} Einheiten gelernt")
            if report.files_failed:
                result += f", {len(report.files_failed)} fehlgeschlagen"
            return {"result": result, "actions": report.notes[:25],
                    "state": self.snapshot()}

    def teach_demo(self) -> dict:
        """Load the bundled demo knowledge pack (knowledge/demo)."""
        with self.lock:
            try:
                taught = self.kernel.teach_path("knowledge/demo", cycles=2)
            except OSError as exc:
                return {"error": f"knowledge/demo not found: {exc}",
                        "state": self.snapshot()}
            self.kernel.run(cycles=3)
            self._persist()
            return {"taught": taught,
                    "result": f"learned {taught} sentences from the demo pack",
                    "state": self.snapshot()}

    def step(self, cycles: int) -> dict:
        with self.lock:
            self.kernel.run(cycles=max(1, min(cycles, 50)))
            return self.snapshot()

    def ask(self, subject: str, obj: str) -> dict:
        with self.lock:
            goal = InheritanceLink(
                ConceptNode(subject.strip().lower()),
                ConceptNode(obj.strip().lower()),
            )
            result = self.kernel.ask(goal)
            answer = {
                "proven": result.conclusion is not None,
                "strength": result.tv.strength,
                "confidence": result.tv.confidence,
                "trace": [repr(step) for step in result.trace],
            }
            return {"answer": answer, "state": self.snapshot()}

    def ask_relation(self, predicate: str, subject: str) -> dict:
        with self.lock:
            hits = self.kernel.ask_relation(predicate.strip().lower(),
                                            subject.strip().lower())
            answer = [
                {"object": name, "strength": tv.strength, "confidence": tv.confidence}
                for name, tv in hits
            ]
            return {"answer": answer, "state": self.snapshot()}

    def self_update_now(self) -> dict:
        with self.lock:
            agent = self.kernel.self_update
            if agent is None:
                return {"error": "Self-Update ist deaktiviert", "state": self.snapshot()}
            report = agent.check_now()
            self._persist()
            return {
                "result": agent.last_result,
                "actions": report.actions,
                "state": self.snapshot(),
            }

    def listen_now(self) -> dict:
        with self.lock:
            agent = self.kernel.listener
            if agent is None:
                return {"error": "Denker-Agenten sind deaktiviert", "state": self.snapshot()}
            report = agent.check_now()
            # Frisch Gehoertes sofort durchdenken lassen (PLN/ECAN/Mining)
            self.kernel.run(cycles=1)
            self._persist()
            return {
                "result": agent.last_result,
                "actions": report.actions[:25],
                "state": self.snapshot(),
            }

    # ---- Introspektion -----------------------------------------------------------
    def snapshot(self) -> dict:
        kernel = self.kernel
        atoms = sorted(kernel.atomspace, key=lambda a: a.av.sti, reverse=True)
        shown = atoms[:MAX_GRAPH_ATOMS]
        shown_keys = {a.key for a in shown}

        nodes, edges = [], []
        for atom in shown:
            if isinstance(atom, Node):
                nodes.append({
                    "id": str(atom.key),
                    "label": atom.name,
                    "type": atom.atom_type,
                    "sti": round(atom.av.sti, 2),
                    "vlti": atom.av.vlti,
                })
            elif isinstance(atom, Link) and len(atom.outgoing) == 2:
                a, b = atom.outgoing
                if a.key in shown_keys and b.key in shown_keys:
                    edges.append({
                        "from": str(a.key),
                        "to": str(b.key),
                        "type": atom.atom_type.removesuffix("Link"),
                        "strength": round(atom.tv.strength, 3),
                        "confidence": round(atom.tv.confidence, 3),
                        "sti": round(atom.av.sti, 2),
                    })

        focus = [
            {"label": repr(a), "sti": round(a.av.sti, 2)}
            for a in kernel.attention.focus()
        ]
        demands = [
            {"name": d.name, "level": round(d.level, 3), "urge": round(d.urge, 3)}
            for d in kernel.goals.demands.values()
        ]
        history = [
            {
                "cycle": log.cycle,
                "reports": [
                    {"agent": r.agent, "actions": r.actions}
                    for r in log.reports if r.actions
                ],
            }
            for log in kernel.history[-12:]
        ]
        update_agent = kernel.self_update
        listener = kernel.listener
        return {
            "cycle": kernel.cycle_count,
            "perception": self.perception_backend,
            "atom_count": len(kernel.atomspace),
            "graph": {"nodes": nodes, "edges": edges},
            "focus": focus,
            "demands": demands,
            "history": history,
            "metagoal_log": kernel.goals.metagoal_log[-5:],
            "self_update": {
                "enabled": update_agent is not None and update_agent.enabled,
                "last_result": update_agent.last_result if update_agent else "—",
                "known_works": len(update_agent._known) if update_agent else 0,
            },
            "listener": {
                "enabled": listener is not None and listener.enabled,
                "last_result": listener.last_result if listener else "—",
                "known_works": len(listener._known) if listener else 0,
                "corpus_docs": listener.corpus_size() if listener else 0,
                "sources": [s.name for s in listener.sources] if listener else [],
            },
        }


def make_handler(service: KernelService):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

        def log_message(self, fmt, *args):  # ruhiges Konsolen-Log
            pass

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length == 0:
                return {}
            try:
                return json.loads(self.rfile.read(length))
            except ValueError:
                return {}

        def do_GET(self):
            if self.path == "/api/state":
                with service.lock:
                    self._json(service.snapshot())
                return
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()

        def do_POST(self):
            data = self._body()
            try:
                if self.path == "/api/tell":
                    text = str(data.get("text", "")).strip()
                    if not text:
                        self._json({"error": "text fehlt"}, 400)
                        return
                    self._json(service.tell(text))
                elif self.path == "/api/ask":
                    subject = str(data.get("subject", "")).strip()
                    obj = str(data.get("object", "")).strip()
                    if not subject or not obj:
                        self._json({"error": "subject/object fehlen"}, 400)
                        return
                    self._json(service.ask(subject, obj))
                elif self.path == "/api/ask_relation":
                    predicate = str(data.get("predicate", "")).strip()
                    subject = str(data.get("subject", "")).strip()
                    if not predicate or not subject:
                        self._json({"error": "predicate/subject fehlen"}, 400)
                        return
                    self._json(service.ask_relation(predicate, subject))
                elif self.path == "/api/teach":
                    text = str(data.get("text", "")).strip()
                    if not text:
                        self._json({"error": "text fehlt"}, 400)
                        return
                    self._json(service.teach(text, int(data.get("cycles", 2))))
                elif self.path == "/api/teach_demo":
                    self._json(service.teach_demo())
                elif self.path == "/api/ingest":
                    self._json(service.ingest_inbox())
                elif self.path == "/api/step":
                    self._json(service.step(int(data.get("cycles", 1))))
                elif self.path == "/api/selfupdate":
                    self._json(service.self_update_now())
                elif self.path == "/api/listen":
                    self._json(service.listen_now())
                else:
                    self._json({"error": "unbekannter Endpunkt"}, 404)
            except Exception as exc:  # Fehler an die UI melden statt 500-Stille
                self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Goertzel-AGI Web-UI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-self-update", action="store_true",
                        help="Vordenker-Selbstupdate (arXiv/Substack) deaktivieren")
    args = parser.parse_args()

    service = KernelService(self_update=not args.no_self_update)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(service))
    print(f"Goertzel-AGI UI: http://localhost:{args.port}  "
          f"(Self-Update: {'an' if not args.no_self_update else 'aus'}, "
          f"Wahrnehmung: {service.perception_backend})")
    server.serve_forever()


if __name__ == "__main__":
    main()
