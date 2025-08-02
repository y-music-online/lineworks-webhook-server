import os
import json
import time
import jwt
import requests
from flask import Flask, request
from dotenv import load_dotenv

# ================================
# 設定読み込み
# ================================
load_dotenv()

SERVER_ID = os.getenv("SERVER_ID")
PRIVATE_KEY_FILE = os.getenv("PRIVATE_KEY_FILE", "private_20250728164431.key")
BOT_ID = os.getenv("BOT_ID")
API_ID = os.getenv("API_ID")

app = Flask(__name__)

# ================================
# JWT生成
# ================================
def create_jwt():
    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key = f.read()
    payload = {
        "iss": SERVER_ID,
        "sub": SERVER_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60,
    }
    headers = {"alg": "RS256", "typ": "JWT"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)

# ================================
# AccessToken取得
# ================================
def get_access_token():
    url = "https://auth.worksmobile.com/oauth2/v2.0/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": create_jwt(),
        "client_id": API_ID
    }
    res = requests.post(url, headers=headers, data=data)
    return res.json().get("access_token")

# ================================
# メッセージ返信
# ================================
def reply_message(access_token, bot_id, account_id, content):
    url = f"https://www.worksapis.com/v1.0/bots/{bot_id}/users/{account_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "content": {"type": "text", "text": content}
    }
    response = requests.post(url, headers=headers, json=data)
    print("📩 返信ステータス:", response.status_code)
    print("📨 返信レスポンス:", response.text)

# ================================
# Webhookエンドポイント
# ================================
@app.route("/callback", methods=["POST"])
def callback():
    body = request.json
    print("🔔 Webhook受信データ:", body)

    if body["type"] == "message":
        user_id = body["source"]["userId"]
        user_message = body["content"]["text"]

        print(f"📨 受信メッセージ: {user_message}")

        # 固定メッセージを返信
        token = get_access_token()
        reply_message(token, BOT_ID, user_id, "✅ Webhook受信OK")

    return "OK", 200

# ================================
# メイン
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
