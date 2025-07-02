pip install -r requirements.txt 
curl -o lightning.proto https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/lightning.proto 
python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. lightning.proto; 
cp .env .env.example