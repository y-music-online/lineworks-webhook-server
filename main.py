from flask import Flask, request
import sys

app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔔 Webhook受信データ:", data, flush=True)
    except Exception as e:
        print("⚠️ 受信エラー:", e, flush=True)
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS Webhook Server is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
