import json
import csv
from datetime import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
import time

load_dotenv()

# Gemini APIの設定
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print(GOOGLE_API_KEY)
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# APIの設定を更新
genai.configure(api_key=GOOGLE_API_KEY)

def load_references():
    """references.jsonから参照サイトの情報を読み込む"""
    with open('refs/references.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_today_date():
    """今日の日付をYYYY-MM-DD形式で取得"""
    return datetime.now().strftime('%Y-%m-%d')

def create_output_dir():
    """出力ディレクトリを作成"""
    output_dir = Path('daily_updates')
    output_dir.mkdir(exist_ok=True)
    return output_dir

def check_site_updates(site_info, today_date):
    """Geminiを使用してサイトの更新を確認"""
    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

    prompt = f"""
    以下のウェブサイトの最新の記事を確認し、{today_date}に公開または更新された記事があるか確認してください。
    結果は以下のJSON形式で返してください：

    {{
        "has_updates": true/false,
        "articles": [
            {{
                "title": "記事のタイトル",
                "url": "記事のURL",
                "published_date": "公開日（YYYY-MM-DD形式）"
            }}
        ]
    }}

    サイト情報:
    タイトル: {site_info['title']}
    URL: {site_info['url']}

    注意:
    1. 必ず有効なJSON形式で返してください。余分なテキストやマークダウン記号は含めないでください。
    2. 実際のウェブサイトの内容を確認できない場合は、以下の形式で返してください：
       {{
           "has_updates": false,
           "articles": []
       }}
    3. 説明や例示は不要です。JSONのみを返してください。
    """

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # デバッグ用に応答を表示
        print(f"API Response for {site_info['title']}:")
        print(response_text)

        # マークダウンのコードブロック記号を削除
        response_text = response_text.replace('```json', '').replace('```', '').strip()

        # JSONとして解析
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as je:
            print(f"JSON Parse Error for {site_info['title']}: {str(je)}")
            print(f"Raw response: {response_text}")
            return None

    except Exception as e:
        print(f"Error checking {site_info['title']}: {str(e)}")
        return None

def save_to_csv(updates, output_path):
    """更新情報をCSVファイルに保存"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Site Title', 'Article Title', 'URL'])
        for update in updates:
            writer.writerow(update)

def main():
    # 出力ディレクトリの作成
    output_dir = create_output_dir()
    today_date = get_today_date()
    output_file = output_dir / f'list_{today_date.replace("-", "")}.csv'

    # 参照サイトの読み込み
    references = load_references()

    # 更新情報を格納するリスト
    updates = []

    # 各サイトの更新を確認
    for category in references['blogs'].values():
        for site in category:
            print(f"Checking {site['title']}...")
            result = check_site_updates(site, today_date)

            if result and result.get('has_updates'):
                for article in result.get('articles', []):
                    updates.append([
                        site['title'],
                        article.get('title', ''),
                        article.get('url', '')
                    ])

            # API制限を考慮して待機（1分間に15リクエストの制限に対応）
            print("Waiting for 4 seconds before next request...")
            time.sleep(4)  # 5秒待機

    # 結果をCSVに保存
    if updates:
        save_to_csv(updates, output_file)
        print(f"Updates saved to {output_file}")
    else:
        print("No updates found for today.")

if __name__ == "__main__":
    main()