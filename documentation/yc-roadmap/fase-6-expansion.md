# Fase 6 — Probar expansión internacional

**Precondición dura:** Bolivia debe estar validada (Fase 0–4 con tracción real) antes
de empezar esto. No es un sprint técnico, es una prueba de replicabilidad.

## Selección del segundo país

Criterios: idioma español, medios fragmentados, acceso razonable a fuentes, algún
usuario/contacto local, problema parecido, posibilidad real de conseguir clientes.
Candidatos sugeridos: Paraguay, Perú o Ecuador — pero la decisión debe basarse en
entrevistas y acceso a clientes, no en facilidad técnica.

## Prueba mínima

- 20–30 fuentes nuevas, configuradas vía `country_configurations` +
  gestión dinámica de fuentes (Fase 5) — **sin tocar código**, solo configuración.
- Categorías y regiones locales.
- Entidades relevantes del país.
- Brief diario funcionando.
- ≥50 usuarios o 2 organizaciones piloto.
- Medir explícitamente tiempo y costo de configuración del segundo país.

## Métrica clave para YC

> Bolivia tomó meses porque construimos la plataforma; el segundo país tomó siete días.

Esta frase solo es defendible si Fase 5 (configuración por país, fuentes dinámicas) se
hizo bien. Si el segundo país requiere tocar código Python para funcionar, la fase 5
quedó incompleta — es la señal de que hay que volver atrás antes de intentarlo.
