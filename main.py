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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY2")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# === DB初期化 ===
def init_db():
    try:
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            timestamp TEXT
        )
        ''')
        conn.commit()
        conn.close()
        print("✅ messagesテーブルを確認/作成完了", flush=True)
    except Exception as e:
        print("❌ DB初期化エラー:", e, flush=True)

# === メッセージ保存 ===
def save_message(user_id, message_text):
    try:
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute("INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)",
                       (user_id, message_text, timestamp))
        conn.commit()
        conn.close()
        print("💾 メッセージ保存完了", flush=True)
    except Exception as e:
        print("❌ メッセージ保存エラー:", e, flush=True)

# === アクセストークン取得 ===
def get_access_token():
    try:
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
            print("🔑 AccessToken取得成功", flush=True)
            return response.json()["access_token"]
        else:
            print("❌ アクセストークン取得失敗:", response.text, flush=True)
            return None
    except Exception as e:
        print("⚠️ アクセストークン処理エラー:", e, flush=True)
        return None

# === AI応答生成（429対応版） ===
def ask_ai(question):
    if not OPENAI_API_KEY:
        print("⚠️ OPENAI_API_KEYが設定されていません", flush=True)
        return "現在AIサービスは利用できません。"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは足つぼ反射区の専門家として答えます。"},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )

        # 予期せぬエラーフィールドがある場合は固定メッセージ
        if not hasattr(response, "choices") or len(response.choices) == 0:
            print("⚠️ OpenAI応答が不正です", flush=True)
            return "現在AIサーバーが利用制限中です。しばらく待ってからお試しください。"

        ai_reply = response.choices[0].message.content.strip()
        print(f"🤖 AI応答: {ai_reply}", flush=True)
        return ai_reply

    except Exception as e:
        print("⚠️ AIエラー:", e, flush=True)
        return "現在AIサーバーが利用制限中です。しばらく待ってからお試しください。"

# === ユーザーへ返信 ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        print("⚠️ アクセストークンなし、返信不可", flush=True)
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

# === Webhookエンドポイント ===
@app.route('/callback', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔔 Webhook受信データ:", data, flush=True)

        account_id = data["source"]["userId"]
        user_message = data["content"]["text"]
        print("📨 受信メッセージ:", user_message, flush=True)

        save_message(account_id, user_message)
        reply_message(account_id, user_message)

    except Exception as e:
        print("⚠️ 受信エラー:", e, flush=True)
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS Webhook Server is running."

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
