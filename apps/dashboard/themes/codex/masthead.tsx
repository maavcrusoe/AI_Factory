import Link from "next/link";

export function Masthead() {
  return (
    <div className="codex-masthead" style={{ display: "var(--codex-masthead-display, none)" }}>
      <Link href="/projects">
        <span className="codex-mark" aria-hidden="true" />
        AI Factory
      </Link>
    </div>
  );
}
