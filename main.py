from flask import Flask, request
import time
import jwt
import requests
import sqlite3
from datetime import datetime
import re

app = Flask(__name__)

# === LINE WORKS 認証情報 ===
CLIENT_ID = "e4LbDIJ47FULUbcfyQfJ"
SERVICE_ACCOUNT = "ty2ra.serviceaccount@yllc"
CLIENT_SECRET = "s4smYc7WnC"
BOT_ID = "6808645"
PRIVATE_KEY_PATH = "private_20250728164431.key"
TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

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

# === 反射区情報検索（関連語・部分一致対応） ===
def search_reflex_info(user_message):
    try:
        with open("formatted_reflex_text.txt", "r", encoding="utf-8") as file:
            text_data = file.read()

        text_lower = text_data.lower()
        user_input = user_message.strip().lower()

        # 複数の関連キーワードをスペース・記号区切りで分割
        keywords = re.split(r'[ ,、。]', user_input)

        # 最初にマッチした段落を返す
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
                result = text_data[start:end].strip()
                return result.replace("\\n", "\n")

        return None
    except Exception as e:
        print("❌ ファイル検索エラー:", e, flush=True)
        return None

# === ユーザーへ返信（反射区のみ対応） ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        return

    reply_text = search_reflex_info(message_text)

    if not reply_text:
        reply_text = "⚠️ 該当する反射区情報が見つかりませんでした。"

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
    return "LINE WORKS 反射区BOT サーバー稼働中"

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
