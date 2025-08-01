import os
import json
import time
import jwt
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

# ================================
# 設定読み込み
# ================================
load_dotenv()

SERVER_ID = os.getenv("SERVER_ID")
PRIVATE_KEY_FILE = os.getenv("PRIVATE_KEY_FILE", "private_2048.key")
BOT_ID = os.getenv("BOT_ID")
API_ID = os.getenv("API_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# ================================
# JWT生成関数
# ================================
def create_jwt():
    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key = f.read()

    headers = {
        "alg": "RS256",
        "typ": "JWT"
    }
    payload = {
        "iss": SERVER_ID,
        "sub": SERVER_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
    return token

# ================================
# AccessToken取得
# ================================
def get_access_token():
    url = "https://auth.worksmobile.com/oauth2/v2.0/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": create_jwt(),
        "client_id": API_ID
    }
    res = requests.post(url, headers=headers, data=data)
    return res.json().get("access_token")

# ================================
# AI応答生成
# ================================
def generate_ai_response(user_message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは親切で役立つアシスタントです。"},
                {"role": "user", "content": user_message}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("AI応答エラー:", e)
        return "AIによる回答を取得できませんでした。"

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
        "content": {
            "type": "text",
            "text": content
        }
    }
    requests.post(url, headers=headers, json=data)

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

        # AIの応答のみ利用
        reply_text = generate_ai_response(user_message)

        token = get_access_token()
        reply_message(token, BOT_ID, user_id, reply_text)

    return "OK", 200

# ================================
# メイン
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

