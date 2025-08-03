import yfinance as yf
from google.cloud import bigquery
import numpy as np

# Initialize BigQuery client
client = bigquery.Client()
dataset_id = "stock_data"
table_id = "stocks"

def get_stock_data(ticker):
    """Fetch stock details from Yahoo Finance"""
    stock = yf.Ticker(ticker)
    history = stock.history(period="1y")

    # Calculate additional risk metrics
    daily_returns = history["Close"].pct_change() # percentage difference b/w the values of each row and the previous row
    volatility = np.std(daily_returns)  # Standard deviation of daily returns
    price_change_1y = (history["Close"].iloc[-1] - history["Close"].iloc[0]) / history["Close"].iloc[0] * 100  # 1-year price change

    return {
        "Ticker": ticker,
        "Current_Price": stock.history(period="1d")["Close"].iloc[-1],
        "PE_Ratio": stock.info.get("trailingPE", None),
        "Dividend_Yield": stock.info.get("dividendYield", 0),
        "Market_Cap": stock.info.get("marketCap", None),
        "Sector": stock.info.get("sector", "Unknown"),
        "Beta": stock.info.get("beta", None),
        "Volatility": volatility,
        "Price_Change_1Y": price_change_1y,
        "Risk_Level": categorize_stock_risk(stock, volatility, price_change_1y)
    }


def categorize_stock_risk(stock, volatility, price_change_1y):
    """Classify stocks as Low, Medium, or High risk"""
    beta = stock.info.get("beta", None)
    pe_ratio = stock.info.get("trailingPE", None)
    market_cap = stock.info.get("marketCap", None)
    dividend_yield = stock.info.get("dividendYield", 0)

    risk_category = "Medium"  # Default

    if (beta and beta > 1.5) or (pe_ratio and pe_ratio > 30) or (market_cap and market_cap < 5e9) or (volatility > 0.03):
        risk_category = "High"

    if (beta and beta < 1) or (market_cap and market_cap > 200e9) or (dividend_yield and dividend_yield > 3) or (price_change_1y > 20):
        risk_category = "Low"

    return risk_category

def update_stock_data(request):
    """Fetch stock data, classify risk, and store in BigQuery"""
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]  # Expand later to S&P 500
    stock_data = [get_stock_data(ticker) for ticker in tickers]

    table_ref = client.dataset(dataset_id).table(table_id)

    for stock in stock_data:
        query = """
        MERGE `{}.{}.{}` AS target
        USING (
            SELECT @Ticker AS Ticker, @Current_Price AS Current_Price, @PE_Ratio AS PE_Ratio,
                   @Dividend_Yield AS Dividend_Yield, @Market_Cap AS Market_Cap, @Sector AS Sector,
                   @Beta AS Beta, @Volatility AS Volatility, @Price_Change_1Y AS Price_Change_1Y,
                   @Risk_Level AS Risk_Level
        ) AS source
        ON target.Ticker = source.Ticker

        WHEN MATCHED THEN
            UPDATE SET
                target.Current_Price = source.Current_Price,
                target.PE_Ratio = source.PE_Ratio,
                target.Dividend_Yield = source.Dividend_Yield,
                target.Market_Cap = source.Market_Cap,
                target.Sector = source.Sector,
                target.Beta = source.Beta,
                target.Volatility = source.Volatility,
                target.Price_Change_1Y = source.Price_Change_1Y,
                target.Risk_Level = source.Risk_Level

        WHEN NOT MATCHED THEN
            INSERT (Ticker, Current_Price, PE_Ratio, Dividend_Yield, Market_Cap, Sector, Beta, Volatility, Price_Change_1Y, Risk_Level)
            VALUES (source.Ticker, source.Current_Price, source.PE_Ratio, source.Dividend_Yield, source.Market_Cap, source.Sector, source.Beta, source.Volatility, source.Price_Change_1Y, source.Risk_Level);
        """.format(client.project, dataset_id, table_id)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("Ticker", "STRING", stock["Ticker"]),
                bigquery.ScalarQueryParameter("Current_Price", "FLOAT64", stock["Current_Price"]),
                bigquery.ScalarQueryParameter("PE_Ratio", "FLOAT64", stock["PE_Ratio"]),
                bigquery.ScalarQueryParameter("Dividend_Yield", "FLOAT64", stock["Dividend_Yield"]),
                bigquery.ScalarQueryParameter("Market_Cap", "INT64", stock["Market_Cap"]),
                bigquery.ScalarQueryParameter("Sector", "STRING", stock["Sector"]),
                bigquery.ScalarQueryParameter("Beta", "FLOAT64", stock["Beta"]),
                bigquery.ScalarQueryParameter("Volatility", "FLOAT64", stock["Volatility"]),
                bigquery.ScalarQueryParameter("Price_Change_1Y", "FLOAT64", stock["Price_Change_1Y"]),
                bigquery.ScalarQueryParameter("Risk_Level", "STRING", stock["Risk_Level"]),
            ]
        )

        query_job = client.query(query, job_config=job_config)
        query_job.result()  # Wait for query to finish
        print(f"✅ Stock data updated for {stock['Ticker']}")

    return "Stock data updated successfully", 200
