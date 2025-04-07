import hashlib
import json
from time import time
from typing import List, Any # For type hinting
from transactions import Transaction


class Block:
    def __init__(self, index: int, timestamp: float, transactions: List[Transaction], previous_hash: str, mined_by : str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions # List of Transaction objects or dictionaries
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.mined_by = mined_by
        self.hash = self.calculate_hash() # Calculate hash upon creation

    def calculate_hash(self) -> str:
        # Ensure consistent hashing by sorting dictionary keys if transactions are dicts
        # Or use a consistent representation of Transaction objects
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            # Make sure transaction representation is deterministic
            "transactions": [str(tx) for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def __str__(self):
        # For easy printing/representation
        return f"Block #{self.index} [Nonce: {self.nonce}, Hash: {self.hash}, PrevHash: {self.previous_hash}]"