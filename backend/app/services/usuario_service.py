from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.repository.base import BaseRepository

class UsuarioRepository(BaseRepository[Usuario, UsuarioCreate, UsuarioUpdate]):
    def create(self, db: Session, *, obj_in: UsuarioCreate) -> Usuario:
        db_obj = Usuario(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password), # Hashing password
            nombre_completo=obj_in.nombre_completo,
            rol=obj_in.rol,
            is_active=obj_in.is_active,
            empresa_id=obj_in.empresa_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Usuario, obj_in: Union[UsuarioUpdate, Dict[str, Any]]
    ) -> Usuario:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_by_email(self, db: Session, *, email: str) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.email == email).first()

usuario_repo = UsuarioRepository(Usuario)
