from flask import Flask, request

app = Flask(__name__)

# LINE WORKS の Webhook POST を受け取るエンドポイント
@app.route('/callback', methods=['POST'])
def webhook():
    data = request.json
    print("🔔 Webhook受信:", data)
    return "OK", 200

# 動作確認用（ブラウザで開いたときに表示）
@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS Webhook Server is running."

# サーバー起動
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

