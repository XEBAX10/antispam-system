"""
Punto de entrada de la API REST - AntiSpam System (Neo4j + Redis).

Cada integrante agrega su router aqui con app.include_router(...):
  Persona 1 -> operadoras, troncales, prefijos   (listo)
  Persona 2 -> llamadas (validar, cdr)
  Persona 3 -> reportes comunitarios / reputacion
  Persona 4 -> apelaciones y reportes operativos
  Persona 5 -> analitica de grafos
"""
import time

from fastapi import FastAPI

from app.database import driver, ejecutar, redis_client
from app.init_db import crear_constraints
from app.routers import operadoras, prefijos, troncales

app = FastAPI(
    title="AntiSpam System",
    description="Sistema de reputacion telefonica en tiempo real con Neo4j + Redis",
    version="1.0.0",
)

app.include_router(operadoras.router)
app.include_router(troncales.router)
app.include_router(prefijos.router)


@app.on_event("startup")
def iniciar():
    # Neo4j puede tardar unos segundos en aceptar conexiones
    for intento in range(10):
        try:
            crear_constraints()
            return
        except Exception as error:
            print(f"Esperando a Neo4j ({intento + 1}/10): {error}")
            time.sleep(3)


@app.on_event("shutdown")
def cerrar():
    driver.close()


@app.get("/api/health", tags=["Salud"])
def health():
    """Verifica que la API llegue a Neo4j y a Redis."""
    estado = {"api": "OK"}
    try:
        ejecutar("RETURN 1")
        estado["neo4j"] = "OK"
    except Exception as error:
        estado["neo4j"] = f"ERROR: {error}"
    try:
        redis_client.ping()
        estado["redis"] = "OK"
    except Exception as error:
        estado["redis"] = f"ERROR: {error}"
    return estado
