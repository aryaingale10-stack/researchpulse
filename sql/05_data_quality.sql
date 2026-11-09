-- Data quality checks on the collected data.
-- subfield_vs_field_total_gap: subfield counts should add up to the field totals (same works,
-- grouped two ways); a gap means a call was truncated or failed.
SELECT
    (SELECT ROUND(100.0 * SUM(works_without_topic) / SUM(works), 2) FROM year_totals) AS pct_works_without_topic,
    (SELECT COUNT(*) FROM subfields)                                                    AS subfields_in_taxonomy,
    (SELECT COUNT(DISTINCT subfield_id) FROM subfield_year WHERE works > 0)             AS subfields_with_data,
    (SELECT COUNT(*) FROM (SELECT subfield_id FROM subfield_year GROUP BY subfield_id
                           HAVING MIN(works) = 0))                                      AS subfields_with_zero_year,
    (SELECT ABS(SUM(works) - (SELECT SUM(works - works_without_topic) FROM year_totals))
       FROM subfield_year)                                                              AS subfield_vs_field_total_gap;
