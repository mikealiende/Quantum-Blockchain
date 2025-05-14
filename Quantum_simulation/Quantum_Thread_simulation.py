from quantum_blockchain import Blockchain
from quantum_block import Block
from transactions import Transaction
from typing import List, Any, Set # For type hinting
import time
from quantum_node import Node
import copy
import threading


# --- CONFIGURACION ---
NUM_NODES = 2
INITIAL_DIFFICULTY_RATIO = 0.6
PROTOCOL_N = 14
PROTOCOL_P = 0.5
SIMULATION_TIME = 30  # seconds

# --Inicializacion
print("Iniciando la simulacion...")
nodes : List[Node] = [] 
threads = []
stop_event = threading.Event() # Evento para detener los hilos

# --Crear instancia de Bockchain
initial_blockchain_template = Blockchain(protocol_N=PROTOCOL_N,
                                         protocol_p=PROTOCOL_P, 
                                         initial_difficulty_ratio=INITIAL_DIFFICULTY_RATIO)

# 1. Crear nodos sin inicializar

initial_block_hash = initial_blockchain_template.last_block.calculate_final_hash()
print(f"GENERAL: Initial block hash: {initial_block_hash[:8]}")
for i in range(NUM_NODES):
    node_id = f"Node-{i}"
    node_block_chain_copy = copy.deepcopy(initial_blockchain_template)
    node = Node(node_id=node_id,
                blockchain_instance=node_block_chain_copy, 
                node_list= nodes,
                stop_event=stop_event)
    nodes.append(node)

# 2. Conectar los nodos entre si
print("Conectando nodos...")
if NUM_NODES > 1:
    for i in range(NUM_NODES):
        for j in range(i +1, NUM_NODES):
            nodes[i].add_peer(nodes[j])
            nodes[j].add_peer(nodes[i])
else:
    print("Solo hay un nodo")

# 3. Inicilizar los hilos de los nodos
for node in nodes:
    node.start()
    threads.append(node)

print(f"Simulacion iniciada con {NUM_NODES} nodos por {SIMULATION_TIME} segundos.")
start_time = time.time()

try:
    time.sleep(SIMULATION_TIME)
except KeyboardInterrupt:
    print("Simulacion detenida por el usuario.")

finally:
    print("Deteniendo la simulacion...")
    stop_event.set() # Señal para detener los hilos
    for thread in threads:
        thread.join(timeout=5) # Espera a que los hilos terminen
        if thread.is_alive():
            print(f"{thread.node_id} no ha terminado correctamente.")
    print("\nFin de la simulacion.")
    print(f"Duración {time.time() - start_time:-2f} segundos.")

    print("\nEstado final de los nodos:")
    final_hashes = {}
    max_len = 0
    for node in nodes:
        chain_len = len(node.blockchain.chain)
        lastblock :Block = node.blockchain.last_block
        last_hash = lastblock.calculate_final_hash() if chain_len > 0 else "N/A"
        print(f"Nodo {node.node_id}: Bloques={chain_len}, hash={last_hash[:8]}..., mempool= {len(node.mempool)}")

        max_len = max(max_len, chain_len)
        if last_hash not in final_hashes:
            final_hashes[last_hash] = []
        final_hashes[last_hash].append(node.node_id)
    
    print(f"Cadena mas laga: {max_len} bloques")
    print("Hashes finales:")
    for hash_val, node_ids in final_hashes.items():
        print(f" - Hash {hash_val[:8]}...: {len(node_ids)} nodos ({','. join(node_ids)})")
    if len(final_hashes) == 1:
        print("CONSENSO")
    else:
        print("INCONSISTENCIA")

    '''for node in nodes:
        print(f"\nCadena de bloques de {node.node_id}:")
        for block in node.blockchain.chain:
            print(f" - Bloque {block.index}: {block.calculate_hash()[:8]}... Tx: {len(block.transactions)}, Prevous: {block.previous_hash[:8]}..., Minado por {block.mined_by}")'''

    node_to_print = nodes[0]
    node_to_print.visualize_chain()


    # Validar la cadena de bloques
    all_valid = True
    for node in nodes:
        print(f"Validando cadena de {node.node_id}...")
        is_valid = node.blockchain.is_chain_valid()
        print(f" - Cadena {node.node_id}: {'Válida' if is_valid else 'No valida'}")
        if not is_valid:
            all_valid = False
        if not all_valid:
            print("Cadena no valida")
        
            

