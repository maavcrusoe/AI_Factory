# 10. Configuración de ejemplo

## `.factory/config.yaml`

```yaml
version: 1
project:
  id: example-web
  defaultBranch: main

intake:
  minimumConfidence: 0.65
  automaticConfidence: 0.80
  activationLabels: [factory, ai-ready]

execution:
  maxConcurrentJobs: 3
  maxBuildRounds: 3
  maxSameFailure: 2
  timeoutMinutes: 45
  budgetUsd: 10

protectedPaths:
  - .github/workflows/**
  - .factory/policies/**
  - .factory/checks/**
  - infra/production/**

reviews:
  always: [code]
  rules:
    - when:
        surfaces: [ui]
      add: [ui, accessibility]
    - when:
        surfaces: [authentication, authorization]
      add: [security, tests]
      requireHuman: true
    - when:
        paths: [infra/**]
      add: [security, infrastructure]
      requireHuman: true

autoApproval:
  enabled: false
  allowedRisk: [low]
  allowedTypes: [documentation, ui-cosmetic, test-only]
  maxChangedFiles: 3
  maxChangedLines: 100
  maxRetries: 1

deployment:
  preview: automatic
  development: human
  staging: human
  production: disabled
```

## `.factory/checks/frontend.yaml`

```yaml
version: 1
checks:
  lint:
    command: npm run lint
    timeoutSeconds: 300
  typecheck:
    command: npm run typecheck
    timeoutSeconds: 300
  unit:
    command: npm test -- --run
    timeoutSeconds: 600
  playwright-targeted:
    command: npm run test:e2e -- --grep @factory
    timeoutSeconds: 900
    artifacts:
      - test-results/**
      - playwright-report/**
  accessibility:
    command: npm run test:a11y
    timeoutSeconds: 600
```

## Intake schema resumido

```json
{
  "decision": "ACCEPT",
  "confidence": 0.9,
  "normalizedTitle": "Cambiar el color del botón principal",
  "type": "ui-cosmetic",
  "difficulty": "low",
  "risk": "low",
  "surfaces": ["frontend", "ui", "accessibility"],
  "acceptanceCriteria": [
    "Usa el token aprobado del sistema de diseño",
    "Mantiene contraste WCAG AA",
    "No cambia el comportamiento del botón"
  ],
  "missingInformation": [],
  "suggestedReviewers": ["code", "ui", "accessibility"]
}
```

## Variables de entorno iniciales

```text
DATABASE_URL=
TEMPORAL_ADDRESS=
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MODEL_PROVIDER=
MODEL_API_KEY=
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
WEBHOOK_HMAC_SECRET=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

Nunca guardar valores reales en el repositorio. El `.env.example` solo contiene nombres y valores no sensibles de ejemplo.
