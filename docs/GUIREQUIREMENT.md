# TLE Finder GUI Requirements

This document defines user-facing GUI requirements for TLE Finder. It is derived from `REQUIREMENT.md` and intentionally stays at the level of user capabilities rather than layout or navigation details. The GUI is an API client: it collects user input, submits requests to the API, and displays API responses. It shall not perform API-owned persistence work or core-owned satellite-search work.

## Scope

 1. [GUI-FR-01] The GUI shall provide manual access to the satellite-search capability through the API.

 2. [GUI-FR-02] The GUI shall collect search inputs using the shared search-request model semantics so that equivalent GUI-originated API requests, direct API requests, and Python-module requests are interpreted consistently.

 3. [GUI-FR-03] The GUI shall display API search outputs using the shared search-response model semantics so that ranked results, no-result responses, and errors have the same meaning across all interfaces.

 4. [GUI-FR-04] The GUI shall use domain terms, units, and value meanings consistently with `REQUIREMENT.md`, including TLE, optical ground station, apparent altitude, azimuth, satellite altitude, Sun proximity, match score, and candidate-selection threshold.

 5. [GUI-FR-05] The GUI shall use the API as its direct backend integration point for search execution.

 6. [GUI-FR-06] The GUI shall not invoke the core Python search modules directly.

 7. [GUI-FR-07] The GUI shall not download, parse, cache, validate freshness for, or select TLE data directly.

 8. [GUI-FR-08] The GUI shall not compute satellite passes, pass metrics, filtering results, match scores, ranking, result limiting, or no-result decisions locally.

## Optical Ground Station Management

 1. [GUI-FR-09] The GUI shall provide a selectable list of optical ground stations for use in search requests.

 2. [GUI-FR-10] The GUI shall allow the user to maintain optical ground station entries, including station name, geographic latitude, geographic longitude, and elevation above mean sea level.

 3. [GUI-FR-11] The GUI shall allow the user to review the name, geographic position, and elevation of the selected optical ground station before executing a search.

 4. [GUI-FR-12] The GUI shall retrieve the persisted optical ground station list through the API.

 5. [GUI-FR-13] The GUI shall save user changes to the optical ground station list through the API.

 6. [GUI-FR-14] The GUI shall not read from or write to the persisted optical ground station YAML file directly.

 7. [GUI-FR-15] The GUI shall communicate API errors that prevent loading, creating, validating, or saving the optical ground station list.

 8. [GUI-FR-16] When executing a search from a selected optical ground station, the GUI shall include the selected station's name, latitude, longitude, and elevation in the submitted API request.

 9. [GUI-FR-17] The GUI may allow the user to submit a named optical ground station that is not already present in the persisted list, but the API shall own any resulting persistence update.

## Simple Search Configuration

 1. [GUI-FR-18] The GUI shall provide a simple search configuration workflow in which the user supplies only the optical ground station, search-window start time, and search-window duration as search inputs.

 2. [GUI-FR-19] The GUI shall allow a simple search request to use an optical ground station selected from the maintained optical ground station list.

 3. [GUI-FR-20] The GUI shall allow a simple search request to define the search-window start time in UTC or in local time with an explicitly specified UTC offset.

 4. [GUI-FR-21] The GUI shall provide a selectable UTC offset control when local time is used for the search-window start.

 5. [GUI-FR-22] The GUI shall allow a simple search request to define the search-window duration from the selected start time.

 6. [GUI-FR-23] The GUI shall not expose advanced filtering criteria, candidate-selection threshold controls, or scoring-weight controls as part of the simple search workflow.

 7. [GUI-FR-24] The GUI shall submit the simple search request to the API and shall rely on the API and core workflow to apply the system-defined simple-search defaults, including the default result count of 10 and no threshold filtering.

## Advanced Search Configuration

 1. [GUI-FR-25] The GUI shall provide an advanced search configuration workflow for users who need to control supported filtering criteria, requested result count, and candidate-selection threshold.

 2. [GUI-FR-26] The GUI shall allow an advanced search request to use an optical ground station selected from the maintained optical ground station list.

 3. [GUI-FR-27] The GUI shall allow an advanced search request to define the search-window start time in UTC or in local time with an explicitly specified UTC offset.

 4. [GUI-FR-28] The GUI shall provide a selectable UTC offset control when local time is used for the search-window start.

 5. [GUI-FR-29] The GUI shall allow an advanced search request to define the search-window duration from the selected start time.

 6. [GUI-FR-30] The GUI shall allow the user to define minimum and/or maximum apparent altitude at culmination, expressed in degrees from 0 to 90.

 7. [GUI-FR-31] The GUI shall allow the user to define the desired pass start azimuth, pass end azimuth, and azimuth at pass culmination as independent criteria.

 8. [GUI-FR-32] The GUI shall allow the user to define tolerances for azimuth and apparent-altitude criteria so target values can be converted into acceptance ranges.

 9. [GUI-FR-33] The GUI shall allow the user to define the maximum number of candidate satellites to return.

 10. [GUI-FR-34] The GUI shall allow the user to define the candidate-selection threshold used as the minimum acceptable match score.

 11. [GUI-FR-35] The GUI shall allow the user to define minimum and/or maximum Sun-proximity constraints, expressed in degrees.

 12. [GUI-FR-36] The GUI shall allow the user to define minimum and/or maximum satellite-altitude constraints, expressed as height above the Earth's surface in kilometers.

 13. [GUI-FR-37] The GUI shall not provide active controls for unsupported search criteria that are not listed in this advanced search section.

 14. [GUI-FR-38] The GUI shall not allow the user to modify scoring components, ranking criteria, or scoring weights.

 15. [GUI-FR-39] The GUI shall make it clear which advanced search criteria are required, which optional filtering criteria are available, and which optional filtering criteria are currently enabled.

 16. [GUI-FR-40] The GUI shall show the unit of measure for each numeric search criterion where a unit applies.

