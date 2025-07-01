import os
import base64

def write_macaroon_from_env():
    macaroon_b64 = os.getenv("ADMIN_MACAROON_B64")
    if not macaroon_b64:
        raise RuntimeError("Macaroon non trouvé dans les variables d'environnement")
    
    decoded = base64.b64decode(macaroon_b64)
    with open("certs/admin.macaroon", "wb") as f:
        f.write(decoded)
