from blockchain import Blockchain
from block import Block
from transactions import Transaction
from typing import List, Any, Set # For type hinting
import time
from node import Node
import random

# --- CONFIGURACION ---
NUM_NODES = 4
INITIAL_DIFFICULTY = 4
SIMULATION_DURATION_SECONDS = 90
TRANSACTIONS_INTERVAL_MEAN = 5
MINING_INTERVAL_MEAN = 15

#--- INICIALIZACION ---
print("INICIANDO SIMULACION")
nodes :List[Node] = []

#Crear nodos
for i in range (NUM_NODES):
    node_id = f"Nodo-{i}"
    node = Node(node_id=node_id, difficulty=INITIAL_DIFFICULTY)
    nodes.append(node)
print(f"\n{len(nodes)} nodos creados.")

#2 conectar los nodos
print(f"Estableciendo conexiones entre peers...")
if NUM_NODES > 1:
    for i in range(NUM_NODES):
        for j in range (i+1, NUM_NODES):
            #Conectar nodo i con j y viceversa
            nodes[i].add_peer(nodes[j])
            nodes[j].add_peer(nodes[i])

# --- BUCLE PRINCIPAL SIMULACION ---
start_time = time.time()
last_tx_time = start_time
last_mine_time = start_time

try:
    while time.time() - start_time < SIMULATION_DURATION_SECONDS:
        current_time = time.time()
        acction_ocurred = False

        #Simulamos creacion y transmision de transaciones
        if current_time - last_tx_time > random.expovariate(1.0/TRANSACTIONS_INTERVAL_MEAN):
            if len(nodes) >1:
                sender_node = random.choice(nodes)
                possible_recievers = [n for n in nodes if n.node_id != sender_node.node_id]
                if possible_recievers:
                    recipient_node = random.choice(possible_recievers)
                    amount = round(random.uniform(0.1,5.0),2)

                    print(f"\n--- Evento: {sender_node.node_id} crea Tx para {recipient_node.node_id} ---")
                    sender_node.create_transaction(recipient_address=recipient_node.get_address(), amount=amount)
                    last_tx_time = current_time
                    acction_ocurred = True
                    time.sleep(1)

        #Simular mineria
        if current_time - last_mine_time > random.expovariate(1.0/ MINING_INTERVAL_MEAN):
            miner_node = random.choice(nodes)
            print(f"\n --- Evento: {miner_node.node_id} intenta minar ---")
            mined_block = miner_node.mine_block()
            

except KeyboardInterrupt:
    print(f"Simulacion interrumpida")