import pennylane as qml
from pennylane import numpy as np
import networkx as nx 
import matplotlib.pyplot as plt

# --- 1. DEFINIR EL GRAFO ---

num_nodes = 7
np.random.seed(23)
adj_matrix = np.random.randint(0,2, size=(num_nodes, num_nodes))
adj_matrix = np.triu(adj_matrix, 1)
graph = nx.from_numpy_array(adj_matrix)

#  Dibujar grafo
pos = nx.spring_layout(graph, seed=7)
nx.draw(graph, pos, with_labels=True, node_color='lightblue', edge_color='gray')
plt.title("Grafo de Ejemplo para Max-Cut (PennyLane)")
plt.show()

# Hamiltoniano de Costo (H_C): Suma de Z_i Z_j sobre las aristas (i,j)
cost_h, mixer_h = qml.qaoa.maxcut(graph=graph)

#print("Hamiltoniano de Costo H_C:")
#print(cost_h)

# --- Simulamos dispositivo cuantico ---
dev = qml.device('default.qubit', wires=num_nodes)

# --- Definir circuito QAOA 
n_layers = 2

def qaoa_layer(gamma, beta):
    qml.qaoa.cost_layer(gamma, cost_h)
    qml.qaoa.mixer_layer(beta,mixer_h)
    
def circuit(param, wires):
    gammas = param[0]
    betas = param[1]
    
    #Iniciar superposición
    for i in wires:
        qml.Hadamard(wires=i)
        
    #Aplicar capas de QAOA
    for i in range(n_layers):
        qaoa_layer(gammas[i], betas[i])
        
@qml.qnode(dev)
def cost_function(params):
    circuit(params, wires=range(num_nodes))
    return qml.expval(cost_h)

# Optimizador clásico

optimizer = qml.AdamOptimizer(stepsize=0.1)

np.random.seed(42)
init_params = np.random.uniform(0, np.pi, (2, n_layers), requires_grad=True)
params = init_params

# --- Bucle de optimizacion ---
steps = 100
print("\nIniciando optimizacion")
for i in range(steps):
    params = optimizer.step(cost_function, params)
    if(i+1)%10 ==0:
        cost_val = cost_function(params)
        print(f"Paso {i+1:3d} - Costo (Energia Esperada HC:) {cost_val:.4f}")
        
print("optimizacion finalizada")
optimal_params = params
print(f"\nParametros optimos: \nGammas:{optimal_params[0]}\nBetas: {optimal_params[1]}")

# --- Evaluar solucion ---
@qml.qnode(dev)
def probability_circuit(params):
    circuit(params,wires=range(num_nodes))
    return qml.probs(wires=range(num_nodes))

probs = probability_circuit(optimal_params)

#Encontrar circuito con los parámetros optimos
most_likely_state_index = np.argmax(probs)
solution_bitstring = format(most_likely_state_index, f'0{num_nodes}b')
solution_array = [int(bit) for bit in solution_bitstring]
print(f"\nEstado mas probable: {solution_bitstring} \nProbabilidad: {probs[most_likely_state_index]:.4f}")

print("\n Generado grafico distribucion de probabilidad")
num_states = 2**num_nodes
state_labels = [format(i, f'0{num_nodes}b') for i in range(num_states)]

plt.figure(figsize=(12, 6)) # Ajusta el tamaño si es necesario
plt.bar(state_labels, probs.numpy()) # Usamos .numpy() para obtener el array numpy si es necesario
plt.xlabel("Estado Computacional (Cadena de Bits / Partición)", fontsize=12)
plt.ylabel("Probabilidad", fontsize=12)
plt.title(f"Distribución de Probabilidad del Estado Final QAOA (N={num_nodes}, p={n_layers})", fontsize=14)
plt.xticks(rotation=90, fontsize=8) # Rotar etiquetas si hay muchas
plt.yticks(fontsize=10)
plt.ylim(bottom=0) # Asegurar que el eje Y empiece en 0
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout() # Ajusta el layout para evitar solapamientos
plt.show()

# Calcular corte para la solucion encontrada
def calculate_cut_size(graph, partition_array):
    cut_size = 0
    for i, j in graph.edges():
        if partition_array[i] != partition_array[j]: #si los nodos estan en particiones diferentes
            cut_size += 1
    return cut_size

found_cut_size = calculate_cut_size(graph, solution_array)
print(f"Tamano del corte encontrado: {found_cut_size}")
        
    
# dibujar grafo con particiones
colors = ['r' if solution_array[i] == 0 else 'b' for i in range(num_nodes)]
nx. draw(graph, pos, with_labels = True, node_color = colors, edge_color = 'gray')
plt.title(f"Particiones del Max-Cut. Cortes: {found_cut_size}")
plt.show()


