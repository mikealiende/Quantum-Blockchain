import hashlib
import json
from time import time
from typing import List, Any 
from attack_block import Block

class Blockchain:
    def __init__(self, difficulty: int = 4): # Difficulty = numero de ceros iniciales
        self.chain: List[Block] = []
        self.pending_transactions: List[Any] = [] # Mempool
        self.difficulty = difficulty
        # Crear el bloque genesis
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, time(), [], "0", "none")
        genesis_block.hash = genesis_block.calculate_hash()

        self.chain.append(genesis_block)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Any):
        self.pending_transactions.append(transaction)

    

    
    
    
            
    
