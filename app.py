from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import aiohttp
import json
import friend_request_pb2
from google.protobuf.message import DecodeError

app = Flask(__name__)

# Carrega os tokens conforme o servidor
def load_tokens(server_name):
    try:
        if server_name == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
        elif server_name in {"BR", "US", "SAC", "NA"}:
            with open("token_br.json", "r") as f:
                tokens = json.load(f)
        else:
            with open("token_bd.json", "r") as f:
                tokens = json.load(f)
        return tokens
    except Exception as e:
        app.logger.error(f"[ERRO] Falha ao carregar tokens para {server_name}: {e}")
        return None

# Encriptação AES CBC
def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"[ERRO] Falha na encriptação: {e}")
        return None

# Criação do Protobuf com sender_uid=0 (evita erro de ausência)
def create_friend_request_protobuf(receiver_uid, region):
    try:
        message = friend_request_pb2.FriendRequest()
        message.sender_uid = 0  # Adicionado para evitar erros de estrutura
        message.receiver_uid = int(receiver_uid)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"[ERRO] Falha ao criar protobuf: {e}")
        return None

# Envia uma requisição assíncrona com log de falhas
async def send_friend_request(encrypted_data, token, url):
    try:
        edata = bytes.fromhex(encrypted_data)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB48"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                status = response.status
                if status != 200:
                    body = await response.text()
                    app.logger.warning(f"[FALHA] Token: {token[:15]}... | Status: {status} | Resposta: {body}")
                return status == 200
    except Exception as e:
        app.logger.error(f"[ERRO] Exceção ao enviar requisição: {e}")
        return False

# Controlador geral para várias requisições
async def send_multiple_friend_requests(receiver_uid, server_name, url):
    try:
        protobuf_message = create_friend_request_protobuf(receiver_uid, server_name)
        if not protobuf_message:
            return None
            
        encrypted_data = encrypt_message(protobuf_message)
        if not encrypted_data:
            return None
            
        tokens = load_tokens(server_name)
        if not tokens:
            return None

        # Envia para todos os tokens sem limitar a 100
        tasks = [send_friend_request(encrypted_data, token['token'], url) for token in tokens]
        return await asyncio.gather(*tasks)
        
    except Exception as e:
        app.logger.error(f"[ERRO] Geral: {e}")
        return None

# Endpoint principal
@app.route('/friend', methods=['GET'])
def handle_friend_requests():
    receiver_uid = request.args.get("receiver_uid")
    server_name = request.args.get("server_name", "").upper()
    
    if not receiver_uid or not server_name:
        return jsonify({"error": "receiver_uid e server_name são obrigatórios"}), 400

    if server_name == "IND":
        url = "https://client.ind.freefiremobile.com/RequestAddingFriend"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        url = "https://client.us.freefiremobile.com/RequestAddingFriend"
    else:
        url = "https://clientbp.ggblueshark.com/RequestAddingFriend"

    try:
        results = asyncio.run(send_multiple_friend_requests(receiver_uid, server_name, url))
        if not results:
            return jsonify({"error": "Falha ao processar requisições"}), 500
            
        success_count = sum(1 for success in results if success)
        return jsonify({
            "receiver_uid": receiver_uid,
            "server": server_name,
            "requests_sent": len(results),
            "successful_requests": success_count,
            "success_rate": f"{(success_count/len(results))*100:.2f}%"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)