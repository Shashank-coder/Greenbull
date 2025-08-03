import os
from google.cloud import bigquery
import pandas as pd
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
bq_client = bigquery.Client()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = "stock_data"
SOURCE_TABLE_ID = "financial_news"
DESTINATION_TABLE_ID = "financial_news_embeddings"

SOURCE_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{SOURCE_TABLE_ID}"
DESTINATION_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{DESTINATION_TABLE_ID}"

def generate_free_embeddings(request):
    query = f"""
        SELECT Ticker, Date, Headline, Content
        FROM `{SOURCE_TABLE_REF}` AS financial_news
        WHERE Content IS NOT NULL
          AND Content != ''
          AND NOT EXISTS (
              SELECT 1 FROM `{DESTINATION_TABLE_REF}` AS embeddings
              WHERE embeddings.Headline = financial_news.Headline
                AND embeddings.Date = financial_news.Date
          )
    """

    df = bq_client.query(query).to_dataframe()

    if df.empty:
        return "No articles found for embeddings.", 200

    embeddings_records = []

    for _, row in df.iterrows():
        text = row['Headline'] + ". " + row['Content']
        embedding_vector = model.encode(text).tolist()

        embeddings_records.append({
            "Ticker": row["Ticker"],
            "Date": row["Date"],
            "Headline": row["Headline"],
            "Embedding": embedding_vector
        })

    embeddings_df = pd.DataFrame(embeddings_records)

    # Write embeddings to BigQuery
    print("Loading table from dataframe")
    job = bq_client.load_table_from_dataframe(embeddings_df, DESTINATION_TABLE_REF)
    job.result()

    return f"Successfully generated free embeddings for {len(embeddings_records)} articles.", 200
