from flask import Flask, request

app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def webhook():
    data = request.json
    print("🔔 Webhook受信:", data)  # ← Webhook受信内容をログに表示
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS Webhook Server is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
