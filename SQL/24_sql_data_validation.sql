
USE AirScope;
GO

-- 1. Check total records in all four tables

SELECT 'dim_station' AS table_name, COUNT(*) AS total_records
FROM dbo.dim_station

UNION ALL

SELECT 'dim_date', COUNT(*)
FROM dbo.dim_date

UNION ALL

SELECT 'dim_pollutant', COUNT(*)
FROM dbo.dim_pollutant

UNION ALL

SELECT 'fact_air_quality_daily', COUNT(*)
FROM dbo.fact_air_quality_daily;
GO


-- 2. Check historical date range

SELECT
    MIN(d.[date]) AS first_date,
    MAX(d.[date]) AS last_date,
    COUNT(DISTINCT f.date_key) AS dates_with_measurements
FROM dbo.fact_air_quality_daily f
JOIN dbo.dim_date d
    ON f.date_key = d.date_key;
GO


-- 3. Check pollutant-wise records

SELECT
    p.pollutant_name,
    p.unit,
    COUNT(*) AS total_records,
    ROUND(AVG(f.mean), 2) AS average_concentration,
    ROUND(MIN(f.mean), 2) AS minimum_concentration,
    ROUND(MAX(f.mean), 2) AS maximum_concentration
FROM dbo.fact_air_quality_daily f
JOIN dbo.dim_pollutant p
    ON f.pollutant_key = p.pollutant_key
GROUP BY
    p.pollutant_name,
    p.unit
ORDER BY p.pollutant_name;
GO


-- 4. Check city-wise station and record coverage

SELECT
    s.selected_city,
    COUNT(DISTINCT s.station_key) AS total_stations,
    COUNT(*) AS total_measurements
FROM dbo.fact_air_quality_daily f
JOIN dbo.dim_station s
    ON f.station_key = s.station_key
GROUP BY s.selected_city
ORDER BY total_measurements DESC;
GO


-- 5. Check statistical outlier records

SELECT
    is_statistical_outlier,
    COUNT(*) AS total_records
FROM dbo.fact_air_quality_daily
GROUP BY is_statistical_outlier;
GO


-- 6. Check duplicate fact records

SELECT
    station_key,
    date_key,
    pollutant_key,
    COUNT(*) AS duplicate_count
FROM dbo.fact_air_quality_daily
GROUP BY
    station_key,
    date_key,
    pollutant_key
HAVING COUNT(*) > 1;
GO
