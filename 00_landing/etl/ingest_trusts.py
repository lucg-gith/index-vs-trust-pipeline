# Databricks notebook source
# MAGIC %md
# MAGIC # Landing — trust metadata
# MAGIC
# MAGIC Source: `data/uk_investment_trusts.csv` (trust name, ticker, AIC sector, manager,
# MAGIC management group). Lands **exactly as it arrived** — no cleaning of any kind.
# MAGIC
# MAGIC Expected: **120 rows**.

# COMMAND ----------

import os

import pandas as pd

CATALOG = "`index-vs-trust-pipeline`"
TABLE = f"{CATALOG}.landing.trusts_raw"

# Notebook runs from its own folder in a Git folder, so the repo root is two levels up.
REPO_ROOT = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
CSV_PATH = os.path.join(REPO_ROOT, "data", "uk_investment_trusts.csv")

print(f"reading {CSV_PATH}")

# COMMAND ----------

# dtype=str keeps every column as text, which is what a CSV actually is.
# keep_default_na=False stops pandas turning blank cells into nulls -- that would be
# Landing quietly changing the data.
trusts = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)

print(f"{len(trusts)} rows, {len(trusts.columns)} columns")
print(list(trusts.columns))
trusts.head(3)

# COMMAND ----------

sdf = spark.createDataFrame(trusts)
sdf.write.format("delta").mode("overwrite").saveAsTable(TABLE)

print(f"wrote {TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) AS row_count,
# MAGIC        COUNT(DISTINCT ticker) AS distinct_tickers,
# MAGIC        SUM(CASE WHEN ticker = '' THEN 1 ELSE 0 END) AS blank_tickers
# MAGIC FROM `index-vs-trust-pipeline`.landing.trusts_raw;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **120 rows, 118 distinct tickers, 2 blank** (Island Innovation, Witan).
# MAGIC The blanks staying blank is the point: Landing did not drop them.
