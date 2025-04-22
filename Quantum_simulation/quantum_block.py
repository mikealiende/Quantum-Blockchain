import hashlib
import json
from time import time
from typing import List, Any, Dict, Tuple, Optional

import numpy as np
from transactions import Transaction
import random
import networkx as nx


class Block:
    def __init__(self, 
                 index: int, 
                 timestamp: float, 
                 transactions: List[Transaction], 
                 previous_hash: str, 
                 mined_by : str, 
                 protocol_N: int, #Numero de nodos del grafo
                 protocol_p: float, #Probabilidad de arista
                 difficulty_ratio: float = 0.5
                 ):
        
        
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions # List of Transaction objects or dictionaries
        self.previous_hash = previous_hash
        self.mined_by = mined_by

        # Parametros Max-Cut
        self.graph_N = protocol_N
        self.graph_p = protocol_p
        self.difficulty_ratio = difficulty_ratio
        self.partition_solution = None # 
        self.transaction_hash: str = self._calculate_transaction_hash()
        self.hash  : Optional[str] = None

    def _calculate_transaction_hash(self) -> str:
        """Calcula un hash determinista del contenido de las transacciones."""
        # Usamos una representación JSON ordenada para consistencia
        try:
            # Convertimos cada tx a un dict si es necesario/posible para JSON
            tx_repr = [tx if isinstance(tx, dict) else vars(tx) if hasattr(tx, '__dict__') else str(tx)
                       for tx in self.transactions]
            block_string = json.dumps(tx_repr, sort_keys=True).encode()
            return hashlib.sha256(block_string).hexdigest()
        except Exception as e:
             print(f"Warning: No se pudo serializar transacciones a JSON, usando str(): {e}")
             # Fallback a usar str() si lo anterior falla
             tx_strings = sorted([str(tx) for tx in self.transactions])
             tx_concat = "".join(tx_strings)
             return hashlib.sha256(tx_concat.encode()).hexdigest()

    def get_header_data_for_hash(self) -> Dict[str, Any]:
        '''Prepara los datos de cabecera que usaran para calcular el hash final'''

        if self.partition_solution is None:
            raise ValueError("Partition solution not set. Cannot calculate hash.")
        
        header_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions_hash": self.transactions.calculate_hash(),
            "previous_hash": self.previous_hash,
            "mined_by": self.mined_by,
            "difficulty_ratio": self.difficulty_ratio,
            "graph_N": self.graph_N,
            "graph_p": self.graph_p,
            "partition_solution": self.partition_solution,
        }
        return header_data
    
    def calculate_final_hash(self) -> str:
        '''Calcula el hash final del bloque, incluyendo la solucion de particion'''
        header_data = self.get_header_data_for_hash()
        block_string = json.dumps(header_data, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def generate_graph(self):
        '''
        Genera el grafo a partir de los datos del bloque de forma determinista
        Previous hash y transition hash como seed
        '''
        seed_material = f"{self.previous_hash}-{self.transaction_hash}".encode('utf-8')
        seed = hashlib.sha256(seed_material).digest()
        prng = random.Random(seed)

        G = nx.Graph()
        if self.graph_N <= 0: return G
        G.add_nodes_from(range(self.graph_N))

        for i in range(self.graph_N):
            for j in range(i + 1, self.graph_N):
                if prng.random() < self.graph_p:
                    G.add_edge(i, j)
        return G
    
    def calculate_target(self) -> int:
        graph = self.generate_graph()
        target = np.floor(self.difficulty_ratio * graph.number_of_edges())
        return target
        
    
    @staticmethod
    def _calculate_cut_size(graph: nx.Graph, partition: List[int]) -> int:
        '''Calcula el tamaño del corte dado un grafo y una particion'''
        n_nodes = graph.number_of_nodes()
        if n_nodes == 0: return 0
        if len(partition) != n_nodes:
            raise ValueError(f"Tamano de particion {len(partition)} no coincide con el numero de nodos {n_nodes}")
        cut_size = 0

        for u, v in graph.edges():
            if u >= n_nodes or v >= n_nodes:continue
            if partition[u] != partition[v]:
                cut_size += 1
        return cut_size
    
    def validate_PoW(self, graph: nx.Graph) ->Tuple[bool,int]:
        '''
        Valida si la partition_solution del bloque es correcta
        '''
        print("Ha llegado aqui")
        if self. partition_solution is None:
            print("No hay solucion de particion para validar")
            return False, -1
        if len(self.partition_solution) != self.graph_N:
            print("Tamano de particion no coincide con el grafo")
            return False, -1
        
        try:
            current_graph = graph if graph is not None else self.generate_graph()
            if current_graph.number_of_nodes() != self.graph_N:
                print(f"Error bloque {self.index}: El grafo generado no tiene el mismo numero de nodos que el bloque")
                return False, -1
            
            #Calcuar target en funcion de las aristas del grafo generado y de difficulty_ratio
            target_cut = self.calculate_target()
            
            calculated_cut = Block._calculate_cut_size(current_graph, self.partition_solution)
            is_valid = calculated_cut >= target_cut
            return is_valid, calculated_cut
        except ValueError as e:
            print(f"Error en la validacion de PoW: {e}")
            return False, -1
        except Exception as e:
            print(f"Error inesperado en la validacion de PoW: {e}")
            return False, -1


    def __str__(self):
        # Imprimir por pantalla
        status = "MINADO" if self.hash else "PENDIENTE"
        sol_prewiew = "N/A"
        if self.partition_solution:
            sol_str = "".join(map(str, self.partition_solution))
            sol_prewiew = sol_str[:8] + "..." + sol_str[-8:] if len(sol_str) > 16 else sol_str

        return (f"Block #{self.index} [{status}] "
                f"Difficult Ratio: >= {self.difficulty_ratio} "
                f"| Solution Cut: {'?' if status=='PENDIENTE' else self.validate_proof_of_work()[1]} "
                f"| PrevHash: {self.previous_hash[:8]}..."
                f"| Hash: {self.hash[:8] if self.hash else 'N/A'}...")