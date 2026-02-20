#!/usr/bin/env python3
"""
The Jury - 自動記事生成スクリプト（Gemini API版）
月・水・金に実行され、最新AIニュースを検索してクロスレビュー記事を自動生成する
"""
import os
import json
import re
import sys
import base64
import datetime
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import html as html_module
from pathlib import Path

# ===== 設定 =====
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jyikdveqhvimtyovkgbs.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_LQ-cUMnaam3q1muTdmqtVg_18H23SHM")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# ===== Gemini API呼び出し =====
def call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Gemini APIを呼び出してテキストを生成する"""
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 8192,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"❌ Gemini API エラー: {e.code} {e.read().decode()}")
        sys.exit(1)

# ===== 使用済みニュースの重複チェック =====
def load_used_news() -> list:
    """過去に使用したニュースタイトルのリストを読み込む"""
    used_file = Path(__file__).parent / "used_news.json"
    if used_file.exists():
        return json.loads(used_file.read_text(encoding="utf-8"))
    return []

def save_used_news(used: list, title: str):
    """使用したニュースタイトルを記録する（50件まで保持）"""
    used_file = Path(__file__).parent / "used_news.json"
    used.append(title)
    used_file.write_text(json.dumps(used[-50:], ensure_ascii=False, indent=2), encoding="utf-8")

# ===== Google News RSS取得 =====
def fetch_rss_candidates() -> list:
    """Google News RSSからAI関連ニュースを取得する"""
    query = urllib.parse.quote("AI 人工知能 生成AI LLM")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        items = root.findall(".//item")
        candidates = []
        for item in items[:20]:  # 上位20件を候補に
            title = html_module.unescape(item.findtext("title", ""))
            link = item.findtext("link", "")
            pub = item.findtext("pubDate", "")
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "不明"
            source_url = source_el.get("url", "") if source_el is not None else ""
            candidates.append({
                "title": title,
                "link": link,
                "pub": pub,
                "source": source,
                "source_url": source_url,
            })
        print(f"✅ Google News RSS取得完了: {len(candidates)}件")
        return candidates
    except Exception as e:
        print(f"⚠️ RSS取得失敗（Geminiフォールバックに切り替え）: {e}")
        return []

# ===== ニュース選抜（RSS + Gemini） =====
def fetch_top_ai_news() -> dict:
    """グーグルニュースRSSから候補を取得し、Geminiが最適な1件を選抜して記事内容を生成する"""
    today = datetime.date.today().strftime("%Y年%m月%d日")
    used_titles = load_used_news()

    # RSSから候補取得
    candidates = fetch_rss_candidates()

    # 重複除去
    candidates = [c for c in candidates if c["title"] not in used_titles]

    if candidates:
        # RSS候補をGeminiに渡して最適な1件を選抜させる
        candidate_list = "\n".join(
            [f"{i+1}. [{c['source']}] {c['title']} ({c['pub'][:16]})" for i, c in enumerate(candidates[:15])]
        )
        prompt = f"""
以下は今日（{today}）のAI関連ニュース一覧です。
日本のエンジニア・パーソンマネージャーが最も議論したくなる、賛否が分かれるトピックを1件選んで、記事内容を生成してください。

候補ニュース：
{candidate_list}

選抜したニュースの番号（selected_index）と記事内容を以下のJSON形式のみで回答：
{{
  "selected_index": 1,
  "title": "ニュースタイトル（日本語、30文字以内）",
  "title_html": "HTMLタイトル（キーワードを<span class=\\"ハイライト\\">tagで強調）",
  "hero_lead": "リード文（2。3行、HTMLの<br>タグ使用可）",
  "overview": "ニュースの背景・詳細の説明（3〆5文、読者がニュース内容を十分に理解できるように具体的に記述）",
  "summary_items": [
    "サマリ1（1。2文で要点を簡潔に）",
    "サマリ2（1。2文で要点を簡潔に）",
    "サマリ3（1。2文で要点を簡潔に）"
  ],
  "tags": [
    ["tag-hot", "タグ名1"],
    ["tag-tech", "タグ名2"],
    ["tag-biz", "タグ名3"]
  ],
  "news_summary_short": "Slack通知用の短い説明（50文字以内）"
}}
"""
        raw = call_gemini(prompt)
        # コードブロック（```json ... ```）にも対応
        raw_clean = re.sub(r'^```[\w]*\n?', '', raw.strip(), flags=re.MULTILINE)
        raw_clean = re.sub(r'```$', '', raw_clean.strip())
        match = re.search(r'\{{[\s\S]*\}}', raw_clean)
        if not match:
            print("❌ ニュース選抜失敗。レスポンス:", raw[:500])
            sys.exit(1)
        result = json.loads(match.group())

        # 選抜された候補のソース情報をマージ
        idx = result.get("selected_index", 1) - 1
        if 0 <= idx < len(candidates):
            selected = candidates[idx]
            result["source_name"] = selected["source"]
            result["source_url"] = selected["link"]
        else:
            result["source_name"] = candidates[0]["source"]
            result["source_url"] = candidates[0]["link"]

        # 使用済みに記録
        save_used_news(used_titles, result["title"])
        return result

    else:
        # RSSが使えない場合はGemini単独で生成（フォールバック）
        print("⚠️ RSS候補なし。Gemini単独でニュース生成。")
        used_str = "\n".join([f"- {t}" for t in used_titles[-10:]]) if used_titles else "なし"
        prompt = f"""
