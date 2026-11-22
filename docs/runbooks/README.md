# Runbooks de operación

Procedimientos para operar el hub en el servidor. Los comandos asumen que estás en la carpeta del repo
en el servidor, con `.env` configurado.

| Runbook | Cuándo usarlo |
|---|---|
| [despliegue.md](despliegue.md) | Primera instalación y actualizaciones |
| [backup-restore.md](backup-restore.md) | Copias de seguridad, restauración, prueba de reinicio |
| [rotacion-tokens.md](rotacion-tokens.md) | Rotar tokens de desarrollador, de integración, la clave de cifrado o contraseñas |
| [items-atascados.md](items-atascados.md) | Items que no avanzan (claims, triage, merge) |
| [ollama-no-disponible.md](ollama-no-disponible.md) | El intake no puede llamar a Ollama |
| [metricas-y-logs.md](metricas-y-logs.md) | Métricas Prometheus, logs estructurados, qué mirar |

Convenciones: los comandos `docker compose` se ejecutan desde la raíz del repo. Si el repo se
llama de otra forma, el nombre del proyecto compose cambia y los volúmenes también: no renombres la
carpeta en un servidor que ya tenga datos.
