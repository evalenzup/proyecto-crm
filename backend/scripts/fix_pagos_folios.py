import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.pago import Pago
from app.config import settings

def fix_folios():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Get all payments ordered by creation date
        pagos = db.query(Pago).order_by(Pago.creado_en).all()
        
        print(f"Found {len(pagos)} payments.")
        
        # Group by company to maintain separate sequences per company 
        # (Though user seemingly implid one company context, good practice generally)
        pagos_by_company = {}
        for pago in pagos:
            if pago.empresa_id not in pagos_by_company:
                pagos_by_company[pago.empresa_id] = []
            pagos_by_company[pago.empresa_id].append(pago)
            
        for empresa_id, company_pagos in pagos_by_company.items():
            print(f"Processing company {empresa_id}: {len(company_pagos)} payments.")
            current_folio = 1
            for pago in company_pagos:
                old_folio = pago.folio
                new_folio = str(current_folio)
                
                if old_folio != new_folio:
                    pago.folio = new_folio
                    # Ensure series is P as per our fix
                    if not pago.serie:
                        pago.serie = "P"
                    print(f"  - Updated Pago {pago.id}: Folio {old_folio} -> {new_folio}, Serie {pago.serie}")
                else:
                    print(f"  - Pago {pago.id}: Folio {old_folio} OK")
                
                current_folio += 1
        
        db.commit()
        print("Folios updated successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"Error updating folios: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_folios()