今日（{today}）時点で最もホットなAI関連ニュースを1件選んでください。
条件：直近1週間以内、日本のエンジニア・パーソンマネージャーが関心を持つ話題、議論を呼ぶトピック。

下記は過去に使用済みなので選ばないでください：
{used_str}

JSON形式のみで回答：
{{
  "title": "ニュースタイトル（日本語、30文字以内）",
  "title_html": "HTMLタイトル（キーワードを<span class=\\"ハイライト\\">tagで強調）",
  "hero_lead": "リード文（2。3行）",
  "overview": "ニュースの背景・詳細の説明（3〆5文、読者が内容を十分に理解できるように具体的に）",
  "summary_items": ["サマリ1", "サマリ2", "サマリ3"],
  "tags": [["tag-hot", "タグ名1"], ["tag-tech", "タグ名2"], ["tag-biz", "タグ名3"]],
  "news_summary_short": "Slack通知用の短い説明（50文字以内）",
  "source_name": "情報源メディア名",
  "source_url": "情報源URL"
}}
"""
        raw = call_gemini(prompt)
        # コードブロック（```json ... ```）にも対応
        raw_clean = re.sub(r'^```[\w]*\n?', '', raw.strip(), flags=re.MULTILINE)
        raw_clean = re.sub(r'```$', '', raw_clean.strip())
        match = re.search(r'\{{[\s\S]*\}}', raw_clean)
        if not match:
            print("❌ ニュース取得失敗。レスポンス:", raw[:500])
            sys.exit(1)
        result = json.loads(match.group())
        save_used_news(used_titles, result["title"])
        return result

# ===== クロスレビュー生成 =====
def generate_reviews(news: dict) -> dict:
    """6名のキャラクターによるクロスレビューを生成する"""
    prompt = f"""
あなたは「The Jury」というAIニュースレビューブログの編集AIです。
以下のAIニュースについて、6名のキャラクターそれぞれの視点でレビューを生成してください。

【ニュース】
タイトル: {news['title']}
要約: {' '.join(news['summary_items'])}

【キャラクター設定】
1. 石橋 叩（いしばし たたく）: 守旧派PM/50代。「昔はよかった」が口癖。新技術に懐疑的だが、現場視点では一理ある意見を言う。
2. コード・ゼロ: 天才ハッカー/20代。技術オタク。「技術は止まらない」。石橋を老害と思っている。
3. 黒字 策（くろじ はかる）: 冷徹コンサル/30代。「金になるか？」が判断基準。市場・ROI視点。
4. パケット守（ぱけっと まもる）: NW職人/40代。インフラ・現場実装の観点。「インフラが死んだら全部終わり」。
5. ピュア: 新人社員/20代女性。直感的に反応。「怖い」「便利そう」。読者の素朴な疑問を代弁。
6. 規律 正（きりつ ただし）: コンプラ担当/40代。法的リスクに敏感。「著作権」「情報漏洩」「GDPR/AI Act」。

