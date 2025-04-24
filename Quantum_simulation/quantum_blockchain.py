import hashlib
import json
from time import time
from typing import List, Any 
from quantum_block import Block
import networkx as nx
import threading

class Blockchain:
    def __init__(self, 
                 protocol_N: int,
                 protocol_p: float,
                 initial_difficulty_ratio: float = 0.55): # Dificultad inicial
        
        self.chain: List[Block] = []
        self.pending_transactions: List[Any] = [] # Mempool
        self.N: int = protocol_N # Numero de nodos
        self.p: float = protocol_p 
        self.initial_difficulty_ratio: float = initial_difficulty_ratio 

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
            mined_by="None",
            difficulty_ratio=self.initial_difficulty_ratio,
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
        return self.initial_difficulty_ratio



    def add_transaction(self, transaction: Any):
        # Validad la transacción TO DO
        self.pending_transactions.append(transaction)

    
    
    def add_block(self, block: Block)-> bool:
        '''Añadir un bloque después de la validación'''
        with self.lock:
            last_block =self.last_block
            if not last_block:
                print("No hay bloques en la cadena")
                return False
            
            '''--- Validacion básica ---'''

            # 1. Validar index  
            if block.index != last_block.index + 1:
                print(f"Error: Index del bloque {block.index} no es correcto")
                return False
            
            # 2. Validar hash previo
            if block.previous_hash != last_block.calculate_final_hash():
                print(f"Error: Hash previo del bloque {block.index} no es correcto")
                return False
            
            # 3. Validar integridad. El hash del bloque debe coincidir con el hash calculado
            try:
                expexted_hash = block.calculate_final_hash()
                if block.hash != expexted_hash:
                    print(f"Error: Hash del bloque {block.index} no es correcto")
                    return False
            except ValueError:
                print(f"Error al calcular el hash del bloque {block.index}")
                return False
            
            print(f"Bloque {block.index} con hash: {block.hash[:8]}... añadido a la cadena")
            self.chain.append(block)

            # Limpiar mempool
            try:
                block_tx_ids = {tx.get("id", str(tx)) for tx in block.transactions}
                self.pending_transactions = [tx for tx in self.pending_transactions if tx.get("id", str(tx)) not in block_tx_ids]

            except Exception as e:
                print(f"Error al limpiar el mempool: {e}")
                return False
            
            return True

    def is_chain_valid(self) -> bool:

        # TODO: Validar la cadena de bloques
        with self.lock:
            if not self.chain: return False

        
