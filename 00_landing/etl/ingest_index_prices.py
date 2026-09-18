# Databricks notebook source
# MAGIC %pip install yfinance

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# yfinance is a Python library that fetches historical stock/ETF market data
# for free, by reading the same data Yahoo Finance's own website shows --
# it's not an official Yahoo API, just a well-established community tool for this
import yfinance as yf

# The 4 tickers, all of which track the S&P 500 index in slightly
# different wrappers (different provider, fee, inception date). SPY is the
# primary benchmark (history back to 1993)
index_tickers = ["SPY", "IVV", "VOO", "SPLG"]

for ticker in index_tickers:
    print(f"Downloading {ticker}...")

    # Ask yfinance for this ticker's full history.
    t = yf.Ticker(ticker)

    # .history() actually pulls the data:
    #   period="15y"        -> go back 15 years from today
    #   auto_adjust=False    -> keep the raw Close separate from a dividend/split-adjusted
    #                           version.
    #   actions=True         -> include Dividends / Stock Splits / Capital Gains columns
    hist = t.history(period="15y", auto_adjust=False, actions=True)

    # yfinance puts the date in the table's index (its row label).
    # reset_index() turns that back into a real "Date" column.
    hist = hist.reset_index()

    # yfinance's columns include "Adj Close", "Stock Splits", "Capital Gains" -- all
    # have spaces -- so this replaces every space with an underscore.
    hist.columns = [c.replace(" ", "_") for c in hist.columns]

    # yfinance timestamps carry US market timezone info (e.g. America/New_York).
    # Spark can't convert timezone-aware pandas timestamps cleanly, so we strip it,
    # keeping just the plain calendar date.
    hist["Date"] = hist["Date"].dt.tz_localize(None)

    print(f"  -> got {len(hist)} rows for {ticker}")

    # Landing keeps each ticker's pull separate 
    ticker_sdf = spark.createDataFrame(hist)
    ticker_sdf.show(3)

    table_name = f"landing.index_prices_raw_{ticker.lower()}"
    ticker_sdf.write.format("delta").mode("overwrite").saveAsTable(table_name)
    print(f"  -> wrote {table_name}")
