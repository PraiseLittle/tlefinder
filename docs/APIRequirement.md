# TLE Finder API Requirements

This document defines user-facing API requirements for TLE Finder. It is derived from `REQUIREMENT.md` and preserves a strict responsibility boundary: the API adapts HTTP requests to the shared core search workflow, owns optical-ground-station persistence, and does not implement the satellite-search engine.

## Scope

 1. [API-FR-01] The API shall provide programmatic access to the satellite-search capability and shall serve as the direct backend integration point used by the GUI.

 2. [API-FR-02] The API shall accept search inputs using a machine-readable representation of the shared search-request model so that equivalent GUI-originated API requests, direct API requests, and Python-module requests are interpreted consistently.

 3. [API-FR-03] The API shall return search outputs using a machine-readable representation of the shared search-response model so that ranked results, no-result responses, and errors have the same meaning across all interfaces.

 4. [API-FR-04] The API shall use domain terms, units, and value meanings consistently with `REQUIREMENT.md`, including TLE, optical ground station, apparent altitude, azimuth, satellite altitude, Sun proximity, match score, and candidate-selection threshold.

 5. [API-FR-05] The API shall not expose GUI-specific layout, form, or display behavior.

 6. [API-FR-06] The API shall not implement independent pass detection, filtering, scoring, ranking, orbit propagation, or TLE freshness logic outside the core Python search modules.

## Optical Ground Station List Persistence

 1. [API-FR-16] The API shall own persistence of the optical ground station list used by the GUI and API clients.

 2. [API-FR-17] The API shall store the optical ground station list in a backend-controlled YAML file.

 3. [API-FR-18] The API shall create the optical ground station list file on first access if the file does not already exist.

 4. [API-FR-19] The API shall persist optical ground station entries with a station name, geographic latitude, geographic longitude, and elevation above mean sea level.

 5. [API-FR-20] The API shall validate the full optical ground station list before writing it to the persistence file, including duplicate physical stations, duplicate station names with different coordinates, and invalid station fields.

 6. [API-FR-21] The API shall reject invalid optical ground station list updates with a machine-readable error response.

 7. [API-FR-22] The API shall preserve the previously persisted optical ground station list when a submitted list update is invalid or cannot be written completely.

 8. [API-FR-23] The API shall not require a search request to reference a persisted optical ground station entry.

 9. [API-FR-24] When a valid search request includes a named optical ground station that is not already present in the persisted list, the API shall add that optical ground station to the persisted list.

 10. [API-FR-25] The API shall compare optical ground stations for duplicate detection by normalizing latitude, longitude, and elevation to their first five decimal digits and treating matching normalized values as the same physical station.

 11. [API-FR-26] The persisted optical ground station list shall contain no more than one station name for the same physical station.

 12. [API-FR-27] If a submitted station uses coordinates equivalent to an already persisted station but provides a different name, the API shall preserve the existing persisted station name and shall not create a duplicate station entry.

 13. [API-FR-28] If the persisted optical ground station list cannot be loaded, created, or saved when required, the API shall return an explicit machine-readable error.

 14. [API-FR-29] The core Python search modules shall not read from or write to the persisted optical ground station list file.

## Search Request

 1. [API-FR-30] The API search request shall include the optical ground station parameters, search-window parameters, optional filtering criteria, requested result count, and candidate-selection threshold needed for that request.

 2. [API-FR-31] The API shall support a simple search request containing only the optical ground station, search-window start time, and search-window duration as user-provided search inputs.

 3. [API-FR-32] For a simple search request, the API shall submit the request to the core search workflow with the following system-defined default values for all other supported search criteria:

| Search criterion | Simple-search default |
| --- | --- |
| Minimum apparent altitude at culmination | 0 degrees |
| Maximum apparent altitude at culmination | 90 degrees |
| Pass start azimuth | Any valid azimuth |
| Pass end azimuth | Any valid azimuth |
| Azimuth at pass culmination | Any valid azimuth |
| Azimuth tolerance | Full valid azimuth range |
| Apparent-altitude tolerance | Full valid apparent-altitude range |
| Number of candidate satellites to return | 10 |
| Candidate-selection threshold | No threshold filtering |
| Sun-proximity constraints | `[0, 180]` degrees |
| Satellite-altitude constraints | `[200, 2000] km` |

 4. [API-FR-33] For a simple search request, the API shall submit the request to the core search workflow with the system default result count of 10 candidate satellites.

 5. [API-FR-34] For a simple search request, the API shall submit the request to the core search workflow with candidate-selection threshold filtering disabled.

 6. [API-FR-35] For a simple search request, the API shall not expose scoring configuration in the request; scoring and ranking shall remain owned by the core search workflow, where longer pass duration and earlier pass timing are considered by the core default scoring behavior.

 7. [API-FR-36] The API shall support an advanced search request that may include supported filtering criteria, requested result count, and candidate-selection threshold from the shared search-request model.

 8. [API-FR-37] The API shall allow a search request to define the optical ground station using geographic latitude, geographic longitude, and elevation above mean sea level, with a station name when the station is to be persisted.

 9. [API-FR-38] The API shall allow a search request to define the search-window start time in UTC or in local time with an explicitly specified UTC offset.

 10. [API-FR-39] The API shall allow a search request to define the search-window duration from the selected start time.

 11. [API-FR-40] The API shall allow an advanced search request to define minimum and/or maximum apparent altitude at culmination, expressed in degrees from 0 to 90.

 12. [API-FR-41] The API shall allow an advanced search request to define the desired pass start azimuth, pass end azimuth, and azimuth at pass culmination as independent criteria.

 13. [API-FR-42] The API shall allow an advanced search request to define tolerances for azimuth and apparent-altitude criteria so target values can be converted into acceptance ranges.

 14. [API-FR-43] The API shall allow an advanced search request to define the maximum number of candidate satellites to return.

 15. [API-FR-44] The API shall allow an advanced search request to define the candidate-selection threshold used as the minimum acceptable match score.

 16. [API-FR-45] The API shall allow an advanced search request to define minimum and/or maximum Sun-proximity constraints, expressed in degrees.

 17. [API-FR-46] The API shall allow an advanced search request to define minimum and/or maximum satellite-altitude constraints, expressed as height above the Earth's surface in kilometers.

 18. [API-FR-47] The API shall reject unsupported active search criteria that are not listed in this search-request section.

 19. [API-FR-48] The API shall not allow users or clients to modify scoring components, ranking criteria, or scoring weights in a search request.

