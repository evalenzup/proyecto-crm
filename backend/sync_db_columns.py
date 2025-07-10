from sqlalchemy import create_engine, inspect, text
from app.models.empresa import Empresa
from app.models.cliente import Cliente

# Configuración de conexión manual
db_user = "postgres"
db_password = "postgres"
db_host = "localhost"
db_port = "5432"
db_name = "app"

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Crear conexión al engine
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
connection = engine.connect()


def sync_table_columns(model, table_name):
    print(f"🚀 Sincronizando columnas de la tabla: {table_name}")
    columns_in_db = [col["name"] for col in inspector.get_columns(table_name)]

    for column in model.__table__.columns:
        if column.name not in columns_in_db:
            # Determinar tipo SQL
            col_type = str(column.type)
            if "CHAR" in col_type:
                # VARCHAR con longitud opcional; si no hay, usar TEXT
                length = getattr(column.type, 'length', None)
                if length:
                    col_type = f"VARCHAR({length})"
                else:
                    col_type = "TEXT"
            elif "UUID" in col_type:
                col_type = "UUID"
            elif "INTEGER" in col_type:
                col_type = "INTEGER"
            elif "TIMESTAMP" in col_type:
                col_type = "TIMESTAMP"
            elif "TEXT" in col_type:
                col_type = "TEXT"
            else:
                print(f"⚠️ Tipo no reconocido para {column.name}: {col_type}. Agrega manualmente si es necesario.")
                continue

            alter_stmt = f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {col_type};'
            print(f"➕ Agregando columna: {column.name} con tipo: {col_type}")
            try:
                connection.execute(text(alter_stmt))
                print(f"✅ Columna {column.name} agregada correctamente.")
            except Exception as e:
                print(f"⚠️ Error al agregar columna {column.name}: {e}")


if __name__ == '__main__':
    sync_table_columns(Empresa, "empresas")
    sync_table_columns(Cliente, "clientes")

    connection.commit()
    connection.close()
    print("✅ Sincronización finalizada correctamente.")

