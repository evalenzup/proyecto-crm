from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate, EmpresaOut
from app.catalogos_sat import validar_regimen_fiscal

router = APIRouter()

@router.post("/", response_model=EmpresaOut, status_code=201)
def crear_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    if not validar_regimen_fiscal(empresa.regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido. Debe ser una clave válida del SAT.")
    nueva_empresa = Empresa(**empresa.dict())
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return nueva_empresa

@router.get("/", response_model=List[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    empresas = db.query(Empresa).all()
    return empresas

@router.get("/{id}", response_model=EmpresaOut)
def obtener_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@router.put("/{id}", response_model=EmpresaOut)
def actualizar_empresa(id: UUID, empresa_update: EmpresaUpdate, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if empresa_update.regimen_fiscal and not validar_regimen_fiscal(empresa_update.regimen_fiscal):
        raise HTTPException(status_code=400, detail="Régimen fiscal inválido. Debe ser una clave válida del SAT.")
    for campo, valor in empresa_update.dict(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa

@router.delete("/{id}", status_code=204)
def eliminar_empresa(id: UUID, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(empresa)
    db.commit()
    return Response(status_code=204)
