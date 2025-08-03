import os
import weaviate
import pandas as pd
from google.cloud import bigquery
from flask import jsonify
from weaviate.classes.init import Auth

# Env variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")

# Table
DATASET_ID = "stock_data"
SOURCE_TABLE_ID = "financial_news_embeddings"
SOURCE_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{SOURCE_TABLE_ID}"
DESTINATION_CLASS = "FinancialNewsEmbedding"

# BigQuery + Weaviate clients
bq_client = bigquery.Client()

# Connect to Weaviate Cloud
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
)

try:
    collection = client.collections.get(DESTINATION_CLASS)
    print("✅ Collection already exists.")
except WeaviateObjectNotFoundError:
    print("ℹ️ Collection not found, creating...")
    client.collections.create(
        name=DESTINATION_CLASS,
        vectorizer_config=None,  # Disables built-in vectorization
        properties=[
            {"name": "Ticker", "dataType": "text"},
            {"name": "Date", "dataType": "date"},
            {"name": "Headline", "dataType": "text"},
        ]
    )
    print("✅ Collection created.")

def upload_embeddings_to_weaviate(request):
    query = f"""
        SELECT Ticker, Date, Headline, Embedding
        FROM `{SOURCE_TABLE_REF}`
        WHERE Embedding IS NOT NULL
    """

    df = bq_client.query(query).to_dataframe()

    if df.empty:
        return "No embeddings found in BigQuery.", 200

    count = 0

    for _, row in df.iterrows():
        obj = {
            "Ticker": row["Ticker"],
            "Date": str(row["Date"]),
            "Headline": row["Headline"]
        }

        embedding = row["Embedding"]
        if isinstance(embedding, str):
            embedding = eval(embedding)  # handle stringified list
        elif isinstance(embedding, list):
            pass
        else:
            continue

        client.data_object.create(
            data_object=obj,
            class_name=DESTINATION_CLASS,
            vector=embedding
        )
        count += 1

    return f"Uploaded {count} embedding records to Weaviate.", 200
