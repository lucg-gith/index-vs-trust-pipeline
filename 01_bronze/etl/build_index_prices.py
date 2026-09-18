# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — S&P 500 tracker prices
# MAGIC
# MAGIC `landing.index_prices_raw` → `bronze.index_prices`. Every column cast to STRING.
# MAGIC
# MAGIC This is the table where the cast does real work: Landing holds yfinance's own types
# MAGIC (timestamps, doubles, longs) and Bronze flattens them to text like everything else.
# MAGIC
# MAGIC Stays **daily**. Collapsing to monthly is a business rule and belongs in Silver.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Column guard
# MAGIC
# MAGIC The CSV sources have a fixed set of columns, but yfinance's does vary by instrument
# MAGIC (`Capital_Gains` shows up for some and not others). Check the real column list before
# MAGIC building, so a mismatch is loud rather than silent.

# COMMAND ----------

EXPECTED = [
    "ticker", "Date", "Open", "High", "Low", "Close",
    "Adj_Close", "Volume", "Dividends", "Stock_Splits",
]

actual = spark.table("`index-vs-trust-pipeline`.landing.index_prices_raw").columns

print(f"actual:   {actual}")
print(f"expected: {EXPECTED}")

missing = [c for c in EXPECTED if c not in actual]
extra = [c for c in actual if c not in EXPECTED]

if missing or extra:
    print(f"\nMISMATCH -- missing: {missing}, unexpected: {extra}")
    print("Update the CAST list in the next cell to match, then re-run.")
else:
    print("\nmatch -- safe to build")

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `index-vs-trust-pipeline`.bronze.index_prices AS
# MAGIC SELECT
# MAGIC   CAST(ticker       AS STRING) AS ticker,
# MAGIC   CAST(`Date`       AS STRING) AS `Date`,
# MAGIC   CAST(Open         AS STRING) AS Open,
# MAGIC   CAST(High         AS STRING) AS High,
# MAGIC   CAST(Low          AS STRING) AS Low,
# MAGIC   CAST(Close        AS STRING) AS Close,
# MAGIC   CAST(Adj_Close    AS STRING) AS Adj_Close,
# MAGIC   CAST(Volume       AS STRING) AS Volume,
# MAGIC   CAST(Dividends    AS STRING) AS Dividends,
# MAGIC   CAST(Stock_Splits AS STRING) AS Stock_Splits
# MAGIC FROM `index-vs-trust-pipeline`.landing.index_prices_raw;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.landing.index_prices_raw) AS landing_rows,
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.bronze.index_prices)      AS bronze_rows,
# MAGIC   (SELECT COUNT(DISTINCT ticker) FROM `index-vs-trust-pipeline`.bronze.index_prices) AS tickers;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect the two row counts to be **equal**, and **4** tickers.

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE `index-vs-trust-pipeline`.bronze.index_prices;
