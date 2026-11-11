
USE AirScope;
GO

-- BUSINESS QUESTION 1:
-- Which city has the highest average PM2.5 and PM10?

WITH CityPollution AS
(
    SELECT
        s.selected_city,
        p.pollutant_name,
        p.unit,

        COUNT(*) AS total_measurements,

        COUNT(DISTINCT s.station_key) AS total_stations,

        ROUND(AVG(f.mean), 2) AS average_concentration

    FROM dbo.fact_air_quality_daily f

    INNER JOIN dbo.dim_station s
        ON f.station_key = s.station_key

    INNER JOIN dbo.dim_pollutant p
        ON f.pollutant_key = p.pollutant_key

    GROUP BY
        s.selected_city,
        p.pollutant_name,
        p.unit
),

CityRanking AS
(
    SELECT
        selected_city,
        pollutant_name,
        unit,
        total_stations,
        total_measurements,
        average_concentration,

        DENSE_RANK() OVER
        (
            PARTITION BY pollutant_name
            ORDER BY average_concentration DESC
        ) AS city_rank

    FROM CityPollution
)

SELECT
    pollutant_name,
    selected_city,
    total_stations,
    total_measurements,
    average_concentration,
    city_rank

FROM CityRanking

ORDER BY
    pollutant_name,
    city_rank;
GO
