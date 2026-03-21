import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# ── PYTHONPATH al root del backend ─────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Env mínimos para Settings() antes de importar la app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENCRYPTION_KEY", "2oUnSlmpjN0_TYGhPvJBEK0t3rimeuP3CRcDfH7kLX4=")

from app.main import app as fastapi_app  # noqa: E402
from app.database import get_db          # noqa: E402
from app.models.base import Base         # noqa: E402
from app.models.usuario import Usuario   # noqa: E402
from app.core.security import get_password_hash, create_access_token  # noqa: E402

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


# Forzar FK en SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def usuario_admin(db_session):
    """Crea un usuario admin en la BD de prueba y devuelve (usuario, token)."""
    from app.models.empresa import Empresa

    empresa = Empresa(
        nombre="EMPRESA TEST",
        nombre_comercial="TEST",
        ruc="RUC-TEST",
        rfc="AAA010101AAA",
        regimen_fiscal="601",
        codigo_postal="01000",
        contrasena="x",
    )
    db_session.add(empresa)
    db_session.flush()

    user = Usuario(
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        nombre_completo="Admin Test",
        rol="admin",
        is_active=True,
        empresa_id=empresa.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id)
    return user, token


@pytest.fixture(scope="function")
def auth_client(client, usuario_admin):
    """TestClient con Authorization header ya configurado."""
    _, token = usuario_admin
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