## Input Validation and User Feedback

 1. [GUI-FR-41] The GUI shall validate optical ground station latitude as numeric and within `[-90, 90]` degrees before submitting a request to the API.

 2. [GUI-FR-42] The GUI shall validate optical ground station longitude as numeric and within `[-180, 180]` degrees before submitting a request to the API.

 3. [GUI-FR-43] The GUI shall validate optical ground station elevation as numeric, expressed in meters above mean sea level, and within `[-500, 8000] m` before submitting a request to the API.

 4. [GUI-FR-44] The GUI shall reject any search-window duration that is not greater than 0 minutes and no greater than 30 minutes before submitting a request to the API.

 5. [GUI-FR-45] The GUI shall validate apparent-altitude bounds against `[0, 90]` degrees and shall reject inconsistent minimum and maximum bounds before submitting a request to the API.

 6. [GUI-FR-46] The GUI shall validate azimuth values against `[0, 360)` degrees before submitting a request to the API.

 7. [GUI-FR-47] The GUI shall validate Sun-proximity values against `[0, 180]` degrees before submitting a request to the API.

 8. [GUI-FR-48] The GUI shall validate satellite-altitude values against `[200, 15000] km` before submitting a request to the API.

 9. [GUI-FR-49] The GUI shall validate result count as a strictly positive integer before submitting a request to the API.

 10. [GUI-FR-50] The GUI shall validate candidate-selection threshold as numeric and within `[0, 100]` before submitting a request to the API.

 11. [GUI-FR-51] The GUI shall reject any range constraint where `minimum > maximum` before submitting a request to the API.

 12. [GUI-FR-52] The GUI shall require every local-time search-window start value to include an explicit, valid, and supported UTC offset using ISO 8601 offset format, such as `+01:00` or `-05:00`.

 13. [GUI-FR-53] The GUI shall not infer the search UTC offset from the selected optical ground station.

 14. [GUI-FR-54] The GUI shall present GUI-side validation errors in a way that identifies the affected input and explains what the user must correct.

 15. [GUI-FR-55] The GUI shall prevent submission of a search request that fails GUI-side validation.

 16. [GUI-FR-56] The GUI shall communicate API validation errors returned for a submitted request, because API validation remains authoritative.

## Search Execution

 1. [GUI-FR-57] The GUI shall submit valid search requests to the API.

 2. [GUI-FR-58] The GUI shall communicate when a search is in progress.

 3. [GUI-FR-59] The GUI shall communicate when the API reports that required TLE data is unavailable, stale, malformed, or otherwise prevents search execution.

 4. [GUI-FR-60] The GUI shall preserve the user's configured search criteria after search execution so the user can review or adjust the request.

 5. [GUI-FR-61] The GUI shall not call the core search workflow, pass-analysis functions, filtering functions, scoring functions, ranking functions, or TLE repository functions directly.

## Search Results

 1. [GUI-FR-62] The GUI shall display zero, one, or more candidate satellites returned by the API for a search request.

 2. [GUI-FR-63] The GUI shall preserve the API-provided candidate order and shall not re-rank returned candidate satellites.

 3. [GUI-FR-64] The GUI shall display the match score for each returned candidate satellite.

 4. [GUI-FR-65] The GUI shall display the pass start time and pass end time for each returned candidate satellite.

 5. [GUI-FR-66] The GUI shall display the corresponding TLE data for each returned candidate satellite.

 6. [GUI-FR-67] The GUI shall clearly communicate when the API returns a no-result response for the submitted search request.

 7. [GUI-FR-68] The GUI shall display result times with an explicit UTC time reference, or with the selected UTC offset while also making the displayed time reference explicit.

 8. [GUI-FR-69] The GUI shall display the candidate set returned by the API and shall not apply additional result limiting beyond the API response.

## Traceability

| GUI Requirement | Source in `REQUIREMENT.md` |
| --- | --- |
| GUI-FR-01 to GUI-FR-08 | Modes of Operation; Common Search Model; Results and Interface Behavior; Non-Functional Requirements |
| GUI-FR-09 to GUI-FR-17 | GUI Requirements; Optical Ground Station Persistence; FR-29 to FR-35 |
| GUI-FR-18 to GUI-FR-24 | GUI Requirements; Simple Search Default Behavior; Time Input and Output Behavior |
| GUI-FR-25 to GUI-FR-40 | Search Inputs; GUI Requirements; Match Score and Ranking Behavior |
| GUI-FR-41 to GUI-FR-56 | Validation Rules; Time Input and Output Behavior |
| GUI-FR-57 to GUI-FR-61 | Modes of Operation; TLE Data Requirements; Candidate Search and Evaluation |
| GUI-FR-62 to GUI-FR-69 | Search Outputs; Results and Interface Behavior; Time Input and Output Behavior |
