"""RF-08: CRUD de prefijos, vinculados con (Prefijo)-[:ASIGNADO_A]->(Operadora)."""
from fastapi import APIRouter, HTTPException

from app.database import ejecutar
from app.schemas import PrefijoActualizar, PrefijoCrear

router = APIRouter(prefix="/api/prefijos", tags=["Prefijos"])

# Devuelve el prefijo junto con el id de su operadora
RETORNO = "RETURN p {.*, operadora_id: o.operadora_id} AS prefijo"


def operadora_existe(operadora_id):
    resultado = ejecutar(
        "MATCH (o:Operadora {operadora_id: $id}) RETURN o", {"id": operadora_id}
    )
    return len(resultado) > 0


@router.post("", status_code=201)
def crear_prefijo(prefijo: PrefijoCrear):
    if ejecutar("MATCH (p:Prefijo {codigo: $codigo}) RETURN p", {"codigo": prefijo.codigo}):
        raise HTTPException(status_code=409, detail="El prefijo ya existe")
    if not operadora_existe(prefijo.operadora_id):
        raise HTTPException(status_code=404, detail="La operadora no existe")

    datos = prefijo.model_dump(exclude={"operadora_id"})
    resultado = ejecutar(
        """
        MATCH (o:Operadora {operadora_id: $operadora_id})
        CREATE (p:Prefijo $datos)-[:ASIGNADO_A]->(o)
        """ + RETORNO,
        {"datos": datos, "operadora_id": prefijo.operadora_id},
    )
    return resultado[0]["prefijo"]


@router.get("")
def listar_prefijos():
    resultado = ejecutar(
        "MATCH (p:Prefijo) OPTIONAL MATCH (p)-[:ASIGNADO_A]->(o:Operadora) "
        + RETORNO + " ORDER BY p.codigo"
    )
    return [fila["prefijo"] for fila in resultado]


@router.get("/{codigo}")
def obtener_prefijo(codigo: str):
    resultado = ejecutar(
        "MATCH (p:Prefijo {codigo: $codigo}) OPTIONAL MATCH (p)-[:ASIGNADO_A]->(o:Operadora) "
        + RETORNO,
        {"codigo": codigo},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Prefijo no encontrado")
    return resultado[0]["prefijo"]


@router.put("/{codigo}")
def actualizar_prefijo(codigo: str, cambios: PrefijoActualizar):
    datos = cambios.model_dump(exclude_none=True)
    nueva_operadora = datos.pop("operadora_id", None)

    if not ejecutar("MATCH (p:Prefijo {codigo: $codigo}) RETURN p", {"codigo": codigo}):
        raise HTTPException(status_code=404, detail="Prefijo no encontrado")

    if datos:
        ejecutar(
            "MATCH (p:Prefijo {codigo: $codigo}) SET p += $datos",
            {"codigo": codigo, "datos": datos},
        )

    # Si cambia de operadora, se borra la relacion vieja y se crea la nueva
    if nueva_operadora:
        if not operadora_existe(nueva_operadora):
            raise HTTPException(status_code=404, detail="La operadora no existe")
        ejecutar(
            """
            MATCH (p:Prefijo {codigo: $codigo})
            OPTIONAL MATCH (p)-[r:ASIGNADO_A]->()
            DELETE r
            WITH p
            MATCH (o:Operadora {operadora_id: $operadora_id})
            CREATE (p)-[:ASIGNADO_A]->(o)
            """,
            {"codigo": codigo, "operadora_id": nueva_operadora},
        )

    return obtener_prefijo(codigo)


@router.delete("/{codigo}")
def eliminar_prefijo(codigo: str):
    resultado = ejecutar(
        """
        MATCH (p:Prefijo {codigo: $codigo})
        OPTIONAL MATCH (p)<-[r:PERTENECE_A_PREFIJO]-(:Linea)
        RETURN count(r) AS lineas
        """,
        {"codigo": codigo},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Prefijo no encontrado")
    if resultado[0]["lineas"] > 0:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: hay lineas que pertenecen a este prefijo",
        )

    ejecutar("MATCH (p:Prefijo {codigo: $codigo}) DETACH DELETE p", {"codigo": codigo})
    return {"mensaje": "Prefijo eliminado"}
