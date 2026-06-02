"""
setup_drive_auth.py
-------------------
Ejecutar UNA SOLA VEZ en la Mac para obtener el refresh token de Google Drive.
El token se guarda en data/secrets/drive_token.json y no expira.

Uso:
    python scripts/setup_drive_auth.py

Requiere que el JSON de la service account tenga habilitado OAuth2 client,
O bien un client_secret.json de tipo "Desktop app" en Google Cloud Console.

IMPORTANTE: Este script se ejecuta localmente (Mac), no en el servidor.
El token generado se copia al servidor luego.
"""

import json
import os
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path(__file__).parent.parent / "data/secrets/drive_token.json"
# Ajustar si el client_secret.json está en otro lugar
CLIENT_SECRET = Path(__file__).parent.parent / "data/secrets/client_secret.json"


def main():
    print("=== Configuración OAuth2 para Google Drive ===\n")

    if not CLIENT_SECRET.exists():
        print(f"ERROR: No se encontró {CLIENT_SECRET}")
        print("""
Para obtener el client_secret.json:
1. Ve a https://console.cloud.google.com
2. APIs & Services → Credentials
3. Create Credentials → OAuth 2.0 Client IDs
4. Application type: Desktop app
5. Descarga el JSON y ponlo en: data/secrets/client_secret.json
""")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
    print(f"\n✅ Token guardado en: {TOKEN_PATH}")
    print("\nCopia este archivo al servidor con:")
    print(f"  scp {TOKEN_PATH} usuario@servidor:/ruta/proyecto/backend/data/secrets/drive_token.json")


if __name__ == "__main__":
    main()
