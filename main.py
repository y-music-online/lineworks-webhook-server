from flask import Flask, request
import time
import jwt
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

# === LINE WORKS 認証情報 ===
CLIENT_ID = "e4LbDIJ47FULUbcfyQfJ"
SERVICE_ACCOUNT = "ty2ra.serviceaccount@yllc"
CLIENT_SECRET = "s4smYc7WnC"
BOT_ID = "6808645"
PRIVATE_KEY_PATH = "private_20250728164431.key"
TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

# === データファイル ===
DATA_FILE = "formatted_reflex_text.txt"
reflex_map = {}

# === DB初期化 ===
def init_db():
    try:
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
        print("✅ DB初期化完了", flush=True)
    except Exception as e:
        print("❌ DB初期化エラー:", e, flush=True)

# === 反射区データ読み込み ===
def load_reflex_data():
    reflex_map = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    reflex_map[parts[0]] = parts[1]
        print(f"✅ 反射区データ {len(reflex_map)} 件読み込み", flush=True)
    except FileNotFoundError:
        print("❌ 反射区データファイルが見つかりません", flush=True)
    return reflex_map

# === メッセージ保存 ===
def save_message(user_id, message):
    try:
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)",
            (user_id, message, datetime.now().isoformat())
        )
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
            return response.json()["access_token"]
        else:
            print("❌ アクセストークン取得失敗:", response.text, flush=True)
            return None
    except Exception as e:
        print("❌ get_access_tokenエラー:", e, flush=True)
        return None


# === ファイルからキーワード検索（名前と説明文の両方を対象） ===
def search_reflex_info(user_message):
    try:
        with open("formatted_reflex_text.txt", "r", encoding="utf-8") as file:
            text_data = file.read()

        keyword = user_message.strip().lower()
        idx = text_data.lower().find(keyword)
        if idx != -1:
            start = max(0, text_data.rfind("\n\n", 0, idx))
            end = text_data.find("\n\n", idx)
            return text_data[start:end].strip()
        return "⚠️ 該当する反射区情報が見つかりませんでした。"
    except Exception as e:
        print("❌ ファイル検索エラー:", e, flush=True)
        return "⚠️ データ読み込みエラーが発生しました。"



# === BOTから返信 ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        return

    reply_text = search_reflex_info(message_text)

 reply_text = reply_text.replace("\\n", "\n")

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

# === Webhook受信 ===
@app.route('/callback', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔔 Webhook受信データ:", data, flush=True)

        account_id = data.get("source", {}).get("userId")
        user_message = data.get("content", {}).get("text")
        if not account_id or not user_message:
            print("⚠️ account_id または user_message が取得できません", flush=True)
            return "NG", 400

        save_message(account_id, user_message)
        reply_message(account_id, user_message)

    except Exception as e:
        print("⚠️ 受信エラー:", e, flush=True)
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    return "LINE WORKS 反射区BOT サーバー稼働中"

# --- サーバー起動処理 ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)