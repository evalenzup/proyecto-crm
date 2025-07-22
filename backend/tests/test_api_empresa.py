import os
import sys
import pytest
from fastapi.testclient import TestClient

# Añadimos la carpeta raíz del backend al PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Generar ficheros dummy si faltan
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
os.makedirs(FIXTURES_DIR, exist_ok=True)
for fname in ('demo.cer', 'demo.key'):
    fpath = os.path.join(FIXTURES_DIR, fname)
    if not os.path.exists(fpath):
        with open(fpath, 'wb') as f:
            f.write(b'-----BEGIN DUMMY-----\n')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models.base import Base
# Importar modelos para que metadata cree las tablas
import app.models.cliente  # noqa: F401
import app.models.empresa  # noqa: F401
import app.models.producto_servicio  # noqa: F401

# -------- Importar módulos para metadata sin sobrescribir 'app' --------
import importlib
importlib.import_module('app.models.cliente')
importlib.import_module('app.models.empresa')
importlib.import_module('app.models.producto_servicio')

from app.models.base import Base

# Importar dependencias y aplicación
from app.database import get_db
from app.main import app

# Configurar SQLite en memoria para tests
TEST_SQLALCHEMY_DATABASE_URL = 'sqlite:///:memory:'
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
# Crear todas las tablas en memoria
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope='function')
def db_session():
    """Sesión de base de datos en memoria por test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope='function')
def client(db_session):
    """TestClient con override global de la dependencia get_db."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Sobrescribir la dependencia get_db de FastAPI
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)
