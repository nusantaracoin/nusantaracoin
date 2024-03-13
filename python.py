import hashlib
import json
from time import time
import sqlite3
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Membuat blok genesis
        self.new_block(previous_hash='1', proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Membuat blok baru dalam blockchain

        :param proof: Bukti yang dihasilkan oleh algoritma Proof of Work
        :param previous_hash: Hash dari blok sebelumnya
        :return: Blok baru yang ditambahkan
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset list transaksi saat ini
        self.current_transactions = []

        # Simpan blok ke dalam database
        self.save_block_to_db(block)

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Menambahkan transaksi baru ke dalam daftar transaksi yang akan dimasukkan dalam blok berikutnya

        :param sender: Alamat pengirim
        :param recipient: Alamat penerima
        :param amount: Jumlah uang yang ditransfer
        :return: Index blok yang akan menaunginya transaksi ini
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Membuat hash SHA-256 dari blok

        :param block: Blok
        :return: Hash dalam format string
        """
        # Pastikan dictionary diurutkan untuk hasil yang konsisten
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Mengembalikan blok terakhir dalam rantai
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Algoritma Proof of Work:
         - Cari nilai p' yang membuat hash(p * p') memiliki 4 angka nol pertama

        :param last_proof: Proof terakhir
        :return: Nilai proof yang memenuhi kondisi
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Memvalidasi proof:
         - Apakah hash(last_proof * proof) memiliki 4 angka nol pertama?

        :param last_proof: Proof terakhir
        :param proof: Proof yang akan divalidasi
        :return: True jika valid, False jika tidak
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    def save_block_to_db(self, block):
        """
        Menyimpan blok ke dalam database

        :param block: Blok yang akan disimpan
        """
        conn = sqlite3.connect('blockchain.db')
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS blocks
                          (block_index INTEGER PRIMARY KEY, timestamp REAL, proof INTEGER, previous_hash TEXT)''')

        try:
            cursor.execute('''INSERT INTO blocks (block_index, timestamp, proof, previous_hash)
                              VALUES (?, ?, ?, ?)''',
                           (block['index'], block['timestamp'], block['proof'], block['previous_hash']))
        except sqlite3.IntegrityError:
            # Jika kesalahan keintegritasian terjadi, 
            # atur kembali nilai block_index dengan nilai yang unik
            cursor.execute('''SELECT MAX(block_index) FROM blocks''')
            last_index = cursor.fetchone()[0]
            block['index'] = last_index + 1
            cursor.execute('''INSERT INTO blocks (block_index, timestamp, proof, previous_hash)
                              VALUES (?, ?, ?, ?)''',
                           (block['index'], block['timestamp'], block['proof'], block['previous_hash']))

        conn.commit()
        conn.close()


# Inisialisasi blockchain
blockchain = Blockchain()

# Inisialisasi Flask
app = Flask(__name__)


@app.route('/mine', methods=['GET'])
def mine():
    # Proses Proof of Work untuk menambahkan blok baru
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Menambahkan blok baru ke dalam blockchain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Blok baru telah ditambahkan",
        'block_index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['GET'])
def new_transaction():
    values = request.get_json()

    # Memeriksa apakah bidang yang diperlukan ada dalam data POST
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Data transaksi tidak lengkap', 400

    # Menambahkan transaksi baru
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaksi akan dimasukkan ke dalam blok {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
