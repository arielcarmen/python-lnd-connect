# LND Lightning API Server

A Python FastAPI server that provides an open HTTP API for interacting with an LND Lightning Network node. This API allows you to perform common Lightning Network operations without authentication.

## Features

- 🚀 **No Authentication Required** - Open API for easy integration
- ⚡ **Lightning Operations** - Create invoices, send payments, check balances
- 🔍 **Node Information** - Get node status, channel info, and network data
- 📊 **Payment History** - View invoices and payment records
- 🛠️ **Developer Friendly** - Auto-generated OpenAPI documentation
- 🐍 **Virtual Environment** - Isolated Python environment for clean dependencies

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check and node status |
| GET | `/info` | Detailed node information |
| GET | `/balance` | Wallet and channel balances |
| POST | `/invoices` | Create a new invoice |
| GET | `/invoices` | List all invoices |
| GET | `/invoices/{r_hash}` | Get specific invoice |
| POST | `/payments` | Send a payment |
| GET | `/payments` | List payment history |
| GET | `/decode/{payment_request}` | Decode payment request |

## Prerequisites

- Python 3.8 or higher
- LND Lightning node running and accessible
- LND admin macaroon and TLS certificate

## Quick Setup

### 1. Clone and Setup

```bash
# Clone your project
git clone <your-repo>
cd lnd-lightning-api

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### 2. Configure Environment

Edit the `.env` file with your LND configuration:

```bash
# LND Lightning Node Configuration
LND_HOST=localhost:10009
LND_TLS_CERT_PATH=~/.lnd/tls.cert
LND_MACAROON_PATH=~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 3. Start the Server

```bash
# Make run script executable
chmod +x run.sh

# Start the server
./run.sh
```

## Manual Setup

If you prefer to set up manually:

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate gRPC Stubs

```bash
# Download LND protobuf definition
curl -o lightning.proto https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/lightning.proto

# Generate Python gRPC stubs
python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. lightning.proto
```

### 4. Configure Environment

```bash
cp .env .env.local
# Edit .env with your LND configuration
```

### 5. Start Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python main.py

# Or with uvicorn for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage Examples

### Check Node Health

```bash
curl http://localhost:8000/health
```

### Get Node Information

```bash
curl http://localhost:8000/info
```

### Create an Invoice

```bash
curl -X POST "http://localhost:8000/invoices" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "memo": "Test invoice",
    "expiry": 3600
  }'
```

### Send a Payment

```bash
curl -X POST "http://localhost:8000/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_request": "lnbc..."
  }'
```

### Get Balances

```bash
curl http://localhost:8000/balance
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LND_HOST` | `localhost:10009` | LND gRPC server address |
| `LND_TLS_CERT_PATH` | `~/.lnd/tls.cert` | Path to LND TLS certificate |
| `LND_MACAROON_PATH` | `~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon` | Path to LND admin macaroon |
| `SERVER_HOST` | `0.0.0.0` | API server host |
| `SERVER_PORT` | `8000` | API server port |

### LND Configuration

For testnet, update your `.env`:

```bash
LND_MACAROON_PATH=~/.lnd/data/chain/bitcoin/testnet/admin.macaroon
```

## Development

### Running in Development Mode

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Project Structure

```
lnd-lightning-api/
├── venv/                 # Virtual environment
├── main.py