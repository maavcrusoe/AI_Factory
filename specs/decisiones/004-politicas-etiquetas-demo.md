# 004 Políticas, etiquetas y demo (2026-11-21)

- Azure DevOps: el hub consulta por API REST con token. Dashboard muestra todos los eventos, incluidos logs.
- Política de merge humano (configurable en la fábrica). Exige revisor si: dificultad alta; toca ficheros/paths sensibles (core); funcionalidad no planificada o fuera de alcance; un cambio de texto cuyo significado difiera mucho del original (aunque sea "solo texto"). Cambios triviales (botón, texto menor) pueden ir sin humano.
- Heartbeat timeout por defecto 30 min, configurable.
- Roles: admin, developer, reviewer. Los usuarios los crea el admin.
- Etiqueta de fábrica: la pone el hub si el primer filtrado (intake) es favorable; si no, la revisa un humano y la pone él. Etiqueta "taken": se marca en la plataforma y se sincroniza al repositorio remoto (el remoto es el reflejo).
- Entradas de fuera (app/ticketing, formulario, API): viven en el hub, etiquetadas con su origen ("from app"); el intake las procesa igual.
- Sin crédito o límite del dev: la tarea queda sin asignar ("sin nada") hasta que se renueve el límite o se amplíe; el cliente la devuelve al hub.
- Comando: `/factory`.
- Demo: repo privado `maavcrusoe/meme-demo` (generador de memes), local en `C:\Users\Miguel Angel\Documents\GitHub\meme-demo`, con `checks.sh` y `.factory/config.yaml` (hubUrl placeholder).
