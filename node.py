from blockchain import Blockchain
from block import Block
from transactions import Transaction
from typing import List, Any, Set # For type hinting

class Node:
    def __init__(self, node_id:str, difficulty:int=4):
        self.node_id = node_id
        self.blockchain = Blockchain(difficulty)
        self.mempool: Set[Transaction] = set()
        self.peers: List['Node'] = []
        self.known_tx_hashes: Set[str] = set()
        self.known_block_hashes: Set[str] = set()

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
            return #bloque ya conocido
        print(f"Node {self.node_id}: Received Block {block.index} ({block.hash[:8]}...)")
        self.known_block_hashes.add(block.hash)

        #1. Validar bloque
        last_block = self.blockchain.last_block
        if block.previous_hash != last_block.hash:
            print(f"Nodo {self.node_id}: descarta el bloque {block.index} - hash anterior incorrecto")
            return
        


