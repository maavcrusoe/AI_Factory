# Codex

Una sala de control en azul cobalto con señales lima. Cada columna del tablero representa una estación de la línea de producción. El color de la estación ayuda a localizarla y las etiquetas indican el estado de cada pieza. El detalle reúne las etapas, los registros y el historial en paneles separados.

El tema se activa con `data-theme="codex"` en `<html>`. La rama de presentación lo activa en `apps/dashboard/app/layout.tsx`.

- `apps/dashboard/themes/codex/index.ts` exporta el identificador, el nombre y la cabecera.
- `theme.css` contiene los estilos del tema y el tratamiento para pantallas estrechas y movimiento reducido.
- `masthead.tsx` y `factory.svg` contienen la cabecera y la ilustración de acceso.
