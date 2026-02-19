#!/usr/bin/env python3
"""
The Jury - Article Builder
テンプレートにコンテンツを埋め込んで記事HTMLを生成するスクリプト
"""
import json
import re
from pathlib import Path

# ===== 記事データ =====
article = {
    "vol": "Vol.001",
    "article_id": "vol001-seedance2",
    "publish_date": "2026年2月19日",
    "title": "【衝撃】中国発AI「Seedance 2.0」がハリウッドを破壊する日",
    "title_html": '【衝撃】中国発AI「<span class="highlight">Seedance 2.0</span>」がハリウッドを破壊する日',
    "hero_lead": "ByteDanceが放った動画生成AIが、ハリウッドと日本のアニメ業界を同時に震撼させた。<br>テキスト2行でトム・クルーズが動き出す——これはもう、映画産業の終わりの始まりなのか？",
    "news_summary_short": "ByteDance「Seedance 2.0」が著作権侵害問題でハリウッドを震撼。6名のAIキャラが辛口クロスレビュー。",
    "tags": [
        ("tag-hot", "衝撃"),
        ("tag-copyright", "著作権"),
        ("tag-regulation", "AI規制"),
    ],
    "scores": {
        "ishibashi": 4,
        "zero": 9,
        "kokuji": 8,
        "packet": 6,
        "pure": 7,
        "kitsu": 5,
    },
    "reviews": {
        "ishibashi": "また妙な新技術か。Seedance 2.0？名前だけ聞くとハイテクだが、実態は不安定な動画生成AIで、現場で使えるわけがない。著作権侵害の問題も含めて、まだ時期尚早だ。安定稼働や品質管理が最優先の現場にこんなリスクの高い技術を持ち込むのは愚策だ。現場を知らない若造たちが騒いでいるだけで、実績がない技術に踊らされるな。ハリウッドが怒るのは当然だろう。昔も「デジタル革命で映画は変わる」と騒いで、結局現場は混乱した。堅実に既存の方法でやるのが一番安全だ。誰が責任取るんだ？",
        "zero": "Seedance 2.0のアーキテクチャ、マジでヤバい。Diffusion Transformerベースで時間軸の一貫性を保ちながら15秒の動画を生成できるって、昔のCGパイプラインが泣くレベル。テキスト2行でトム・クルーズが動き出すって、これ実装したら神じゃないですか。著作権侵害問題？そんなのは技術の進化の副作用に過ぎない。石橋みたいな老害はレガシーに固執して未来を見ていない。まだ手作業でCG合成やってるんですか？SeedanceのAPIが公開されたら、俺たちが新しいエンタメを作り直す。これが本当のゲームチェンジャーだ。",
        "kokuji": "Seedance 2.0は単なる技術ではない。これはコンテンツ産業の覇権構造を根底から変えるゲームチェンジャーだ。ハリウッドの映画制作コストは平均1億ドル超——それがテキスト数行で代替可能になる世界のROIを考えてみろ。著作権問題はリスクだが、それを乗り越えた先に莫大な市場が待っている。ByteDanceはDisneyとOpenAIが結んだようなライセンス契約モデルを急いで構築すべきだ。競合が死ぬ前に、先に手を打て。法的摩擦は一時的な障害に過ぎない——重要なのは誰が最初にコンテンツ供給プラットフォームの覇権を握るかだ。",
        "packet": "リアルタイム動画生成はネットワーク帯域とレイテンシの観点で非常に厳しい。15秒の動画生成でどれだけのGPUリソースとI/Oが必要か考えたことあるか？Seedance 2.0のクラウド依存度が高いなら、オンプレミスでのSLA確保は絶望的に見える。動画の品質と安定性は通信品質に直結するから、企業現場での採用はかなり慎重にならざるを得ない。クラウドの障害耐性は？帯域が許容範囲外になった時の対処は？通信インフラの整備が追いつかない限り、現場での実用化は遠い話だ。技術が凄くても、インフラが死んだら全部終わりだ。",
        "pure": "Seedance 2.0ってすごく便利そうだけど、なんだか怖いですね…。好きな俳優さんやアニメのキャラクターが勝手に使われてるって聞くと、ちょっとモヤモヤします。「Deadpool」の脚本家さんが「もう終わりだ」って言ったって本当ですか？え、私の仕事もなくなる？動画制作の仕事って、これからどうなるんだろう。でも、こんなに簡単に動画が作れるなら、社内の資料作りとかには使えそう…。なんか凄そう！でも本当に大丈夫なのかな？",
        "kitsu": "Seedance 2.0の無断キャラクター利用は明確な著作権侵害であり、法的リスクは極めて高い。MPAの声明にある通り「大規模な著作権侵害」は米国法上の損害賠償額が天文学的になりうる。さらにEUのAI Actの観点からも、学習データの透明性開示義務や生成コンテンツへのウォーターマーク要件に抵触する可能性が高い。日本では著作権法30条の4の「情報解析目的」の適用範囲が問われる。企業が安易にこの技術を導入すれば訴訟リスクは避けられず、ブランド毀損にも繋がる。ガバナンスが効かない技術は使ってはいけない。",
    },
    "summary_items": [
        "TikTok親会社ByteDanceが開発した動画生成AI「Seedance 2.0」が、テキスト指示だけで映画品質のリアル動画を生成できるとして世界的に話題となった。",
        "有名俳優（トム・クルーズ、ブラッド・ピット）やディズニーキャラクター、日本のアニメキャラを無断使用した動画がSNSに溢れ、ハリウッドのMPA・SAG-AFTRAが強烈に反発。",
        "ディズニー・パラマウントがByteDanceに停止通告書を送付し、日本のNAFCAも問い合わせを実施。著作権・AI倫理をめぐる国際的な法的闘争へと発展しつつある。",
    ],
    "chat_log": [
        ("ishibashi", "left", "またこんな新技術か。Seedance 2.0？現場で使えるかって話だよ。著作権問題は深刻だし、安定もしていない。現場の混乱を考えたら、こんなものは時期尚早だって言いたいね。昔も「CGで映画が変わる」って騒いで、結局現場は大混乱だったじゃないか。"),
        ("zero", "right", "はあ？石橋さん、その考えは古すぎる。SeedanceのDiffusion Transformerアーキテクチャは既に完成度が高い。テキスト2行でトム・クルーズが動き出すんですよ？技術を怖がってどうするんだよ。まだ手作業でCG合成やってるんですか？"),
        ("ishibashi", "left", "技術だけじゃ飯は食えんよ。現場は安定第一。若造がコードだけで語っても現場の苦労はわからんだろうな。で、誰が著作権侵害の責任取るんだ？お前か？"),
        ("kokuji", "right", "安定も大事だが、それ以上に市場を取ることが急務だ。Seedanceの潜在力は巨大で、法的リスクもビジネス戦略で乗り越えられる。DisneyとOpenAIがやったようなライセンス契約モデルを構築すれば、これは金になる。競合が死ぬな。"),
        ("kitsu", "left", "待て。無断利用は著作権侵害で訴訟リスクが高い。MPAの声明では「大規模な著作権侵害」と明言されている。EU AI Actの学習データ透明性要件にも抵触する。法的基盤が整わなければ、いくらROIが良くても企業は損失を被る。ガバナンスが効かない。"),
        ("zero", "right", "法は技術の進化に追いついていないだけ。技術は止まらない。規律さんの言うこともわかるが、イノベーションは混乱なしには語れない。Sora 2の時も同じ議論したじゃないですか。"),
        ("packet", "left", "技術の話に戻すと、リアルタイム動画生成はネットワークの帯域とレイテンシで足を引っ張られる。クラウド依存ならオンプレ現場ではまともなSLAが出せないぞ。15秒の動画生成でどれだけのGPUリソースが必要か、誰か計算したか？"),
        ("pure", "right", "あの…便利そうだけど、勝手にキャラを使うのは怖いなあ…。「Deadpool」の脚本家さんが「もう終わりだ」って言ったって本当ですか？え、私の仕事もなくなる？"),
        ("ishibashi", "left", "ピュア君の言う通りだ。倫理も守れない技術は結局現場で嫌われる。実績のない技術を急いで採用すれば、結局はトラブルの元だぞ。昔も似たようなことがあって失敗した。焦る必要はない。"),
        ("kokuji", "right", "石橋さん、「昔も失敗した」って何の話ですか。CGの登場で映画産業は縮小しましたか？むしろ市場規模は拡大した。市場の勝者がルールを作るんです。Seedanceのような技術が覇権を握れば、業界ルールも変わる。先行者利益を取るのが正解だ。"),
        ("kitsu", "left", "黒字さん、法改正は必須で、無秩序な利用は業界全体の信用を失う。コンプラ無視は長期的に見て自殺行為だ。日本でも小野田大臣が「看過できない」と発言している。政府が動き始めたら、規制は一気に厳しくなるぞ。"),
        ("zero", "right", "規律さんも石橋さんも古い頭だな。技術が先に進むんだよ。今守ってたら未来はない。Seedanceのコード見たらわかる、自由度が段違いだ。これを使いこなせる人間が次の時代を作る。"),
        ("packet", "left", "自由度もいいが、インフラが追いつかないと宝の持ち腐れだ。現場のネットワーク整備とGPUリソースの確保とセットで考えないと、どんな革命的な技術も動かない。遅延が許容範囲外だ。"),
        ("pure", "right", "みんな意見が違って面白い…。でも自分ももっと勉強しないと、この技術の良さも怖さもわからないな。とりあえずSeedanceで何か作ってみようかな…著作権的に大丈夫なやつで。"),
        ("kokuji", "right", "まとめると、Seedance 2.0は技術革新とビジネスチャンスの両面を持つ。リスクはある。だが積極的に攻めない限り市場で負ける。ByteDanceはライセンス交渉を急ぎ、我々は自社コンテンツへの応用を今すぐ検討すべきだ。未来は強者が作るんだ。"),
        ("zero", "right", "そうだ。石橋も規律も古い常識に縛られてるだけ。俺たち若い世代がSeedanceのAPIを武器に、次の時代のエンタメを創っていく。コードを書けばわかる——これは止められない革命だ。乗り遅れるな。"),
    ],
    "quote": "「技術革新はリスクとチャンスの二刀流。<br>恐れず挑まなければ、未来は奪われる。」",
    "sources": [
        ("TechCrunch", "https://techcrunch.com/"),
        ("ITmedia AI+", "https://www.itmedia.co.jp/aiplus/"),
    ],
    # レーダーチャートデータ（各キャラの6軸評価）
    # 軸: 技術革新性, ビジネス影響, リスク度, 社会的影響, 現場実用性, 倫理・法的問題
    "radar": [
        {"name": "石橋 叩", "color": "#a1887f", "data": [2, 3, 8, 5, 7, 6]},
        {"name": "コード・ゼロ", "color": "#00d4ff", "data": [10, 8, 2, 7, 9, 2]},
        {"name": "黒字 策", "color": "#ffd166", "data": [8, 10, 5, 7, 6, 4]},
        {"name": "パケット守", "color": "#06d6a0", "data": [6, 5, 7, 5, 4, 5]},
        {"name": "ピュア", "color": "#c77dff", "data": [7, 6, 6, 8, 7, 7]},
        {"name": "規律 正", "color": "#4361ee", "data": [4, 3, 10, 8, 3, 10]},
    ],
    "supabase_url": "https://jyikdveqhvimtyovkgbs.supabase.co",
    "supabase_anon_key": "sb_publishable_LQ-cUMnaam3q1muTdmqtVg_18H23SHM",
}

