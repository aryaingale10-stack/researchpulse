-- Each subfield's output per year, as a raw count AND as a share of all research that year.
-- Share is the key normalization: total OpenAlex output grows every year (and coverage
-- improves), so raw growth alone would make almost every field look "rising".
DROP VIEW IF EXISTS v_subfield_year;
CREATE VIEW v_subfield_year AS
SELECT
    sy.subfield_id,
    s.subfield,
    s.field,
    s.domain,
    sy.year,
    sy.works,
    yt.works                                                  AS all_works,
    1000.0 * sy.works / yt.works                              AS share_per_mille,
    sy.works - LAG(sy.works) OVER w                           AS yoy_change,
    ROUND(100.0 * (sy.works - LAG(sy.works) OVER w)
          / NULLIF(LAG(sy.works) OVER w, 0), 2)               AS yoy_pct
FROM subfield_year sy
JOIN subfields   s  ON s.subfield_id = sy.subfield_id
JOIN year_totals yt ON yt.year = sy.year
WINDOW w AS (PARTITION BY sy.subfield_id ORDER BY sy.year);
