# Databricks notebook source
# MAGIC %pip install yfinance

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# yfinance is a Python library that fetches historical stock/ETF market data
# for free, by reading the same data Yahoo Finance's own website shows —
# it's not an official Yahoo API, just a well-established community tool for this
import yfinance as yf
from pyspark.sql.functions import col

# The 4 tickers we want, all of which track the S&P 500 index in slightly
# different wrappers (different provider, fee, inception date). SPY is the
# primary benchmark (history back to 1993); the other three exist for a
# secondary "these trackers should overlap" credibility chart later on.
index_tickers = ["SPY", "IVV", "VOO", "SPLG"]

# This will hold our combined result. It starts empty (None) because we haven't
# downloaded anything yet -- the loop below fills it in, one ticker at a time.
sdf = None

# Loop through the list above -- this block of code runs once per ticker,
# with "ticker" standing in for whichever name we're currently on
for ticker in index_tickers:
    print(f"Downloading {ticker}...")

    # Ask yfinance for this ticker's full history.
    # yf.Ticker(ticker) just creates a handle to the symbol -- nothing downloads yet.
    t = yf.Ticker(ticker)

    # .history() actually pulls the data:
    #   period="15y"        -> go back 15 years from today
    #   auto_adjust=False    -> keep the raw Close separate from a dividend/split-adjusted
    #                           version, since we want dividends visible as their own column
    #   actions=True         -> include Dividends / Stock Splits / Capital Gains columns
    hist = t.history(period="15y", auto_adjust=False, actions=True)

    # yfinance puts the date in the table's index (its row label), not a normal column.
    # reset_index() turns that back into a real "Date" column.
    hist = hist.reset_index()

    # Delta Lake refuses column names containing spaces (or a few other symbols).
    # yfinance's columns include "Adj Close", "Stock Splits", "Capital Gains" -- all
    # have spaces -- so this replaces every space with an underscore before it's a problem.
    hist.columns = [c.replace(" ", "_") for c in hist.columns]

    # yfinance timestamps carry US market timezone info (e.g. America/New_York).
    # Spark can't convert timezone-aware pandas timestamps cleanly, so we strip it,
    # keeping just the plain calendar date.
    hist["Date"] = hist["Date"].dt.tz_localize(None)

    # Tag every row with which ticker it belongs to -- once all 4 are stacked together
    # into one table, this column is the only way to tell them apart.
    hist["ticker"] = ticker

    print(f"  -> got {len(hist)} rows for {ticker}")

    # Convert this ticker's pandas table into a Spark table. This is the handoff point --
    # everything before this line had to be pandas (because yfinance only speaks pandas);
    # everything from here on is Spark.
    ticker_sdf = spark.createDataFrame(hist)

    # Bronze stores everything as a string -- no type decisions get made yet.
    # Silver is where we deliberately cast back to real types (dates, decimals),
    # so ingestion can never fail on a type mismatch from the source.
    ticker_sdf = ticker_sdf.select([col(c).cast("string").alias(c) for c in ticker_sdf.columns])

    ticker_sdf.show(3)

    # Add this ticker's rows onto the combined table we're building up.
    if sdf is None:
        sdf = ticker_sdf              # first time through the loop: this becomes the starting table
    else:
        sdf = sdf.union(ticker_sdf)   # every time after: stack this ticker's rows on top

# COMMAND ----------

# By now the loop has finished -- sdf holds all 4 tickers' data combined into one table
print("Done. Writing and previewing the combined table:")

# Save it as a permanent Delta table named bronze.index_prices_raw.
# mode("overwrite") replaces the whole table each run -- this is what makes the
# notebook idempotent: running it once or fifty times leaves the table in the
# same end state, since we always pull the full fresh 15-year window rather
# than appending on top of what's already there.
sdf.write.format("delta").mode("overwrite").saveAsTable("bronze.index_prices_raw")

sdf.show(10)  # preview 10 rows of the final combined table, not all ~15,000

# Count how many rows each ticker ended up with -- a final check that nothing's missing
# (VOO should be the lowest, since it only launched in 2010)
print(sdf.groupBy("ticker").count().toPandas())
