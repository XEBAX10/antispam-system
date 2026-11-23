"""RF-06: CRUD de operadoras."""
from fastapi import APIRouter, HTTPException

from app.database import ejecutar
from app.schemas import OperadoraActualizar, OperadoraCrear

router = APIRouter(prefix="/api/operadoras", tags=["Operadoras"])


@router.post("", status_code=201)
def crear_operadora(operadora: OperadoraCrear):
    existe = ejecutar(
        "MATCH (o:Operadora {operadora_id: $id}) RETURN o",
        {"id": operadora.operadora_id},
    )
    if existe:
        raise HTTPException(status_code=409, detail="La operadora ya existe")

    resultado = ejecutar(
        "CREATE (o:Operadora $datos) RETURN o",
        {"datos": operadora.model_dump()},
    )
    return resultado[0]["o"]


@router.get("")
def listar_operadoras():
    resultado = ejecutar("MATCH (o:Operadora) RETURN o ORDER BY o.nombre")
    return [fila["o"] for fila in resultado]


@router.get("/{operadora_id}")
def obtener_operadora(operadora_id: str):
    resultado = ejecutar(
        "MATCH (o:Operadora {operadora_id: $id}) RETURN o",
        {"id": operadora_id},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Operadora no encontrada")
    return resultado[0]["o"]


@router.put("/{operadora_id}")
def actualizar_operadora(operadora_id: str, cambios: OperadoraActualizar):
    datos = cambios.model_dump(exclude_none=True)
    if not datos:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    resultado = ejecutar(
        "MATCH (o:Operadora {operadora_id: $id}) SET o += $datos RETURN o",
        {"id": operadora_id, "datos": datos},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Operadora no encontrada")
    return resultado[0]["o"]


@router.delete("/{operadora_id}")
def eliminar_operadora(operadora_id: str):
    resultado = ejecutar(
        """
        MATCH (o:Operadora {operadora_id: $id})
        OPTIONAL MATCH (o)<-[r:OPERADA_POR|ASIGNADO_A]-()
        RETURN count(r) AS relaciones
        """,
        {"id": operadora_id},
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Operadora no encontrada")
    if resultado[0]["relaciones"] > 0:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: tiene troncales o prefijos asociados",
        )

    ejecutar("MATCH (o:Operadora {operadora_id: $id}) DELETE o", {"id": operadora_id})
    return {"mensaje": "Operadora eliminada"}
