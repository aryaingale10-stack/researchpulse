-- Field-level output indexed to the first year (first year = 100), plus share of all research.
DROP VIEW IF EXISTS v_field_index;
CREATE VIEW v_field_index AS
WITH f AS (
    SELECT fy.field_id, MIN(s.field) AS field, fy.year, fy.works
    FROM field_year fy JOIN subfields s ON s.field_id = fy.field_id
    GROUP BY fy.field_id, fy.year, fy.works
)
SELECT f.field_id, f.field, f.year, f.works,
       ROUND(100.0 * f.works / FIRST_VALUE(f.works) OVER (PARTITION BY f.field_id ORDER BY f.year), 1) AS index_first_year,
       ROUND(100.0 * f.works / yt.works, 3) AS share_pct
FROM f JOIN year_totals yt ON yt.year = f.year;
