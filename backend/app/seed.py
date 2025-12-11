# seed.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.usuario import Usuario, RolUsuario
from app.core.security import get_password_hash
from app.models.base import Base


def init_db(db: Session) -> None:
    # Asegurar que las tablas existen (en caso de que no usen alembic aun para esto)
    # Base.metadata.create_all(bind=engine) # Opcional si ya tienen migraciones

    admin_email = "admin@example.com"
    admin_password = "admin"
    
    user = db.query(Usuario).filter(Usuario.email == admin_email).first()
    if not user:
        user = Usuario(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            nombre_completo="Administrador",
            rol=RolUsuario.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Usuario admin creado: {admin_email} / {admin_password}")
    else:
        print(f"Usuario admin ya existe: {admin_email}")

if __name__ == "__main__":
    db = SessionLocal()
    init_db(db)