【出力形式】
以下のJSON形式のみで回答してください（radarは不要、scoresとreviewsのみ）：
{{
  "scores": {{
    "ishibashi": 点数(1-10の整数),
    "zero": 点数(1-10の整数),
    "kokuji": 点数(1-10の整数),
    "packet": 点数(1-10の整数),
    "pure": 点数(1-10の整数),
    "kitsu": 点数(1-10の整数)
  }},
  "reviews": {{
    "ishibashi": "石橋のレビュー（350〜400文字、口語体、辛口）",
    "zero": "ゼロのレビュー（350〜400文字、口語体、技術的）",
    "kokuji": "黒字のレビュー（350〜400文字、口語体、ビジネス視点）",
    "packet": "パケットのレビュー（350〜400文字、口語体、インフラ視点）",
    "pure": "ピュアのレビュー（350〜400文字、口語体、素朴な疑問）",
    "kitsu": "規律のレビュー（350〜400文字、口語体、法的視点）"
  }}
}}
"""
    raw = call_gemini(prompt)
    # コードブロック（```json ... ```）にも対応
    raw_clean = re.sub(r'^```[\w]*\n?', '', raw.strip(), flags=re.MULTILINE)
    raw_clean = re.sub(r'```$', '', raw_clean.strip())
    match = re.search(r'\{[\s\S]*\}', raw_clean)
    if not match:
        print("❌ レビュー生成失敗。レスポンス:", raw[:500])
        sys.exit(1)
    result = json.loads(match.group())

    # radarデータはスコアから自動生成（APIに頼らず確実に生成）
    scores = result.get("scores", {})
    char_configs = [
        # (id, name, color, [技術革新性係数, ビジネス影響係数, リスク度係数, 社会的影響係数, 現場実用性係数, 倫理法的問題係数])
        # 各キャラクターの視点に応じた係数でスコアを変換
        ("ishibashi", "石橋 叩",   "#a1887f", [0.6, 0.8, 1.2, 0.9, 1.1, 0.8]),
        ("zero",      "コード・ゼロ", "#00d4ff", [1.3, 0.9, 0.7, 0.8, 1.1, 0.6]),
        ("kokuji",    "黒字 策",    "#ffd166", [0.8, 1.3, 0.9, 0.9, 0.9, 0.7]),
        ("packet",    "パケット守",  "#06d6a0", [1.0, 0.7, 1.1, 0.8, 1.3, 0.9]),
        ("pure",      "ピュア",     "#c77dff", [1.0, 1.0, 1.0, 1.1, 1.0, 0.9]),
        ("kitsu",     "規律 正",    "#4361ee", [0.7, 0.8, 1.3, 1.0, 0.8, 1.4]),
    ]
    radar = []
    for cid, cname, color, factors in char_configs:
        base = scores.get(cid, 5)
        data = [min(10, max(1, round(base * f))) for f in factors]
        radar.append({"name": cname, "color": color, "data": data})
    result["radar"] = radar
    return result

# ===== 座談会生成 =====
def generate_roundtable(news: dict, reviews: dict) -> dict:
    """6名による座談会（チャット形式）と格言を生成する"""
    # 各キャラクターのレビュー内容を座談会プロンプトに注入して姿勢の一貫性を保つ
    char_map = {
        "ishibashi": "石橋 叩",
        "zero":      "コード・ゼロ",
        "kokuji":    "黒字 策",
        "packet":    "パケット守",
        "pure":      "ピュア",
        "kitsu":     "規律 正",
    }
    scores = reviews.get("scores", {})
    review_texts = reviews.get("reviews", {})
    stance_summary = ""
    for cid, cname in char_map.items():
        score = scores.get(cid, "?")
        review = review_texts.get(cid, "")
        # レビューの先頭100文字を姿勢要約として使用
        summary = review[:100].replace('\n', '') + "…" if len(review) > 100 else review
        stance_summary += f"- {cname}（スコア{score}/10）: {summary}\n"

    prompt = f"""
あなたは「The Jury」というAIニュースレビューブログの編集AIです。
以下のニュースについて、6名による激論座談会（チャット形式）と格言を生成してください。

【ニュース】{news['title']}

【各キャラクターがレビューで表明した立場（必ずこの姿勢を座談会でも一貫させること）】
{stance_summary}
【ルール】
- 16ターン以上
- 上記の各キャラクターの立場を座談会でも必ず引き継ぐこと（レビューと矛盾しない）
- 意見の対立構造を作ること（特に「石橋 vs ゼロ」「黒字 vs 規律」）
- 石橋（老害）の意見は一見理不尽だが現場視点では一理ある内容にすること
- 最後はコンサル（黒字）かハッカー（ゼロ）が未来への示唆で強引に締めること
- 口語体で感情的に

【キャラID】ishibashi=石橋叩, zero=コードゼロ, kokuji=黒字策, packet=パケット守, pure=ピュア, kitsu=規律正

