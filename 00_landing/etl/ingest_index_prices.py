# Databricks notebook source
# MAGIC %md
# MAGIC # Landing — S&P 500 tracker prices
# MAGIC
# MAGIC Source: Yahoo Finance via the `yfinance` library — not an official API, but the
# MAGIC established free way to read the same data Yahoo's site shows.
# MAGIC
# MAGIC Four tickers, all tracking the S&P 500 in different wrappers. **SPY is the
# MAGIC benchmark** used in every calculation (its history goes back to 1993); the other
# MAGIC three exist only for a secondary "these trackers should overlap" credibility chart.
# MAGIC
# MAGIC Lands **daily**, as it arrives. Collapsing to monthly is a business rule and belongs
# MAGIC in Silver.

# COMMAND ----------

# MAGIC %pip install yfinance

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import pandas as pd
import yfinance as yf

CATALOG = "`index-vs-trust-pipeline`"
TABLE = f"{CATALOG}.landing.index_prices_raw"

INDEX_TICKERS = ["SPY", "IVV", "VOO", "SPLG"]

# COMMAND ----------

pulls = []

for ticker in INDEX_TICKERS:
    print(f"downloading {ticker}...")

    # auto_adjust=False keeps the raw Close separate from the adjusted one -- we need the
    # raw Close, because the trust data has no dividends to match against.
    hist = yf.Ticker(ticker).history(period="15y", auto_adjust=False, actions=True)

    # yfinance puts the date in the row label, not a column.
    hist = hist.reset_index()

    # Columns like "Adj Close" and "Stock Splits" have spaces, which Delta dislikes.
    hist.columns = [c.replace(" ", "_") for c in hist.columns]

    # Timestamps carry a US market timezone that Spark can't convert cleanly.
    hist["Date"] = hist["Date"].dt.tz_localize(None)

    # The response never says which ETF it is, so without this column the rows are
    # unusable. Identification, not transformation.
    hist.insert(0, "ticker", ticker)

    print(f"  -> {len(hist)} rows")
    pulls.append(hist)

index_prices = pd.concat(pulls, ignore_index=True)
print(f"total {len(index_prices)} rows")
index_prices.head(3)

# COMMAND ----------

sdf = spark.createDataFrame(index_prices)
sdf.write.format("delta").mode("overwrite").saveAsTable(TABLE)

print(f"wrote {TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ticker,
# MAGIC        COUNT(*) AS row_count,
# MAGIC        MIN(Date) AS first_date,
# MAGIC        MAX(Date) AS last_date
# MAGIC FROM `index-vs-trust-pipeline`.landing.index_prices_raw
# MAGIC GROUP BY ticker
# MAGIC ORDER BY ticker;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **4 tickers**, roughly 3,700-3,800 daily rows each, starting around 2011.
# MAGIC VOO launched Sept 2010 and SPLG's history is shorter, so their counts may differ —
# MAGIC that is the data, not a bug.
