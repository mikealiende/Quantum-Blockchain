import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

from qiskit_optimization.applications import Maxcut

# ---1. Definir grafo---
num_nodes = 4
np.random.seed(123) #para reproducibilidad del grafo
adj_matrix = np.random.randint(0, 2, size=(num_nodes, num_nodes))
adj_matrix = np.triu(adj_matrix, 1) # Hacer la matriz triangular superior
graph = nx.from_numpy_array(adj_matrix)

#Dibujar el grafo
pos = nx.spring_layout(graph, seed=7)
nx.draw(graph, pos, with_labels=True, node_color='lightblue', edge_color='gray')
plt.title("Grafo de entrada")
plt.show()

# ---2. Definir el problema de Max-Cut---
maxcut = Maxcut(graph)
qp = maxcut.to_quadratic_program()
print(f"Cuadratic Program: {qp.prettyprint()}")
