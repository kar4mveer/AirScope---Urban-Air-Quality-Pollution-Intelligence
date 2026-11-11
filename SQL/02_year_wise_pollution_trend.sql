
USE AirScope;
GO

-- BUSINESS QUESTION 2:
-- Has pollution increased or decreased from 2022 to 2024?

WITH YearlyPollution AS
(
    SELECT
        d.[year],
        p.pollutant_name,

        COUNT(*) AS total_measurements,

        COUNT(DISTINCT f.station_key) AS total_stations,

        ROUND(AVG(f.mean), 2) AS average_concentration

    FROM dbo.fact_air_quality_daily f

    INNER JOIN dbo.dim_date d
        ON f.date_key = d.date_key

    INNER JOIN dbo.dim_pollutant p
        ON f.pollutant_key = p.pollutant_key

    GROUP BY
        d.[year],
        p.pollutant_name
),

PollutionComparison AS
(
    SELECT
        year,
        pollutant_name,
        total_measurements,
        total_stations,
        average_concentration,

        FIRST_VALUE(average_concentration) OVER
        (
            PARTITION BY pollutant_name
            ORDER BY year
        ) AS baseline_2022

    FROM YearlyPollution
)

SELECT
    year,
    pollutant_name,
    total_stations,
    total_measurements,
    average_concentration,
    baseline_2022,

    ROUND(
        (
            (average_concentration - baseline_2022)
            / NULLIF(baseline_2022, 0)
        ) * 100,
        2
    ) AS percentage_change_from_2022

FROM PollutionComparison

ORDER BY
    pollutant_name,
    year;
GO
