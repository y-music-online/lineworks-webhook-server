from flask import Flask, request
import time
import jwt
import requests
import sqlite3
from datetime import datetime


app = Flask(__name__)


# === LINE WORKS 開発者コンソールで取得した情報 ===
CLIENT_ID = "e4LbDIJ47FULUbcfyQfJ"
SERVICE_ACCOUNT = "ty2ra.serviceaccount@yllc"
CLIENT_SECRET = "s4smYc7WnC"
BOT_ID = "6808645"
PRIVATE_KEY_PATH = "private_20250728164431.key"
TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

DATA_FILE = "formatted_reflex_text.txt"  # 整形済みのテキストファイル

# === 反射区データ読み込み ===
def load_reflex_data():
    reflex_map = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    reflex_map[parts[0]] = parts[1]
    except Exception as e:
        print("⚠️ 反射区データ読み込みエラー:", e)
    return reflex_map

# === DB保存 ===
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
    payload = {"iss": CLIENT_ID, "sub": SERVICE_ACCOUNT, "iat": iat, "exp": exp, "aud": TOKEN_URL}
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

# === ユーザーへの返信 ===
def reply_message(account_id, message_text):
    access_token = get_access_token()
    if not access_token:
        return

       # ユーザー入力を整形（全角スペース削除・小文字化）
    user_message = message_text.strip().replace(" ", "").lower()

    # 反射区検索
    reply_text = "⚠️ 該当する反射区情報が見つかりませんでした。"
    for reflex, info in reflex_map.items():
        if reflex.replace(" ", "").lower() in user_message:
            reply_text = f"🔎 {reflex}の反射区情報:\n{info}"
            break

    # 返信送信

    url = f"https://www.worksapis.com/v1.0/bots/{BOT_ID}/users/{account_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    requests.post(url, headers=headers, json={
        "content": {"type": "text", "text": reply_text}
    })
    print("📩 BOT返信完了", flush=True)

# === Webhook ===
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
    app.run(host='0.0.0.0', port=10000)