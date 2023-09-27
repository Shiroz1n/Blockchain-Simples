import hashlib
import json
from urllib.parse import urlparse
from time import time
from uuid import uuid4
import requests
from flask import Flask, jsonify, request


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #Criar o bloco genesis(um bloco sem antecessores)
        self.new_block(previous_hash=1, proof=100)
    
    def register_node(self, address):
         #Adicione um novo nó à lista de nós
         parsed_url = urlparse(address)
         self.nodes.add(parsed_url.netloc)
    
    def valid_chain(self, chain):
         #Determine se um determinado blockchain é válido
         last_block = chain[0]
         current_index = 1

         while current_index < len(chain):
              block = chain[current_index]
              print(f'{last_block}')
              print(f'{block}')
              print("\n-----------\n")
              #Verifique se o hash do bloco está correto
              if block['previous_hash'] !=self.hash(last_block):
                   return False
              #Verifique se a Prova(proff) de Trabalho está correta
              if not self.valid_proof(last_block['proof'], block['proof']):
                   return False
              last_block = block
              current_index += 1

         return True
         
    def resolve_conflicts(self):
        #Este é o nosso Algoritmo de Consenso, ele resolve conflitos substituindo nossa cadeia pela mais longa da rede  
        neighbours = self.nodes
        new_chain = None

        #Estamos apenas procurando correntes mais longas que as nossas
        max_length = len(self.chain)

        #Pegue e verifique as cadeias de todos os nós da nossa rede
        for node in neighbours:
             response = requests.get(f'http://{node}/chain')

            #Verifique se o comprimento é maior e a corrente é válida
             if response.status_code == 200:
                  length = response.json()['length']
                  chain = response.json()['chain']

                  #Verifique se o comprimento é maior e a corrente é válida
                  if length > max_length and self.valid_chain(chain):
                       max_length = length
                       new_chain = chain
                    #Substitua nossa cadeia se descobrirmos uma cadeia nova e válida, mais longa que a nossa
        if new_chain:
             self.chain = new_chain
             return True
        
        return False

    def new_block(self, proof, previous_hash=None):
        #Cria um novo bloco e o adiciona à cadeia
        block = {
            "index" : len(self.chain) + 1,
            "timestamp" : time(),
            "transactions" : self.current_transactions,
            "proof" : proof,
            "previous_hash" : previous_hash or self.hash(self.chain[-1])
        }
        #Redefinir a lista atual de transações
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        #Adiciona uma nova transação à lista de transações
        self.current_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })

        return self.last_block["index"] + 1

    @property
    def last_block(self):
        #Hash um bloco
        return self.chain[-1]
    
    @staticmethod
    def hash(block):
        #Retorna o último bloco da cadeia
        #Cria um hash SHA-256 de um bloco
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        #Algoritmo simples de prova de trabalho:
        #Encontre um número p' tal que hash(pp') contenha 4 zeros iniciais, onde p é o p' anterior - p é a prova anterior e p' é a nova prova
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        
        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    #Instancie nosso nó
app = Flask(__name__)

    #Gere um endereço globalmente exclusivo para este nó
node_identifier = str(uuid4()).replace('-', '')

    #Instancie o Blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
        # Executamos o algoritmo de prova(proof) de trabalho para obter a próxima prova
        last_block = blockchain.last_block
        last_proof = last_block["proof"]
        proof = blockchain.proof_of_work(last_proof)

        #Devemos receber uma recompensa por encontrar a prova.
        # O remetente é "0" para significar que este nó extraiu uma nova moeda.
        blockchain.new_transaction(
            sender="0",
            recipient = node_identifier,
            amount=1,
            #return "Vamos minerar um novo bloco"
        )
        # Forje o novo bloco adicionando-o à cadeia
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)

        response = {
            "message": "Novo Bloco Forjado",
            "index": block["index"],
            "transactions": block["transactions"],
            "proof": block["proof"],
            "previous_hash": block["previous_hash"],
        }
        return jsonify(response), 200

    
@app.route('/transaction/new', methods=["POST"])
def new_transaction():
        values = request.get_json()
        #Verifique se os campos obrigatórios estão nos dados do POST
        required = ["sender", "recipient", "amount"]
        if not all(k in values for k in required):
            return 'Missing values', 400
        
        #Cria uma nova transação
        index = blockchain.new_transaction(values["sender"], values["recipient"], values["amount"])

        response = {'message': f'A transação será adicionada ao bloco {index}'}
        return jsonify(response), 201
        
        #return "Adicionaremos uma nova transação"
    
@app.route('/chain', methods=["GET"])
def full_chain():
        response = {
            "chain": blockchain.chain,
            "length": len(blockchain.chain),
        }
        return jsonify(response), 200
    
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
     values = request.get_json()

     nodes = values.get('nodes')
     if nodes is None:
        return "Erro: forneça uma lista válida de nós", 400
     
     for node in nodes:
          blockchain.register_node(node)

     response = {
         'message': "Novos nós foram adicionados",
         'total_nodes': list(blockchain.nodes),
    }
     return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
     replaced = blockchain.resolve_conflicts()

     if replaced:
          response = {
               'message': "Nossa corrente foi substituída",
               'new_chain': blockchain.chain
          }
     else:
          response = {
               'message': "Nossa rede é autoritária",
               'chain': blockchain.chain
          }
     return jsonify(response), 200

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
