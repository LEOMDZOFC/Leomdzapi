from flask import Flask, jsonify, request
import requests
import mymessage_pb2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import random
import binascii
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# إعدادات التشفير
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'
keys = set()  # مجموعة لتخزين المفاتيح الصالحة

# دالة إنشاء مفتاح UID عشوائي
def generate_random_uid_64():
    return random.randint(1, 9_223_372_036_854_775_807)

# دالة تشفير الرسالة
def encrypt_message(key, iv, plaintext):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(plaintext, AES.block_size)
    encrypted_message = cipher.encrypt(padded_message)
    return encrypted_message

# دالة جلب التوكينات
def fetch_tokens():
    token_url = "http://164.92.134.31:5001/token"
    try:
        response = requests.get(token_url)
        if response.status_code == 200:
            tokens = response.json()['tokens']
            return tokens[:100]  # إرجاع أول 99 توكن فقط
        else:
            print(f"Failed to fetch tokens, status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        return []

# دالة إرسال طلبات الرسائل
def send_request(token, hex_encrypted_data):
    url = "https://clientbp.ggblueshark.com/RequestAddingFriend"
    payload = bytes.fromhex(hex_encrypted_data)
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': f"Bearer {token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB48"
    }

    response = requests.post(url, data=payload, headers=headers)
    return response.status_code == 200

# إضافة مفتاح جديد
@app.route('/make_key', methods=['GET'])
def make_key():
    key = request.args.get('key')
    if not key:
        return jsonify({"error": "Key parameter is missing"}), 400
    keys.add(key)
    return jsonify({"message": f"KEY '{key}' ADDED SUCCESSFULLY"}), 200

# حذف مفتاح موجود
@app.route('/del_key', methods=['GET'])
def del_key():
    key = request.args.get('key')
    if not key:
        return jsonify({"error": "Key parameter is missing"}), 400
    if key in keys:
        keys.remove(key)
        return jsonify({"message": f"Key '{key}' DELETED SUCCESSFULLY"}), 200
    else:
        return jsonify({"error": f"Key '{key}' not found"}), 404

# إرسال طلبات الرسائل باستخدام مفتاح
@app.route('/request', methods=['GET'])
def send_spam():
    api_key = request.args.get('api_key')
    user_id = request.args.get('uid')

    if not api_key or not user_id:
        return jsonify({"error": "Missing required parameters: api_key or uid"}), 400

    # تحقق من المفتاح
    if api_key not in keys:
        return jsonify({"error": "Invalid API key"}), 403

    # معالجة الطلبات
    message = mymessage_pb2.MyMessage()
    message.field1 = 9797549324
    message.field2 = int(user_id)
    message.field3 = 22

    serialized_message = message.SerializeToString()
    encrypted_data = encrypt_message(AES_KEY, AES_IV, serialized_message)
    hex_encrypted_data = binascii.hexlify(encrypted_data).decode('utf-8')

    tokens = fetch_tokens()
    if not tokens:
        return jsonify({"error": "No tokens available"}), 500

    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(lambda token: send_request(token, hex_encrypted_data), tokens)

    success_count = sum(1 for result in results if result)

    return jsonify({"message": f"SUCCESSFULLY SENT {success_count} FRIEND REQUESTS"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=50066)