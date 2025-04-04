from blockchain import Blockchain
from block import Block
from transactions import Transaction, Wallet
from typing import List, Any, Set, Dict # For type hinting
from time import time
#import threading
#import queue

class Node:
    def __init__(self, node_id:str, difficulty:int=4):
        #super().__init__(daemon=True) # Llamar al init del Thread, daemon=True para que termine si el principal termina
        self.node_id = node_id
        self.blockchain = Blockchain(difficulty)
        self.wallet = Wallet()
        self.mempool: Set[Transaction] = set()
        self.peers: List['Node'] = []
        #self.peers_queues: Dict[str, queue.Queue] = {} #Almacena colas de enrada de los peers
        #self.incoming_queue = queue.Queue() #Cola de entrada a este nodo
        self.known_tx_hashes: Set[str] = set()
        self.known_block_hashes: Set[str] = set()
        if self.blockchain.chain:
            self.known_block_hashes.add(self.blockchain.chain[0].hash)

        #self.node_list = node_list
        #self.stop_event = stop_event

        #self.is_minig = False #Flag para evitar minado en pararelo consigo mismo
        #self.mining_thread = None #Referencia al hilo minero

        #self.data_lock = threading.lock() #Lock para bloquear accesos concurrentes


        print(f"Nodo {self.node_id} creado. Dirección Wallet: {self.wallet.get_address()[:10]}... ")

    def get_address(self) -> str:
        "Devuelve la dirección de la wallet del nodo"
        return self.wallet.get_address()
    
    def add_peer(self, peer_node: 'Node'):
        "Simular establecer una conexión con otro nodo"
        if peer_node not in self.peers and peer_node != self:
            self.peers.append(peer_node)
            print(f"Nodo {self.node_id}: conectado al nodo {peer_node.node_id}")

    def create_transaction(self, recipient_address:str, amount:float):
        # Crear una transaccion desde la wallet de este nodo y la transmite
        print(f"Nodo {self.node_id}: creando transacción a {recipient_address[:10]}... por {amount}")
        tx = Transaction(sender_address=self.get_address(),
                         recipient_address=recipient_address,
                         amount=amount,
                         inputs=[])
        tx.sign_transaction(self.wallet)
        tx_hash = tx.calculate_hash()

        if tx.is_valid():
            print(f"Nodo {self.node_id}: transacción válida {tx_hash[:8]}...")
            if tx not in self.mempool:
                self.mempool.add(tx)
                self.known_tx_hashes.add(tx_hash)
                print(f"Nodo {self.node_id}: transacción añadida al mempool {tx_hash[:8]}...")
                self.broadcast_transacitions(tx)
            else:
                print(f"Nodo {self.node_id} Tx {tx_hash[:8]} ya estaba en mempool local")
        else:
            print(f"Nodo {self.node_id}: transacción inválida {tx_hash[:8]}...")
        return tx


    def broadcast_transacitions(self, transaction: Transaction):
        "Transación a todos los nodos conocidos"
        tx_hash = transaction.calculate_hash()
        if tx_hash not in self.known_tx_hashes:
            self.known_tx_hashes.add(tx_hash)
            print(f"Node {self.node_id}: Broadcasting Tx {tx_hash[:8]}...")
            for peer in self.peers:
                peer.recieve_transactions(transaction)

    def recieve_transactions(self, transaction: Transaction):
        "Procesa transación recibida de otro nodo"
        tx_hash = transaction.calculate_hash()
        
        if tx_hash in self.known_tx_hashes:
            return #Transación ya conocida
        

        print (f"Node {self.node_id}: Recieved Tx {tx_hash[:8]}...")
        
        if not transaction.is_valid():
            print(f"Node{self.node_id} Invalid Tx {tx_hash[:8]} recieved")
            self.known_tx_hashes.add(tx_hash) #Marcar como conocida para no propagar
            return
        
        if transaction not in self.mempool: #Si es nueva y valida la añadimos al mempol local
            print(f"Node {self.node_id}: añadió la transacción {tx_hash[:8]} al mempool")
            self.mempool.add(transaction)
            self.known_tx_hashes.add(tx_hash)
            self.broadcast_transacitions(transaction)
        else:
            self.known_tx_hashes.add(tx_hash)

    #Manejo de bloques

    def mine_block(self):
        #Minar bloque con las transaciones de la mempool
        if not self.mempool:
            print(f"Nodo {self.node_id}: Memepool vacia")
            return None
       
        print(f"Nodo {self.node_id}: Intentnado minar bloque con {len(self.mempool)} transacciones")
        transactions_to_mine = list(self.mempool)

        #Crear bloque candidato
        last_block = self.blockchain.last_block
        new_block_candidate = Block(
            index=last_block.index+1,
            timestamp= time(),
            transactions=transactions_to_mine,
            previous_hash=last_block.hash,
            nonce=0
        )

        #Realizar PoW
        found_nonce = self.blockchain.proof_of_work(new_block_candidate)
        new_candidate_hash = new_block_candidate.calculate_hash()
        if not new_candidate_hash.startswith('0'* self.blockchain.difficulty):            
            print(f"Nodo {self.node_id}: ERROR - PoW. {new_block_candidate.hash[:8]} no cumple la dificultad.")
            return None
        print(f"Nodo {self.node_id}: Bloque {new_block_candidate.index} minado. Nonce: {found_nonce}. Hash: {new_block_candidate.hash[:8]}...")

        #Añadir bloque a cadena propia
        self.blockchain.chain.append(new_block_candidate)
        self.known_block_hashes.add(new_block_candidate.hash)

        #Limpiar mempool de transaciones incluidas en el bloque
        mined_tx_hashes = {tx.calculate_hash() for tx in transactions_to_mine}
        self.mempool = {tx for tx in self.mempool if tx.calculate_hash() not in mined_tx_hashes}

        #Limpiamos know tx
        self.known_tx_hashes.difference_update(mined_tx_hashes)
        print(f"Nodo {self.node_id}: Mempool limpiada. Txs restantes {len(self.mempool)}")

        #Transmitir nuevo bloque
        self.broadcast_block(new_block_candidate)


    def broadcast_block(self, block:Block):
        "Enviar bloque minado a todos los nodos"
        if block.hash in self.known_block_hashes:
            return #Bloque ya procesado
        
        self.known_block_hashes.add(block.hash)
        print(f"Nodo {self.node_id} comparte por Broadcast el bloque {block.index} ({block.hash[:8]}...)")
        for peer in self.peers:
            peer.recieve_block(block)

    def recieve_block(self, block:Block):

        if block.hash in self.known_block_hashes:
            return False#bloque ya conocido
        print(f"Node {self.node_id}: Received Block {block.index} ({block.hash[:8]}...)")
        self.known_block_hashes.add(block.hash)

        #1. Validar bloque
        last_block = self.blockchain.last_block
        if block.previous_hash != last_block.hash:
            print(f"Nodo {self.node_id}: descarta el bloque {block.index} - hash anterior incorrecto")
            return False
        
        #3. Validar Proof of Work
        if not block.hash.startswith('0'*self.blockchain.difficulty):
            print(f"Nodo {self.node_id} descarta el bloque {block.index} con hash {block.hash[:8]} porque no cumple con PoW")
            return False
        
        #4. Validad transaciones en el bloque
        for tx in block.transactions:
            if not tx.is_valid():
                tx_hash = tx.calculate_hash()
                print(f"Nodo {self.node_id}: Bloque {block.index} descartado - Contiene Tx inválida {tx_h[:8]}.")
                return False

        # Todas las validaciones correctas
        print(f"Nodo {self.node_id}: Bloque {block.index} ({block.hash}) VALIDADO. Añadiendo a cadena local.")
        self.blockchain.chain.append(block)

        #Limpiar meempol
        block_tx_hashes = {tx.calculate_hash() for tx in block.transactions}
        original_mempool_size = len(self.mempool)
        self.mempool = {tx for tx in self.mempool if tx.calculate_hash not in block_tx_hashes}
        self.known_tx_hashes.difference_update(block_tx_hashes) #Quitarlas del known tambien
        if len(self.mempool) < original_mempool_size:
            print(f"Nodo {self.node_id}: Mempool local limpiada de {original_mempool_size - len(self.mempool)} Txs incluidas en el bloque.")
        
        self. broadcast_block(block)
        return True
    
    #Utilidades
    def __str__(self):
        #Representación del estado del nodo
        status = (f"Nodo ID: {self.node_id} | "
                  f"Peers: {len(self.peers)} | "
                  f"Bloques: {len(self.blockchain.chain)} ({self.blockchain.last_block.hash[:8]}...) | "
                  f"Mempool Txs: {len(self.mempool)} | "
                  f"Known Blocks: {len(self.known_block_hashes)} | "
                  f"Known Txs: {len(self.known_tx_hashes)}")
        return status
    
    def sync_with_peers(self):
        #Metodo simplificado para intentar obtener bloques faltantes
        print(f"Nodo: {self.node_id} intentando sincronizar...")
        longest_chain_len = len(self.blockchain.chain)
        longest_chain_node = None

        #Encontrar peer con la cadena más larga
        for peer in self.peers:
            if len(peer.blockchain.chain > longest_chain_len):
                longest_chain_len = len(peer.blockchain.chain)
                longest_chain_node = peer
            
        if longest_chain_node:
            print(f"Nodo {self.node_id}: Encontrada cadena de {longest_chain_len} bloques en el nodo {longest_chain_node.node_id}")
            current_len = len(self.blockchain.chain)
            for i in range(current_len, longest_chain_len):
                block_to_add = longest_chain_node.blockchain.chain[i]
                print(f"Nodo {self.node_id}: Obtenido bloque {block_to_add.index} de {longest_chain_node.node_id}")
                self.blockchain.chain.append(block_to_add)
                self.known_block_hashes.add(block_to_add.hash)
                
                #Limpiar mempool
                block_tx_hashes = {tx.calculate_hash() for tx in block_to_add.transactions}
                self.mempool = {tx for tx in self.mempool if tx.calculate_hash() not in block_tx_hashes}
                self.known_tx_hashes.difference_update(block_tx_hashes)
            
            print(f"Nodo {self.node_id}: Sincronizacion completada con {len(self.blockchain.chain)} bloques")
        else:
            print(f"Nodo {self.node_id}: Ya tengo la cadena más larga")