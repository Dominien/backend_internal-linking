from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import re

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes and origins by default

# Assuming the CSV file is preloaded or stored in memory
CSV_FILE = 'keyword_url_list.csv'

def load_keyword_url_pairs():
    try:
        df = pd.read_csv(CSV_FILE)
        if 'Keyword' not in df.columns or 'URL' not in df.columns:
            raise ValueError("CSV must contain 'Keyword' and 'URL' columns.")
        return df.to_dict('records')
    except Exception as e:
        return []

keyword_url_pairs = load_keyword_url_pairs()

def generate_hyperlinked_text(input_text, keyword_url_pairs, excluded_url):
    linked_keywords = set()
    url_link_count = {}

    keyword_url_pairs.sort(key=lambda x: len(x['Keyword']), reverse=True)

    def replace_keyword(match):
        keyword = match.group(0)
        for pair in keyword_url_pairs:
            url = pair['URL']
            if url == excluded_url:
                continue
            if (keyword.lower() == pair['Keyword'].lower() and 
                pair['Keyword'].lower() not in linked_keywords and 
                url_link_count.get(url, 0) < 2):
                
                linked_keywords.add(pair['Keyword'].lower())
                url_link_count[url] = url_link_count.get(url, 0) + 1
                return f'<a href="{url}">{keyword}</a>'
        return keyword

    pattern = r'\b(?:' + '|'.join(re.escape(pair['Keyword']) for pair in keyword_url_pairs) + r')\b'
    return re.sub(pattern, replace_keyword, input_text, flags=re.IGNORECASE)

@app.route('/process-text', methods=['POST'])
def process_text():
    data = request.json
    input_text = data.get('input_text', '')
    excluded_url = data.get('exclude_url', '')

    if not input_text:
        return jsonify({'error': 'No input text provided'}), 400

    hyperlinked_text = generate_hyperlinked_text(input_text, keyword_url_pairs, excluded_url)
    return jsonify({'hyperlinked_text': hyperlinked_text})

if __name__ == '__main__':
    app.run(debug=True)