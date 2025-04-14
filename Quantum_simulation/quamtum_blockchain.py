import hashlib
import json
from time import time
from typing import List, Any # For type hinting
from Quantum_simulation.quantum_block import Block
import networkx as nx
import threading

class Blockchain:
    def __init__(self, 
                 protocol_N: int,
                 protocol_p: float,
                 initial_target_cut_size: int = 4): # Difficulty = number of leading zeros for PoW
        
        self.chain: List[Block] = []
        self.pending_transactions: List[Any] = [] # Mempool simulation
        self.N: int = protocol_N # Number of nodes
        self.p: float = protocol_p 
        self.target_cut_size: int = initial_target_cut_size 

        self.lock = threading.Lock() # For thread safety
    
        # Create the genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        '''Crear primer bloque de la cadena'''
        genesis_block = Block(
            index=0,
            timestamp=time(),
            transactions=[],
            previous_hash="0" * 64, # Genesis block has no previous hash
            target_cut_size=self.target_cut_size,
            protocol_N=self.N,
            protocol_p=self.p
        )
        genesis_partition = [0] * self.N
        genesis_block.partition_solution = genesis_partition
        try:
            genesis_block.hash = genesis_block.calculate_final_hash()
            print(f"Primer bloque creado: {genesis_block.hash[:8]}...")
            self.chain.append(genesis_block)
        except ValueError as e:
            print(f"Error al crear el bloque génesis: {e}")
        except Exception as e:
            print(f"Error inesperado: {e}")


    @property
    def last_block(self) -> Block:
        return self.chain[-1]
    
    def get_current_difficulty(self) -> int:
        return self.target_cut_size



    def add_transaction(self, transaction: Any):
        # Basic validation could go here (e.g., signature check)
        # For now, just add to pending
        self.pending_transactions.append(transaction)

    '''
    def mine_pending_transactions(self, miner_reward_address: str) -> Block | None:
        if not self.pending_transactions:
            print("No transactions to mine.")
            return None # Or maybe mine an empty block? Bitcoin allows this.

        # In real Bitcoin, miners select transactions (often based on fees)
        # Here, we'll just take all pending ones for simplicity
        transactions_to_mine = self.pending_transactions[:] # Copy the list

        # Create the new block candidate
        new_block = Block(
            index=len(self.chain),
            timestamp=time(),
            transactions=transactions_to_mine,
            previous_hash=self.last_block.hash
        )

        # Perform Proof-of-Work
        new_block.nonce = self.proof_of_work(new_block)
        new_block.hash = new_block.calculate_hash() # Recalculate hash with the correct nonce

        # Add the mined block to the chain
        print(f"Block successfully mined: {new_block}")
        self.chain.append(new_block)

        # Clear pending transactions and add miner reward (simplified)
        self.pending_transactions = [
            # Transaction(sender="NETWORK", recipient=miner_reward_address, amount=MINING_REWARD)
            # For now, just clear
        ]
        self.pending_transactions = []

        return new_block


    def proof_of_work(self, block: Block) -> int:
        """
        Simple Proof-of-Work Algorithm:
        - Find a number 'nonce' such that hash(block_data + nonce) contains leading zeros.
        - Adjusting 'nonce' changes the resulting hash.
        """
        target = '0' * self.difficulty
        nonce = 0
        while True:
            block.nonce = nonce
            hash_result = block.calculate_hash()
            if hash_result.startswith(target):
                print(f"PoW Success! Nonce found: {nonce}, Hash: {hash_result}")
                return nonce
            nonce += 1
        # This loop will run until a valid nonce is found
        '''
    
    def add_block(self, block: Block)-> bool:
        '''Añadir un bloque después de la validación'''
        with self.lock:
            last_block =self.last_block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            hash_previous_block = previous_block.calculate_hash()
            hash_current_block = current_block.calculate_hash()
            # Check if the block's stored hash is correct
            #if current_block.hash != current_block.calculate_hash():
             #   print(f" - Block {i}: Invalid hash")
                #return False

            # Check if it points to the previous block correctly
            if current_block.previous_hash != hash_previous_block:
                print(f"- Block {i}: Invalid previous hash link")
                return False

            # Check if PoW was satisfied for the block (optional, but good practice)
            if not hash_current_block.startswith('0' * self.difficulty):
                 print(f"- Block {i}: Proof of Work requirement not met")
                 return False

        print("Chain is valid.")
        return True
    
    
            
    
