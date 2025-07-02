from urllib import request
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import grpc
import os
import codecs
import json
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from macaroon_import import write_macaroon_from_env

# Load environment variables from .env file
load_dotenv()

# Import LND gRPC stubs (you'll need to generate these)
# Run: python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. lightning.proto
try:
    import lightning_pb2 as ln
    import lightning_pb2_grpc as lnrpc
except ImportError:
    print("Warning: LND gRPC stubs not found. Please generate them using:")
    print("python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. lightning.proto")
    print("Make sure to activate your virtual environment first!")

app = FastAPI(
    title="LND Lightning API", 
    version="1.0.0",
    description="Open Lightning Network API for LND node operations"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class Config:
    LND_HOST = os.getenv("LND_HOST", "localhost:10009")
    LND_TLS_CERT_PATH = os.getenv("LND_TLS_CERT_PATH", "certs/tls.cert")
    LND_MACAROON_PATH = os.getenv("LND_MACAROON_PATH", "certs/admin.macaroon")
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    
    # Validate configuration
    @classmethod
    def validate(cls):
        print(f"🚀 Starting LND Lightning API Server")
        print(f"📡 LND host: {cls.LND_HOST}")
        print(f"🔑 TLS cert path: {cls.LND_TLS_CERT_PATH}")
        print(f"🍪 Macaroon path: {cls.LND_MACAROON_PATH}")
        print(f"🌐 Server will run on: http://{cls.SERVER_HOST}:{cls.SERVER_PORT}")
        print(f"📚 API docs available at: http://{cls.SERVER_HOST}:{cls.SERVER_PORT}/docs")

config = Config()
config.validate()

# Pydantic models
class InvoiceRequest(BaseModel):
    amount: int
    memo: Optional[str] = ""
    expiry: Optional[int] = 3600

class PaymentRequest(BaseModel):
    payment_request: str
    amount: Optional[int] = None

class WalletInfo(BaseModel):
    alias: str
    identity_pubkey: str
    num_active_channels: int
    num_peers: int
    block_height: int
    synced_to_chain: bool
    synced_to_graph: bool
    version: str

class Invoice(BaseModel):
    payment_request: str
    r_hash: str
    add_index: int
    amount: int
    memo: str
    expiry: int
    settled: bool
    creation_date: int
    settle_date: Optional[int] = None

class Payment(BaseModel):
    payment_hash: str
    payment_preimage: str
    value: int
    creation_date: int
    fee: int
    payment_request: str
    status: str

class SignMessageRequest(BaseModel):
    message: str

# LND Connection Class
class LNDConnection:
    def __init__(self):
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish connection to LND node"""
        try:
            # Read TLS certificate
            tls_cert_path = os.path.expanduser(config.LND_TLS_CERT_PATH)
            with open(tls_cert_path, 'rb') as f:
                cert = f.read()
            
            # Read macaroon
            macaroon_path = os.path.expanduser(config.LND_MACAROON_PATH)
            with open(macaroon_path, 'rb') as f:
                macaroon_bytes = f.read()
                self.macaroon = codecs.encode(macaroon_bytes, 'hex')
            
            # Create SSL credentials
            ssl_creds = grpc.ssl_channel_credentials(cert)
            
            # Create channel
            self.channel = grpc.secure_channel(config.LND_HOST, ssl_creds)
            
            # Create stub
            self.stub = lnrpc.LightningStub(self.channel)
            
        except Exception as e:
            print(f"Failed to connect to LND: {e}")
            raise
    
    def _get_metadata(self):
        """Get authentication metadata"""
        return [('macaroon', self.macaroon)]
    
    def get_info(self):
        """Get node information"""
        try:
            request = ln.GetInfoRequest()
            response = self.stub.GetInfo(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get node info: {str(e)}")
    
    def create_invoice(self, amount: int, memo: str = "", expiry: int = 3600):
        """Create a new invoice"""
        try:
            request = ln.Invoice(
                value=amount,
                memo=memo,
                expiry=expiry
            )
            response = self.stub.AddInvoice(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")
    
    def lookup_invoice(self, r_hash: str):
        """Look up an invoice by hash"""
        try:
            r_hash_bytes = codecs.decode(r_hash, 'hex')
            request = ln.PaymentHash(r_hash=r_hash_bytes)
            response = self.stub.LookupInvoice(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to lookup invoice: {str(e)}")
    
    def send_payment(self, payment_request: str, amount: int = None):
        """Send a payment"""
        try:
            request = ln.SendRequest(
                payment_request=payment_request,
                amt=amount
            )
            response = self.stub.SendPaymentSync(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send payment: {str(e)}")
    
    def list_invoices(self, num_max_invoices: int = 100):
        """List invoices"""
        try:
            request = ln.ListInvoiceRequest(num_max_invoices=num_max_invoices)
            response = self.stub.ListInvoices(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list invoices: {str(e)}")
    
    def list_payments(self, max_payments: int = 100):
        """List payments"""
        try:
            request = ln.ListPaymentsRequest(max_payments=max_payments)
            response = self.stub.ListPayments(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list payments: {str(e)}")
    
    def get_balance(self):
        """Get wallet balance"""
        try:
            request = ln.WalletBalanceRequest()
            response = self.stub.WalletBalance(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get balance: {str(e)}")
    
    def get_channel_balance(self):
        """Get channel balance"""
        try:
            request = ln.ChannelBalanceRequest()
            response = self.stub.ChannelBalance(request, metadata=self._get_metadata())
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get channel balance: {str(e)}")


# Initialize LND connection
lnd = LNDConnection()

# API Routes
@app.get("/")
async def root():
    return {
        "message": "LND Lightning API Server", 
        "version": "1.0.0",
        "description": "Open API for Lightning Network operations",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    try:
        info = lnd.get_info()
        return {
            "status": "healthy", 
            "node_alias": info.alias,
            "synced_to_chain": info.synced_to_chain,
            "synced_to_graph": info.synced_to_graph,
            "block_height": info.block_height
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/info", response_model=WalletInfo)
async def get_node_info():
    """Get node information"""
    info = lnd.get_info()
    return WalletInfo(
        alias=info.alias,
        identity_pubkey=info.identity_pubkey,
        num_active_channels=info.num_active_channels,
        num_peers=info.num_peers,
        block_height=info.block_height,
        synced_to_chain=info.synced_to_chain,
        synced_to_graph=info.synced_to_graph,
        version=info.version
    )

@app.get("/balance")
async def get_balances():
    """Get wallet and channel balances"""
    wallet_balance = lnd.get_balance()
    channel_balance = lnd.get_channel_balance()
    
    return {
        "wallet_balance": {
            "total_balance": wallet_balance.total_balance,
            "confirmed_balance": wallet_balance.confirmed_balance,
            "unconfirmed_balance": wallet_balance.unconfirmed_balance
        },
        "channel_balance": {
            "balance": channel_balance.balance,
            "pending_open_balance": channel_balance.pending_open_balance
        }
    }

@app.post("/invoices")
async def create_invoice(invoice_req: InvoiceRequest):
    """Create a new invoice"""
    response = lnd.create_invoice(
        amount=invoice_req.amount,
        memo=invoice_req.memo,
        expiry=invoice_req.expiry
    )
    
    return {
        "payment_request": response.payment_request,
        "r_hash": codecs.encode(response.r_hash, 'hex').decode(),
        "add_index": response.add_index
    }

@app.get("/invoices/{r_hash}")
async def get_invoice(r_hash: str):
    """Get invoice details by hash"""
    invoice = lnd.lookup_invoice(r_hash)
    
    return {
        "payment_request": invoice.payment_request,
        "r_hash": codecs.encode(invoice.r_hash, 'hex').decode(),
        "add_index": invoice.add_index,
        "amount": invoice.value,
        "memo": invoice.memo,
        "expiry": invoice.expiry,
        "settled": invoice.settled,
        "creation_date": invoice.creation_date,
        "settle_date": invoice.settle_date if invoice.settled else None
    }

@app.get("/invoices")
async def list_invoices(limit: int = 100):
    """List invoices"""
    invoices = lnd.list_invoices(num_max_invoices=limit)
    
    result = []
    for invoice in invoices.invoices:
        result.append({
            "payment_request": invoice.payment_request,
            "r_hash": codecs.encode(invoice.r_hash, 'hex').decode(),
            "add_index": invoice.add_index,
            "amount": invoice.value,
            "memo": invoice.memo,
            "expiry": invoice.expiry,
            "settled": invoice.settled,
            "creation_date": invoice.creation_date,
            "settle_date": invoice.settle_date if invoice.settled else None
        })
    
    return {"invoices": result}

@app.post("/payments")
async def send_payment(payment_req: PaymentRequest):
    """Send a payment"""
    response = lnd.send_payment(
        payment_request=payment_req.payment_request,
        amount=payment_req.amount
    )
    
    if response.payment_error:
        raise HTTPException(status_code=400, detail=response.payment_error)
    
    return {
        "payment_hash": codecs.encode(response.payment_hash, 'hex').decode(),
        "payment_preimage": codecs.encode(response.payment_preimage, 'hex').decode(),
        "payment_route": {
            "total_fees": response.payment_route.total_fees,
            "total_amt": response.payment_route.total_amt,
            "total_time_lock": response.payment_route.total_time_lock
        }
    }

@app.get("/payments")
async def list_payments(limit: int = 100):
    """List payments"""
    payments = lnd.list_payments(max_payments=limit)
    
    result = []
    for payment in payments.payments:
        result.append({
            "payment_hash": payment.payment_hash,
            "payment_preimage": payment.payment_preimage,
            "value": payment.value,
            "creation_date": payment.creation_date,
            "fee": payment.fee,
            "payment_request": payment.payment_request,
            "status": payment.status.name
        })
    
    return {"payments": result}

@app.get("/decode/{payment_request}")
async def decode_payment_request(payment_request: str):
    """Decode a payment request"""
    try:
        request = ln.PayReqString(pay_req=payment_request)
        response = lnd.stub.DecodePayReq(request, metadata=lnd._get_metadata())
        
        return {
            "destination": response.destination,
            "payment_hash": response.payment_hash,
            "num_satoshis": response.num_satoshis,
            "timestamp": response.timestamp,
            "expiry": response.expiry,
            "description": response.description,
            "description_hash": response.description_hash,
            "fallback_addr": response.fallback_addr,
            "cltv_expiry": response.cltv_expiry
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode payment request: {str(e)}")

from fastapi import Body

@app.post('/signmessage')
async def sign_message(data: SignMessageRequest):
    """Sign a message with the node's private key"""
    msg = data.message
    if not msg:
        return JSONResponse(content={"error": "Message is required"}, status_code=400)

    try:
        sign_req = ln.SignMessageRequest(msg=msg.encode('utf-8'))
        sign_resp = lnd.stub.SignMessage(sign_req, metadata=lnd._get_metadata())
        return JSONResponse(content={"signature": sign_resp.signature}, status_code=200)
    except grpc.RpcError as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post('/verifymessage')
async def verify_message(data: dict = Body(...)):
    msg = data.get('message')
    signature = data.get('signature')
    pubkey = data.get('pubkey') # The public key of the sender
    if not msg or not signature or not pubkey:
        return JSONResponse(content={"error": "Message, signature, and pubkey are required"}, status_code=400)

    try:
        verify_req = ln.VerifyMessageRequest(msg=msg.encode('utf-8'), signature=signature)
        verify_resp = lnd.stub.VerifyMessage(verify_req, metadata=lnd._get_metadata())

        # Safely get recovered_pubkey if it exists
        recovered_pubkey = getattr(verify_resp, 'recovered_pubkey', None)
        is_valid = verify_resp.valid
        return JSONResponse(content={"valid": is_valid }, status_code=200)
    except grpc.RpcError as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
# HAIL !
# 
# HYDRA

# Configuration de la connexion à MongoDB

# import pymongo
# import qrcode
# import datetime

# url = "mongodb://localhost:27017/"

# client = pymongo.MongoClient(url)
# db = client["lntest"]
# collection = db["carnets"] 

# @app.get('/vaccine')
# async def vaccines(data: dict = Body(...)):
    # pub_key = data.get('key')
    # user = collection.find_one({"pub_key": pub_key},)
    # carnet = user['carnet']

    # cles_a_supprimer = ["âge", "ville", "profession"]

    # # Supprimer les clés du dictionnaire
    # for cle in cles_a_supprimer:
    #     if cle in user:
    #         del user[cle]

    # img = qrcode.make(carnet)
    # img.save(f"{pub_key}_{datetime.datetime.now()}_qrcode.png")

    # if not vaccines:
    #     return JSONResponse(content={"error": "No vaccines for this patient"}, status_code=400)
    # return JSONResponse(content={"content": carnet }, status_code=200)


# @app.post('/addvaccine')
# async def add_vaccine(data: dict = Body(...)):
#     pub_key = data.get('key')
#     user = collection.find_one({"pub_key": pub_key},)
#     carnet = user['carnet']

#     vaccin = data.get('vaccin')
#     centre_key = data.get('centre_key')
#     date_vaccin = data.get('date_vaccin')
#     expiry_date = data.get('expiry_date')

#     vaccine_datas = {
#         "vaccin": vaccin,
#         "centre_key": centre_key,
#         "date": date_vaccin,
#         "date_expiration": expiry_date
#     }

#     try:
#         sign_request = ln.SignMessageRequest(msg=f"{pub_key+vaccin}".encode('utf-8'))
#         sign_response = lnd.stub.SignMessage(sign_request, metadata=lnd._get_metadata())

#         signature = sign_response.signature
#         vaccine_datas["centre_signature"] = signature

#         carnet[vaccin] = vaccine_datas

#         collection.update_one(
#             {"pub_key": pub_key},
#             {"$set": {'carnet': carnet}}
#         )

#         return JSONResponse(content={"content": carnet}, status_code=200)
#     except grpc.RpcError as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)

def verify_signature(msg, sig):
    try:
        verify_req = ln.VerifyMessageRequest(msg=msg.encode('utf-8'), signature=sig)
        verify_resp = lnd.stub.VerifyMessage(verify_req, metadata=lnd._get_metadata())

        # Safely get recovered_pubkey if it exists
        recovered_pubkey = getattr(verify_resp, 'recovered_pubkey', None)
        is_valid = verify_resp.valid
        return is_valid
    except grpc.RpcError as e:
        return str(e)
    
# Database actions
    
import firebase_admin
from firebase_admin import credentials, firestore

# Use the application default credentials.
cred = credentials.Certificate('./med-book.json')

# Application Default credentials are automatically created.
db_app = firebase_admin.initialize_app(cred)
db = firestore.client()

# from passlib.context import CryptContext
import bcrypt

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str):
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else None

