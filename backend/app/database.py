# Importa la función para crear el motor de conexión a la base de datos
from sqlalchemy import create_engine
# Importa el generador de sesiones para interactuar con la base de datos
from sqlalchemy.orm import sessionmaker
# Importa la configuración del entorno desde config.py
from app.config import settings
# Crea una instancia del motor de base de datos utilizando la URL definida en el archivo .env
engine = create_engine(settings.DATABASE_URL)
# Configura la clase SessionLocal para crear nuevas sesiones de base de datos
SessionLocal = sessionmaker(
    autocommit=False,  # Desactiva el autocommit para tener control manual del guardado
    autoflush=False,   # Desactiva el autoflush para evitar sincronización automática
    bind=engine        # Asocia el motor de base de datos a las sesiones
)

# Función generadora que retorna una sesión de base de datos para usar en los endpoints de FastAPI
def get_db():
    db = SessionLocal()  # Crea una nueva sesión
    try:
        yield db         # Entrega la sesión al consumidor (por ejemplo, un endpoint)
    finally:
        db.close()       # Asegura que la sesión se cierre después de su uso
