
#  %pip install yfinance



dbutils.library.restartPython()



import yfinance as yf
from pyspark.sql.functions import col

# SPY is the primary benchmark (history to 1993); IVV/VOO/SPLG are only for a
# secondary "trackers overlap" cross-check chart.
index_tickers = ["SPY", "IVV", "VOO", "SPLG"]

sdf = None

for ticker in index_tickers:
    print(f"Downloading {ticker}...")

    t = yf.Ticker(ticker)
    # auto_adjust=False keeps raw Close separate from the adjusted Close --
    # dividends need to stay their own column.
    hist = t.history(period="15y", auto_adjust=False, actions=True)

    hist = hist.reset_index()

    # Delta rejects spaces in column names.
    hist.columns = [c.replace(" ", "_") for c in hist.columns]

    # Spark can't handle timezone-aware timestamps.
    hist["Date"] = hist["Date"].dt.tz_localize(None)

    hist["ticker"] = ticker

    print(f"  -> got {len(hist)} rows for {ticker}")

    ticker_sdf = spark.createDataFrame(hist)

    # Bronze: everything stays string, no type decisions yet.
    ticker_sdf = ticker_sdf.select([col(c).cast("string").alias(c) for c in ticker_sdf.columns])

    ticker_sdf.show(3)

    if sdf is None:
        sdf = ticker_sdf
    else:
        sdf = sdf.union(ticker_sdf)

# COMMAND ----------

print("Done. Writing and previewing the combined table:")

# Full overwrite each run -- keeps it idempotent.
sdf.write.format("delta").mode("overwrite").saveAsTable("bronze.index_prices_raw")

sdf.show(10)

# VOO should have the fewest rows -- it only launched in 2010.
print(sdf.groupBy("ticker").count().toPandas())
