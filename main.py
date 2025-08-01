from flask import Flask, request
import time
import jwt
import requests
import sqlite3
from datetime import datetime
import re
import openai
import os

app = Flask(__name__)

# === LINE WORKS 認証情報 ===
CLIENT_ID = "e4LbDIJ47FULUbcfyQfJ"
SERVICE_ACCOUNT = "ty2ra.serviceaccount@yllc"
CLIENT_SECRET = "s4smYc7WnC"
BOT_ID = "6808645"
PRIVATE_KEY_PATH = "private_20250728164431.key"
TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

# === OpenAI APIキーをRender環境変数から読み込む ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === DB初期化 ===
def init_db():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        message TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

# === メッセージ保存 ===
def save_message(user_id, message_text):
    try:
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)",
                       (user_id, message_text, datetime.now().isoformat()))
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

# === 反射区情報検索 ===
def search_reflex_info(user_message):
    try:
        with open("formatted_reflex_text.txt", "r", encoding="utf-8") as file:
            text_data = file.read()

        text_lower = text_data.lower()
        keywords = re.split(r'[ ,、。]', user_message.strip().lower())

        for kw in keywords:
            if not kw:
                continue
            idx = text_lower.find(kw)
            if idx != -1:
                start = text_data.rfind("\n\n", 0, idx)
                if start == -1:
                    start = 0
                end = text_data.find("\n\n", idx)
                if end == -1:
                    end = len(text_data)
                return text_data[start:end].strip().replace("\\n", "\n")
        return None
    except Exception as e:
        print("❌ ファイル検索エラー:", e)
        return None

# === ChatGPTを使った回答生成 ===
def ask_chatgpt(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは足つぼ反射区の専門家です。質問に日本語で答えてください。"},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print("❌ ChatGPTエラー:", e)
        return "AIによる回答を取得できませんでした。"

# === ユーザーへ返信 ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        return

    # まず反射区データを検索
    reply_text = search_reflex_info(message_text)

    # 見つからなければChatGPTに質問
    if not reply_text:
        reply_text = ask_chatgpt(message_text)

    url = f"https://www.worksapis.com/v1.0/bots/{BOT_ID}/users/{account_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "content": {
            "type": "text",
            "text": reply_text
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print("📩 返信ステータス:", response.status_code, flush=True)
    print("📨 返信レスポンス:", response.text, flush=True)

# === Webhookエンドポイント ===
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
    return "LINE WORKS 反射区BOT（ChatGPT対応版）サーバー稼働中"

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
