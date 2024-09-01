import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI
import csv
from tqdm import tqdm
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize the Flask app
app = Flask(__name__)
CORS(app)

# Initialize the OpenAI client with your API key from environment variables
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

def fetch(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to retrieve {url}: {e}")
        return None

def get_all_urls(domain, max_depth=2):
    visited_urls = set()
    urls_to_visit = set([domain])
    all_urls = set()

    print(f"Starting URL crawl on: {domain}")
    for depth in range(1, max_depth + 1):
        print(f"\nDepth {depth} crawling...")
        new_urls = set()
        
        for url in urls_to_visit:
            if url in visited_urls:
                continue
            
            response = fetch(url)
            if response is None:
                continue
            
            visited_urls.add(url)
            soup = BeautifulSoup(response, 'html.parser')

            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                parsed_url = urlparse(full_url)
                if parsed_url.netloc == urlparse(domain).netloc:
                    if full_url not in visited_urls and full_url not in all_urls:
                        new_urls.add(full_url)
                        all_urls.add(full_url)

        urls_to_visit = new_urls
        if not urls_to_visit:
            break

    print(f"\nTotal URLs found: {len(all_urls)}")
    return list(all_urls)

def generate_keywords(urls, model="gpt-4o-mini"):
    prompt = (
        "For each URL below given, generate exactly 2 double-word keywords and 2 single-word keywords in German.\n\n"
        "Please follow only the format and don't generate anything else.\n"
        "Provide the keywords in the following format:\n\n"
        "keyword, url\n\n"
        "for these urls:\n"
    )
    for url in urls:
        prompt += f"{url}\n"

    retry_attempts = 5
    backoff = 20  # Start with a 20-second backoff

    for attempt in range(retry_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful SEO Expert assistant that generates concise and relevant keywords based on URLs provided."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            # Split content into lines and parse
            lines = content.split('\n')
            results = []

            for line in lines:
                if ',' in line:
                    keyword, url = map(str.strip, line.split(',', 1))
                    results.append([keyword, url])

            return results
        except Exception as e:
            if 'rate_limit' in str(e).lower():
                print(f"Rate limit exceeded, retrying in {backoff} seconds... (Attempt {attempt + 1}/{retry_attempts})")
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                print(f"Failed to generate keywords for URLs: {e}")
                return []

def process_batch(batch_urls):
    # Process a batch of URLs
    return generate_keywords(batch_urls)

@app.route('/process-text', methods=['POST'])
def process_text():
    data = request.json
    domain = data.get('domain', '')
    max_depth = data.get('max_depth', 2)

    # Retrieve URLs
    all_urls = get_all_urls(domain, max_depth=max_depth)

    # Generate keywords and return as JSON
    if all_urls:
        print("\nStarting keyword generation...")
        results = []
        batch_size = 5
        for i in tqdm(range(0, len(all_urls), batch_size), desc="Generating keywords", unit="batch"):
            batch_urls = all_urls[i:i + batch_size]
            batch_results = process_batch(batch_urls)
            if batch_results:
                results.extend(batch_results)
            else:
                print(f"No results returned for batch {i // batch_size + 1}")

        return jsonify({'keywords': results})
    else:
        return jsonify({'error': 'No URLs found to process.'})

if __name__ == "__main__":
    app.run(debug=True)