## Request Validation and Error Handling

 1. [API-FR-49] The API shall validate optical ground station latitude as numeric and within `[-90, 90]` degrees.

 2. [API-FR-50] The API shall validate optical ground station longitude as numeric and within `[-180, 180]` degrees.

 3. [API-FR-51] The API shall validate optical ground station elevation as numeric, expressed in meters above mean sea level, and within `[-500, 8000] m`.

 4. [API-FR-52] The API shall validate search-window duration as greater than 0 minutes and no greater than 30 minutes.

 5. [API-FR-53] The API shall validate UTC search-window start times as ISO 8601 datetime values with an explicit UTC designator, such as `Z` or `+00:00`.

 6. [API-FR-54] The API shall validate local search-window start times as ISO 8601 date-time values with an explicit UTC offset using ISO 8601 offset format, such as `+01:00` or `-05:00`.

 7. [API-FR-55] The API shall reject local-time search-window start values whose UTC offset is missing, invalid, or unsupported.

 8. [API-FR-56] The API shall not infer the search UTC offset from the optical ground station location.

 9. [API-FR-57] The API shall validate apparent-altitude bounds against `[0, 90]` degrees and shall reject inconsistent minimum and maximum bounds before search execution.

 10. [API-FR-58] The API shall validate azimuth values against `[0, 360)` degrees.

 11. [API-FR-59] The API shall validate Sun-proximity values against `[0, 180]` degrees.

 12. [API-FR-60] The API shall validate satellite-altitude values against `[200, 15000] km`.

 13. [API-FR-61] The API shall validate result count as a strictly positive integer.

 14. [API-FR-62] The API shall validate candidate-selection threshold as numeric and within `[0, 100]`.

 15. [API-FR-63] The API shall reject any range constraint where `minimum > maximum`.

 16. [API-FR-64] The API shall return validation failures in a machine-readable error response that identifies the affected input and explains the validation failure.

 17. [API-FR-65] The API shall not execute a search request that fails request validation.

 18. [API-FR-66] The API shall return an explicit machine-readable error response when required TLE data is unavailable, stale, malformed, or otherwise prevents search execution.

## Search Execution

 1. [API-FR-67] The API shall translate valid API search requests into the shared core search-request model and submit them to the core Python search workflow.

 2. [API-FR-68] The API shall not implement an independent satellite-search engine that bypasses the core Python search modules.

 3. [API-FR-69] The API shall rely on the core TLE repository workflow for TLE acquisition, cache use, parsing, and freshness enforcement.

 4. [API-FR-70] The API shall not execute searches with TLE data reported by the core workflow as stale or unavailable.

 5. [API-FR-71] The API shall execute searches without relying on server-side user session state.

 6. [API-FR-72] Given the same search request, configuration, and TLE dataset, the API shall return the same search response.

## Search Response

 1. [API-FR-73] The API shall return zero, one, or more candidate satellites for the submitted search request.

 2. [API-FR-74] The API shall return search results in a machine-readable representation of the shared search-response model.

 3. [API-FR-75] The API shall return multiple candidate satellites in ranked order from most suitable to least suitable when the search response contains ranked results.

 4. [API-FR-76] The API shall return the match score for each returned candidate satellite.

 5. [API-FR-77] The API shall return the pass start time and pass end time for each returned candidate satellite.

 6. [API-FR-78] The API shall return the corresponding TLE data for each returned candidate satellite.

 7. [API-FR-79] The API shall return an explicit no-result response when no candidate satellite satisfies the submitted search request.

 8. [API-FR-80] The API shall return result times with an explicit UTC time reference so clients can interpret returned pass times unambiguously.

 9. [API-FR-81] The API shall return the candidate set produced by the core search workflow after core result limiting has been applied.

## Traceability

Traceability shall be updated after the API requirement set is stabilized.
