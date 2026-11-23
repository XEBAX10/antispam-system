"""
Crea los UNIQUE CONSTRAINT e indices de Neo4j.
Se ejecuta automaticamente al iniciar la API (ver main.py).
"""
from app.database import ejecutar

CONSTRAINTS = [
    "CREATE CONSTRAINT linea_numero IF NOT EXISTS FOR (l:Linea) REQUIRE l.numero IS UNIQUE",
    "CREATE CONSTRAINT usuario_id IF NOT EXISTS FOR (u:Usuario) REQUIRE u.usuario_id IS UNIQUE",
    "CREATE CONSTRAINT operadora_id IF NOT EXISTS FOR (o:Operadora) REQUIRE o.operadora_id IS UNIQUE",
    "CREATE CONSTRAINT troncal_id IF NOT EXISTS FOR (t:Troncal) REQUIRE t.troncal_id IS UNIQUE",
    "CREATE CONSTRAINT prefijo_codigo IF NOT EXISTS FOR (p:Prefijo) REQUIRE p.codigo IS UNIQUE",
    "CREATE CONSTRAINT campana_id IF NOT EXISTS FOR (c:Campana) REQUIRE c.campana_id IS UNIQUE",
    "CREATE CONSTRAINT apelacion_id IF NOT EXISTS FOR (a:Apelacion) REQUIRE a.apelacion_id IS UNIQUE",
]

INDICES = [
    # Para filtrar lineas por estado o score en los reportes
    "CREATE INDEX linea_estado IF NOT EXISTS FOR (l:Linea) ON (l.estado)",
    "CREATE INDEX linea_score IF NOT EXISTS FOR (l:Linea) ON (l.spam_score)",
    # Para reportes por rango de fechas (RF-20)
    "CREATE INDEX llamo_fecha IF NOT EXISTS FOR ()-[r:LLAMO]-() ON (r.fecha_hora)",
    "CREATE INDEX reporto_fecha IF NOT EXISTS FOR ()-[r:REPORTO]-() ON (r.fecha_reporte)",
]


def crear_constraints():
    for query in CONSTRAINTS + INDICES:
        ejecutar(query)
    print("Constraints e indices de Neo4j listos")


if __name__ == "__main__":
    crear_constraints()
