import os
import sys

# Añadir la raíz del proyecto al path para que funcionen las importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.associations import cliente_empresa


def delete_all_clients():
    """Se conecta a la BD y elimina todos los registros de la tabla de clientes y sus asociaciones."""
    db = SessionLocal()
    try:
        # Primero, eliminar las asociaciones en la tabla cliente_empresa
        db.execute(cliente_empresa.delete())

        # Después, eliminar a los clientes
        num_rows_deleted = db.query(Cliente).delete()
        db.commit()
        print(f"Éxito: Se eliminaron {num_rows_deleted} clientes y sus asociaciones.")
    except Exception as e:
        db.rollback()
        print(f"Error: No se pudieron eliminar los clientes. {e}")
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_clients()
