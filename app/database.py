"""
Conexiones compartidas a Neo4j y Redis.
Todos los integrantes importan desde aqui:
    from app.database import ejecutar, redis_client
"""
import os

import redis
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "antispam123")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Driver de Neo4j (uno solo para toda la app)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Cliente de Redis (decode_responses=True devuelve str en vez de bytes)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def convertir(valor):
    """Convierte fechas de Neo4j (DateTime) a texto ISO para que FastAPI las pueda devolver en JSON."""
    if isinstance(valor, dict):
        return {k: convertir(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [convertir(v) for v in valor]
    if hasattr(valor, "iso_format"):
        return valor.iso_format()
    return valor


def ejecutar(query, parametros=None):
    """Ejecuta una consulta Cypher y devuelve una lista de diccionarios."""
    with driver.session() as session:
        resultado = session.run(query, parametros or {})
        return [convertir(registro.data()) for registro in resultado]
