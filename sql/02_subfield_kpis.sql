-- One row per subfield: size, 5-year CAGRs for two periods, acceleration and share change.
--   cagr_recent  = growth {mid}->{last}      cagr_prior = growth {first}->{mid}
--   share_cagr   = growth of the subfield's SHARE of all research {mid}->{last}
--                  (> 0 means it is growing faster than research overall)
DROP VIEW IF EXISTS v_subfield_kpis;
CREATE VIEW v_subfield_kpis AS
WITH p AS (
    SELECT subfield_id, subfield, field, domain,
           MAX(CASE WHEN year = {first} THEN works END)           AS works_first,
           MAX(CASE WHEN year = {mid}   THEN works END)           AS works_mid,
           MAX(CASE WHEN year = {last}  THEN works END)           AS works_last,
           MAX(CASE WHEN year = {mid}   THEN share_per_mille END) AS share_mid,
           MAX(CASE WHEN year = {last}  THEN share_per_mille END) AS share_last
    FROM v_subfield_year
    GROUP BY subfield_id, subfield, field, domain
)
SELECT p.*,
    ROUND(100 * (POWER(1.0 * works_last / NULLIF(works_mid, 0), 1.0 / ({last} - {mid})) - 1), 2)   AS cagr_recent,
    ROUND(100 * (POWER(1.0 * works_mid / NULLIF(works_first, 0), 1.0 / ({mid} - {first})) - 1), 2) AS cagr_prior,
    ROUND(100 * (POWER(share_last / NULLIF(share_mid, 0), 1.0 / ({last} - {mid})) - 1), 2)         AS share_cagr
FROM p;