@app.get('/users')
async def get_users(data: dict = Body(...)):
    users_ref = db.collection("users").stream()
    return [doc.to_dict() for doc in users_ref]

@app.post('/login')
async def login(data: dict = Body(...)):
    npi = data.get('npi')
    password = data.get('password')
    db_user = db.collection("users").document(npi).get().to_dict()
    if not db_user:
        return JSONResponse(status_code=404, content={"success": False, "message": "Utilisateur non trouvé"})

    if not verify_password(password, db_user["hashed_password"]):
        return JSONResponse(content={"success": False,"message": "Mot de passe incorrect"}, status_code=401)

    user_ref = db.collection("users").document(npi)
    return JSONResponse(content={"message": user_ref.get().to_dict()}, status_code=201)

@app.get('/vaccines')
async def get_vaccines_by_user(npi: str):
    user_ref = db.collection("users").document(npi)
    vaccins_in_book = user_ref.get().to_dict()['vaccins']
    return JSONResponse(content={"vaccins": vaccins_in_book}, status_code=200)

@app.post('/add_user')
async def add_vaccine(data: dict = Body(...)):
    npi = data.get('npi')
    nom = data.get('nom')
    prenom = data.get('prenom')
    sexe = data.get('sexe')
    nom = data.get('nom')
    date = data.get('date')
    email = data.get('email')
    telephone = data.get('telephone')
    pwd = data.get('password')

    if get_user(npi):
        return JSONResponse(content={"message": "NPI déjà exitant"}, status_code=400)
    password = hash_password(pwd)
    
    try:
        doc_ref = db.collection("users").document(npi)
        doc_ref.set({"npi": npi,"hashed_password": password, "nom": nom, "prenom": prenom, "sexe": sexe, "email": email, "telephone": telephone, "date": date, "vaccins": {}})
        return JSONResponse(content={"message": "Utilisateur crée avec succes"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    

def get_pubkey():
    response = lnd.stub.GetInfo(ln.GetInfoRequest())
    return response.identity_pubkey
    
@app.post('/add_vaccine')
def add_vaccine(data: dict = Body(...)):
    npi = data.get('npi')

    user_ref = db.collection("users").document(npi)

    vaccin = data.get('vaccin')
    date = data.get('date')
    date_expiration = data.get('date_expiration')
    infos_vaccin = {"vaccin": vaccin, "date": date, "date_expiration": date_expiration}
    
    try:

        try:
            sign_request = ln.SignMessageRequest(msg=f"{npi+vaccin}".encode('utf-8'))
            sign_response = lnd.stub.SignMessage(sign_request, metadata=lnd._get_metadata())

            signature = sign_response.signature
            infos_vaccin["signature"] = signature

            infos_vaccin["pub_key"] = get_pubkey()
            
            vaccins_in_book = user_ref.get().to_dict()['vaccins']

            vaccins_in_book[vaccin] = infos_vaccin

            user_ref.update({"vaccins": vaccins_in_book})

            return JSONResponse(content={"message": "Vaccin crée avec succes"}, status_code=200)
        except grpc.RpcError as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
                
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post('/verify_vaccines')
async def verify_vaccines(data: dict = Body(...)):
    npi = data.get('npi')
    user_ref = db.collection("users").document(npi)

    vaccins_in_book = user_ref.get().to_dict()['vaccins']

    vaccines_to_check = data.get('vaccines_list')

    conform = True

    messages = ""

    for vaccine in vaccines_to_check:
        vaccin = {}
        if vaccine not in vaccins_in_book:
            messages += f"Vaccin {vaccine}: non fait - "
            conform = False
        else:
            vaccin = vaccins_in_book[vaccine]
            signature = vaccin['signature']
            pub_key = vaccin['pub_key']
            message = f"{pub_key+vaccin['vaccin']}"
            if verify_signature(message, signature) == True:
                messages += f"Vaccin {vaccine}: certifcate is ok - "
                
            else:
                print(message)
                messages += f"Vaccin {vaccine}: certifcate invalid - "
                conform = False

    return JSONResponse(content={"message": messages, "conformity": conform}, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)