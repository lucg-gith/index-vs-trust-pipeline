# Databricks notebook source
# The seed CSV is hand-curated (see specs/01_bronze/discover_trust_universe.md
# for how it was built) -- Landing just reads it in and lands it, unchanged.
sdf = spark.read.csv(
    "file:/Workspace/Shared/index-vs-trust-pipeline/data/trust_universe_seed.csv",
    header=True,
    inferSchema=True,
)

sdf.show(5)
print(f"Row count: {sdf.count()}")

sdf.write.format("delta").mode("overwrite").saveAsTable("landing.trust_universe_raw")
