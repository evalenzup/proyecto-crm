import sys
import os

# Add parent dir to path to import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app.services.usuario_service import usuario_repo
from app.schemas.usuario import UsuarioCreate, RolUsuario
from app.models import Base

def create_admin():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        email = "admin@example.com"
        print(f"Checking if user {email} exists...")
        existing = usuario_repo.get_by_email(db, email=email)
        if existing:
            print("User already exists.")
            return

        print("Creating default admin user...")
        user_in = UsuarioCreate(
            email=email,
            password="admin",
            rol=RolUsuario.ADMIN,
            nombre_completo="Admin Default",
            is_active=True
        )
        usuario_repo.create(db, obj_in=user_in)
        print("Admin user created successfully.")
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
