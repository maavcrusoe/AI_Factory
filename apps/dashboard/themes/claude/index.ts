/** Tema "Claude": fábrica de juguetes (cintas transportadoras, luces de estado, engranajes). */
const claudeTheme = {
  id: "claude",
  label: "Claude",
  description: "Fábrica alegre: papel crema, tinta marino, cintas transportadoras y luces de estado.",
  /** Hoja de estilos del tema; se activa con <html data-theme="claude">. */
  stylesheet: "./theme.css",
} as const;

export default claudeTheme;
