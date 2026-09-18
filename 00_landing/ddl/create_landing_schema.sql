-- Landing: receiving zone. Data stays exactly as the source sent it.
-- Catalog name has hyphens, so every reference needs backticks.
CREATE SCHEMA IF NOT EXISTS `index-vs-trust-pipeline`.landing
COMMENT 'Sources exactly as they arrived. No cleaning, no dedup, no type-fixing.';
