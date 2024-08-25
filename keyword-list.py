from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import csv
import time

# Initialize the OpenAI client with your API key
openai.api_key = 'sk-mF6DwaD6zmujy1peK69JlgPsExD_H7oLT40ZAjTBswT3BlbkFJSCd866IclcXIzayMax2CgpkjgUDuzzDE6Nos8KJe4A'  # Replace with your actual OpenAI API key

app = Flask(__name__)

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

    for depth in range(1, max_depth + 1):
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

    return list(all_urls)

def generate_keywords(urls):
    prompt = (
        "For each URL below given, generate exactly 2 double-word keywords and 2 single-word keywords in German.\n\n"
        "Provide the keywords in the following format:\n\n"
        "keyword, url\n\n"
        "for these urls:\n"
    )
    for url in urls:
        prompt += f"{url}\n"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful SEO Expert assistant that generates concise and relevant keywords based on URLs provided."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        content = response['choices'][0]['message']['content'].strip()
        # Split content into lines and parse
        lines = content.split('\n')
        results = []

        for line in lines:
            if ',' in line:
                keyword, url = map(str.strip, line.split(',', 1))
                results.append([keyword, url])

        return results
    except Exception as e:
        print(f"Failed to generate keywords for URLs: {e}")
        return []

@app.route('/generate-keywords', methods=['POST'])
def generate_keywords_api():
    data = request.json
    domain = data.get('domain')
    max_depth = data.get('max_depth', 2)

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    all_urls = get_all_urls(domain, max_depth)
    results = []

    if all_urls:
        # Process URLs in batches of 10
        batch_size = 10
        for i in range(0, len(all_urls), batch_size):
            batch_urls = all_urls[i:i + batch_size]
            results.extend(generate_keywords(batch_urls))

        return jsonify(results)
    else:
        return jsonify({"error": "No URLs found to process"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