【出力形式】JSON形式のみで回答：
{{
  "chat_log": [
    ["キャラID", "left または right", "発言内容"],
    ...
  ],
  "quote": "本日の格言（読者の行動を促す一言、HTMLの<br>タグ使用可）"
}}

※ leftは左寄り（石橋・パケット・規律）、rightは右寄り（ゼロ・黒字・ピュア）
"""
    raw = call_gemini(prompt)
    # コードブロック（```json ... ```）にも対応
    raw_clean = re.sub(r'^```[\w]*\n?', '', raw.strip(), flags=re.MULTILINE)
    raw_clean = re.sub(r'```$', '', raw_clean.strip())
    match = re.search(r'\{[\s\S]*\}', raw_clean)
    if not match:
        print("❌ 座談会生成失敗。レスポンス:", raw[:500])
        sys.exit(1)
    return json.loads(match.group())

# ===== HTMLビルド =====
def build_html(vol_num: int, news: dict, reviews: dict, roundtable: dict) -> Path:
    """全データをテンプレートに埋め込んでHTMLを生成する"""
    template_path = Path(__file__).parent / "template.html"
    template = template_path.read_text(encoding="utf-8")

    # アイコンをBase64に変換
    icons_dir = Path(__file__).parent / "assets" / "icons"
    icon_b64 = {}
    for name in ["ishibashi", "zero", "kokuji", "packet", "pure", "kitsu"]:
        p = icons_dir / f"{name}.png"
        if p.exists():
            icon_b64[name] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
        else:
            icon_b64[name] = f"assets/icons/{name}.png"

    scores = reviews["scores"]
    total = round(sum(scores.values()) / len(scores), 1)
    today = datetime.date.today().strftime("%Y年%m月%d日")
    vol_str = f"Vol.{vol_num:03d}"
    article_id = f"vol{vol_num:03d}"

    # タグHTML
    tags_html = "\n    ".join(
        f'<span class="tag {cls}">{label}</span>'
        for cls, label in news.get("tags", [])
    )

    def pct(v): return int(v / 10 * 100)

    # 概要テキスト
    overview_html = news.get("overview", "")

    # サマリーアイテム
    summary_html = "\n      ".join(
        f"<li>{item}</li>" for item in news.get("summary_items", [])
    )

    # チャットログHTML
    char_names = {
        "ishibashi": "石橋 叩", "zero": "コード・ゼロ",
        "kokuji": "黒字 策", "packet": "パケット守",
        "pure": "ピュア", "kitsu": "規律 正",
    }
    chat_html_parts = []
    for char, side, text in roundtable.get("chat_log", []):
        name = char_names.get(char, char)
        icon_src = icon_b64.get(char, f"assets/icons/{char}.png")
        chat_html_parts.append(f"""      <div class="chat-msg {char} {side}">
        <img src="{icon_src}" alt="{name}" class="chat-icon">
        <div class="chat-bubble-wrap">
          <span class="chat-name">{name}</span>
          <div class="chat-bubble">{text}</div>
        </div>
      </div>""")
    chat_html = "\n".join(chat_html_parts)

    # レーダーチャートデータ
    radar_datasets = []
    for r in reviews.get("radar", []):
        radar_datasets.append({
            "label": r["name"],
            "data": r["data"],
            "borderColor": r["color"],
            "backgroundColor": r["color"] + "22",
            "borderWidth": 2,
            "pointBackgroundColor": r["color"],
            "pointRadius": 3,
        })

    # ソースリンク
    source_links = f'<a href="{news.get("source_url", "#")}" target="_blank" rel="noopener">{news.get("source_name", "参考記事")}</a>'
    source_badge = f'<a href="{news.get("source_url", "#")}" target="_blank" rel="noopener">{news.get("source_name", "参考記事")}</a>'

    # テンプレート置換
    html = template
    replacements = {
        "{{ARTICLE_TITLE}}": news["title"],
        "{{ARTICLE_TITLE_HTML}}": news.get("title_html", news["title"]),
        "{{ARTICLE_ID}}": article_id,
        "{{VOL_NUMBER}}": vol_str,
        "{{PUBLISH_DATE}}": today,
        "{{NEWS_SUMMARY_SHORT}}": news.get("news_summary_short", ""),
        "{{HERO_LEAD}}": news.get("hero_lead", ""),
        "{{TAGS_HTML}}": tags_html,
        "{{TOTAL_SCORE}}": str(total),
        "{{SCORE_ISHIBASHI}}": str(scores.get("ishibashi", 5)),
        "{{SCORE_ZERO}}": str(scores.get("zero", 5)),
        "{{SCORE_KOKUJI}}": str(scores.get("kokuji", 5)),
        "{{SCORE_PACKET}}": str(scores.get("packet", 5)),
        "{{SCORE_PURE}}": str(scores.get("pure", 5)),
        "{{SCORE_KITSU}}": str(scores.get("kitsu", 5)),
        "{{SCORE_ISHIBASHI_PCT}}": str(pct(scores.get("ishibashi", 5))),
        "{{SCORE_ZERO_PCT}}": str(pct(scores.get("zero", 5))),
        "{{SCORE_KOKUJI_PCT}}": str(pct(scores.get("kokuji", 5))),
        "{{SCORE_PACKET_PCT}}": str(pct(scores.get("packet", 5))),
        "{{SCORE_PURE_PCT}}": str(pct(scores.get("pure", 5))),
        "{{SCORE_KITSU_PCT}}": str(pct(scores.get("kitsu", 5))),
        "{{REVIEW_ISHIBASHI}}": reviews["reviews"].get("ishibashi", ""),
        "{{REVIEW_ZERO}}": reviews["reviews"].get("zero", ""),
        "{{REVIEW_KOKUJI}}": reviews["reviews"].get("kokuji", ""),
        "{{REVIEW_PACKET}}": reviews["reviews"].get("packet", ""),
        "{{REVIEW_PURE}}": reviews["reviews"].get("pure", ""),
        "{{REVIEW_KITSU}}": reviews["reviews"].get("kitsu", ""),
        "{{OVERVIEW}}": overview_html,
        "{{SUMMARY_ITEMS}}": summary_html,
        "{{CHAT_LOG_HTML}}": chat_html,
        "{{RADAR_DATA_JSON}}": json.dumps(radar_datasets, ensure_ascii=False),
        "{{QUOTE_TEXT}}": roundtable.get("quote", ""),
        "{{SOURCE_LINKS}}": source_links,
        "{{SOURCE_BADGE}}": source_badge,
        "{{SUPABASE_URL}}": SUPABASE_URL,
        "{{SUPABASE_ANON_KEY}}": SUPABASE_ANON_KEY,
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    out_path = Path(__file__).parent / f"vol{vol_num:03d}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path

# ===== 記事インデックス更新 =====
def update_index(vol_num: int, news: dict, total_score: float):
    """index.htmlの記事一覧に新しい記事を追加する"""
    index_path = Path(__file__).parent / "index.html"
    today = datetime.date.today().strftime("%Y年%m月%d日")
    vol_str = f"Vol.{vol_num:03d}"
    article_id = f"vol{vol_num:03d}"

    new_entry = f"""      <article class="article-card latest">
        <a href="{article_id}.html">
          <div class="card-top">
            <span class="card-vol">{vol_str}</span>
            <span class="badge-latest">LATEST</span>
            <span class="card-date">{today}</span>
          </div>
          <h2 class="card-title">{news['title']}</h2>
          <p class="card-summary">{news.get('news_summary_short', '')}</p>
          <div class="card-score-block">
            <div class="card-score-num">{total_score}</div>
            <div class="card-score-denom">/ 10</div>
            <div class="card-score-label">総合スコア</div>
          </div>
        </a>
      </article>"""

    if not index_path.exists():
        # index.htmlが存在しない場合は新規作成
        index_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI News Cross-Review "The Jury"</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #0d1117; color: #e6edf3; font-family: 'Noto Sans JP', sans-serif; padding: 40px 20px; }}
    .header {{ text-align: center; margin-bottom: 60px; }}
    .header h1 {{ font-size: 2rem; color: #ff4d4d; letter-spacing: 2px; }}
    .header p {{ color: #8b949e; margin-top: 10px; }}
    .articles {{ max-width: 900px; margin: 0 auto; display: grid; gap: 20px; }}
    .article-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; overflow: hidden; transition: transform 0.2s; }}
    .article-card:hover {{ transform: translateY(-4px); }}
    .article-card a {{ display: block; padding: 24px; text-decoration: none; color: inherit; }}
    .card-vol {{ font-size: 12px; color: #ff4d4d; font-weight: 700; margin-bottom: 8px; }}
    .card-title {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 10px; color: #e6edf3; }}
    .card-summary {{ font-size: 14px; color: #8b949e; margin-bottom: 16px; line-height: 1.6; }}
    .card-meta {{ display: flex; justify-content: space-between; font-size: 12px; color: #8b949e; }}
    .card-score {{ color: #ffd166; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>AI NEWS CROSS-REVIEW "THE JURY"</h1>
    <p>6名のAIキャラクターが最新AIニュースを辛口クロスレビュー</p>
  </div>
  <div class="articles">
{new_entry}
  </div>
</body>
</html>"""
        index_path.write_text(index_html, encoding="utf-8")
    else:
        # 既存のindex.htmlに記事を追加（最新が上に来るよう先頭に挿入）
        content = index_path.read_text(encoding="utf-8")
        # 既存のlatestバッジを履歴カードに変更（新しい記事が最新になるため）
        content = content.replace('article-card latest', 'article-card')
        content = content.replace('<span class="badge-latest">LATEST</span>', '')
        # 新しい記事を先頭に挿入
        content = content.replace(
            '<div class="articles">',
            f'<div class="articles">\n{new_entry}'
        )
        index_path.write_text(content, encoding="utf-8")

