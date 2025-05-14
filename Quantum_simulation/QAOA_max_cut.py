import pennylane as qml
from pennylane import numpy as np
import networkx as nx 
import time
import threading
from typing import Optional, List, Tuple

def _calculate_cut_size(graph: nx.Graph, partition: List[int]) -> int:
    '''Calcula el numero de cortes de una particion dada'''
    n_nodes = graph.number_of_nodes()
    if n_nodes == 0: return 0
    
    if len(partition) != n_nodes:
        print(f"Error! Tamano de particion y de numero de nodos no coincide")
        return -1
    
    
    cut_size = 0
    
    for u, v in graph.edges():
        # Asegurar que los indices estén dentro de los limites de la particion
        if u >= n_nodes or v >= n_nodes or u < 0 or v < 0:
            print(f"Error! Arista ({u}, {v}) fuera de los limites. Numero de nodos {n_nodes}")
            continue
        try: 
            if partition[u] != partition[v]:
                cut_size +=1
        except IndexError:
            print(f"Indice fuera del rango de particion")
            return -1
        
    return cut_size

def solve_max_cut_qaoa(
    graph: nx.Graph,
    target_cut: int,
    stop_event: threading.Event,
    node_id: str = "QAOA_solver", # Para logs
    n_layer: int = 2, # Capas QAOA
    optim_steps: int = 20, # Pasos optimizador clásico
    check_interval: int = 10 # Cada cuando verifica si alcanzó el target_cut
    ) -> Optional[List[int]]:
    
    '''
    Intenta resolver max-cut para un grafo dado usando QAOA
    
    Devuelve una lista representando la partición [0,1,0,...]
    '''
    
    num_nodes = graph.number_of_nodes()
    start_time = time.time()
    
    if num_nodes == 0:
        print(f"Nodo {node_id}: Grafo vacio")
        return None
    
    print(f"Nodo {node_id}: Iniciando QAOA (N={num_nodes}, Target: {target_cut}, Capas: {n_layer}, Pasos: {optim_steps})")
    
    # --- 1. Definir Hamiltoniano desde el grafo ---
    
    try:
        cost_h, mixer_h = qml.qaoa.maxcut(graph=graph)
    except Exception as e:
        print(f"Nodo {node_id}: Error al generar Hamiltoniano - {e}")
        return None
    
    #  --- 2. Configurar dispositivo simulación ---
    try: 
        dev = qml.device('default.qubit', wires=num_nodes)
    except qml.DeviceError as e:
        print(f"Nodo {node_id}: Error al crear simulador Pennylane - {e}")
        return None
    
    # --- 3. Definir circuito QAOA en la función
    
    def qaoa_layer(gamma, beta):
        qml.qaoa.cost_layer(gamma, cost_h)
        qml.qaoa.mixer_layer(beta, mixer_h)
        
    def circuit(params, wires):
        gammas = params[0]
        betas = params[1]
        
        for i in wires: # Ponemos todos los qubits en superposición
            qml.Hadamard(wires=i)
            
        for i in range(n_layer): # Aplicar capas
            qaoa_layer(gammas[i],betas[i])
            
    @qml.qnode(dev)
    def cost_function(params):
        circuit(params, wires = range(num_nodes))
        return qml.expval(cost_h)
    
    @qml.qnode(dev)
    def probability_circuit(params):
        circuit(params, wires=range(num_nodes))
        return qml.probs(wires=range(num_nodes))
    
    # --- 4. Configurar optimizador
    optimizer = qml.AdamOptimizer(stepsize=0.1)
    
    #np.random.seed(int(time.time()) + hash(node_id)) # Inicilizar parametros aleatoriamente
    params = np.random.uniform(0, 2 * np.pi, (2, n_layer), requires_grad = True)
    
    
    # -- Bucle que optimizacion
    best_found_partition = None
    best_found_cut = -1
    
    print(f"Nodo {node_id}: Iniciando optimización...")
    for i in range (optim_steps):
        if stop_event.is_set(): # Comprobamos si tenemos que deternos antes de empezar la optimizacion
            print(f"Nodo {node_id}: Optimizacion detenida")
            return None
            
        try:
            params = optimizer.step(cost_function, params)
        except Exception as e:
            print(f"Nodo {node_id}: Error en optimizacion")
            return None
       
        # Verficiar solucion cada check_interval
        if (i + 1) % check_interval == 0 or  i == optim_steps -1:
            
            if stop_event.is_set(): # 
                print(f"[{node_id}] Solver: Detenido (stop_event) durante verificacion de solucion.")
                return None
            
            try:
                current_probs = probability_circuit(params).numpy() # Obtener probabilidades
                max_probs = np.argmax(current_probs)
                current_partition_str = format(max_probs, f'0{num_nodes}b')
                current_partition = [int(bit) for bit in current_partition_str]
                
                current_cut = _calculate_cut_size(graph, current_partition)
               
                if current_cut == -1:
                    print(f"Nodo {node_id}: Error calculando corte de particion")
                    continue
                
                # Actualizar mejor corte
                if current_cut > best_found_cut:
                    best_found_cut = current_cut
                    best_found_partition = current_partition
                    
                #print(f"Iteracion {i+1}. Mejor corte hasta ahora: {best_found_cut}")
                
                if current_cut >= target_cut:
                    duration = time.time() - start_time
                    print(f"Nodo {node_id}: Solucion encontrada. Corte: {current_cut}. Tiempo: {duration:.2f}s")
                    return current_partition
                    
            
            except qml.QuantumFunctionError as e:
                print(f"Nodo {node_id}: Error QuantumFunctionError - {e}")
            except Exception as e:
                 print(f"Nodo {node_id}: Error inesperado - {e}")
                 
            time.sleep(0.1) # Para no saturar el procesador
            
            
    
    # --- 6. Si el bucle termina sin exito ---
    duration = time.time() -start_time
    print(f"Nodo {node_id}: Bucle terminado sin solución. Mejor corte:{best_found_cut}.Corte obejetivo: {target_cut} Tiempo: {duration:.2f}s")
    return None





    