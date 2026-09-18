# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — trust metadata
# MAGIC
# MAGIC `landing.trusts_raw` → `bronze.trusts`. Every column cast to STRING, nothing else.
# MAGIC
# MAGIC Landing already holds this as text, so the casts are a no-op here **by design** —
# MAGIC the point is that all three Bronze tables honour one contract, with no exceptions
# MAGIC to remember.
# MAGIC
# MAGIC Expected: **120 rows**, same as Landing.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Explicit column list rather than SELECT * : it documents the source contract, so
# MAGIC -- a column appearing or vanishing upstream shows up as an error, not a surprise.
# MAGIC CREATE OR REPLACE TABLE `index-vs-trust-pipeline`.bronze.trusts AS
# MAGIC SELECT
# MAGIC   CAST(trust_name       AS STRING) AS trust_name,
# MAGIC   CAST(ticker           AS STRING) AS ticker,
# MAGIC   CAST(aic_sector       AS STRING) AS aic_sector,
# MAGIC   CAST(source_url       AS STRING) AS source_url,
# MAGIC   CAST(manager          AS STRING) AS manager,
# MAGIC   CAST(management_group AS STRING) AS management_group,
# MAGIC   CAST(notes            AS STRING) AS notes
# MAGIC FROM `index-vs-trust-pipeline`.landing.trusts_raw;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Bronze must reject nothing, so the two counts have to be equal.
# MAGIC SELECT
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.landing.trusts_raw) AS landing_rows,
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.bronze.trusts)      AS bronze_rows,
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.bronze.trusts
# MAGIC      WHERE ticker = '')                                               AS blank_tickers;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **120 / 120 / 2**. The two blank tickers (Island Innovation, Witan) surviving
# MAGIC is the proof that Bronze dropped nothing.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Every column must be STRING. Any other type here is a bug.
# MAGIC DESCRIBE TABLE `index-vs-trust-pipeline`.bronze.trusts;
