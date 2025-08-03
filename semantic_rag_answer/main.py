import os
import json
from flask import jsonify
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery
from sentence_transformers import SentenceTransformer
from together import Together
import pandas as pd
from google.cloud import bigquery

WEAVIATE_COLLECTION = os.getenv("WEAVIATE_FINANCE_COLLECTION")

# Connect to Weaviate Cloud
weaviate_client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY"))
)

# Initialize BigQuery
bq_client = bigquery.Client()

# Initialize together for LLM chat completions
together_client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))


# SentenceTransformer for embedding user queries
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Main cloud function entry point
def semantic_rag_answer(request):
    request_json = request.get_json()
    if not request_json or "query" not in request_json:
        return jsonify({"error": "Missing 'query' field in request."}), 400

    user_query = request_json["query"]
    try:
        response = run_pipeline(user_query)
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# RAG pipeline
def run_pipeline(user_query):
    # Extract tickers from query
    tickers = extract_tickers(user_query)

    # Fetch structured data based on tickers
    if tickers:
        structured_context = fetch_structured_data(tickers)
    else:
        structured_context = "No relevant structured financial data identified."

    # Step 1: Generate embedding
    query_vector = embedding_model.encode(user_query).tolist()

    # Step 2: Search Weaviate
    weaviate_collection = weaviate_client.collections.get(WEAVIATE_COLLECTION)
    results = weaviate_collection.query.near_vector(
        near_vector = query_vector,
        limit = 5,
        return_metadata=MetadataQuery(distance=True)
    )
    weaviate_client.close()

    # Step 3: Build prompt
    semantic_context = "\n".join(
        f"{r.properties['date']} | {r.properties['ticker']} | {r.properties['headline']}" for r in results.objects
    )
    prompt = build_prompt(semantic_context, structured_context, user_query)
    print(f"Prompt: {prompt}"")

    # Step 4: Get LLM response
    return get_LLM_response(prompt)

def build_prompt(semantic_context, structured_context, user_query):
    prompt = f"""
        You are a helpful financial AI assistant. Use the context below to answer the question.

        Financial News Context:
        {semantic_context}

        Structured Financial Data:
        {structured_context}


        Question:
        {user_query}

        Detailed Answer:"""

    return prompt

def get_LLM_response(prompt):
    # Step 4: Get LLM response
    completion = together_client.chat.completions.create(
        model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content.strip()

def extract_tickers(user_query):
    extraction_prompt = f"""
        Extract all stock ticker symbols mentioned or implied from the user query.
        Return only the comma-separated ticker symbols. If no tickers are found, return NONE.

        Examples:
        - "How did Apple and Tesla perform?" -> AAPL,TSLA
        - "Show recent news for Nvidia" -> NVDA
        - "How's the overall tech sector?" -> NONE

        User query: "{user_query}"

        Give the answer strictly with comma separated ticker symbols only. Answer "NONE" if no ticker symbols are extracted.
        """

    tickers_text = get_LLM_response(extraction_prompt)

    if tickers_text == "NONE":
        return []
    return [ticker.strip() for ticker in tickers_text.split(",")]

def fetch_structured_data(tickers):
    tickers_condition = ", ".join(f"'{ticker}'" for ticker in tickers)
    project_id = os.getenv('GCP_PROJECT_ID')

    # Fetch latest daily stock prices
    query_prices = f"""
        SELECT *
        FROM `{project_id}.stock_data.daily_stock_prices`
        WHERE Symbol IN ({tickers_condition})
        ORDER BY Date DESC
        LIMIT {len(tickers)}
    """

    # Fetch stock fundamentals
    query_fundamentals = f"""
        SELECT *
        FROM `{project_id}.stock_data.stocks`
        WHERE Ticker IN ({tickers_condition})
    """

    # Fetch latest earnings report
    query_earnings = f"""
        SELECT *
        FROM `{project_id}.stock_data.earnings_report`
        WHERE symbol IN ({tickers_condition})
        ORDER BY fiscalDateEnding DESC
        LIMIT {len(tickers)}
    """

    df_prices = bq_client.query(query_prices).to_dataframe()
    df_fundamentals = bq_client.query(query_fundamentals).to_dataframe()
    df_earnings = bq_client.query(query_earnings).to_dataframe()

    # Format context clearly
    context = f"""
        Daily Stock Prices:
        {df_prices.to_string(index=False)}

        Stock Fundamentals:
        {df_fundamentals.to_string(index=False)}

        Recent Earnings Reports:
        {df_earnings.to_string(index=False)}
        """

    return context
