"""
Modelos de entrada (Pydantic) para los CRUD de catalogo.
Los Literal limitan los valores a los definidos en la especificacion.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- Operadora (RF-06) ----------
class OperadoraCrear(BaseModel):
    operadora_id: str
    nombre: str
    pais: str
    nivel_confianza: float = Field(ge=0, le=100)
    estado: Literal["ACTIVA", "INACTIVA"] = "ACTIVA"


class OperadoraActualizar(BaseModel):
    nombre: Optional[str] = None
    pais: Optional[str] = None
    nivel_confianza: Optional[float] = Field(default=None, ge=0, le=100)
    estado: Optional[Literal["ACTIVA", "INACTIVA"]] = None


# ---------- Troncal (RF-07) ----------
class TroncalCrear(BaseModel):
    troncal_id: str
    nombre: str
    tipo: Literal["SIP", "PBX"]
    ciudad: str
    pais: str
    nivel_confianza: float = Field(ge=0, le=100)
    politica_trafico: Literal["PERMITIDO", "RESTRINGIDO", "BLOQUEADO"] = "PERMITIDO"
    operadora_id: str


class TroncalActualizar(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[Literal["SIP", "PBX"]] = None
    ciudad: Optional[str] = None
    pais: Optional[str] = None
    nivel_confianza: Optional[float] = Field(default=None, ge=0, le=100)
    politica_trafico: Optional[Literal["PERMITIDO", "RESTRINGIDO", "BLOQUEADO"]] = None
    operadora_id: Optional[str] = None


# ---------- Prefijo (RF-08) ----------
class PrefijoCrear(BaseModel):
    codigo: str
    pais: str
    region: str
    nivel_confianza: float = Field(ge=0, le=100)
    estado: Literal["ACTIVO", "MONITOREADO"] = "ACTIVO"
    operadora_id: str


class PrefijoActualizar(BaseModel):
    pais: Optional[str] = None
    region: Optional[str] = None
    nivel_confianza: Optional[float] = Field(default=None, ge=0, le=100)
    estado: Optional[Literal["ACTIVO", "MONITOREADO"]] = None
    operadora_id: Optional[str] = None
