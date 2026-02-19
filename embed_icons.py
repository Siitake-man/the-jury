#!/usr/bin/env python3
"""
アイコン画像をBase64に変換してHTMLのsrc属性を書き換えるスクリプト
ローカルでもGitHub Pagesでも確実に表示されるようにする
"""
import base64
import re
from pathlib import Path

icons_dir = Path("/home/ubuntu/the-jury/assets/icons")
template_path = Path("/home/ubuntu/the-jury/template.html")

# 対象アイコン一覧
icon_files = {
    "ishibashi": icons_dir / "ishibashi.png",
    "zero":      icons_dir / "zero.png",
    "kokuji":    icons_dir / "kokuji.png",
    "packet":    icons_dir / "packet.png",
    "pure":      icons_dir / "pure.png",
    "kitsu":     icons_dir / "kitsu.png",
}

# Base64変換
b64 = {}
for name, path in icon_files.items():
    if path.exists():
        data = path.read_bytes()
        b64[name] = "data:image/png;base64," + base64.b64encode(data).decode()
        print(f"✅ {name}: {len(data):,} bytes → base64 {len(b64[name]):,} chars")
    else:
        print(f"❌ {name}: ファイルが見つかりません: {path}")

# テンプレートのsrc属性を置換
template = template_path.read_text(encoding="utf-8")

for name, data_uri in b64.items():
    # assets/icons/{name}.png を data URI に置換
    template = template.replace(f'src="assets/icons/{name}.png"', f'src="{data_uri}"')

template_path.write_text(template, encoding="utf-8")
print(f"\n✅ テンプレート更新完了: {template_path}")
print(f"   ファイルサイズ: {len(template):,} bytes")
