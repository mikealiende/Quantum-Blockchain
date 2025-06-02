import pennylane as qml
from pennylane import numpy as np
import networkx as nx 
import matplotlib.pyplot as plt
import random

# --- 1. DEFINIR EL GRAFO ---

prng = random.Random(7)

PROTOCOL_N = 6
PROTOCOL_P = 0.5

graph = nx.Graph()
graph.add_nodes_from(range(PROTOCOL_N))
for i in range(PROTOCOL_N):
    for j in range(i + 1, PROTOCOL_N):
        if prng.random() < PROTOCOL_P:
            graph.add_edge(i, j)

#  Dibujar grafo
pos = nx.spring_layout(graph, seed=7)
nx.draw(graph, pos, with_labels=True, node_color='lightblue', edge_color='gray')
plt.title("Grafo de Ejemplo para Max-Cut (PennyLane)")
plt.show()

# Hamiltoniano de Coste y mezcla
cost_h, mixer_h = qml.qaoa.maxcut(graph=graph)

print("Hamiltoniano de Coste (H_C):")
print(cost_h)

# --- Simulamos dispositivo cuantico ---
dev = qml.device('default.qubit', wires=PROTOCOL_N)

# --- Definir circuito QAOA 
n_layers = 2

def qaoa_layer(gamma, beta):
    qml.qaoa.cost_layer(gamma, cost_h)
    qml.qaoa.mixer_layer(beta,mixer_h)
    
def circuit(param, wires):
    gammas = param[0]
    betas = param[1]
    
    # Iniciar superposición
    for i in wires:
        qml.Hadamard(wires=i)
        
    # Aplicar capas de QAOA
    for i in range(n_layers):
        qaoa_layer(gammas[i], betas[i])
        
@qml.qnode(dev)
def cost_function(params):
    circuit(params, wires=range(PROTOCOL_N))
    return qml.expval(cost_h)

# Optimizador clásico

optimizer = qml.AdamOptimizer(stepsize=0.1)

np.random.seed(42)
init_params = np.random.uniform(0, np.pi, (2, n_layers), requires_grad=True)
params = init_params

# --- Bucle de optimizacion ---
steps = 100
print("\nIniciando optimizacion ...")
for i in range(steps):
    params = optimizer.step(cost_function, params)
    if(i+1)%10 ==0:
        cost_val = cost_function(params)
               
print("optimizacion finalizada")
optimal_params = params
print(f"\nParametros optimos: \nGammas:{optimal_params[0]}\nBetas: {optimal_params[1]}")

# --- Evaluar solucion ---
@qml.qnode(dev)
def probability_circuit(params):
    circuit(params,wires=range(PROTOCOL_N))
    return qml.probs(wires=range(PROTOCOL_N))

probs = probability_circuit(optimal_params)

# Encontrar circuito con los parámetros optimos
most_likely_state_index = np.argmax(probs)
solution_bitstring = format(most_likely_state_index, f'0{PROTOCOL_N}b')
solution_array = [int(bit) for bit in solution_bitstring]
print(f"\nEstado mas probable: {solution_bitstring} \nProbabilidad: {probs[most_likely_state_index]:.4f}")

print("\n Generado grafico distribucion de probabilidad")
num_states = 2**PROTOCOL_N
state_labels = [format(i, f'0{PROTOCOL_N}b') for i in range(num_states)]

plt.figure(figsize=(12, 6))
plt.bar(state_labels, probs.numpy()) 
plt.xlabel("Estado Computacional (Cadena de Bits / Partición)", fontsize=12)
plt.ylabel("Probabilidad", fontsize=12)
plt.title(f"Distribución de Probabilidad del Estado Final QAOA (N={PROTOCOL_N}, p={n_layers})", fontsize=14)
plt.xticks(rotation=90, fontsize=8)
plt.yticks(fontsize=10)
plt.ylim(bottom=0) # Asegurar que el eje Y empiece en 0
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

# Calcular corte para la solucion encontrada
def calculate_cut_size(graph, partition_array):
    cut_size = 0
    for i, j in graph.edges():
        if partition_array[i] != partition_array[j]: # si los nodos estan en particiones diferentes
            cut_size += 1
    return cut_size

found_cut_size = calculate_cut_size(graph, solution_array)
print(f"Tamano del corte encontrado: {found_cut_size}")
        
# dibujar grafo con particiones
colors = ['r' if solution_array[i] == 0 else 'b' for i in range(PROTOCOL_N)]
nx. draw(graph, pos, with_labels = True, node_color = colors, edge_color = 'gray')
plt.title(f"Particiones del Max-Cut. Cortes: {found_cut_size}")
plt.show()

