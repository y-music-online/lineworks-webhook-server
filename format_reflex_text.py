import re

input_file = "reflex_text.txt"
output_file = "formatted_reflex_text.txt"

with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

formatted_lines = []
current_keyword = ""
current_desc = ""

for line in lines:
    # 反射区名らしき行（漢字やカタカナ、ひらがなで始まる）
    if re.match(r'^[\u3040-\u30FF\u4E00-\u9FFFA-Za-z0-9]+', line):
        # すでに溜まっているデータがあれば保存
        if current_keyword:
            formatted_lines.append(f"{current_keyword} {current_desc.strip()}")
        # 新しいキーワード開始
        parts = line.split(maxsplit=1)
        current_keyword = parts[0]
        current_desc = parts[1] if len(parts) > 1 else ""
    else:
        # 説明文の続き
        current_desc += " " + line

# 最終行を追加
if current_keyword:
    formatted_lines.append(f"{current_keyword} {current_desc.strip()}")

# ファイルに書き込み
with open(output_file, "w", encoding="utf-8") as f:
    for line in formatted_lines:
        f.write(line + "\n")

print("✅ 整形が完了しました。'formatted_reflex_text.txt'を確認してください。")
