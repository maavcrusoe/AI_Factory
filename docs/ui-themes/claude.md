# Tema `claude` — la fábrica de juguetes

## Idea de diseño

El dashboard se ve como una fábrica alegre y fácil de leer:

- **Papel crema con rejilla de plano**, tinta azul marino, bordes gruesos y sombras duras (estilo "caja de juguete").
- **Cinta de peligro** animada arriba de todas las pantallas y **engranajes** girando despacio abajo a la derecha.
- **Navegación = panel de control**: píldoras con luz de color, la pantalla activa va resaltada (`aria-current="page"`) y la barra se queda fija al hacer scroll.
- **Tablero = línea de producción**: cada columna es una *estación* con placa de color, luz de estado (verde si tiene trabajo), contador redondo y una **cinta transportadora** animada. Los items son *cajas* que entran rodando; el color del lateral indica el estado.
- **Luces de estado** en cada insignia (parpadean si el item está en curso o espera a una persona).
- **Latido caducando** = alarma roja parpadeante y caja que se bambolea; **rechazadas** = borde discontinuo y título tachado.
- **Detalle de trabajo**: las etapas del pipeline son estaciones numeradas unidas por una cinta vertical; la línea de tiempo usa puntos de color.
- **Admin/estado**: tabla con cabecera oscura, tablero de luces (verde/rojo) para el estado del hub.
- En **móvil** el tablero es una cinta horizontal con imán de scroll (una estación por pantalla).

Accesibilidad: texto siempre tinta sobre colores claros (o blanco sobre rojo oscuro), foco visible de 3 px azul, y todas las animaciones se desactivan con `prefers-reduced-motion: reduce`.

## Cómo activarlo

El tema se activa con `<html data-theme="claude">`. En esta rama está fijo en `app/layout.tsx`
(que también importa `themes/claude/theme.css`). Todo el CSS cuelga de `[data-theme="claude"]`, así que
con otro valor (o sin atributo) no se aplica nada. El selector de temas lo hará el integrador.

## Ficheros

- `apps/dashboard/themes/claude/theme.css`: todos los estilos (tokens, shell, tablero, formularios, tablas, movimiento).
- `apps/dashboard/themes/claude/index.ts`: `export default { id: "claude", label: "Claude", ... }`.
- `apps/dashboard/app/layout.tsx`: `data-theme` + import del CSS (2 líneas).
- `apps/dashboard/components/site-nav.tsx`: ahora es componente de cliente para marcar la pantalla activa con `aria-current` (sin cambios de rutas ni lógica).

Sin dependencias nuevas: solo CSS y SVG embebido. Las clases de Tailwind existentes se siguen usando; el tema las supera con selectores por atributo y `data-testid`/`data-status` (que no se han tocado, los E2E siguen valiendo).
