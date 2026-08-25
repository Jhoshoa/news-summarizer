# Orden de ejecución

## Orden completo recomendado

| # | Entregable | Tiempo aprox. | Depende de |
| --- | --- | --- | --- |
| 1 | [Fase 0](fase-0-analitica.md) — Analítica y métricas | 1 semana | — |
| 2 | [Fase 1](fase-1-historias.md) — Modelo de historias canónicas | 1–2 semanas | — (extiende dedup existente) |
| 3 | [Fase 1](fase-1-historias.md) — Deduplicación por niveles y actualizaciones | 2 semanas | #2 |
| 4 | [Fase 2](fase-2-confianza.md) — Fuentes, afirmaciones y trazabilidad | 1–2 semanas | #2 |
| 5 | [Fase 3](fase-3-personalizacion.md) — Onboarding y preferencias | 1 semana | — |
| 6 | [Fase 3](fase-3-personalizacion.md) — Brief personalizado por email | 1 semana | #5 |
| 7 | [Fase 3](fase-3-personalizacion.md) — Entidades, seguimiento y alertas | 2 semanas | #2, #5 |
| 8 | Entrevistas y primeros pilotos B2B | en paralelo desde semana 1 | — |
| 9 | [Fase 4](fase-4-b2b.md) — Workspaces y monitores B2B mínimos | 2 semanas | #7 |
| 10 | [Fase 4](fase-4-b2b.md) — Informes automáticos | 1 semana | #9 |
| 11 | [Fase 4](fase-4-b2b.md) — Cobro a primeros clientes | inmediato, manual | #8 |
| 12 | [Fase 6](fase-6-expansion.md) — Segundo país | después de validar Bolivia | Fase 5 completa |

[Fase 5](fase-5-editorial-ops.md) (panel editorial, fuentes dinámicas,
`country_configurations`) corre en paralelo con #3–#9, priorizando lo que cada fase
necesita (correcciones para Fase 2, gestión de fuentes antes de intentar #12).

**No hay que esperar 12 semanas para hablar con clientes — el punto 8 empieza esta
semana, en paralelo con el punto 1.**

## Esta semana (próximos 7 días)

1. Instalar analítica (Fase 0.1 — tabla `analytics_events` + endpoint `POST /events`).
2. Publicar EcoBrief en una URL estable (verificar que `docker-compose.yml` de
   producción esté sirviendo la versión actual; ver `DEPLOYMENT.md`).
3. Hablar con 15 personas (usuarios finales potenciales).
4. Hablar con 5 posibles clientes B2B.
5. Enviarles manualmente un brief diario (no hace falta automatizar todavía).
6. Preguntar qué información necesitan monitorear (esto informa directamente
   Fase 4.2 — qué monitores construir primero).
7. Medir quién abre el brief y quién pide recibir el siguiente.
8. Intentar cobrar, aunque el producto empresarial sea todavía manual.
9. Empezar el modelo `Story` (migración `012_stories.sql`, Fase 1.1) para sustituir
   la experiencia centrada en artículos sueltos.
10. Documentar cada número para la solicitud de YC (usar
    [narrativa-yc.md](narrativa-yc.md) como plantilla de qué cifras importan).

## Cómo usar este roadmap con Claude Code en las próximas sesiones

Cada fase (`fase-N-*.md`) tiene tablas SQL propuestas, ubicación sugerida de archivos
nuevos, y qué código existente reutilizar. Al pedir implementación, referenciar
directamente el archivo de fase (ej. "implementa la migración 012 de
fase-1-historias.md") en vez de repetir el contexto — así cada sesión no necesita
re-explorar todo el repo.

## Checklist de progreso

- [x] Fase 0 — Analítica y métricas (0.1 y 0.2 mínimas; costo IA y errores de scraping quedan pendientes, no bloqueantes)
- [x] Fase 1.1 — Modelo de historias canónicas (tabla `stories`/`story_articles`, backfill, endpoints `/api/stories`)
- [x] Fase 1.2 — Dedup por niveles (1,2,3,6 construidos; 4,5,7 bloqueados por diseño hasta Fase 3.2/5 o evidencia de que 1-3 no alcanzan)
- [x] Fase 1.3 — Resumen consolidado con contexto multi-fuente
- [x] Fase 1.4 — Actualizaciones incrementales (heurística de título, sin IA todavía)
- [x] Fase 1.5 — Línea de tiempo básica (`articles` + `is_update`; clasificación fina de `relationship_type` queda para cuando 1.3 se extienda con IA)
- [x] Fase 2.1 — Fuentes visibles (backend: `sources`, autor, `is_update` en `/api/stories`)
- [x] Fase 2.4 — Nivel de confianza explicable (`classify_story_confidence`)
- [ ] Fase 2.2 — Citas por afirmación (requiere extender el prompt del summarizer)
- [ ] Fase 2.3 — Comparación de cobertura
- [ ] Fase 2.5 — Correcciones (botón "Reportar error", `story_corrections`, despublicar)
- [ ] Fase 2 (frontend) — Renderizar fuentes/confianza en la UI
- [ ] Fase 3 — Onboarding
- [ ] Fase 3 — Brief por email personalizado
- [ ] Fase 3 — Entidades y seguimiento
- [ ] Entrevistas B2B (mínimo 5 potenciales clientes contactados)
- [ ] Fase 4 — Workspaces y monitores
- [ ] Fase 4 — Informes automáticos
- [ ] Fase 4 — Primer cliente pagando
- [ ] Fase 5 — Panel editorial mínimo
- [ ] Fase 5 — Configuración multi-país
- [ ] Fase 6 — Segundo país piloto
