import sqlite3

# DBファイルを作成（なければ自動生成されます）
conn = sqlite3.connect("messages.db")
cursor = conn.cursor()

# メッセージ保存用テーブル作成
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
print("✅ messages.db を作成しました")
