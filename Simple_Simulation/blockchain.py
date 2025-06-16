import hashlib
import json
from time import time
from typing import List, Any
from block import Block

class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.pending_transactions: List[Any] = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, time(), [], "0")
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Any):
        self.pending_transactions.append(transaction)

    def mine_pending_transactions(self, miner_reward_address: str) -> Block | None:
        if not self.pending_transactions:
            print("No hay transacciones para minar.")
            return None

        transactions_to_mine = self.pending_transactions[:] # Copy the list


        new_block = Block(
            index=len(self.chain),
            timestamp=time(),
            transactions=transactions_to_mine,
            previous_hash=self.last_block.hash
        )


        new_block.nonce = self.proof_of_work(new_block)
        new_block.hash = new_block.calculate_hash()


        print(f"Bloque minado: {new_block}")
        self.chain.append(new_block)

        self.pending_transactions = [
    
        ]
        self.pending_transactions = []

        return new_block


    def proof_of_work(self, block: Block) -> int:
       
        target = '0' * self.difficulty
        nonce = 0
        while True:
            block.nonce = nonce
            hash_result = block.calculate_hash()
            if hash_result.startswith(target):
                print(f"PoW Existosa! Nonce encontrado: {nonce}, Hash: {hash_result}")
                return nonce
            nonce += 1

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                print(f"Bloque {i}: hash invalido")
                return False

            if current_block.previous_hash != previous_block.hash:
                print(f"Bloque {i}: enlace de hash anterior invalido")
                return False

            if not current_block.hash.startswith('0' * self.difficulty):
                 print(f"Bloque {i}: requisito de Proof of Work no cumplido")
                 return False

        print("La cadena es valida.")
        return True