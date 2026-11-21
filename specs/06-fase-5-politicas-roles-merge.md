# Spec 06: Fase 5, políticas, roles y merge

## Objetivo
Decidir cuándo se exige revisión humana y quién puede aprobar y mergear.

## Roles
`admin` (crea usuarios, edita políticas), `developer` (usa `/factory`), `reviewer` (aprueba merges).

## Política de merge humano (configurable)
Exige revisor si: dificultad alta; paths sensibles del core; funcionalidad no planificada o fuera de alcance; cambio de texto cuyo significado difiere mucho del original. Los triviales (botón, texto menor) pueden ir automáticos. El reviewer del dev valora el cambio; si es dudoso, humano.
Valor inicial recomendado: todo merge requiere humano y se relaja con datos.

## Success Criteria
1. Política editable por admin y versionada.
2. Un cambio trivial puede quedar listo sin humano; uno sensible queda `WAITING_HUMAN_MERGE`.
3. Solo `reviewer`/`admin` aprueban en el dashboard.
4. Merge solo tras aprobación y gate final sobre el commit exacto.
5. Auditoría de cada decisión.

## Tareas
- [ ] Modelo de política + motor de evaluación. Verify: tests por regla.
- [ ] Roles y permisos. Verify: tests de auth.
- [ ] Pantalla de aprobaciones. Verify: Playwright.
- [ ] Merge controlado vía adapter. Verify: merge en meme-demo.

## Preguntas abiertas
- Lista inicial de paths sensibles por proyecto.
