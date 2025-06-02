from ecdsa import SigningKey, VerifyingKey, SECP256k1
import binascii
import hashlib
import json
from time import time
from typing import List, Any

class Wallet:

    def __init__(self):
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()

    def get_address(self)-> str:
        public_key_bytes = self.public_key.to_string() # Obtener bytes de la clave pública
        hex_address = binascii.hexlify(public_key_bytes).decode('utf-8')
        return hex_address

    def sign(self, data:bytes) -> str:
        signature = self.private_key.sign(data)
        return binascii.hexlify(signature).decode()
    

class Transaction:
    def __init__(self, sender_address:str, recipient_address:str, amount: float, inputs:List[Any]):
        self.sender = sender_address
        self.recipient = recipient_address
        self.amount = amount
        self.inputs = inputs
        self.timestamp = time()
        self.signature = None  # Se añade a posteriori en la cartera

    def calculate_hash(self) -> str:
        tx_data = {
            "sender": self.sender,
            "recipient":self.recipient,
            "amount":self.amount,
            "inputs":self.inputs,
            "timestamp": self.timestamp
        }
        tx_string = json.dumps(tx_data,sort_keys=True).encode()
        return hashlib.sha256(tx_string).hexdigest()
    
    def sign_transaction(self, wallet:Wallet):
        if wallet.get_address() != self.sender:
            raise ValueError("No puedes firmar una transacción para otra cartera")
        tx_hash = self.calculate_hash().encode()
        self.signature = wallet.sign(tx_hash)

    def is_valid(self) -> bool:
        if not self.signature:
            print("Transaction is not signed")
            return False
        
        try:
            public_key_bytes = binascii.unhexlify(self.sender)
            verifying_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)

            signature_bytes = binascii.unhexlify(self.signature)
            tx_hash = self.calculate_hash().encode()

            return verifying_key.verify(signature_bytes, tx_hash)
        except Exception as e:
            print(f"Error en  la Verificacion de firma {e}")
            return False
        
    def __str__(self) :
        sig_preview = self.signature[:10] + "..." if self.signature else "None"
        return f"Tx(From: {self.sender[:10]}..., To: {self.recipient[:10]}..., Amt: {self.amount}, Sig: {sig_preview})"