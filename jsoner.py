import os
import base64

b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64")

if b64:
    decoded = base64.b64decode(b64)
    with open("med-book.json", "wb") as f:
        f.write(decoded)
    print("✅ serviceAccount.json généré avec succès")
else:
    print("❌ Variable GOOGLE_SERVICE_ACCOUNT_B64 manquante")