"""Tests de las reglas de rondas (sin E/S). Ejecutar: python -m unittest discover -s .claude/skills/factory/scripts"""

import unittest

import rounds


class GateRoundsTest(unittest.TestCase):
    def test_green_gate_goes_to_review_in_same_round(self):
        nxt = rounds.after_gate(2, passed=True)
        self.assertEqual((nxt.phase, nxt.round), ("review", 2))

    def test_red_gate_goes_back_to_builder_with_next_round(self):
        nxt = rounds.after_gate(1, passed=False)
        self.assertEqual((nxt.phase, nxt.round), ("build", 2))

    def test_red_gate_in_third_round_needs_human(self):
        nxt = rounds.after_gate(rounds.MAX_BUILD_ROUNDS, passed=False)
        self.assertEqual(nxt.phase, "human")
        self.assertIn("gate rojo tras 3 rondas", nxt.reason)


class ReviewRoundsTest(unittest.TestCase):
    def test_both_approve_goes_to_diff(self):
        self.assertEqual(rounds.after_review(1, approved=True).phase, "diff")

    def test_changes_requested_goes_back_to_builder(self):
        nxt = rounds.after_review(2, approved=False)
        self.assertEqual((nxt.phase, nxt.round), ("build", 3))

    def test_changes_requested_at_limit_needs_human(self):
        self.assertEqual(rounds.after_review(3, approved=False).phase, "human")


class SpecProblemTest(unittest.TestCase):
    def test_first_spec_problem_replans(self):
        self.assertEqual(rounds.after_spec_problem(0, "falta el endpoint").phase, "plan")

    def test_second_spec_problem_needs_human(self):
        nxt = rounds.after_spec_problem(rounds.MAX_PLAN_RUNS, "sigue sin encajar")
        self.assertEqual(nxt.phase, "human")
        self.assertIn("sigue sin encajar", nxt.reason)


class ParsingTest(unittest.TestCase):
    def test_spec_problem_line_is_detected(self):
        out = "trabajo parcial\nSPEC_PROBLEM: el spec pide un borrado sin confirmación\n"
        self.assertEqual(rounds.parse_spec_problem(out), "el spec pide un borrado sin confirmación")

    def test_no_spec_problem_when_absent(self):
        self.assertIsNone(rounds.parse_spec_problem("hecho, todo verde"))

    def test_verdict_approve_and_request_changes(self):
        self.assertIs(rounds.parse_verdict("ok\nVERDICT: APPROVE"), True)
        self.assertIs(rounds.parse_verdict("falta test\nVERDICT: REQUEST_CHANGES"), False)

    def test_missing_verdict_counts_as_not_approved(self):
        self.assertIsNone(rounds.parse_verdict("me parece bien"))
        self.assertIs(rounds.parse_verdict("me parece bien") is True, False)


if __name__ == "__main__":
    unittest.main()
