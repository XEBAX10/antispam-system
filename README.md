# AntiSpam System — Neo4j + Redis

Proyecto Final de Bases de Datos NoSQL (Prof. Héctor Fabio Ocampo Arbeláez).
API REST en **Python + FastAPI** con **Neo4j** (grafos) y **Redis** (memoria).

## Requisitos
- Docker Desktop
- Git

## Levantar el proyecto

```bash
docker compose up -d --build
```

| Servicio       | URL                                  | Credenciales            |
|----------------|--------------------------------------|-------------------------|
| API (Swagger)  | http://localhost:8000/docs           | —                       |
| Neo4j Browser  | http://localhost:7474                | neo4j / antispam123     |
| Redis          | localhost:6379                       | —                       |

Verificar conexión: http://localhost:8000/api/health

## Poblar la base (script semilla)

```bash
docker compose exec api python -m scripts.seed --limpiar
```

Carga: 5 operadoras, 20 troncales, 12 prefijos, 4.000 usuarios, ~4.700 líneas,
6 campañas de fraude (150 líneas FRAUDULENTAS), 60 números rotativos,
**50.000 CDRs** (`LLAMO`) y 3.000 reportes (`REPORTO`).
Usa `random.seed(42)`, así que todo el equipo tiene los mismos datos.

Comprobar en Neo4j Browser:
```cypher
MATCH (n) RETURN labels(n) AS etiqueta, count(*) AS total;
MATCH ()-[r]->() RETURN type(r) AS relacion, count(*) AS total;
```

## Estructura

```
app/
  main.py          -> arranque de la API (cada integrante registra su router aquí)
  database.py      -> conexión compartida: from app.database import ejecutar, redis_client
  init_db.py       -> UNIQUE CONSTRAINT e índices de Neo4j
  schemas.py       -> modelos Pydantic
  routers/
    operadoras.py  -> RF-06
    troncales.py   -> RF-07
    prefijos.py    -> RF-08
scripts/
  seed.py          -> datos sintéticos (50.000+ CDRs)
```

## Endpoints de catálogo (Persona 1)

| Método | Ruta                          | RF    |
|--------|-------------------------------|-------|
| POST   | /api/operadoras               | RF-06 |
| GET    | /api/operadoras               | RF-06 |
| GET    | /api/operadoras/{id}          | RF-06 |
| PUT    | /api/operadoras/{id}          | RF-06 |
| DELETE | /api/operadoras/{id}          | RF-06 |
| POST   | /api/troncales                | RF-07 |
| GET    | /api/troncales                | RF-07 |
| GET    | /api/troncales/{id}           | RF-07 |
| PUT    | /api/troncales/{id}           | RF-07 |
| DELETE | /api/troncales/{id}           | RF-07 |
| POST   | /api/prefijos                 | RF-08 |
| GET    | /api/prefijos                 | RF-08 |
| GET    | /api/prefijos/{codigo}        | RF-08 |
| PUT    | /api/prefijos/{codigo}        | RF-08 |
| DELETE | /api/prefijos/{codigo}        | RF-08 |

Ejemplo crear troncal:
```json
POST /api/troncales
{
  "troncal_id": "TR-100",
  "nombre": "Troncal Cali Norte",
  "tipo": "SIP",
  "ciudad": "Cali",
  "pais": "CO",
  "nivel_confianza": 85,
  "politica_trafico": "PERMITIDO",
  "operadora_id": "OP-01"
}
```

No se puede borrar una operadora con troncales/prefijos, ni una troncal o prefijo con líneas asociadas (responde 409).

## Contratos acordados (Fase 1)

**Etiquetas Neo4j:** `Linea`, `Usuario`, `Operadora`, `Troncal`, `Prefijo`, `Campana`, `Apelacion`
**Relaciones:** `LLAMO`, `REPORTO`, `POSEE`, `PERTENECE_A_PREFIJO`, `ASIGNADO_A`, `OPERADA_POR`, `SALE_POR`, `MIEMBRO_DE`, `APELA`, `SOLICITADA_POR`

**Claves Redis:**

| Clave                     | Tipo        | TTL    | Responsable |
|---------------------------|-------------|--------|-------------|
| `whitelist:{numero}`      | String      | Opcional | Persona 4 |
| `bloqueo:{numero}`        | Hash        | 24 h   | Persona 3   |
| `cuarentena:{numero}`     | String      | 30 min | Persona 2   |
| `rate:{numero}:{minuto}`  | String INCR | 120 s  | Persona 2   |
| `ultracortas:{numero}`    | String      | 10 min | Persona 2   |
| `idx:bloqueos`            | Sorted Set  | No     | Persona 3   |
| `alertas:propagacion`     | Pub/Sub     | No     | Persona 3   |

Números en formato E.164 sin `+`: `573001234567`.

## Cómo agregar tu módulo

1. Crea tu rama: `git checkout -b feature/trafico-redis` (o la tuya)
2. Crea tu archivo en `app/routers/` (copia la estructura de `operadoras.py`)
3. Regístralo en `app/main.py`:
   ```python
   from app.routers import llamadas
   app.include_router(llamadas.router)
   ```

Ramas: `feature/catalogos` (P1), `feature/trafico-redis` (P2), `feature/reputacion` (P3),
`feature/apelaciones-reportes` (P4), `feature/grafos-benchmark` (P5).