# ===== Slack通知 =====
def notify_slack(vol_num: int, news: dict, total_score: float, html_url: str):
    """Slackに新記事の通知を送信する"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL が未設定のためSlack通知をスキップします")
        return

    import urllib.request
    vol_str = f"Vol.{vol_num:03d}"
    today = datetime.date.today().strftime("%Y/%m/%d")

    # スコアバー（絵文字で表現）
    score_bar = "🟥" * int(total_score) + "⬜" * (10 - int(total_score))

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📰 AIニュースクロスレビュー {vol_str} 公開！",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{news['title']}*\n\n{news.get('news_summary_short', '')}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*総合スコア*\n{score_bar} {total_score}/10"},
                    {"type": "mrkdwn", "text": f"*公開日*\n{today}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🧱 石橋叩 vs 💻 ゼロ vs 💼 黒字策 vs 📡 パケット守 vs 🌱 ピュア vs ⚖️ 規律正\n6名の激論はブログで！"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📖 記事を読む", "emoji": True},
                        "url": html_url,
                        "style": "primary"
                    }
                ]
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"✅ Slack通知送信完了: {resp.status}")
    except Exception as e:
        print(f"⚠️ Slack通知失敗（記事生成は成功）: {e}")

# ===== 記事番号の自動採番 =====
def get_next_vol_num() -> int:
    """既存のvolXXX.htmlファイルを確認して次の番号を返す"""
    base = Path(__file__).parent
    existing = list(base.glob("vol*.html"))
    if not existing:
        return 2  # vol001はサンプルとして存在するので002から
    nums = []
    for f in existing:
        m = re.match(r'vol(\d+)\.html', f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 2

# ===== メイン処理 =====
def main():
    print("=" * 50)
    print("🚀 The Jury - 自動記事生成開始")
    print("=" * 50)

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY が設定されていません")
        sys.exit(1)

    # 1. 次の記事番号を決定
    vol_num = get_next_vol_num()
    print(f"\n📌 生成する記事: Vol.{vol_num:03d}")

    # 2. ニュース取得
    print("\n🔍 最新AIニュースを検索中...")
    news = fetch_top_ai_news()
    print(f"✅ ニュース取得: {news['title']}")

    # 3. クロスレビュー生成
    print("\n✍️  6名のクロスレビューを生成中...")
    reviews = generate_reviews(news)
    scores = reviews["scores"]
    total = round(sum(scores.values()) / len(scores), 1)
    print(f"✅ レビュー生成完了（総合スコア: {total}/10）")

    # 4. 座談会生成
    print("\n💬 激論！座談会を生成中...")
    roundtable = generate_roundtable(news, reviews)
    print(f"✅ 座談会生成完了（{len(roundtable.get('chat_log', []))}ターン）")

    # 5. HTML生成
    print("\n🔨 HTMLを生成中...")
    out_path = build_html(vol_num, news, reviews, roundtable)
    print(f"✅ HTML生成完了: {out_path}")

    # 6. インデックス更新
    print("\n📋 記事インデックスを更新中...")
    update_index(vol_num, news, total)
    print("✅ インデックス更新完了")

    # 7. Slack通知
    print("\n📣 Slack通知を送信中...")
    blog_url = f"https://siitake-man.github.io/the-jury/vol{vol_num:03d}.html"
    notify_slack(vol_num, news, total, blog_url)

    print("\n" + "=" * 50)
    print(f"🎉 完了！ Vol.{vol_num:03d} を公開しました")
    print(f"   URL: {blog_url}")
    print("=" * 50)

if __name__ == "__main__":
    main()
