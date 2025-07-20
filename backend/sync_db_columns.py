from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import UniqueConstraint
from app.models.empresa import Empresa
from app.models.cliente import Cliente
from app.models.producto_servicio import ProductoServicio

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

def get_unique_constraints_from_db(table_name):
    result = connection.execute(text(f"""
        SELECT conname
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = :table_name AND contype = 'u';
    """), {"table_name": table_name})
    return [row["conname"] for row in result.mappings()]

def sync_table_columns(model, table_name):
    print(f"🚀 Sincronizando columnas de la tabla: {table_name}")
    columns_in_db = {col["name"]: col for col in inspector.get_columns(table_name)}

    for column in model.__table__.columns:
        col_name = column.name
        col_type = str(column.type)
        length = getattr(column.type, 'length', None)

        if "CHAR" in col_type:
            col_type_sql = f"VARCHAR({length})" if length else "TEXT"
        elif "UUID" in col_type:
            col_type_sql = "UUID"
        elif "INTEGER" in col_type:
            col_type_sql = "INTEGER"
        elif "TIMESTAMP" in col_type:
            col_type_sql = "TIMESTAMP"
        elif "TEXT" in col_type:
            col_type_sql = "TEXT"
        elif "BOOLEAN" in col_type:
            col_type_sql = "BOOLEAN"
        elif "NUMERIC" in col_type or "DECIMAL" in col_type:
            precision = getattr(column.type, 'precision', 18)
            scale = getattr(column.type, 'scale', 2)
            col_type_sql = f"NUMERIC({precision},{scale})"
        else:
            print(f"⚠️ Tipo no reconocido para {col_name}: {col_type}")
            continue

        # Nueva columna
        if col_name not in columns_in_db:
            alter_stmt = f'ALTER TABLE {table_name} ADD COLUMN "{col_name}" {col_type_sql};'
            print(f"➕ Agregando columna: {col_name} con tipo: {col_type_sql}")
            try:
                connection.execute(text(alter_stmt))
                print(f"✅ Columna {col_name} agregada.")
            except Exception as e:
                print(f"❌ Error al agregar columna {col_name}: {e}")
                connection.rollback()
        else:
            # Verificar si necesita modificación
            db_col = columns_in_db[col_name]
            db_type = db_col["type"]
            db_nullable = db_col["nullable"]
            model_nullable = column.nullable

            # Nota: comparación simplificada
            if db_nullable != model_nullable:
                action = "DROP" if model_nullable else "SET"
                alter_null = f'ALTER TABLE {table_name} ALTER COLUMN "{col_name}" {action} NOT NULL;'
                print(f"🛠 Ajustando nullable: {col_name} → {action} NOT NULL")
                try:
                    connection.execute(text(alter_null))
                    print("✅ Atributo nullable actualizado.")
                except Exception as e:
                    print(f"❌ Error al modificar nullable: {e}")
                    connection.rollback()

    # ──────────────────────────────────────
    # Validar UNIQUE constraints
    existing_uniques = get_unique_constraints_from_db(table_name)
    for constraint in model.__table__.constraints:
        if isinstance(constraint, UniqueConstraint):
            name = constraint.name
            cols = [col.name for col in constraint.columns]
            if name not in existing_uniques:
                col_list = ", ".join(f'"{col}"' for col in cols)
                sql = f'ALTER TABLE {table_name} ADD CONSTRAINT {name} UNIQUE ({col_list});'
                print(f"➕ Agregando UNIQUE constraint: {name} en columnas: {col_list}")
                try:
                    connection.execute(text(sql))
                    print("✅ UNIQUE constraint creado correctamente.")
                except Exception as e:
                    print(f"❌ Error al crear UNIQUE constraint {name}: {e}")
                    connection.rollback()


def corregir_emails_invalidos():
    print("🔍 Corrigiendo emails inválidos en la tabla empresas...")
    update_stmt = text("""
        UPDATE empresas
        SET email = CONCAT(SPLIT_PART(email, '@', 1), '@example.com')
        WHERE email IS NOT NULL AND email NOT LIKE '%@%.%';
    """)
    try:
        result = connection.execute(update_stmt)
        print(f"✅ Corrección completada. Filas afectadas: {result.rowcount}")
    except Exception as e:
        print(f"⚠️ Error al corregir emails inválidos: {e}")
        connection.rollback()


if __name__ == '__main__':
    for model, name in [
        (Empresa, "empresas"),
        # (Cliente, "clientes"),
        (ProductoServicio, "productos_servicios"),
    ]:
        try:
            sync_table_columns(model, name)
        except Exception as e:
            print(f"❌ Error al sincronizar {name}: {e}")
            connection.rollback()

    corregir_emails_invalidos()
    connection.commit()
    connection.close()
    print("✅ Sincronización finalizada correctamente.")