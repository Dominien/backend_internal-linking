from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import re
import openai

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes and origins by default

# Initialize OpenAI client with the API key (replace 'your-openai-api-key' with your actual API key)
class OpenAIClient:
    def __init__(self, api_key):
        self.client = openai
        self.client.api_key = api_key
    
    def generate_keywords(self, urls, model="gpt-4o-mini"):
        prompt = (
            "Given the following URLs, please generate a list of relevant keywords that would be "
            "appropriate for internal linking within a webpage:\n\n"
        )
        for url in urls:
            prompt += f"- {url}\n"
        
        prompt += "\nProvide the keywords in a list format."
        
        response = self.client.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful SEO Expert assistant that generates concise and relevant keywords based on URLs provided."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        keywords = response.choices[0].message['content'].strip().split("\n")
        return [keyword.strip() for keyword in keywords]

# Instantiate the OpenAI client with your API key
openai_client = OpenAIClient(api_key='your-openai-api-key')

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
    found_keywords = []

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
                found_keywords.append({'keyword': keyword, 'url': url})
                return f'<a href="{url}">{keyword}</a>'
        return keyword

    pattern = r'\b(?:' + '|'.join(re.escape(pair['Keyword']) for pair in keyword_url_pairs) + r')\b'
    processed_text = re.sub(pattern, replace_keyword, input_text, flags=re.IGNORECASE)

    return processed_text, found_keywords

def improve_linking_with_openai(input_text, found_keywords):
    prompt = (
        "You are an AI text enhancer. Here is a text with some hyperlinked keywords:\n\n"
        f"{input_text}\n\n"
        "Below are the keywords and their corresponding URLs:\n"
    )
    for item in found_keywords:
        prompt += f"- {item['keyword']}: {item['url']}\n"
    
    prompt += (
        "\nPlease analyze the context of the text and suggest better placements for the links to improve readability and relevance. "
        "Do not introduce new links or URLs, only reposition or improve the context around the existing linked keywords."
    )

    response = openai_client.client.ChatCompletion.create(
        model="gpt-4o-mini",  # Using the specified model
        messages=[
            {"role": "system", "content": "You are a helpful SEO Expert assistant that improves hyperlink placement within text."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024,
        temperature=0.7,
    )

    improved_text = response.choices[0].message['content'].strip()
    return improved_text

@app.route('/process-text', methods=['POST'])
def process_text():
    data = request.json
    input_text = data.get('input_text', '')
    excluded_url = data.get('exclude_url', '')

    if not input_text:
        return jsonify({'error': 'No input text provided'}), 400

    # Step 1: Generate the initial hyperlinked text and get the found keywords
    hyperlinked_text, found_keywords = generate_hyperlinked_text(input_text, keyword_url_pairs, excluded_url)

    # Step 2: Use OpenAI to improve the linking based on context
    improved_text = improve_linking_with_openai(hyperlinked_text, found_keywords)

    return jsonify({'hyperlinked_text': improved_text})

if __name__ == '__main__':
    app.run(debug=True)
