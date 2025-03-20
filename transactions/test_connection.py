import os
from web3 import Web3

RPC_URL = os.getenv("PRIVATE_RPC_URL")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if web3.is_connected():
    print("Connected securely to blockchain")
else:
    print("Connection failed")
