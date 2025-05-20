import hashlib
import json
from time import time
from typing import List, Any, Set 
from quantum_block import Quantum_Block
from quantum_transactions import Transaction
import networkx as nx
import threading
import copy

class Quantum_Blockchain:
    def __init__(self, 
                 protocol_N: int,
                 protocol_p: float,
                 initial_difficulty_ratio: float = 0.55): # Dificultad inicial
        
        self.chain: List[Quantum_Block] = []
        self.pending_transactions: Set[Transaction] = set()
        self.N: int = protocol_N # Numero de nodos
        self.p: float = protocol_p 
        self.initial_difficulty_ratio: float = initial_difficulty_ratio 

        self.lock = threading.Lock() 
    
        # Crear primer bloque
        self.create_genesis_block()

    def create_genesis_block(self):
        '''Crear primer bloque de la cadena'''
        genesis_block = Quantum_Block(
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
    def last_block(self) -> Quantum_Block:
        return self.chain[-1]
    
    def get_current_difficulty(self) -> int:
        return self.initial_difficulty_ratio



    def add_transaction(self, transaction: Any):
        # Validad la transacción TO DO
        self.pending_transactions.append(transaction)

    
    
    def add_block(self, block: Quantum_Block)-> bool:
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
            
            #print(f"Bloque {block.index} con hash: {block.hash[:8]}... añadido a la cadena")
            self.chain.append(block)

            # Limpiar mempool
            try:
                hashes_in_block = {tx_in_block.calculate_hash() for tx_in_block in block.transactions}
                new_pending_transactions = []
                for pending_tx in self.pending_transactions:                    
                    if pending_tx.calculate_hash() not in hashes_in_block:
                        new_pending_transactions.append(pending_tx)
                self.pending_transactions = new_pending_transactions
            except AttributeError as ae:
                print(f"Error al limpiar el mempool (AttributeError): {ae}. "
                      f"Asegúrate de que todas las transacciones sean objetos Transaction con calculate_hash().")
                
                return False
            except Exception as e:
                print(f"Error inesperado al limpiar el mempool: {e}")
                return False
            
            
            return True

    def is_chain_valid(self) -> bool:

        # TODO: Validar la cadena de bloques
        with self.lock:
            if not self.chain: return False
            
    #Metodo especial para deepcopy porque al tener locks no funciona bien
    def __deepcopy__(self,memo): 
        cls = self.__class__
        new_blockchain = cls.__new__(cls) # Crear instancia sin llamar a __init__
        memo[id(self)] = new_blockchain

        # Copiar atributos simples
        new_blockchain.N = self.N
        new_blockchain.p = self.p
        new_blockchain.initial_difficulty_ratio = self.initial_difficulty_ratio

        # Copiar la cadena de bloques PROFUNDAMENTE
        new_blockchain.chain = copy.deepcopy(self.chain, memo)

        # Crear un NUEVO lock
        new_blockchain.lock = threading.Lock()

        # --- MANEJO DE PENDING_TRANSACTIONS ---
        new_blockchain.pending_transactions = set() # Inicializar como set vacío
        if hasattr(self, 'pending_transactions') and self.pending_transactions is not None:
            for tx_data in self.pending_transactions: # Iterar sobre lo que sea que haya en la plantilla
                if isinstance(tx_data, Transaction):
                    # Si ya es un objeto Transaction, hacer deepcopy (Transaction debería ser deepcopyable)
                    new_blockchain.pending_transactions.add(copy.deepcopy(tx_data, memo))
                elif isinstance(tx_data, dict):
                    # Si es un diccionario, convertirlo a un objeto Transaction
                    print(f"Deepcopy Blockchain: Convirtiendo dict de pending_tx a objeto Transaction.")
                    try:
                        # Asume que el dict tiene las claves necesarias.
                        # Podrías necesitar más validaciones aquí.
                        new_tx_obj = Transaction(
                            sender_address=tx_data.get('sender'),
                            recipient_address=tx_data.get('recipient'),
                            amount=tx_data.get('amount'),
                            inputs=copy.deepcopy(tx_data.get('inputs', []), memo) # Deepcopy de inputs también
                        )
                        # Restaurar otros atributos si existen en el dict
                        new_tx_obj.timestamp = tx_data.get('timestamp', time.time())
                        new_tx_obj.signature = tx_data.get('signature')
                        # Validar y añadir (opcional, pero bueno para consistencia)
                        # if new_tx_obj.is_valid(): # OJO: is_valid necesita la clave pública correcta
                        new_blockchain.pending_transactions.add(new_tx_obj)
                        # else:
                        #    print(f"Deepcopy: Tx convertida de dict no es válida, no se añade: {new_tx_obj}")
                    except Exception as e:
                        print(f"Deepcopy Blockchain: Error convirtiendo dict de pending_tx: {e}. Data: {tx_data}")
                else:
                    print(f"Deepcopy Blockchain: Tipo inesperado en pending_transactions de plantilla: {type(tx_data)}")
        # --- FIN MANEJO DE PENDING_TRANSACTIONS ---

        return new_blockchain
        

        
