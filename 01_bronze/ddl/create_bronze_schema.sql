-- Databricks notebook source
-- Bronze is schema-on-read: we don't define column types up front,
-- we just need somewhere for the raw ingested tables to live.
CREATE SCHEMA IF NOT EXISTS bronze;
