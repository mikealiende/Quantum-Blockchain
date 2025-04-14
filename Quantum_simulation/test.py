from transactions import Wallet
from quantum_block import Block
from time import time
import networkx as nx
import matplotlib.pyplot as plt

PROTOCOL_N = 8
PROTOCOL_P = 0.5
INITIAL_DIFFICULTY = 4

block = Block(index=1,
            timestamp=time(),
            transactions=[{"from": "A", "to": "B", "amount": 15}],
            previous_hash="0"*64,
            mined_by="Miner1",
            protocol_N=PROTOCOL_N,
            protocol_p=PROTOCOL_P,  
            target_cut_size=INITIAL_DIFFICULTY)

print(block)

#generar el bloque
graph_challenge = block.generate_graph()
print(f"\nGrafo Desafío: {graph_challenge.number_of_nodes()} nodos, {graph_challenge.number_of_edges()} aristas.")

pos = nx.spring_layout(graph_challenge, seed=7)
nx.draw(graph_challenge, pos, with_labels=True, node_color='lightblue', edge_color='gray')
plt.title("Grafo de Ejemplo para Max-Cut (PennyLane)")
plt.show()