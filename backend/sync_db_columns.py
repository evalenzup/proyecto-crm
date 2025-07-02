from sqlalchemy import create_engine, inspect, text
from app.models.empresa import Empresa
from app.models.cliente import Cliente

# Configuración de conexión manual
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "app"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear conexión al engine
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
connection = engine.connect()

def sync_table_columns(model, table_name):
    print(f"🚀 Sincronizando columnas de la tabla: {table_name}")
    columns_in_db = [col["name"] for col in inspector.get_columns(table_name)]
    for column in model.__table__.columns:
        if column.name not in columns_in_db:
            col_type = str(column.type)
            if "VARCHAR" in col_type or "CHAR" in col_type:
                col_type = f"VARCHAR({column.type.length})"
            elif "UUID" in col_type:
                col_type = "UUID"
            elif "INTEGER" in col_type:
                col_type = "INTEGER"
            elif "TIMESTAMP" in col_type:
                col_type = "TIMESTAMP"
            elif "TEXT" in col_type:
                col_type = "TEXT"
            else:
                print(f"⚠️ Tipo no reconocido: {col_type}, agrega manualmente si es necesario.")
                continue

            alter_stmt = f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {col_type};'
            print(f"➕ Agregando columna: {column.name} con tipo: {col_type}")
            try:
                connection.execute(text(alter_stmt))
                print(f"✅ Columna {column.name} agregada correctamente.")
            except Exception as e:
                print(f"⚠️ Error al agregar columna {column.name}: {e}")

sync_table_columns(Empresa, "empresas")
sync_table_columns(Cliente, "clientes")

connection.commit()
connection.close()
print("✅ Sincronización finalizada correctamente.")
