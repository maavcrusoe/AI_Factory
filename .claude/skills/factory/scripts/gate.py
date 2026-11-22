"""Gate determinista: ejecuta `checks.sh` del proyecto y guarda el resultado de la ronda.

Uso: python gate.py <worktree> <log-file>   (sale con 0 si pasa, 1 si falla)
El resultado de la prueba lo decide el script del proyecto, nunca un LLM.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CHECKS = "checks.sh"
TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class GateResult:
    passed: bool
    returncode: int
    log_path: Path
    output: str


def _bash() -> str | None:
    # En Windows, `bash` puede resolver a WSL; preferimos Git Bash si existe.
    git = shutil.which("git")
    if git:
        candidate = Path(git).parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    return shutil.which("bash")


def run_gate(worktree: Path, log_path: Path, round_no: int = 0) -> GateResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    if not (worktree / CHECKS).exists():
        output = f"{CHECKS} no existe en {worktree}\n"
        returncode = 127
    else:
        shell = _bash()
        if shell is None:
            output = "no se encuentra bash para ejecutar checks.sh\n"
            returncode = 127
        else:
            try:
                proc = subprocess.run(
                    [shell, CHECKS],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=TIMEOUT_SECONDS,
                )
                output = proc.stdout + proc.stderr
                returncode = proc.returncode
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + (exc.stderr or "") + f"\ntimeout tras {TIMEOUT_SECONDS} s\n"
                returncode = 124
    passed = returncode == 0
    header = f"# gate ronda {round_no} {started} rc={returncode} {'PASS' if passed else 'FAIL'}\n"
    log_path.write_text(header + output, encoding="utf-8")
    return GateResult(passed=passed, returncode=returncode, log_path=log_path, output=output)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("uso: python gate.py <worktree> <log-file>", file=sys.stderr)
        sys.exit(2)
    result = run_gate(Path(sys.argv[1]), Path(sys.argv[2]))
    print("PASS" if result.passed else "FAIL", f"rc={result.returncode}", f"log={result.log_path}")
    sys.exit(0 if result.passed else 1)
