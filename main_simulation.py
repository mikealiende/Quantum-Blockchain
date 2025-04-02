from blockchain import Blockchain
from block import Block
from transactions import Transaction
from typing import List, Any, Set # For type hinting
from time import time
from node import Node

# --- CONFIGURACION ---
NUM_NODES = 4
INITIAL_DIFFICULTY = 4
SIMULATION_DURATION_SECONDS = 60
TRANSACTIONS_INTERVAL = 5
MINING_INTERVAL_MEAN = 15

#--- INICIALIZACION ---
print("INICIANDO SIMULACION")
network_nodes = []

#Crear nodos
for i in range (NUM_NODES):
    node_id = f"Nodo-{i}"
    if i == 0:
        node = Node(node_id=node_id, network_nodes)
