import os
import json
import requests
from google.cloud import bigquery
import pandas as pd

def fetch_income_statement():
    """
    Fetches quarterly income statement data for a given stock symbol using Alpha Vantage.
    Returns:
        list: A list of quarterly income statement dictionaries.
    """
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    tickers = ['AAPL', 'GOOGL', 'MSFT']  # Customize your ticker list
    base_url = 'https://www.alphavantage.co/query'
    all_quarterly_reports = []

    for ticker in tickers:
        params = {
            'function': 'INCOME_STATEMENT',
            'symbol': ticker,
            'apikey': ALPHA_VANTAGE_API_KEY
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch income statement data. HTTP Status Code: {response.status_code}")

        data = response.json()
        quarterly_reports = data.get("quarterlyReports", [])
        for quarterly_report in quarterly_reports:
            quarterly_report['symbol'] = ticker
            all_quarterly_reports.append(quarterly_report)

    return all_quarterly_reports

def fetch_earnings():
    """
    Fetches quarterly earnings data for a given stock symbol using Alpha Vantage.
    Returns:
        list: A list of quarterly earnings dictionaries.
    """
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    tickers = ['AAPL', 'GOOGL', 'MSFT']  # Customize your ticker list
    base_url = 'https://www.alphavantage.co/query'
    all_quarterly_earnings = []

    for ticker in tickers:
        params = {
            'function': 'EARNINGS',
            'symbol': ticker,
            'apikey': ALPHA_VANTAGE_API_KEY
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch earnings data. HTTP Status Code: {response.status_code}")

        data = response.json()
        quarterly_earnings = data.get("quarterlyEarnings", [])
        for quarterly_earning in quarterly_earnings:
            quarterly_earning['symbol'] = ticker
            all_quarterly_earnings.append(quarterly_earning)

    return all_quarterly_earnings

def pre_process_dataframe(earnings_report_df):
    # Convert date columns to proper datetime types
    earnings_report_df['fiscalDateEnding'] = pd.to_datetime(earnings_report_df['fiscalDateEnding'])
    earnings_report_df['reportedDate'] = pd.to_datetime(earnings_report_df['reportedDate'])
    # List of columns that should be numeric
    numeric_columns = [
        'reportedEPS', 'estimatedEPS', 'surprise', 'surprisePercentage',
        'grossProfit', 'totalRevenue', 'costOfRevenue', 'costofGoodsAndServicesSold',
        'operatingIncome', 'sellingGeneralAndAdministrative', 'researchAndDevelopment',
        'operatingExpenses', 'investmentIncomeNet', 'netInterestIncome', 'interestIncome',
        'interestExpense', 'nonInterestIncome', 'otherNonOperatingIncome', 'depreciation',
        'depreciationAndAmortization', 'incomeBeforeTax', 'incomeTaxExpense',
        'interestAndDebtExpense', 'netIncomeFromContinuingOperations',
        'comprehensiveIncomeNetOfTax', 'ebit', 'ebitda', 'netIncome'
    ]
    # Convert these columns to numeric, forcing errors to NaN if conversion fails
    for col in numeric_columns:
        if col in earnings_report_df.columns:
            earnings_report_df[col] = pd.to_numeric(earnings_report_df[col], errors='coerce')

    return earnings_report_df

def insert_into_bigquery(table_id, df):
    """Insert rows into a BigQuery table using the load table from dataframe method."""
    client = bigquery.Client()
    job = client.load_table_from_dataframe(df, table_id)
    job.result()
    print(f"Loaded {job.output_rows} rows into {table_id}.")

def fetch_and_store_earnings_report(request):
    """
    HTTP-triggered Cloud Function.
    Fetches quarterly earnings and income statements,
    and writes the data to the BigQuery 'earnings_report' table.
    """
    earnings_data = fetch_earnings()
    income_data = fetch_income_statement()
    earnings_df = pd.DataFrame(earnings_data)
    income_df = pd.DataFrame(income_data)

    # Merge the two DataFrames on 'symbol' & 'fiscalDateEnding'
    earnings_report_df = pd.merge(earnings_df, income_df, on=['symbol', 'fiscalDateEnding'], suffixes=('_earnings', '_income'))
    earnings_report_df = pre_process_dataframe(earnings_report_df)

    # The BigQuery table ID should be set as an environment variable.
    table_id = os.environ.get('EARNINGS_REPORT_TABLE_ID')
    insert_into_bigquery(table_id, earnings_report_df)

    # Return an HTTP response to indicate success.
    return ("Earnings report data fetched and stored successfully.", 200)