# ===== ビルド処理 =====
def build():
    import base64
    template = Path("/home/ubuntu/the-jury/template.html").read_text(encoding="utf-8")

    # アイコンをBase64に変換
    icons_dir = Path("/home/ubuntu/the-jury/assets/icons")
    icon_b64 = {}
    for name in ["ishibashi", "zero", "kokuji", "packet", "pure", "kitsu"]:
        p = icons_dir / f"{name}.png"
        if p.exists():
            icon_b64[name] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
        else:
            icon_b64[name] = f"assets/icons/{name}.png"

    scores = article["scores"]
    total = round(sum(scores.values()) / len(scores), 1)

    # タグHTML
    tags_html = "\n    ".join(
        f'<span class="tag {cls}">{label}</span>'
        for cls, label in article["tags"]
    )

    # スコアバーのパーセント
    def pct(v): return int(v / 10 * 100)

    # サマリーアイテム
    summary_html = "\n      ".join(
        f"<li>{item}</li>" for item in article["summary_items"]
    )

    # チャットログHTML
    char_names = {
        "ishibashi": "石橋 叩",
        "zero": "コード・ゼロ",
        "kokuji": "黒字 策",
        "packet": "パケット守",
        "pure": "ピュア",
        "kitsu": "規律 正",
    }
    chat_html_parts = []
    for char, side, text in article["chat_log"]:
        name = char_names[char]
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
    for r in article["radar"]:
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
    source_links = " / ".join(
        f'<a href="{url}" target="_blank" rel="noopener">{name}</a>'
        for name, url in article["sources"]
    )

    # テンプレート置換
    html = template
    replacements = {
        "{{ARTICLE_TITLE}}": article["title"],
        "{{ARTICLE_TITLE_HTML}}": article["title_html"],
        "{{ARTICLE_ID}}": article["article_id"],
        "{{VOL_NUMBER}}": article["vol"],
        "{{PUBLISH_DATE}}": article["publish_date"],
        "{{NEWS_SUMMARY_SHORT}}": article["news_summary_short"],
        "{{HERO_LEAD}}": article["hero_lead"],
        "{{TAGS_HTML}}": tags_html,
        "{{TOTAL_SCORE}}": str(total),
        "{{SCORE_ISHIBASHI}}": str(scores["ishibashi"]),
        "{{SCORE_ZERO}}": str(scores["zero"]),
        "{{SCORE_KOKUJI}}": str(scores["kokuji"]),
        "{{SCORE_PACKET}}": str(scores["packet"]),
        "{{SCORE_PURE}}": str(scores["pure"]),
        "{{SCORE_KITSU}}": str(scores["kitsu"]),
        "{{SCORE_ISHIBASHI_PCT}}": str(pct(scores["ishibashi"])),
        "{{SCORE_ZERO_PCT}}": str(pct(scores["zero"])),
        "{{SCORE_KOKUJI_PCT}}": str(pct(scores["kokuji"])),
        "{{SCORE_PACKET_PCT}}": str(pct(scores["packet"])),
        "{{SCORE_PURE_PCT}}": str(pct(scores["pure"])),
        "{{SCORE_KITSU_PCT}}": str(pct(scores["kitsu"])),
        "{{REVIEW_ISHIBASHI}}": article["reviews"]["ishibashi"],
        "{{REVIEW_ZERO}}": article["reviews"]["zero"],
        "{{REVIEW_KOKUJI}}": article["reviews"]["kokuji"],
        "{{REVIEW_PACKET}}": article["reviews"]["packet"],
        "{{REVIEW_PURE}}": article["reviews"]["pure"],
        "{{REVIEW_KITSU}}": article["reviews"]["kitsu"],
        "{{SUMMARY_ITEMS}}": summary_html,
        "{{CHAT_LOG_HTML}}": chat_html,
        "{{RADAR_DATA_JSON}}": json.dumps(radar_datasets, ensure_ascii=False),
        "{{QUOTE_TEXT}}": article["quote"],
        "{{SOURCE_LINKS}}": source_links,
        "{{SUPABASE_URL}}": article["supabase_url"],
        "{{SUPABASE_ANON_KEY}}": article["supabase_anon_key"],
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    out_path = Path("/home/ubuntu/the-jury/vol001.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 生成完了: {out_path}")
    print(f"   総合スコア: {total}/10")

if __name__ == "__main__":
    build()
