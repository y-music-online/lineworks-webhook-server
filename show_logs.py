# show_logs.py

import sqlite3

conn = sqlite3.connect("messages.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM messages ORDER BY id DESC")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}, User: {row[1]}, Message: {row[2]}, Time: {row[3]}")

conn.close()
