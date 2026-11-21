# 005 (2026-11-21)

- El intake con qwen3.5:4b (en el hub) resume el contexto y da una valoración; si es óptimo -> automático, si duda -> humano. Modelo cambiable más adelante (interfaz `IntakeModel`).
- Etiquetas: si alguien cambia algo en el remoto, gana el hub y se re-sincroniza.
- Specs de las fases 0 a 7 creadas en `specs/`. Pendientes de aprobación del usuario.
