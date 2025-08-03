import os
import json
import requests
from google.cloud import bigquery
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def fetch_financial_news():
    """Fetch news articles for a list of tickers using NewsAPI."""
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    tickers = ['AAPL', 'GOOGL', 'MSFT']  # Customize your ticker list
    base_url = 'https://newsapi.org/v2/everything'
    all_articles = []

    for ticker in tickers:
        params = {
            'q': ticker,
            'apiKey': NEWS_API_KEY,
            'sortBy': 'publishedAt',
            'language': 'en'
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            for article in data.get('articles', []):
                article['ticker'] = ticker
                all_articles.append(article)
        else:
            print(f"Error fetching news for {ticker}: {response.text}")
    return all_articles

def analyze_sentiment(text):
    """Analyze sentiment of text using VADER and return a compound score."""
    analyzer = SentimentIntensityAnalyzer()
    vs = analyzer.polarity_scores(text)
    return vs['compound']

def insert_into_bigquery(table_id, rows_to_insert):
    """Insert rows into a BigQuery table using the JSON insert method."""
    client = bigquery.Client()
    errors = client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        print("Errors occurred while inserting rows: ", errors)
    else:
        print("Rows inserted successfully.")

def fetch_and_store_financial_news(request):
    """
    HTTP-triggered Cloud Function.
    Fetches news articles, enriches them with sentiment analysis,
    and writes the data to the BigQuery 'financial_news' table.
    """
    articles = fetch_financial_news()

    rows = []
    for article in articles:
        # Use the content field if available; otherwise, fall back to description.
        content = article.get('content') or article.get('description') or ""
        sentiment_score = analyze_sentiment(content)
        # Build the row in accordance with your BigQuery schema.
        row = {
            "Ticker": article.get('ticker'),
            "Date": article.get('publishedAt')[:10],  # Extracts YYYY-MM-DD
            "Headline": article.get('title'),
            "Content": content,
            "Source": article.get('source', {}).get('name'),
            "Sentiment_Score": sentiment_score,
            "Summary": ""  # Placeholder for an AI-generated summary
        }
        rows.append(row)

    # The BigQuery table ID should be set as an environment variable.
    table_id = os.environ.get('FINANCIAL_NEWS_TABLE_ID')
    insert_into_bigquery(table_id, rows)

    return f"Inserted {len(rows)} rows into {table_id}"
