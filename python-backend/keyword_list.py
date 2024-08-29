from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import os

# Initialize the OpenAI client with your API key from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

def fetch(url):
    """Fetches the HTML content of a given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        app.logger.error(f"Failed to retrieve {url}: {e}")
        return None

def get_all_urls(domain, max_depth=2):
    """Crawls the given domain up to a certain depth and returns all found URLs."""
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

    app.logger.info(f"URLs found: {all_urls}")
    return list(all_urls)

def generate_keywords(urls):
    """Generates keywords for a list of URLs using OpenAI's API."""
    prompt = (
        "For each URL below, generate exactly 2 double-word keywords and 2 single-word keywords in German.\n\n"
        "Provide the keywords in the following format:\n\n"
        "keyword, url\n\n"
        "for these URLs:\n"
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

        app.logger.info(f"Generated keywords: {results}")
        return results
    except Exception as e:
        app.logger.error(f"Failed to generate keywords for URLs: {e}")
        return []

@app.route('/generate-keywords', methods=['POST'])
def generate_keywords_api():
    """API endpoint to generate keywords for a given domain."""
    try:
        data = request.json
        domain = data.get('domain')
        max_depth = data.get('max_depth', 2)

        if not domain:
            app.logger.error("Domain is missing from the request.")
            return jsonify({"error": "Domain is required"}), 400

        app.logger.info(f"Processing domain: {domain} with max depth: {max_depth}")

        all_urls = get_all_urls(domain, max_depth)
        results = []

        if all_urls:
            # Process URLs in batches of 10
            batch_size = 10
            for i in range(0, len(all_urls), batch_size):
                batch_urls = all_urls[i:i + batch_size]
                batch_results = generate_keywords(batch_urls)
                if batch_results:
                    results.extend(batch_results)

            if not results:
                app.logger.warning("No keywords generated")
                return jsonify({"message": "No keywords generated"}), 200

            return jsonify(results)
        else:
            app.logger.warning(f"No URLs found for domain: {domain}")
            return jsonify({"error": "No URLs found to process"}), 404
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify that the service is running."""
    return "<h1>Healthy</h1>", 200

if __name__ == "__main__":
    # Ensure the app binds to the port provided by the environment
    port = int(os.environ.get("PORT", 10000))  # Default to port 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port, debug=True)
