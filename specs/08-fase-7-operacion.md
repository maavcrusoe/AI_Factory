# Spec 08: Fase 7, operación

## Objetivo
Desplegar el hub en un servidor interno y operarlo.

## Alcance
Docker Compose (api, dashboard, postgres), backups/restore, métricas y logs, runbooks, rotación de tokens, retención.

## Success Criteria
1. `docker compose up` levanta el hub.
2. Backup y restore probados.
3. Un reinicio no pierde estado.
4. Métricas básicas por proyecto.

## Preguntas abiertas
- Servidor y SO de despliegue.
