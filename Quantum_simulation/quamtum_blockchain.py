import hashlib
import json
from time import time
from typing import List, Any 
from Quantum_simulation.quantum_block import Block
import networkx as nx
import threading

class Blockchain:
    def __init__(self, 
                 protocol_N: int,
                 protocol_p: float,
                 initial_target_cut_size: int = 4): # Dificultad inicial
        
        self.chain: List[Block] = []
        self.pending_transactions: List[Any] = [] # Mempool
        self.N: int = protocol_N # Numero de nodos
        self.p: float = protocol_p 
        self.target_cut_size: int = initial_target_cut_size 

        self.lock = threading.Lock() 
    
        # Crear primer bloque
        self.create_genesis_block()

    def create_genesis_block(self):
        '''Crear primer bloque de la cadena'''
        genesis_block = Block(
            index=0,
            timestamp=time(),
            transactions=[],
            previous_hash="0" * 64, # Primer bloque no tiene hash previo
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
        # Validad la transacción TO DO
        self.pending_transactions.append(transaction)

    
    
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
            
            if current_block.previous_hash != hash_previous_block:
                print(f"- Block {i}: Previous hash no concuerda")
                return False

            
            if not hash_current_block.startswith('0' * self.difficulty):
                 print(f"- Block {i}: Requisitos de la Proof of Work no cumplen")
                 return False

        print("Cadena valida.")
        return True
    
    
            
    
