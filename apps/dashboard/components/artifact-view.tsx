import type { WorkArtifact } from "@/lib/api";

/** Clase de color de una línea de diff unificado. Las cabeceras `+++`/`---` no son cambios. */
export function diffLineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---")) return "text-neutral-600";
  if (line.startsWith("+")) return "bg-green-50 text-green-900";
  if (line.startsWith("-")) return "bg-red-50 text-red-900";
  if (line.startsWith("@@")) return "bg-sky-50 text-sky-900";
  return "";
}

/** Un log o un diff del pipeline. Los diffs se colorean línea a línea; los logs se muestran tal cual. */
export function ArtifactView({ artifact }: { artifact: WorkArtifact }) {
  const lines = artifact.content.split("\n");
  return (
    <details data-testid="artifact" data-kind={artifact.kind} className="rounded border p-2">
      <summary className="cursor-pointer text-sm">
        <span className="font-mono text-xs">{artifact.kind}</span> · {artifact.stage} · ronda {artifact.round} ·{" "}
        {lines.length} líneas
      </summary>
      <pre className="mt-2 max-h-[28rem] overflow-auto rounded bg-neutral-50 p-2 font-mono text-xs leading-relaxed">
        {artifact.kind === "diff"
          ? lines.map((line, index) => (
              <span key={index} className={`block whitespace-pre-wrap break-all px-1 ${diffLineClass(line)}`}>
                {line || " "}
              </span>
            ))
          : artifact.content}
      </pre>
    </details>
  );
}
