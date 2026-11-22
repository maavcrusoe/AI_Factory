"""Empuja la rama del trabajo y abre el PR en borrador con `gh` (sesión local, sin token en el hub).

Regla dura: solo ramas `factory/*`. El cliente nunca hace merge.
Uso: python pr.py <worktree> <branch> <item-id> <issue-or-0> <title> <summary-file>
"""

import re
import subprocess
import sys
from pathlib import Path

BRANCH_PREFIX = "factory/"
BASE = "main"
PR_URL_RE = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/(\d+)")


class PrError(Exception):
    pass


def check_branch(branch: str) -> None:
    if not branch.startswith(BRANCH_PREFIX) or branch == BRANCH_PREFIX:
        raise PrError(f"rama no permitida (solo {BRANCH_PREFIX}*): {branch}")


def build_body(item_id: int, summary: str, closes_issue: int | None) -> str:
    lines = [summary.strip(), "", f"Trabajo del hub AI Factory #{item_id}."]
    if closes_issue:
        lines.extend(["", f"Closes #{closes_issue}"])
    lines.extend(["", "Borrador: el cliente nunca hace merge. Lo revisa una persona."])
    return "\n".join(lines) + "\n"


def _git(worktree: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.name=AI Factory", "-c", "user.email=factory@localhost", *args],
        cwd=worktree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise PrError(f"git {args[0]} falló: {proc.stderr.strip()[:500]}")
    return proc.stdout


def push_branch(worktree: Path, branch: str) -> None:
    check_branch(branch)
    _git(worktree, "push", "--set-upstream", "origin", f"{branch}:{branch}")


def create_draft_pr(worktree: Path, branch: str, title: str, body_file: Path) -> tuple[str, int]:
    check_branch(branch)
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--draft",
            "--base",
            BASE,
            "--head",
            branch,
            "--title",
            title[:250],
            "--body-file",
            str(body_file),
        ],
        cwd=worktree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise PrError(f"gh pr create falló: {(proc.stderr or proc.stdout).strip()[:500]}")
    match = PR_URL_RE.search(proc.stdout)
    if not match:
        raise PrError(f"gh no devolvió URL de PR: {proc.stdout.strip()[:300]}")
    return match.group(0), int(match.group(1))


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("uso: python pr.py <worktree> <branch> <item-id> <issue|0> <title> <summary-file>", file=sys.stderr)
        sys.exit(2)
    worktree, branch, item_id, issue, title, summary_file = sys.argv[1:]
    summary = Path(summary_file).read_text(encoding="utf-8")
    body_path = Path(summary_file).with_suffix(".body.md")
    body_path.write_text(build_body(int(item_id), summary, int(issue) or None), encoding="utf-8")
    push_branch(Path(worktree), branch)
    url, number = create_draft_pr(Path(worktree), branch, title, body_path)
    print(url, number)
