"""RF-07: CRUD de troncales SIP/PBX, vinculadas con (Troncal)-[:OPERADA_POR]->(Operadora)."""
from fastapi import APIRouter, HTTPException

from app.database import ejecutar
from app.schemas import TroncalActualizar, TroncalCrear

router = APIRouter(prefix="/api/troncales", tags=["Troncales"])

# Devuelve la troncal junto con el id de su operadora
RETORNO = "RETURN t {.*, operadora_id: o.operadora_id} AS troncal"


def operadora_existe(operadora_id):
    resultado = ejecutar(
        "MATCH (o:Operadora {operadora_id: $id}) RETURN o", {"id": operadora_id}
    )
    return len(resultado) > 0


@router.post("", status_code=201)
def crear_troncal(troncal: TroncalCrear):
    if ejecutar("MATCH (t:Troncal {troncal_id: $id}) RETURN t", {"id": troncal.troncal_id}):
        raise HTTPException(status_code=409, detail="La troncal ya existe")
    if not operadora_existe(troncal.operadora_id):
        raise HTTPException(status_code=404, detail="La operadora no existe")

    datos = troncal.model_dump(exclude={"operadora_id"})
    resultado = ejecutar(
        """
        MATCH (o:Operadora {operadora_id: $operadora_id})
        CREATE (t:Troncal $datos)-[:OPERADA_POR]->(o)
        """ + RETORNO,
        {"datos": datos, "operadora_id": troncal.operadora_id},
    )
    return resultado[0]["troncal"]


@router.get("")
def listar_troncales():
    resultado = ejecutar(
        "MATCH (t:Troncal) OPTIONAL MATCH (t)-[:OPERADA_POR]->(o:Operadora) "
        + RETORNO + " ORDER BY t.troncal_id"
    )
    return [fila["troncal"] for fila in resultado]


@router.get("/{troncal_id}")
def obtener_troncal(troncal_id: str):
    resultado = ejecutar(
        "MATCH (t:Troncal {troncal_id: $id}) OPTIONAL MATCH (t)-[:OPERADA_POR]->(o:Operadora) "
        + RETORNO,
        {"id": troncal_id},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Troncal no encontrada")
    return resultado[0]["troncal"]


@router.put("/{troncal_id}")
def actualizar_troncal(troncal_id: str, cambios: TroncalActualizar):
    datos = cambios.model_dump(exclude_none=True)
    nueva_operadora = datos.pop("operadora_id", None)

    if not ejecutar("MATCH (t:Troncal {troncal_id: $id}) RETURN t", {"id": troncal_id}):
        raise HTTPException(status_code=404, detail="Troncal no encontrada")

    if datos:
        ejecutar(
            "MATCH (t:Troncal {troncal_id: $id}) SET t += $datos",
            {"id": troncal_id, "datos": datos},
        )

    # Si cambia de operadora, se borra la relacion vieja y se crea la nueva
    if nueva_operadora:
        if not operadora_existe(nueva_operadora):
            raise HTTPException(status_code=404, detail="La operadora no existe")
        ejecutar(
            """
            MATCH (t:Troncal {troncal_id: $id})
            OPTIONAL MATCH (t)-[r:OPERADA_POR]->()
            DELETE r
            WITH t
            MATCH (o:Operadora {operadora_id: $operadora_id})
            CREATE (t)-[:OPERADA_POR]->(o)
            """,
            {"id": troncal_id, "operadora_id": nueva_operadora},
        )

    return obtener_troncal(troncal_id)


@router.delete("/{troncal_id}")
def eliminar_troncal(troncal_id: str):
    resultado = ejecutar(
        """
        MATCH (t:Troncal {troncal_id: $id})
        OPTIONAL MATCH (t)<-[r:SALE_POR]-(:Linea)
        RETURN count(r) AS lineas
        """,
        {"id": troncal_id},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Troncal no encontrada")
    if resultado[0]["lineas"] > 0:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: hay lineas que salen por esta troncal",
        )

    ejecutar("MATCH (t:Troncal {troncal_id: $id}) DETACH DELETE t", {"id": troncal_id})
    return {"mensaje": "Troncal eliminada"}
