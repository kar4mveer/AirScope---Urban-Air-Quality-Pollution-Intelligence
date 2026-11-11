
USE AirScope;
GO

-- BUSINESS QUESTION 3:
-- Which monitoring stations have the highest pollution concentrations?

WITH StationPollution AS
(
    SELECT
        s.station_id,
        s.station_name,
        s.selected_city,
        p.pollutant_name,

        COUNT(*) AS total_measurements,

        ROUND(AVG(f.mean), 2) AS average_concentration,

        ROUND(MAX(f.mean), 2) AS highest_daily_mean

    FROM dbo.fact_air_quality_daily f

    INNER JOIN dbo.dim_station s
        ON f.station_key = s.station_key

    INNER JOIN dbo.dim_pollutant p
        ON f.pollutant_key = p.pollutant_key

    GROUP BY
        s.station_id,
        s.station_name,
        s.selected_city,
        p.pollutant_name
),

StationRanking AS
(
    SELECT
        *,
        DENSE_RANK() OVER
        (
            PARTITION BY pollutant_name
            ORDER BY average_concentration DESC
        ) AS hotspot_rank

    FROM StationPollution
)

SELECT
    pollutant_name,
    hotspot_rank,
    station_name,
    selected_city,
    total_measurements,
    average_concentration,
    highest_daily_mean

FROM StationRanking

WHERE hotspot_rank <= 10

ORDER BY
    pollutant_name,
    hotspot_rank;
GO
