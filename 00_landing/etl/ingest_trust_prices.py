# Databricks notebook source
# MAGIC %md
# MAGIC # Landing — trust price history
# MAGIC
# MAGIC Source: `data/uk_investment_trusts_price_history_monthly.csv` — monthly, price only,
# MAGIC no dividends. Lands **exactly as it arrived**, known problems included:
# MAGIC
# MAGIC - date labels mix month-end and next-month-first (Dec 31 shows as Jan 1)
# MAGIC - ~25 tickers carry interleaved rows on a wrong scale
# MAGIC - one zero price (`PCFT`, 2019-11-01)
# MAGIC
# MAGIC All of that is Silver's job. Landing must leave it alone.
# MAGIC
# MAGIC Expected: **16,357 rows**.

# COMMAND ----------

import os

import pandas as pd

CATALOG = "`index-vs-trust-pipeline`"
TABLE = f"{CATALOG}.landing.trust_prices_raw"

REPO_ROOT = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
CSV_PATH = os.path.join(
    REPO_ROOT, "data", "uk_investment_trusts_price_history_monthly.csv"
)

print(f"reading {CSV_PATH}")

# COMMAND ----------

# Text in, text out -- the price column stays a string so a malformed number survives
# to Silver instead of becoming a null at the front door.
prices = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)

print(f"{len(prices)} rows, {len(prices.columns)} columns")
print(list(prices.columns))
prices.head(3)

# COMMAND ----------

sdf = spark.createDataFrame(prices)
sdf.write.format("delta").mode("overwrite").saveAsTable(TABLE)

print(f"wrote {TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) AS row_count,
# MAGIC        COUNT(DISTINCT ticker) AS distinct_tickers,
# MAGIC        MIN(`date`) AS first_date,
# MAGIC        MAX(`date`) AS last_date
# MAGIC FROM `index-vs-trust-pipeline`.landing.trust_prices_raw;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **16,357 rows, 102 tickers, 2011-09-30 to 2026-09-17**.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- The known-bad row must still be bad. This proves Landing cleaned nothing.
# MAGIC SELECT ticker, `date`, price_gbx_or_gbp
# MAGIC FROM `index-vs-trust-pipeline`.landing.trust_prices_raw
# MAGIC WHERE ticker = 'PCFT' AND `date` = '2019-11-01';
