from Quantum_simulation.quamtum_blockchain import Blockchain
from Quantum_simulation.quantum_block import Block
from transactions import Transaction, Wallet
from typing import List, Any, Set, Dict # For type hinting
import time
import threading
import queue
import random
from graphviz import Digraph

class Node(threading.Thread):
    def __init__(self, node_id:str, blockchain_instance = Blockchain, node_list: list = None, stop_event: threading.Event = None):
        threading.Thread.__init__(self,daemon=True) # Llamar al init del Thread, daemon=True para que termine si el principal termina
        self.node_id = node_id
        self.blockchain = blockchain_instance
        self.wallet = Wallet()
        self.mempool: Set[Transaction] = set()
        # self.peers: List['Node'] = []
        self.peers_queues: Dict[str, queue.Queue] = {} #Almacena colas de enrada de los peers
        self.incoming_queue = queue.Queue() #Cola de entrada a este nodo
        self.known_tx_hashes: Set[str] = set()
        self.known_block_hashes: Set[str] = set()
        if self.blockchain.chain:
            self.known_block_hashes.add(self.blockchain.chain[0].hash)

        self.node_list = node_list
        self.stop_event = stop_event

        self.is_minig = False #Flag para evitar minado en pararelo consigo mismo
        self.mining_thread = None #Referencia al hilo minero

        self.data_lock = threading.Lock() #Lock para bloquear accesos concurrentes


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
                #print(f"Nodo {self.node_id}: Anadida Tx {tx_hash[:8]} a memepool")
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
            last_local_block = self.blockchain.last_block #Leer ultimo bloque
            #print(f"Nodo {self.node_id}: Validando bloque {block.index}. Previous hash del bloque a validar: {block.previous_hash[:8]}.Hash del ultimo bloque de la blockchain: {last_local_block.calculate_hash()[:8]}")
            # 3. Validar enlace (previous hash e index)
            if block.index == last_local_block.index + 1 and block.previous_hash == last_local_block.calculate_hash():
                #Bloque valido, extiende la cadena actual
                print(f"Nodo {self.node_id}: Bloque {block.index} VALIDA, anadiendlo a blockchain")
                self.blockchain.chain.append(block)

                # Limpiar mempool
                block_tx_hashes = {tx.calculate_hash() for tx in block.transactions}
                self.mempool.difference_update(block_tx_hashes)
                self.known_tx_hashes.difference_update(block_tx_hashes)

                #Paramos minado
                if self.is_minig:
                    self._stop_mining()
                need_broadcast = True
            else:
                #Blqoue no valido
                print(f"Nodo {self.node_id}: Bloque {block.index} no valido, (index o previous hash incorrecto)")
                need_broadcast = False
        # 4. Enviar bloque a los peers
        if need_broadcast:
            print(f"Nodo {self.node_id}: Transmitiendo bloque {block.index} ({block_hash[:8]}...)")
            self._broadcast("block", block)

    def _broadcast(self, msg_type:str, data:any):
        '''Envia mensaje a las colas de todos los peers conocidos'''
        #print(f"Nodo {self.node_id}: transmitiendo {msg_type}...")
        message = (msg_type, data) #Empaquetar tipo y datos
        for peer_id, peer_queue in self.peers_queues.items():
            try:
                peer_queue.put(message,block=False) #No bloquear si la cola esta llena
            except queue.Full:
                print(f"Nodo {self.node_id}: WARN - Cola del peer {peer_id} llena. Mensaje descartado")
    
    def _start_mining(self):
        '''Inicia el hilo de minado'''  
        with self.data_lock:
            if self.is_minig:
                print(f"Nodo {self.node_id}: Minado ya en curso")
                return
            mempool_copy = list(self.mempool)
            #print(f"Nodo {self.node_id}: Copiando mempool ({len(mempool_copy)}) transacciones")

            if not mempool_copy:
                print(f"Nodo {self.node_id}: Nada que minar")
                return

            
            self.is_minig = True
            # Crear hilo de minado
            self.mining_thread = threading.Thread(target=self._mine_worker, args=(mempool_copy,), daemon=True)
            self.mining_thread.start() #Iniciar hilo de minado            
        
    
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
        #print(f"Nodo {self.node_id}: Ultimo bloque conocido: {last_block.index} ({hash_last_block[:8]}...)")

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
        #print(f"Nodo {self.node_id}. Hash original del bloque candidato {new_block_candidate.index}: {new_block_candidate.calculate_hash()[:8]}...")
        start_mining_time = time.time()
        while self.is_minig:
            new_block_candidate.nonce = nonce
            hash_result = new_block_candidate.calculate_hash()
            if hash_result.startswith(target):
                print(f"Nodo {self.node_id}: BLOQUE MINADO! con nonce {nonce} ({hash_result[:8]}...). Tiempo de minado: {(time.time()-start_mining_time):.2f}")
                self.incoming_queue.put(("mined_block", new_block_candidate)) #Enviar bloque minado a la cola de entrada
                self.is_minig = False #Parar el hilo de minado
                return
            nonce += 1
            #Pequeño delay para evitar bucle infinito
            if nonce % 10000==0:
                if not self.is_minig or self.stop_event.is_set():
                    print(f"Nodo {self.node_id}: Minado detenido por evento de parada")
                    self.is_minig = False
                    return
        print(f"Nodo {self.node_id}: Minado detenido por evento de parada")

    def run(self):
        '''Ejecuta el hilo del nodo, procesando mensajes de la cola de entrada'''
        print(f"Nodo {self.node_id}: Iniciando hilo de procesamiento")
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
                if action < 0.1: #10% de probabilidad por ciclo
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
                elif action < 0.3: #20% de probabilidad por ciclo
                    with self.data_lock: #Necesario para chequear mempool
                        can_mine =  not self.is_minig and len(self.mempool) > 0
                    if can_mine:
                        self._start_mining()
                #Pausa para evitar consumo excesivo de CPU
                time.sleep(random.uniform(0.1, 0.5)) #Pausa aleatoria entre 0.1 y 0.5 segundos
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
            with self.data_lock: #Acceso a mempool y known_tx_hashes
                if tx not in self.mempool and tx_hash not in self.known_tx_hashes:
                    #print(f"Nodo {self.node_id}: Transacción válida {tx_hash[:8]}...")
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
    def visualize_chain(self, filename: str = None, max_blocks:int = None):
        
        if filename is None:
            filename = f"simulation{self.node_id}_chain"
        print(f"\n--- Generando visualizacion para {self.node_id}")

        dot = Digraph(comment=f'Blockchain de {self.node_id}', format='png')
        # rankdir='TB' (Top to Bottom) puede ser más natural para una sola cadena
        dot.attr(rankdir='TB')
        dot.attr('node', shape='record', style='filled', color='lightblue')
        dot.attr(label=f'Cadena del Nodo: {self.node_id}', fontsize='16') # Título del grafo

        chain_to_visualize = self.blockchain.chain
        if not chain_to_visualize:
            print(f"Nodo {self.node_id}: sin cadena")
            return
        if max_blocks and len(chain_to_visualize) > max_blocks:
            print(f"Mostrando los ultimos {max_blocks} bloques de {len(chain_to_visualize)}")
            chain_to_visualize = chain_to_visualize[-max_blocks:]
        start_index = self.blockchain.chain.index(chain_to_visualize[0])

        for i, block in enumerate(chain_to_visualize):
            actual_index = start_index + i # El índice real del bloque en la cadena completa
            miner_info = getattr(block, 'mined_by', 'N/A') # Asume atributo 'mined_by'
            label = (f"{{ {actual_index}: Bloque {block.index} | " # Usar índice real para título
                     f"Hash: {block.hash[:8]}... | "
                     f"Prev: {block.previous_hash[:8]}... | "
                     f"Nonce: {block.nonce} | "
                     f"Txs: {len(block.transactions)} | "
                     f"Minado por: {block.mined_by} }}")

            # Usar el hash como ID único para el nodo graphviz
            node_id = block.hash

            dot.node(node_id, label=label)

            # Marcar el nodo génesis si está en la vista
            if block.previous_hash == "0":
                 dot.node(node_id, _attributes={'style': 'filled', 'color':'lightgreen'})

        # 2. Añadir aristas (conexiones) entre los bloques VISUALIZADOS
        #    Asume que la lista `chain_to_visualize` es secuencialmente correcta para este nodo
        for i in range(1, len(chain_to_visualize)):
            prev_block = chain_to_visualize[i-1]
            current_block = chain_to_visualize[i]

            # Añadir eje desde el hash del bloque anterior al hash del actual
            # La validación visual se hará comparando el "Prev:" del bloque actual
            # con el "Hash:" del bloque anterior en la imagen.
            dot.edge(prev_block.hash, current_block.hash)


        # 3. Renderizar
        try:
            # Puedes añadir engine='dot' si quieres especificarlo
            output_path = dot.render(filename, view=False, cleanup=True)
            print(f"  Visualización para {self.node_id} guardada como: {output_path}")
        except Exception as e:
            print(f"\n  Error al generar Graphviz para {self.node_id}: {e}")
            print("  Verifica que Graphviz esté instalado y en el PATH.")
