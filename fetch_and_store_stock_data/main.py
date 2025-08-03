import yfinance as yf
from google.cloud import bigquery
from datetime import datetime
import requests

# Initialize BigQuery client
client = bigquery.Client()

# Define BigQuery dataset and table
PROJECT_ID = "earnest-fuze-109910"  # Replace with your actual GCP project ID
DATASET_ID = "stock_data"
TABLE_ID = "daily_stock_prices"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Function to get the latest S&P 500 tickers dynamically
def get_sp500_tickers():
    """Fetches the latest S&P 500 tickers from Yahoo Finance."""

    sp500_tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B",
    "JNJ", "XOM", "JPM", "V", "PG", "UNH", "HD", "MA", "ABBV", "PFE", "AVGO", "KO"]
    return sp500_tickers

def fetch_and_store_stock_data(request):
    """Fetches stock data for S&P 500 and updates BigQuery."""

    tickers = get_sp500_tickers()
    print(tickers)  # Prints a list of 100 S&P 500 stock symbols
    rows_to_insert = []

    # Fetch latest stock data
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")

        if not data.empty:
            latest = data.iloc[-1]
            record = {
                "symbol": ticker,
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "open": round(latest["Open"], 2),
                "close": round(latest["Close"], 2),
                "high": round(latest["High"], 2),
                "low": round(latest["Low"], 2),
                "volume": int(latest["Volume"]),
            }

            # Check if the stock data for the date already exists in BigQuery
            query = f"""
            SELECT COUNT(*) AS count FROM `{TABLE_REF}`
            WHERE symbol = '{ticker}' AND date = '{record["date"]}'
            """
            query_job = client.query(query)
            results = list(query_job.result())

            if results[0].count == 0:
                rows_to_insert.append(record)
            else:
                # Update existing record using MERGE statement
                update_query = f"""
                MERGE `{TABLE_REF}` AS target
                USING (SELECT '{ticker}' AS symbol, '{record["date"]}' AS date) AS source
                ON target.symbol = source.symbol AND target.date = source.date
                WHEN MATCHED THEN
                  UPDATE SET open = {record["open"]}, close = {record["close"]},
                             high = {record["high"]}, low = {record["low"]},
                             volume = {record["volume"]}
                """
                client.query(update_query)

    # Insert new records into BigQuery
    if rows_to_insert:
        errors = client.insert_rows_json(TABLE_REF, rows_to_insert)
        if errors:
            return f"Error inserting rows: {errors}", 500

    return "Stock data updated successfully", 200
