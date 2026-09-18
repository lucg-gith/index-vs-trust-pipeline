-- Bronze: every column STRING, exactly the rows Landing received.
-- No cleaning, no validation, no rejection -- bad rows must arrive intact.
CREATE SCHEMA IF NOT EXISTS `index-vs-trust-pipeline`.bronze
COMMENT 'Landing recast to a uniform all-STRING contract. Nothing rejected.';
