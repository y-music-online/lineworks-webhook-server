from flask import Flask, request
import time
import jwt
import requests
import sqlite3
from datetime import datetime
import os
from openai import OpenAI

app = Flask(__name__)

# === LINE WORKS 認証情報 ===
CLIENT_ID = "e4LbDIJ47FULUbcfyQfJ"
SERVICE_ACCOUNT = "ty2ra.serviceaccount@yllc"
CLIENT_SECRET = "s4smYc7WnC"
BOT_ID = "6808645"
PRIVATE_KEY_PATH = "private_20250728164431.key"
TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

# === OpenAI API設定 ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === DB保存関数 ===
def save_message(user_id, message_text):
    try:
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)",
            (user_id, message_text, timestamp)
        )
        conn.commit()
        conn.close()
        print("💾 メッセージ保存完了")
    except Exception as e:
        print("❌ メッセージ保存エラー:", e)

# === アクセストークン取得 ===
def get_access_token():
    iat = int(time.time())
    exp = iat + 3600
    payload = {
        "iss": CLIENT_ID,
        "sub": SERVICE_ACCOUNT,
        "iat": iat,
        "exp": exp,
        "aud": TOKEN_URL
    }
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = f.read()
    jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode('utf-8')

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "bot"
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("❌ アクセストークン取得失敗:", response.text, flush=True)
        return None

# === AIに質問を送信 ===
def ask_ai(question):
    prompt = f"""
あなたは足つぼ反射区の専門家です。
ユーザーからの質問に対して、足つぼや反射区に関連する情報を日本語で丁寧に答えてください。
反射区に関係ない質問が来た場合は「このBOTは足つぼ反射区に関する質問専用です」と答えてください。

質問:
{question}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは足つぼ反射区の専門家として答えます。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("AIエラー:", e)
        return "⚠️ AIによる回答を取得できませんでした。"

# === ユーザーへ返信 ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        return

    ai_reply = ask_ai(message_text)

    url = f"https://www.worksapis.com/v1.0/bots/{BOT_ID}/users/{account_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "content": {
            "type": "text",
            "text": ai_reply
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print("📩 返信ステータス:", response.status_code, flush=True)
    print("📨 返信レスポンス:", response.text, flush=True)

# === Webhook受信エンドポイント ===
@app.route('/callback', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔔 Webhook受信データ:", data, flush=True)

        account_id = data["source"]["userId"]
        user_message = data["content"]["text"]
        save_message(account_id, user_message)
        reply_message(account_id, user_message)

    except Exception as e:
        print("⚠️ 受信エラー:", e, flush=True)
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS Webhook Server is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
