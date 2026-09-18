# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — trust price history
# MAGIC
# MAGIC `landing.trust_prices_raw` → `bronze.trust_prices`. Every column cast to STRING.
# MAGIC
# MAGIC The known problems **must survive this layer**: the mixed date labels, the ~25
# MAGIC tickers on a wrong scale, and the `PCFT` zero price. Silver fixes them, and the fix
# MAGIC is only auditable if Bronze still holds the original.
# MAGIC
# MAGIC Expected: **16,357 rows**, same as Landing.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- price stays STRING: casting to DOUBLE here would turn any malformed value into a
# MAGIC -- silent NULL, which is exactly the rejection this layer is not allowed to do.
# MAGIC CREATE OR REPLACE TABLE `index-vs-trust-pipeline`.bronze.trust_prices AS
# MAGIC SELECT
# MAGIC   CAST(trust_name        AS STRING) AS trust_name,
# MAGIC   CAST(ticker            AS STRING) AS ticker,
# MAGIC   CAST(aic_sector        AS STRING) AS aic_sector,
# MAGIC   CAST(`date`            AS STRING) AS `date`,
# MAGIC   CAST(price_gbx_or_gbp  AS STRING) AS price_gbx_or_gbp
# MAGIC FROM `index-vs-trust-pipeline`.landing.trust_prices_raw;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.landing.trust_prices_raw) AS landing_rows,
# MAGIC   (SELECT COUNT(*) FROM `index-vs-trust-pipeline`.bronze.trust_prices)      AS bronze_rows,
# MAGIC   (SELECT COUNT(DISTINCT ticker) FROM `index-vs-trust-pipeline`.bronze.trust_prices) AS tickers;

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **16,357 / 16,357 / 102**.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- The known-bad row proves Bronze cleaned nothing. Must still read 0.000.
# MAGIC SELECT ticker, `date`, price_gbx_or_gbp
# MAGIC FROM `index-vs-trust-pipeline`.bronze.trust_prices
# MAGIC WHERE ticker = 'PCFT' AND `date` = '2019-11-01';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE `index-vs-trust-pipeline`.bronze.trust_prices;
