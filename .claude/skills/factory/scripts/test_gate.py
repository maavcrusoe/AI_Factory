"""Tests del gate: resultado según checks.sh del proyecto. Ejecutar desde la raíz de AI_Factory:
python -m unittest discover -s .claude/skills/factory/scripts"""

import tempfile
import unittest
from pathlib import Path

import gate


class GateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.log = self.root / "logs" / "round-1" / "gate.log"

    def tearDown(self):
        self._tmp.cleanup()

    def _checks(self, body: str) -> None:
        (self.root / "checks.sh").write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")

    def test_passing_checks_sh_is_pass_and_logged(self):
        self._checks('echo "ok"')
        result = gate.run_gate(self.root, self.log, round_no=1)
        self.assertTrue(result.passed)
        self.assertEqual(result.returncode, 0)
        text = self.log.read_text(encoding="utf-8")
        self.assertIn("gate ronda 1", text)
        self.assertIn("PASS", text)
        self.assertIn("ok", text)

    def test_failing_checks_sh_is_fail_with_its_output(self):
        self._checks('echo "fail motivo" >&2; exit 3')
        result = gate.run_gate(self.root, self.log, round_no=2)
        self.assertFalse(result.passed)
        self.assertEqual(result.returncode, 3)
        text = self.log.read_text(encoding="utf-8")
        self.assertIn("FAIL", text)
        self.assertIn("fail motivo", text)

    def test_missing_checks_sh_is_a_failure_not_a_crash(self):
        result = gate.run_gate(self.root, self.log, round_no=1)
        self.assertFalse(result.passed)
        self.assertEqual(result.returncode, 127)
        self.assertIn("checks.sh no existe", self.log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
