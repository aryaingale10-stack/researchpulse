-- Cross-field overlap: of the works whose PRIMARY topic is in field X, what % also carry a
-- topic in field Y (Y != X). Compared between the first and last sampled year.
DROP VIEW IF EXISTS v_cross_field;
CREATE VIEW v_cross_field AS
WITH own AS (
    SELECT year, primary_field_id, works AS base_works
    FROM cross_field WHERE primary_field_id = other_field_id
)
SELECT c.year,
       c.primary_field_id, pf.field AS primary_field,
       c.other_field_id,   ofl.field AS other_field,
       c.works,
       ROUND(100.0 * c.works / own.base_works, 2) AS pct_of_primary
FROM cross_field c
JOIN own ON own.year = c.year AND own.primary_field_id = c.primary_field_id
JOIN (SELECT DISTINCT field_id, field FROM subfields) pf  ON pf.field_id  = c.primary_field_id
JOIN (SELECT DISTINCT field_id, field FROM subfields) ofl ON ofl.field_id = c.other_field_id
WHERE c.primary_field_id <> c.other_field_id;
