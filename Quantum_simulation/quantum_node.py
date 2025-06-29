from quantum_blockchain import Quantum_Blockchain
from quantum_block import Quantum_Block
from quantum_transactions import Transaction, Wallet
from QAOA_max_cut import solve_max_cut_qaoa
import numpy as np
from typing import List, Any, Set, Dict, Optional # For type hinting
import time
import threading
import queue
import random
import hashlib
import networkx as nx
from datetime import datetime

#graphviz_bin = r"C:\Program Files\Graphviz\bin"
#os.environ["PATH"] += os.pathsep + graphviz_bin
from graphviz import Digraph

class Quantum_Node(threading.Thread):
    def __init__(self, node_id:str, blockchain_instance = Quantum_Blockchain, node_list: list = None, stop_event: threading.Event = None):
        threading.Thread.__init__(self,daemon=True) # Llamar al init del Thread, daemon=True para que termine si el principal termina
        self.node_id = node_id
        self.blockchain = blockchain_instance
        self.wallet = Wallet()
        self.mempool: Set[Transaction] = set()
        self.peers_queues: Dict[str, queue.Queue] = {} #  Almacena colas de enrada de los peers
        self.incoming_queue = queue.Queue() #C ola de entrada a este nodo
        self.known_tx_hashes: Set[str] = set()
        self.known_block_hashes: Set[str] = set()
        if self.blockchain.chain:
            self.known_block_hashes.add(self.blockchain.chain[0].hash)

        self.node_list = node_list
        self.stop_event = stop_event

        self.is_minig = False # Flag para evitar minado en pararelo consigo mismo
        self.mining_thread_active = False # Indica si una tarea de minado está en marcha
        self.current_mining_task_stop_event: Optional[threading.Event] = None # Para detener un hilo de minado cuando se recibe un bloque válido
        self.is_validating_block = False # Indica si _handle_block esta ocupado
        self.mining_thread = None #Referencia al hilo minero

        self.data_lock = threading.Lock() # Lock para bloquear accesos concurrentes

        # -- Parametos PoW Max-Cut --
        self.N = self.blockchain.N # Numero de nodos del grafo
        self.p = self.blockchain.p # Probabilidad de arista

        print(f"Nodo {self.node_id} creado. Dirección Wallet: {self.wallet.get_address()[:10]}... Parametros Max-Cut: N={self.N}, p={self.p}")

    def get_address(self) -> str:
        "Devuelve la dirección de la wallet del nodo"
        return self.wallet.get_address()
    
    def add_peer(self, peer_node: 'Quantum_Node'):
        "Almacena la cola del peer para poder enviar mensajes"
        if peer_node.node_id != self.node_id:
            self.peers_queues[peer_node.node_id] = peer_node.incoming_queue
            print(f"Nodo {self.node_id}: Conectado a la cola de {peer_node.node_id}")

    # --- METODOS DE PROCESAMIENTO, se llaman desde el run
    def _handle_transaction(self, transaction: Transaction):
        '''Usar self.data_lock para proteger mempool y known_tx_hashes'''
        with self.data_lock:
            tx_hash = transaction.calculate_hash()
            if tx_hash in self.known_tx_hashes:
                return
            self.known_tx_hashes.add(tx_hash)
            if transaction.is_valid() and transaction not in self.mempool:
                self.mempool.add(transaction)
                needs_broadcast = True
            else:
                needs_broadcast = False
                print(f"Nodo {self.node_id}: Tx {tx_hash[:8]} no valida o ya en mempool")
        if needs_broadcast:
            self._broadcast("transaction", transaction)
    
    def _handle_block(self, block: Quantum_Block):
        '''Maneja bloques entrantes. Validacion max-cut'''
        
        # 1. Comporbar si conecemos el bloque
        self.is_validating_block = True
        
        block_hash  = block.hash
        print(f"Nodo {self.node_id}: Recibiendo bloque {block.index} con hash {block_hash[:8]}... Minado por {block.mined_by}")
        with self.data_lock:
            if block_hash in self.known_block_hashes:
                print(f"Nodo {self.node_id}: Bloque {block.index} con hash: {block_hash[:8]} ya conocido")
                self.is_validating_block = False
                return
            self.known_block_hashes.add(block_hash)
            last_local_block = self.blockchain.last_block
        
        # Validar bloque (fuera de lock)
        if not last_local_block:
            print(f"Nodo {self.node_id}: No hay last block conocido")
            return
        
        # 2. Validar enlace
        if block.index != last_local_block.index + 1:
            print(f"Nodeo {self.node_id}: Error: Index del bloque {block.index} no es correcto (esperado {last_local_block.index + 1})")
            return
        if block.previous_hash != last_local_block.calculate_final_hash():
            print(f"Nodo {self.node_id}: Error: Hash previo del bloque {block.index} no es correcto")
            print(f"  Esperado: {last_local_block.calculate_final_hash()[:8]}... - Recibido: {block.previous_hash[:8]}...")
            return
        
        # 3. Generar grafo y calcular corte objetivo
        try:
            graph_for_validation = block.generate_graph()
            target_cut_size = block.calculate_target(graph_for_validation)
        except Exception as e:
            print(f"Nodo {self.node_id}: Error al generar grafo para validar bloque: {e}")
            return

        # 4. Validar PoW
        try:
            is_pow_valid, calculated_cut = block.validate_PoW(graph_for_validation)
        except Exception as e:
            print(f"Nodo {self.node_id}: Error al validar PoW: {e}")
            return
        if not is_pow_valid:
            print(f"Nodo {self.node_id}: Error en la validacion de PoW del bloque {block.index}. Corte = {calculated_cut}, Target = {target_cut_size}")
            return

        # 5. Validar el hash final
        try:
            expected_hash = block.calculate_final_hash()
            print(f"Nodo {self.node_id}: particion: {block.partition_solution}")
            if block.hash != expected_hash:
                print(f"Nodo {self.node_id}: Bloque {block.index} no valido. Hash final no coincide")
                print(f"Nodo {self.node_id}: hash del bloque {block.hash[:8]}. hash esperado: {expected_hash[:8]}")
                return
        except ValueError as e:
            print(f"Nodo {self.node_id}: Error al calcular el hash final del bloque {block.index}: {e}")
            return
        except Exception as e:
            print(f"Nodo {self.node_id}: Error inesperado al calcular el hash final del bloque {block.index}: {e}")
            return
        
        # --- Bloque valido ---
        print(f"Nodo {self.node_id}: Bloque {block.index} valido. Hash: {block.hash[:8]}... - Corte: {calculated_cut} - Target: {target_cut_size}")

        # --- Modifiacion estado (con lock) ---
        with self.data_lock:
            # Volver a comprobar si la cadena cambió fuera del lock
            current_last_block = self.blockchain.last_block
            if block.previous_hash == current_last_block.calculate_final_hash():
                # Anadir a la blockchain
                if self.blockchain.add_block(block):
                    print(f"Nodo {self.node_id}: Añadiendo bloque {block.index}  con hash: {block.hash[:8]}a la cadena local. Minado por {block.mined_by}")
                    block_tx_ids = { hashlib.sha256(str(tx).encode()).hexdigest() for tx in block.transactions }
                    self.mempool = {tx for tx in self.mempool if hashlib.sha256(str(tx).encode()).hexdigest() not in block_tx_ids}

                    if self.is_minig:
                        self._stop_mining()
                    needs_broadcast = True
                else:
                    #add_block fallo
                    print(f"Nodo {self.node_id}: Error al añadir bloque {block.index} a la cadena local")
                    needs_broadcast = False
            else:
                print(f"Nodo {self.node_id}: Error al añadir bloque {block.index} a la cadena local. Hash previo no coincide")
                needs_broadcast = False
        self.is_validating_block = False
        
        if needs_broadcast:
            self._broadcast("block", block)

    def _broadcast(self, msg_type:str, data:any):
        '''Envia mensaje a las colas de todos los peers conocidos'''
        message = (msg_type, data) # Empaquetar tipo y datos
        for peer_id, peer_queue in self.peers_queues.items():
            try:
                peer_queue.put(message,block=False) # No bloquear si la cola esta llena
            except queue.Full:
                print(f"Nodo {self.node_id}: WARN - Cola del peer {peer_id} llena. Mensaje descartado")
    
    def _start_mining(self):
        '''Inicia el hilo de minado'''  
        with self.data_lock:
            if self.is_minig:
                print(f"Nodo {self.node_id}: Minado ya en curso")
                return
            mempool_copy = list(self.mempool)

            if not mempool_copy:
                print(f"Nodo {self.node_id}: Nada que minar")
                return
            
            self.is_minig = True
            self.mining_thread_active = True
            # Crear hilo de minado
      
            self.current_mining_task_stop_event = threading.Event() # Evento de parada para esta tarea en concreto
            self.mining_thread = threading.Thread(target=self._mine_worker, args=(mempool_copy, self.current_mining_task_stop_event,self.stop_event), daemon=True)
            self.mining_thread.start() # Iniciar hilo de minado            
        
    
    def _stop_mining(self):
        '''Detiene el hilo de minado'''
        if self.mining_thread_active and self.current_mining_task_stop_event:
            self.current_mining_task_stop_event.set() # Señalizar hilo de minado que pare
            if self.is_minig:
                print(f"Nodo {self.node_id}: Deteniendo minado")
                if self.mining_thread and self.mining_thread.is_alive():
                    self.mining_thread.join(timeout=0.5)
                    if self.mining_thread.is_alive():
                        print(f"Node {self.node_id}: Warning! Hilo de minado no termino bien")

                self.is_minig = False
                self.mining_thread = None
                self.mining_thread_active = False
            
    def _mine_worker(self, transactions_to_mine: List[Transaction],task_stop_event:threading.Event, node_stop_event: threading.Event):
        '''Minado max-cut QAOA'''
        if not transactions_to_mine:
            print(f"Node {self.node_id} No hay transacciones.")
            self.is_minig = False
            return
        
        with self.data_lock: # Obtener estado actual
            last_block: Quantum_Block = self.blockchain.last_block
            if not last_block or not last_block.calculate_final_hash(): # No hay último bloque
                print(f"Nodo {self.node_id}: No hay bloques en la cadena")
                self.is_minig = False
                return 
            difficulty_ratio = self.blockchain.get_current_difficulty()
            prev_hash = last_block.calculate_final_hash()
            
            # Creamos bloque candidato
            candidate_block = Quantum_Block(
                index=last_block.index +1,
                timestamp=time.time(),
                transactions=transactions_to_mine,
                previous_hash=prev_hash,
                mined_by=self.node_id,
                difficulty_ratio=difficulty_ratio,
                protocol_N=self.N,
                protocol_p=self.p
            )
            
            print(f"Nodo {self.node_id}: Iniciando minado bloque {candidate_block.index}. Difficulty ratio: {difficulty_ratio}. Numero de transaciones: {len(candidate_block.transactions)}. Hash bloque anterior: {candidate_block.previous_hash[:8]}")
           
            #Generar grafo para puzle                   
        try:
            graph_to_solve = candidate_block.generate_graph()
            if graph_to_solve.number_of_nodes() == 0 and self.N > 0:
                print(f"Nodo {self.node_id}: Error - grafo vacio")
                self.is_minig = False
                return
        except Exception as e:
            print(f"Nodo {self.node_id}: Error generando grafo - {e}")
            self.is_minig = False
            return 
        
        target_cut = np.ceil(graph_to_solve.number_of_edges() * difficulty_ratio)
        
        # Resolvemos Max-Cut
        start_solver_time = time.time()
        solution_partition = solve_max_cut_qaoa(graph=graph_to_solve, target_cut=target_cut, node_id=self.node_id, stop_event=task_stop_event)
        solver_duration = time.time() - start_solver_time
        
        
    
        print(f"Nodo {self.node_id}: Solucion: {solution_partition}")
        if solution_partition and not node_stop_event.is_set():
            candidate_block.partition_solution = solution_partition                
            
            try:
                candidate_block.hash = candidate_block.calculate_final_hash()
                
                #BUCLE DE ESPERA Y COMPROBACION ANTES DE PUBLICAR
                
                max_wait_attempts = 20
                attempt = 0
                
                while attempt < max_wait_attempts:
                    if node_stop_event.is_set(): # Comprobar de nuevo si hemos recibido alguna para
                        print(f"Nodo: {self.node_id}: Parada recibida mientras se esperaba para publicar")
                        candidate_block.hash = None
                        break
                    
                    can_publish = not self.is_validating_block
                    
                    if can_publish:
                        print(f"Nodo {self.node_id}: Bloque minado y listo para publicar")
                        # Enviar bloque minado a cola para procesarlo
                        print(f"Nodo {self.node_id}: Bloque minado {candidate_block.index} Hash: {candidate_block.hash[:8]}. Hash bloque anterior: {candidate_block.previous_hash[:8]} Numero de transaciones:{len(candidate_block.transactions)} Tiempo de minado: {solver_duration:.2f}")
                        self.incoming_queue.put(("mined_block", candidate_block))
                        break
                    else: # Estamos validando otro bloque
                        time.sleep(0.1)
                        attempt +=1
                        
                if attempt == max_wait_attempts and candidate_block.hash:
                    print(f"Nodo {self.node_id}: Timeout para publicar expirado")
                       
            except ValueError as e:
                print(f"Nodo {self.node_id}: Error al calcular el hash despues de minar: {e}")
            except Exception as e:
                print(f"Nodo {self.node_id}: Error inesperado al calcular el hash después de minar: {e}")
                
        elif node_stop_event.is_set() or task_stop_event.is_set():
            print(f"Nodo {self.node_id}: Minado detenido")
        else: #Solver ha fallado
            print(f"Nodo {self.node_id}: No se ha encontrado solucion al problema") #Que hacemos, volvemos a empezar?
        
        if self.mining_thread == threading.current_thread(): # Si somos el hilo actual
            self.is_minig = False
            
    def _stop(self): # Parada global del nodo
        print(f"Nodo {self.node_id}: Parada general del nodo")
        self.stop_event.set() # Señalizar el evento de parada
        self.is_minig = False
        self._stop_mining() 
      
    def run(self):
        '''Ejecuta el hilo del nodo, procesando mensajes de la cola de entrada'''
        print(f"Nodo {self.node_id}: Iniciando hilo de procesamiento")
        
        lastblock:Quantum_Block = self.blockchain.last_block
        while not self.stop_event.is_set():
            try:
                # 1. Procesar mensajes entrantes (no bloqueante)
                message_type, data = self.incoming_queue.get(block=False)
                #print(f"Nodo {self.node_id}: Recibo mensaje {message_type}")
                if message_type == "transaction":
                    self._handle_transaction(data)
                elif message_type == "block":
                    print(f"Nodo {self.node_id}: Recibo bloque")
                    self._handle_block(data)
                elif message_type == "mined_block":
                    print(f"Nodo {self.node_id}: Recibo bloque minado")
                    self._handle_block(data)
                self.incoming_queue.task_done() #Marcar tarea como completada
            except queue.Empty:
                #No hay mensajes en la cola
                action = random.random()
                
                # 2. Posibilidad de crear una transaccion
                if action < 0.6: 
                    if len(self.peers_queues) > 0 :#Hay mas de un nodo conectado)
                        if self.node_list and len (self.node_list) > 1:
                            possible_recipients = [n for n in self.node_list if n.node_id != self.node_id]
                            if possible_recipients:
                                recipient_node = random.choice(possible_recipients)
                                amount = round(random.uniform(0.1,1.0),2 )
                                print(f"Nodo {self.node_id}: Tx a {recipient_node.node_id} por {amount}")
                                self._create_and_broadcast_transaction(recipient_node.get_address(), amount)
                            else:
                                print(f"Nodo {self.node_id}: No hay nodos disponibles para enviar Tx")
                # 3. Posibilidad de minar un bloque
                if action < 0.2:
                    with self.data_lock: #Necesario para chequear mempool
                        can_mine =  not self.is_minig and len(self.mempool) > 0
                    if can_mine:
                        self._start_mining()
                # Pausa para evitar consumo excesivo de CPU
                time.sleep(random.uniform(0.5, 1.0)) # Pausa aleatoria entre 0.1 y 0.5 segundos
        print(f"Nodo {self.node_id}: Hilo detenido")        
    
    def _create_and_broadcast_transaction(self, recipient_address:str, amount:float):
        '''Metodo auxiliar para crear Tx desde el hilo'''
        tx = Transaction(
            sender_address=self.get_address(),
            recipient_address=recipient_address,
            amount=amount,
            inputs=[]
        )
        tx.sign_transaction(self.wallet)
        tx_hash = tx.calculate_hash()
        if tx.is_valid():
            with self.data_lock: # Acceso a mempool y known_tx_hashes
                if tx not in self.mempool and tx_hash not in self.known_tx_hashes:
                    self.mempool.add(tx)
                    self.known_tx_hashes.add(tx_hash)
                    needs_broadcast = True
                else:
                    needs_broadcast = False
                if needs_broadcast:
                    self._broadcast("transaction", tx)
        else:
            print(f"Nodo {self.node_id}: ERROR Tx {tx_hash[:8]}...")

    # --- UTILITIES ---
  
    def visualize_chain(self, filename: str = None, max_blocks: int = None):
       """
       Genera un archivo de imagen de la blockchain DE ESTE NODO usando Graphviz.
       Los bloques se encadenan de Izquierda a Derecha.
       La información DENTRO de cada bloque se lista Verticalmente.
       Args:
           filename (str, optional): Nombre base del archivo de salida (sin extensión).
                                     Defaults to "node_{self.node_id}_chain_LR_V".
           max_blocks (int, optional): Número máximo de bloques recientes a mostrar.
                                       Defaults to None (mostrar todos).
       """
       if filename is None:
           filename = f"Imagenes_simulacion/_{self.node_id}_{datetime.now().strftime("%Y-%m-%d_%H-%M")}" # Indicar layout
       print(f"\n--- Generando visualización Graphviz (LR, V-Label) para {self.node_id} ({filename}) ---")
       dot = Digraph(comment=f'Blockchain de {self.node_id}', format='png')
       # 1. Dirección del grafo: Izquierda a Derecha
       dot.attr(rankdir='LR')
       # 2. Forma del nodo: Caja estándar (o el default). El label hará el trabajo vertical.
       dot.attr('node', shape='box', style='filled', color='lightblue', fontname='Courier New') # Usar fuente monoespaciada ayuda
       dot.attr(label=f'Cadena del Nodo: {self.node_id}', fontsize='16')
       chain_to_visualize = self.blockchain.chain
       if not chain_to_visualize:
           print(f"  Nodo {self.node_id}: Cadena vacía, no se genera gráfico.")
           return
       if max_blocks and len(chain_to_visualize) > max_blocks:
           print(f"  (Mostrando los últimos {max_blocks} bloques de {len(chain_to_visualize)})")
           chain_to_visualize = chain_to_visualize[-max_blocks:]
       start_index = self.blockchain.chain.index(chain_to_visualize[0])
       # 3. Añadir bloques
       for i, block in enumerate(chain_to_visualize):
           actual_index = start_index + i
           miner_info = getattr(block, 'mined_by', 'N/A')
           hash = block.calculate_final_hash()
           label_lines = [
               f"Bloque {block.index}",
               f"Hash: {hash[:10]}...",
               f"Prev: {block.previous_hash[:10]}...",
               f"Partition: {block.partition_solution}",
               f"Txs: {len(block.transactions)}",
               f"Minado por: {miner_info}"
           ]
           label = "\n".join(label_lines)          
           node_id = block.hash
           if block.index == 0:
               print(f"Imprimiendo bloque genesis")
               dot.node(node_id, _attributes={'style': 'filled', 'color':'lightgreen'}) 
               
           dot.node(node_id, label=label)
                          
       # 4. Añadir aristas
       for i in range(1, len(chain_to_visualize)):
           prev_block = chain_to_visualize[i-1]
           current_block = chain_to_visualize[i]
           dot.edge(prev_block.hash, current_block.hash)
       # 5. Renderizar
       try:
           output_path = dot.render(filename, view=False, cleanup=True)
           print(f"  Visualización para {self.node_id} guardada como: {output_path}")
       except Exception as e:
           print(f"\n  Error al generar Graphviz para {self.node_id}: {e}")
           print("  Verifica que Graphviz esté instalado y en el PATH.")
           
