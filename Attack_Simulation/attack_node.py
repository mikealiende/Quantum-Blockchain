import os
from attack_blockchain import Blockchain
from attack_block import Block
from attack_transactions import Transaction, Wallet
from typing import List, Set, Dict
import time
import threading
import queue
import random
from datetime import datetime

# Para represetanción visual de los bloques. Con el MAC no hace falta
graphviz_bin = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] += os.pathsep + graphviz_bin
from graphviz import Digraph

class Node(threading.Thread):
    def __init__(self, node_id:str, blockchain_instance = Blockchain, node_list: list = None, stop_event: threading.Event = None, mining_speed : float = 1.0):
        threading.Thread.__init__(self,daemon=True) # Llamar al init del Thread, daemon=True para que termine si el principal termina
        self.node_id = node_id
        self.blockchain = blockchain_instance
        self.wallet = Wallet()
        self.mempool: Set[Transaction] = set()
        self.peers_queues: Dict[str, queue.Queue] = {} # Almacena colas de enrada de los peers
        self.incoming_queue = queue.Queue() # Cola de entrada a este nodo
        self.known_tx_hashes: Set[str] = set()
        self.known_block_hashes: Set[str] = set()
        if self.blockchain.chain:
            self.known_block_hashes.add(self.blockchain.chain[0].hash)

        self.node_list = node_list
        self.stop_event = stop_event

        self.is_minig = False # Flag para evitar minado en pararelo consigo mismo
        self.mining_thread = None # Referencia al hilo minero

        self.data_lock = threading.Lock() # Lock para bloquear accesos concurrentes
        self.mining_speed = mining_speed

        print(f"Nodo {self.node_id} creado. Dirección Wallet: {self.wallet.get_address()[:10]}... ")

    def get_address(self) -> str:
        "Devuelve la dirección de la wallet del nodo"
        return self.wallet.get_address()
    
    def add_peer(self, peer_node: 'Node'):
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
    
    def _handle_block(self, block: Block):
        with self.data_lock:
            block_hash = block.calculate_hash()
            if block_hash in self.known_block_hashes:
                print(f"Nodo {self.node_id}: Bloque {block.index} Ya conocido")
                return
            self.known_block_hashes.add(block_hash)
            
        # --VALIDACION (no necesita locks) ---
        # 1. Validar PoW y hash interno
        calculated_hash = block.calculate_hash()
        if block_hash != calculated_hash or not block_hash.startswith('0'*self.blockchain.difficulty):
            print(f"Nodo {self.node_id}: Bloque {block.index} no valido.")
            return
        
        # 2. Validar transaciones internas
        for tx in block.transactions:
            if not tx.is_valid():
                print(f"Nodo {self.node_id}: Bloque {block.index} no valido, (Tx interna no valida)")
                return
        
        # --- MODIFICACION ESTADO  (necesita lock)---  
        with self.data_lock:
            last_local_block = self.blockchain.last_block # Leer ultimo bloque
            # 3. Validar enlace (previous hash e index)
            if block.index == last_local_block.index + 1 and block.previous_hash == last_local_block.calculate_hash():
                # Bloque valido, extiende la cadena actual
                print(f"Nodo {self.node_id}: Bloque {block.index} VALIDA, anadiendlo a blockchain")
                self.blockchain.chain.append(block)

                # Limpiar mempool
                block_tx_hashes = {tx.calculate_hash() for tx in block.transactions}
                self.mempool.difference_update(block_tx_hashes)
                self.known_tx_hashes.difference_update(block_tx_hashes)

                # Paramos minado
                if self.is_minig:
                    self._stop_mining()
                need_broadcast = True
            else:
                # Blqoue no valido
                print(f"Nodo {self.node_id}: Bloque {block.index} no valido, (index o previous hash incorrecto)")
                need_broadcast = False
        # 4. Enviar bloque a los peers
        if need_broadcast:
            print(f"Nodo {self.node_id}: Transmitiendo bloque {block.index} ({block_hash[:8]}...)")
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
            # Crear hilo de minado
            self.mining_thread = threading.Thread(target=self._mine_worker, args=(mempool_copy,), daemon=True)
            self.mining_thread.start() # Iniciar hilo de minado            
        
    
    def _stop_mining(self):
        '''Detiene el hilo de minado'''
        if self.is_minig:
            print(f"Nodo {self.node_id}: Deteniendo minado")
            self.is_minig = False
            self.mining_thread = None
    
    def _mine_worker(self, transactions_to_mine: List[Transaction]):
        '''Funcion ejecutada por el hilo de minado'''
        if not transactions_to_mine:
            print(f"Nodo {self.node_id}: No hay transacciones para minar")
            self.is_minig = False
            return
        print(f"Nodo {self.node_id}: Iniciando minado de bloque con {len(transactions_to_mine)} Txs")
        last_block = self.blockchain.last_block
        hash_last_block = last_block.calculate_hash()

        new_block_candidate = Block(
            index=last_block.index +1,
            timestamp=time.time(),
            transactions=transactions_to_mine,
            previous_hash=hash_last_block,
            mined_by=self.node_id,
            nonce=0
        )

        # --- BUCLE PoW ---
        target = '0' * self.blockchain.difficulty
        nonce = 0
        BASE_CHECK_INTERVAL = 10000 # Numero de nonces que se prueban antes de una pausa. 
        check_interval = int(BASE_CHECK_INTERVAL * self.mining_speed)
        if check_interval <= 0: check_interval = 1 # Para eviar problemas.
        pause_duration = 1   
        start_mining_time = time.time()
        while self.is_minig:
            new_block_candidate.nonce = nonce
            hash_result = new_block_candidate.calculate_hash()
            if hash_result.startswith(target):
                print(f"Nodo {self.node_id}: BLOQUE MINADO! con nonce {nonce} ({hash_result[:8]}...). Tiempo de minado: {(time.time()-start_mining_time):.2f}")
                self.incoming_queue.put(("mined_block", new_block_candidate)) # Enviar bloque minado a la cola de entrada
                self.is_minig = False # Parar el hilo de minado
                return
            nonce += 1
            # Pequeño delay para evitar bucle infinito
            if nonce % check_interval==0:
                if not self.is_minig or self.stop_event.is_set():
                    print(f"Nodo {self.node_id}: Minado detenido por evento de parada")
                    self.is_minig = False
                    return
                time.sleep(pause_duration)
             
        print(f"Nodo {self.node_id}: Minado detenido por evento de parada")

    def run(self):
        '''Ejecuta el hilo del nodo, procesando mensajes de la cola de entrada'''
        print(f"Nodo {self.node_id}: Iniciando hilo de procesamiento")
        while not self.stop_event.is_set():
            try:
                # 1. Procesar mensajes entrantes (no bloqueante)
                message_type, data = self.incoming_queue.get(block=False)
                if message_type == "transaction":
                    self._handle_transaction(data)
                elif message_type == "block":
                    print(f"Nodo {self.node_id}: Recibo bloque")
                    self._handle_block(data)
                elif message_type == "mined_block":
                    print(f"Nodo {self.node_id}: Recibo bloque minado")
                    self._handle_block(data)
                self.incoming_queue.task_done() # Marcar tarea como completada
            except queue.Empty:
                # No hay mensajes en la cola
                action = random.random()
                # 2. Posibilidad de crear una transaccion
                if action < 0.1: # 10% de probabilidad por ciclo
                    if len(self.peers_queues) > 0 :# Hay mas de un nodo conectado)
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
                elif action < 0.3: # 30% de probabilidad por ciclo
                    with self.data_lock: # Necesario para chequear mempool
                        can_mine =  not self.is_minig and len(self.mempool) > 0
                    if can_mine:
                        self._start_mining()
                # Pausa para evitar consumo excesivo de CPU
                time.sleep(random.uniform(0.1, 0.5)) # Pausa aleatoria entre 0.1 y 0.5 segundos
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
            filename = f"Imagenes_simulacion/Attack_{self.node_id}_{datetime.now().strftime("%Y-%m-%d_%H-%M")}" 

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

        # 3. Añadir nodos (bloques) al grafo
        for i, block in enumerate(chain_to_visualize):
            actual_index = start_index + i
            miner_info = getattr(block, 'mined_by', 'N/A')
            hash = block.calculate_hash()

            label_lines = [
                f"Bloque {block.index}",
                f"Hash: {hash[:10]}...", # Mostrar un poco más del hash?
                f"Prev: {block.previous_hash[:10]}...",
                f"Txs: {len(block.transactions)}",
                f"Minado por: {miner_info}"
            ]
            label = "\n".join(label_lines) # Unir líneas con salto de línea

            node_id = block.hash
            dot.node(node_id, label=label) # El label ahora tiene saltos de línea

            if block.previous_hash == "0":
                 dot.node(node_id, _attributes={'style': 'filled', 'color':'lightgreen'})

        # 4. Añadir aristas (conexiones) - De Izquierda a Derecha
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