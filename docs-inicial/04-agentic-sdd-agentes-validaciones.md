# 4. Agentic SDD, agentes y validaciones

## Especificaciones dentro del repositorio

```text
.factory/
├── config.yaml
├── policies/
├── checks/
└── specs/
    └── WORK-0182/
        ├── request.md
        ├── requirements.md
        ├── acceptance-criteria.md
        ├── technical-design.md
        ├── tasks.md
        ├── validation-plan.yaml
        ├── decisions.md
        ├── progress.md
        └── final-report.md
```

## Función de cada archivo

- `request.md`: entrada original, fuente, autor y enlaces.
- `requirements.md`: objetivo normalizado, requisitos, restricciones y fuera de alcance.
- `acceptance-criteria.md`: condiciones verificables.
- `technical-design.md`: solución propuesta, componentes afectados, compatibilidad y rollback.
- `tasks.md`: tareas pequeñas y comprobables.
- `validation-plan.yaml`: gates y reviewers requeridos.
- `decisions.md`: decisiones y motivos acumulados.
- `progress.md`: rondas, commits y estado.
- `final-report.md`: resumen, evidencias y riesgos residuales.

El Builder trabaja contra la especificación, no vuelve a reinterpretar desde cero la issue en cada ronda.

## Agentes

| Agente | Responsabilidad | Modifica código |
|---|---|---:|
| Intake | Normalizar, clasificar y pedir información | No |
| Spec Writer | Crear requisitos, criterios, diseño y tareas | Solo especificaciones |
| Builder | Implementar la especificación | Sí |
| Test Engineer | Crear o mejorar tests permitidos | Sí, limitado |
| Code Reviewer | Corrección, alcance y mantenibilidad | No |
| Test Reviewer | Cobertura y calidad de pruebas | No |
| Security Reviewer | Riesgo, SAST, secretos y dependencias | No |
| UI Reviewer | Fidelidad visual y sistema de diseño | No |
| UX Reviewer | Flujo y comportamiento | No |
| Accessibility Reviewer | WCAG y axe-core | No |
| Release Reviewer | Evidencias finales y readiness | No |

## Review Router

Selecciona reviewers mediante:

- Tipo de tarea.
- Riesgo del intake.
- Paths previstos y paths realmente modificados.
- Lenguajes y frameworks detectados.
- Tamaño y complejidad del diff.
- Resultados del Gate.
- Destino de despliegue.
- Política del proyecto.

## Matriz de validaciones

| Cambio | Validaciones mínimas |
|---|---|
| Documentación | markdownlint, links |
| UI menor | lint, tests relevantes, Playwright dirigido, snapshot y axe-core |
| Backend menor | lint, typecheck, unit e integración relevante |
| API pública | unit, integración, contract y compatibilidad |
| Auth/seguridad | suite completa, Semgrep, Gitleaks, integración y Security Review |
| Dependencias | tests, OSV-Scanner, Trivy/Grype y changelog |
| Docker | Hadolint, build, Trivy y smoke test |
| Kubernetes/OpenShift | kubeconform, Checkov, Trivy config y políticas |
| Terraform | fmt, validate, TFLint, Checkov y plan |
| Migraciones | tests, rollback y base de datos efímera |
| PowerShell | PSScriptAnalyzer y Pester |

## Gate determinista

El Gate ejecuta comandos reales, guarda stdout, stderr, código de salida, duración, commit SHA y artefactos. El LLM puede explicar el resultado, pero no cambiarlo.

## Failure Report

```json
{
  "phase": "ui-validation",
  "category": "visual-regression",
  "fingerprint": "sha256:...",
  "retryable": true,
  "summary": "El modal desborda en 375x667",
  "evidence": [
    "screenshots/mobile-modal.png",
    "playwright/trace.zip"
  ],
  "suspectedFiles": ["src/components/Dialog.tsx"],
  "requiredAction": "Corregir el responsive sin cambiar el contrato público",
  "attempt": 2,
  "maxAttempts": 3
}
```

## Resultados de reviewers

- `APPROVED`
- `APPROVED_WITH_NOTES`
- `CHANGES_REQUIRED`
- `BLOCKED`
- `HUMAN_REVIEW`

Cada finding incluye severidad, evidencia, archivo/línea, acción requerida y criterio afectado.

## Protección frente a manipulación

- El Builder no modifica policies ni checks protegidos sin aprobación.
- Los checks base se obtienen de la rama principal o imagen del worker.
- La evaluación se asocia al commit SHA.
- Si cambia el commit, los resultados anteriores dejan de ser válidos.
- El Test Engineer no puede eliminar una prueba fallida sin decisión registrada.
