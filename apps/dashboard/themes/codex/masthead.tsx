import Link from "next/link";

export function Masthead() {
  return (
    <div className="codex-masthead" hidden>
      <Link href="/projects">
        <span className="codex-mark" aria-hidden="true" />
        AI Factory
      </Link>
    </div>
  );
}
