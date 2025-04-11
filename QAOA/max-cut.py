import pennylane as qml
from pennylane import numpy as np
import networkx as nx 
import matplotlib.pyplot as plt

# --- 1. DEFINIR EL GRAFO ---

num_nodes = 6
np.random.seed(123)
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

print("Hamiltoniano de Costo H_C:")
print(cost_h)

# --- Simulamos dispositivo cuantico ---
dev = qml.device('defuault.qubit', wires=num_nodes)

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


        
    



