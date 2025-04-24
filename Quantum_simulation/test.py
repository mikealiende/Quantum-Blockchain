from transactions import Wallet
from quantum_block import Block
from time import time
import networkx as nx
import matplotlib.pyplot as plt

from QAOA_max_cut import solve_max_cut_qaoa, _calculate_cut_size


PROTOCOL_N = 12
PROTOCOL_P = 0.6
DIFFICULTY_RATIO = 0.55

def draw_partions(graph,solution_array,num_nodes,found_cut_size ):
    '''Dibujar la particion para hacer pruebas'''
    pos = nx.spring_layout(graph, seed=7)
    colors = ['r' if solution_array[i] == 0 else 'b' for i in range(num_nodes)]
    nx. draw(graph, pos, with_labels = True, node_color = colors, edge_color = 'gray')
    plt.title(f"Particiones del Max-Cut. Cortes: {found_cut_size}")
    plt.show()

block = Block(index=1,
            timestamp=time(),
            transactions=[{"de": "A", "para": "B", "cantidad": 15},{"de": "C", "para": "B", "cantidad": 5} ],
            previous_hash="0"*64,
            mined_by="Miner1",
            protocol_N=PROTOCOL_N,
            protocol_p=PROTOCOL_P,  
            difficulty_ratio=DIFFICULTY_RATIO)

print(block)

#generar el bloque
graph_challenge = block.generate_graph()
print(f"\nGrafo Desafío: {graph_challenge.number_of_nodes()} nodos, {graph_challenge.number_of_edges()} aristas.")
target_cut = block.calculate_target()
print(f"Target cut: {target_cut}")
number_of_edges = graph_challenge.number_of_edges()
target_cut_decimal = number_of_edges * DIFFICULTY_RATIO
print(f"Target cut decimal: {target_cut_decimal}")



#pos = nx.spring_layout(graph_challenge, seed=7)
#nx.draw(graph_challenge, pos, with_labels=True, node_color='lightblue', edge_color='gray')
#plt.title("Grafo de Ejemplo para Max-Cut (PennyLane)")
#plt.show()


partition = solve_max_cut_qaoa(graph=graph_challenge, target_cut=target_cut, node_id="Node 1")

#Esto lo haria el nodo
block.partition_solution = partition
block.hash = block.calculate_final_hash()
# Fin de lo que hace el nodo

Validation_result = block.validate_PoW(graph_challenge)
print(f"Validación del bloque: {Validation_result}")
print(block)
draw_partions(graph_challenge, partition, PROTOCOL_N, Validation_result[1])



