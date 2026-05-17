# TLE Finder

TLE Finder is a software system intended to identify the most suitable satellite to track from an optical ground station based on user-defined observation constraints. TLEs (Two-Line Elements) are standardized orbital element sets describing Earth-orbiting objects at a given epoch.

## Definitions and Terms

 1. `TLE (Two-Line Element)`: A standardized orbital-data format describing the orbit of an Earth-orbiting object at a given epoch.

 2. `Optical ground station`: The observing site from which the search is performed, defined at minimum by geographic latitude, geographic longitude, and elevation above mean sea level.

 3. `Search request`: The complete set of user inputs needed to execute one search, including time, location, filtering criteria, requested result count, and candidate-selection threshold.

 4. `Search response`: The complete set of outputs returned by one search, including zero, one, or more candidate satellites and any associated result data.

 5. `Shared search-request model`: The common structured representation of a search request used by the GUI, the API, and the Python modules.

 6. `Shared search-response model`: The common structured representation of a search response used by the GUI, the API, and the Python modules.

 7. `Search window`: The time interval over which the system searches for candidate passes, defined by a start time and a duration.

 8. `Local time with explicitly specified UTC offset`: A local date and time value provided together with an explicit UTC offset, so that the time can be converted unambiguously.

 9.  `Candidate satellite`: An Earth-orbiting object considered by the system during the search.

 10. `Candidate pass`: One pass of a candidate satellite that occurs within the search window for the specified optical ground station.

 11. `Pass start time`: The time at which the candidate pass begins according to the system pass-detection criteria.

 12. `Pass end time`: The time at which the candidate pass ends according to the system pass-detection criteria.

 13. `Culmination`: The instant during a pass at which the candidate satellite reaches its maximum apparent altitude as seen from the optical ground station.

 14. `Azimuth`: The apparent horizontal direction of the satellite, expressed in degrees and measured clockwise from geographic north.

 15. `Apparent altitude`: The apparent elevation angle of the satellite above the local horizon, expressed in degrees from 0 to 90.

 16. `Satellite altitude`: The height of the satellite above the Earth's surface, expressed in kilometers, and distinct from apparent altitude above the local horizon.

 17. `Acceptance range`: The interval within which a candidate value is considered acceptable, defined either directly by minimum and maximum bounds or indirectly by a target value and an associated tolerance.

 18. `Sun proximity`: The closest angular separation, expressed in degrees, between the Sun and the apparent satellite pass trajectory as seen from the optical ground station.

 19. `Match score`: The numerical indication, expressed on a 0 to 100 scale where higher is better, of how well a candidate pass satisfies the scoring criteria for a search request.

 20. `Candidate-selection threshold`: The minimum acceptable match score, expressed on the same 0 to 100 scale as the match score, required for a candidate pass to be returned by the system.

 21. `Satellite group`: The named TLE source group used to select the candidate satellite dataset before orbit propagation.

 22. `Candidate-pass duration`: The elapsed time between the detected pass start time and detected pass end time for a candidate pass.

 23. `Pass-timing preference`: A scoring preference that rewards candidate passes that become observable sooner relative to the search-window start.

 24. `Advanced search`: The API search workflow that exposes the full supported search-input set instead of applying the simple-search preset.

## Operational Requirements

### 1. Modes of Operation

 1. The system shall provide a graphical user interface (GUI) for manual search configuration and review of search results.
 2. The system shall provide an application programming interface (API) for programmatic search configuration and retrieval of search results.
 3. The system shall expose the core search engine as importable Python modules for use in scripts and external applications.
 4. The GUI, API, and Python modules shall provide access to the same search capability and shall operate on the same input model.
 5. The GUI shall use the API as its backend integration point for search execution and shall not invoke the core Python search modules directly.

### 2. Search Inputs

 1. The system shall allow the user to define the optical ground station, including its geographic position and elevation.
 2. The system shall allow the user to define the start time of the search window either in UTC or in local time with an explicitly specified UTC offset.
 3. The system shall allow the user to define the duration of the search window from the selected start time.
 4. The maximum search-window duration for a single search request shall be 30 minutes.
 5. The system shall allow the user to define a minimum and/or maximum apparent altitude at culmination, in degrees, within the range 0 to 90.
 6. The system shall allow the user to define the pass start azimuth.
 7. The system shall allow the user to define the pass end azimuth.
 8. The system shall allow the user to define the azimuth at pass culmination.
 9. The system shall allow the user to define acceptable tolerances on azimuth and apparent altitude values used during the search, such that each target value and tolerance define an acceptance range.
 10. The system shall allow the user to define the number of candidate satellites to return.
 11. The system shall allow the user to define a candidate-selection threshold representing the minimum acceptable match score for a candidate pass.
 12. The system shall allow the user to define Sun-proximity constraints for a candidate pass, expressed as a minimum and/or maximum acceptable Sun proximity, in degrees, between the Sun and the apparent satellite pass trajectory as seen from the optical ground station.
 13. The system shall allow the user to define minimum and/or maximum satellite altitude constraints, where satellite altitude is measured as height above the Earth's surface.
 14. The system shall allow full-search and advanced-search requests to define the satellite group used to select the TLE source dataset.

### 3. Search Outputs

 1. The system shall return zero, one, or more candidate satellites for the search request.
 2. The system shall allow the user to retrieve up to the requested number of candidate satellites that satisfy the configured constraints and candidate-selection threshold.
 3. For each returned candidate satellite, the system shall provide the corresponding TLE data.
 4. For each returned candidate satellite, the system shall provide the associated pass start time and pass end time.
 5. For each returned candidate satellite, the system shall provide a match score indicating how well the corresponding candidate pass matches the user-defined search criteria.
 6. When more than one candidate satellite is returned, the system shall present the candidate satellites in ranked order from most suitable to least suitable.
 7. If no candidate satellite satisfies the configured constraints, the system shall return a no-result response for the search request.
 8. The GUI shall display the search results to the user.
 9. The API shall return the search results in a machine-readable form.
 10. The Python modules shall return the search results in a programmatically usable form.

### 4. GUI Requirements

 1. The GUI shall provide a maintainable list of optical ground stations for use in search requests, with each station entry containing at least geographic latitude, geographic longitude, and elevation above mean sea level.
 2. The GUI shall provide a simple search workflow that allows the user to configure and execute a search using an optical ground station, a search-window start time, and a search-window duration, while the GUI or API applies system-defined default values for all other supported search criteria before submitting the search to the core search engine.
 3. The GUI shall provide a full search workflow that allows the user to configure and execute a search using the supported search inputs defined in Search Inputs 1 through 14, including filtering criteria, requested result count, candidate-selection threshold, and satellite group.
 4. The GUI shall allow the user to choose the UTC offset used for local-time search-window start values.

### 5. Optical Ground Station Persistence

 1. The API shall own persistence of the optical ground station list used by the GUI and API clients.
 2. The API shall store the persisted optical ground station list in a backend-controlled YAML file.
 3. If the persisted optical ground station list file does not exist, the API shall create the file on first access.
 4. Each persisted optical ground station entry shall contain a station name, geographic latitude, geographic longitude, and elevation above mean sea level.
 5. The GUI shall access the persisted optical ground station list only through the API.
 6. The core Python search modules shall not read from or write to the persisted optical ground station list file.
 7. A search request may use an optical ground station that is not already present in the persisted optical ground station list by providing a station name, latitude, longitude, and elevation.
 8. When a valid search request uses a named optical ground station that is not already present in the persisted list, the API shall add that optical ground station to the persisted list.
 9. The API shall treat two optical ground station entries as the same physical station when their latitude, longitude, and elevation values match after normalizing each value to its first five decimal digits.
 10. The persisted optical ground station list shall contain no more than one station name for the same physical station.
 11. If a submitted station uses coordinates equivalent to an already persisted station but provides a different name, the API shall preserve the existing persisted station name and shall not create a duplicate station entry.
 12. If a submitted station list update contains duplicate physical stations, duplicate station names with different coordinates, invalid station fields, or cannot be written completely, the API shall reject the update and preserve the previously persisted list.
 13. If the persisted optical ground station list cannot be loaded, created, or saved when required, the API shall return an explicit machine-readable error.

### 6. Simple Search Preset Behavior

 1. A simple search shall be a GUI or API workflow preset and shall not be a distinct core search-engine mode.
 2. A simple search workflow shall require the user to provide an optical ground station, a search-window start time, and a search-window duration.
 3. The GUI or API shall transform a simple search into the same shared search-request model used for full searches by applying explicit system-defined default values for every supported search criterion that is not provided by the user.
 4. The simple-search default result count shall be 10 candidate satellites.
 5. The simple-search default candidate-selection threshold shall be `0` on the 0 to 100 match-score scale, so threshold filtering does not reject any candidate pass that otherwise satisfies the simple-search default criteria.
 6. The simple-search default criteria shall be:

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
| Candidate-selection threshold | `0` |
| Sun-proximity constraints | `[0, 180]` degrees |
| Satellite-altitude constraints | `[200, 2000] km` |
| Satellite group | `active` |
| Scoring criteria | Pass-duration scoring and pass-timing scoring |

 7. A simple search workflow shall use the `active` satellite group and shall not expose satellite-group selection unless a future requirement explicitly adds that capability to simple search.
 8. A simple search workflow shall use a core-supported default scoring behavior in which pass-duration scoring and pass-timing scoring both contribute to the match score.
 9. The GUI or API shall not expose scoring configuration for simple search and shall not compute pass-duration scoring, pass-timing scoring, scoring-component combination, thresholding, ranking, or result limiting outside the core search workflow.
 10. After defaults are applied, the core search engine shall process the resulting simple-search request using the same validation, propagation, filtering, scoring, threshold, ranking, and result-limiting workflow used for any other search request.
 11. The core search engine shall not receive, store, or branch on a simple-search or full-search mode flag.

### 7. Match Score and Ranking Behavior

 1. The system shall compute a match score for every candidate pass that satisfies the mandatory filtering criteria for a search request.
 2. The match score shall use a numeric scale from 0 to 100, where 0 represents the lowest suitability and 100 represents the highest suitability.
 3. The candidate-selection threshold shall use the same 0 to 100 scale as the match score.
 4. The system shall reject any candidate pass whose match score is lower than the configured candidate-selection threshold.
 5. The match score shall be computed as a deterministic combination of normalized scoring-component values.
 6. Each scoring-component value shall be normalized to the 0 to 100 match-score scale before scoring-component combination is applied.
 7. The system shall use system-defined scoring components and a system-defined scoring-component combination defined by the application requirements or core design.
 8. The system shall not allow users, GUI clients, or API clients to modify scoring components, ranking criteria, or scoring weights in a search request.
 9. Non-applicable scoring components shall not contribute to the match score.
 10. The system shall support a pass-duration scoring component that rewards longer candidate-pass duration.
 11. The pass-duration scoring component shall rank a longer candidate pass higher than an otherwise equivalent shorter candidate pass.
 12. The system shall support a pass-timing scoring component that rewards candidate passes that become observable sooner relative to the search-window start.
 13. For pass-timing scoring, the system shall compare the candidate pass observable start within the search window, defined as the later of the detected pass start time and the search-window start time.
 14. The pass-timing scoring component shall rank a candidate pass with an earlier observable start higher than an otherwise equivalent candidate pass with a later observable start.
 15. The default simple-search scoring behavior shall use the pass-duration scoring component and the pass-timing scoring component; the exact scoring-component combination shall be core-owned and not configurable through the API or GUI.
 16. The core search engine shall not use simple-search or full-search workflow labels to select scoring behavior.
 17. The official match score shall not be affected by hidden heuristics or undeclared scoring inputs.
 18. When more than one candidate pass has the same match score, ranking shall remain deterministic.
 19. Equal-score candidates shall be ordered by earlier pass start time first, then by lower satellite catalog number when available.

### 8. Validation Rules

 1. The system shall require the optical ground station latitude to be numeric and within `[-90, 90]` degrees.
 2. The system shall require the optical ground station longitude to be numeric and within `[-180, 180]` degrees.
 3. The system shall require the optical ground station elevation to be numeric, expressed in meters above mean sea level, and within `[-500, 8000] m`.
 4. The system shall require search-window duration to be greater than 0 minutes and no greater than 30 minutes.
 5. The system shall require local time input to include an explicit UTC offset.
 6. The shared search-request model shall require `SearchWindow.start_at` to be timezone-aware, and naive date-time values shall be invalid.
 7. The system shall not infer the search UTC offset from the optical ground station.
 8. The system shall require culmination apparent-altitude minimum and maximum bounds to be within `[0, 90]` degrees.
 9. The system shall require azimuth values to be numeric and within `[0, 360)` degrees.
 10. The system shall require Sun-proximity values to be numeric and within `[0, 180]` degrees.
 11. The system shall require satellite-altitude values to be numeric, expressed in kilometers, and within `[200, 15000] km`.
 12. The system shall reject any range constraint where `minimum > maximum`.
 13. The system shall require the requested result count to be a strictly positive integer.
 14. The system shall require the candidate-selection threshold to be numeric and within `[0, 100]`.
 15. The system shall require the satellite group, when provided, to be one of `active`, `visual`, or `amateur`; omitted satellite group values shall default to `active`, and unsupported values shall be rejected with an explicit machine-readable validation error.

### 9. Time Input and Output Behavior

 1. The core shared search-request model shall accept the search-window start time as a timezone-aware datetime value.
 2. The API shall accept UTC search-window start times using an ISO 8601 datetime value with an explicit UTC designator, such as `Z` or `+00:00`.
 3. The API shall accept local search-window start times using a local ISO 8601 date-time value together with an explicit UTC offset.
 4. The GUI shall allow the user to enter or select the local date and time for the search-window start and shall provide a selectable UTC offset control.
 5. UTC offsets shall use ISO 8601 offset format, such as `+01:00` or `-05:00`.
 6. The system shall reject local search-window start values whose UTC offset is missing, invalid, or unsupported.
 7. The system shall normalize all accepted search-window start values to UTC before orbit propagation.
 8. The system shall return candidate pass times with an explicit UTC time reference.
 9. The GUI may display returned candidate pass times in the selected UTC offset, but it shall also make the displayed time reference explicit.

### 10. TLE Data Requirements

 1. The system shall obtain TLE data through the core TLE repository workflow before candidate orbit propagation.
 2. The system shall support configured TLE source groups used to select the candidate dataset before propagation.
 3. The supported TLE source groups shall be `active`, `visual`, and `amateur`.
 4. If a search request omits the TLE source group after workflow defaults have been applied, the system shall use the `active` TLE source group.
 5. The TLE repository workflow shall be responsible for TLE acquisition, local cache use, parsing, and freshness enforcement.
 6. The system shall parse TLE records as named three-line records containing a satellite name, TLE line 1, and TLE line 2.
 7. The system shall reject malformed TLE records that do not contain valid TLE line prefixes or matching catalog numbers.
 8. The system shall derive the TLE epoch from TLE line 1 and use that epoch to evaluate TLE freshness.
 9. The system shall evaluate freshness for the requested TLE dataset using the TLE epochs and a maximum allowed age of 24 hours relative to the search execution reference time.
 10. The system shall not propagate candidate passes from a requested TLE dataset that fails the freshness check.
 11. If the requested candidate dataset does not satisfy the freshness requirement, the system shall return an explicit error and shall not return a no-result response.
 12. The system shall preserve the raw TLE data associated with each returned candidate satellite.

### 11. Pass Detection Criteria

 1. The system shall detect candidate passes by propagating candidate orbits for the configured optical ground station and normalized UTC search interval.
 2. The pass-detection horizon shall be an apparent altitude of 10 degrees above the local horizon.
 3. The pass start time shall be the rise event at which the candidate satellite crosses the pass-detection horizon upward.
 4. The pass end time shall be the set event at which the candidate satellite crosses the pass-detection horizon downward.
 5. The pass culmination time shall be the event at which the candidate satellite reaches its maximum apparent altitude between the pass start and pass end events.
 6. A candidate pass shall be considered part of a search when its pass interval overlaps the requested search window.
 7. The system shall include a candidate pass that overlaps the search window even when the pass start time, culmination time, or pass end time occurs outside the requested search window.
 8. The system shall search sufficient time before and after the requested search window to determine the real pass start, culmination, and end events for overlapping passes when those events are available.
 9. If a real pass start or end event cannot be determined but the pass can still be bounded by a culmination event and the opposite endpoint, the system may estimate the missing endpoint symmetrically around culmination and shall mark the pass as partial in diagnostics.
 10. The system shall compute pass start azimuth, pass end azimuth, culmination azimuth, and apparent altitude at culmination from the propagated topocentric position at the corresponding event times.
 11. The system shall compute candidate-pass duration from the detected pass start time and pass end time.
 12. The system shall compute pass-level satellite altitude as the mean satellite altitude over the full detected pass.
 13. The system shall compute Sun proximity as the minimum angular separation between the Sun and the apparent satellite trajectory over the full detected pass.
 14. The system shall compute pass-level derived metrics using at least 49 evenly spaced samples from pass start to pass end.
 15. Candidate pass detection and pass-level metric computation shall be deterministic for the same search request, optical ground station, and TLE dataset.

## Functional Requirements

The functional requirements below are written to be explicitly traceable to the operational requirements above.

### 1. Common Search Model

 1. [FR-01] The system shall define a shared search-request model that contains the optical ground station parameters, search-window parameters, filtering criteria, requested result count, candidate-selection threshold, satellite group, and system-selected scoring behavior needed to execute a search request. (related to: modes of operation 4; search inputs 1-14)

 2. [FR-02] The system shall define a shared search-response model that can represent zero, one, or more candidate satellites together with their ranking, associated candidate-pass data, and any no-result response. (related to: search outputs 1, 6, 7, 9, 10)

 3. [FR-03] The GUI shall submit search requests through the API, and the API and Python modules shall invoke the same core search workflow and interpret equivalent search requests in the same way. Simple-search and full-search workflow differences shall be resolved by the GUI or API before a shared core search request is submitted. (related to: modes of operation 1-5)

### 2. Search Request Handling

 1. [FR-04] The system shall validate the optical ground station definition in the search request before executing the search, including latitude, longitude, and elevation. (related to: search input 1)

 2. [FR-05] The system shall accept in the search request a user-defined start time for the search window in either UTC or local time with an explicitly specified UTC offset, and shall convert it to the internal time reference used by the search engine before propagation without inferring the UTC offset from the optical ground station location. (related to: search input 2)

 3. [FR-06] The system shall accept in the search request a user-defined search-window duration and shall reject any search request whose search window exceeds 30 minutes. (related to: search inputs 3, 4)

 4. [FR-07] The system shall allow the user to set a minimum apparent altitude at culmination, a maximum apparent altitude at culmination, or both, and shall reject any bound outside the range 0 to 90 degrees or any inconsistent bound pair. (related to: search input 5)

 5. [FR-08] The system shall allow the user to specify the desired pass start azimuth, pass end azimuth, and azimuth at pass culmination as independent search criteria. (related to: search inputs 6, 7, 8)

 6. [FR-09] The system shall allow the user to define acceptable azimuth and apparent altitude tolerances and shall apply those tolerances by converting each target value into an acceptance range used to compare candidate passes to the requested geometry. (related to: search input 9)

 7. [FR-11] The system shall allow the user to request the maximum number of candidate satellites to be returned for a search. (related to: search input 10)

 8. [FR-12] The system shall allow the user to define a candidate-selection threshold and shall apply that threshold to the match score generated for each candidate pass by the search engine. (related to: search input 11)

 9. [FR-13] The system shall allow the user to define minimum and/or maximum Sun-proximity constraints and shall interpret them as an acceptance range on the closest angular separation between the Sun and the apparent satellite pass trajectory. (related to: search input 12)

 10. [FR-14] The system shall allow the user to define minimum and/or maximum satellite-altitude constraints, where satellite altitude is measured above the Earth's surface. (related to: search input 13)

 11. [FR-15] The system shall allow full-search and advanced-search requests to define the satellite group as `active`, `visual`, or `amateur`, shall default omitted satellite group values to `active`, and shall reject unsupported values with a machine-readable validation error through the API. (related to: search input 14; validation rule 15; TLE data requirements 2-4)

### 3. Candidate Search and Evaluation

 1. [FR-16] The system shall obtain the TLE records required for the selected satellite group in the search request and shall preserve the TLE associated with each returned candidate satellite. (related to: search input 14; search outputs 3)

 2. [FR-17] The system shall propagate candidate orbits from the selected TLE data over the search window for the configured optical ground station in order to detect candidate passes. (related to: search inputs 1, 2, 3, 14; search outputs 1)

 3. [FR-18] For each detected candidate pass, the system shall determine the pass start time, pass end time, candidate-pass duration, pass start azimuth, pass end azimuth, culmination time, apparent altitude at culmination, and azimuth at culmination. (related to: search inputs 5-8; search outputs 4)

 4. [FR-19] For each detected candidate pass, the system shall compute the comparison data needed to evaluate every enabled user constraint, including apparent altitude, azimuth, Sun proximity, and satellite altitude. (related to: search inputs 5-13; search outputs 5)

 5. [FR-20] The system shall exclude any candidate pass that falls outside at least one mandatory user-defined acceptance range, whether that range is entered directly as minimum and maximum bounds or derived from a target value and tolerance. (related to: search inputs 5-13; search outputs 1, 2, 7)

 6. [FR-21] The system shall compute a match score for each candidate pass that satisfies the mandatory acceptance ranges, including the default simple-search scoring behavior that considers pass duration and pass timing when selected, and shall reject any candidate pass whose match score does not meet the configured candidate-selection threshold. (related to: search input 11; search outputs 5, 6; match score and ranking behavior 10-15)

### 4. Results and Interface Behavior

 1. [FR-22] The system shall rank all returned candidate satellites from most suitable to least suitable according to the match score of the corresponding candidate pass. (related to: search outputs 5, 6)

 2. [FR-23] The system shall limit the returned result set to the number of candidate satellites requested by the user after ranking has been applied. (related to: search input 10; search outputs 2, 6)

 3. [FR-24] For each returned candidate satellite, the system shall provide the corresponding TLE data, pass start time, pass end time, and match score as the indication of fit to the user-defined criteria. (related to: search outputs 3, 4, 5)

 4. [FR-25] If no candidate satellite satisfies the configured constraints and candidate-selection threshold, the system shall return an explicit no-result response for the search request. (related to: search outputs 1, 7)

 5. [FR-26] The GUI shall provide a manual data-entry mechanism for the supported search-request inputs and shall display either the ranked list of candidate satellites or the no-result response. (related to: modes of operation 1; search outputs 7, 8)

 6. [FR-27] The API shall accept a machine-readable representation of the shared search-request model and shall return a machine-readable representation of the shared search-response model. (related to: modes of operation 2, 4; search outputs 9)

 7. [FR-28] The Python modules shall expose callable search functions or classes that accept the shared search-request model and return a programmatically usable shared search-response model. (related to: modes of operation 3, 4; search outputs 10)

### 5. Optical Ground Station Persistence

 1. [FR-29] The API shall provide the persistence mechanism for the optical ground station list and shall store that list in a backend-controlled YAML file. (related to: optical ground station persistence 1, 2)

 2. [FR-30] The API shall create the optical ground station list file on first access if the file does not already exist. (related to: optical ground station persistence 3)

 3. [FR-31] The API shall persist each optical ground station entry with a station name, latitude, longitude, and elevation above mean sea level. (related to: optical ground station persistence 4)

 4. [FR-32] The GUI shall retrieve and save optical ground station list data through the API, and the core Python search modules shall not directly access the optical ground station persistence file. (related to: optical ground station persistence 5, 6)

 5. [FR-33] The API shall accept search requests that define a named optical ground station not already present in the persisted optical ground station list, and shall add the station to the persisted list when the request is valid. (related to: optical ground station persistence 7, 8)

 6. [FR-34] The API shall compare optical ground stations for duplicate detection by normalizing latitude, longitude, and elevation to their first five decimal digits and treating matching normalized values as the same physical station. (related to: optical ground station persistence 9, 10, 11)

 7. [FR-35] The API shall reject invalid optical ground station list updates without modifying the previously persisted list and shall return a machine-readable error when loading, creating, validating, or saving the list fails. (related to: optical ground station persistence 12, 13)

## Non-Functional Requirements

 1. The system shall use TLE data that is no more than 24 hours old at the time of search execution.

 2. If TLE data no more than 24 hours old is not available for the search request, the system shall return an explicit error and shall not execute the search with older TLE data.

 3. The system shall interpret all date-time inputs unambiguously, including UTC or local time with an explicitly specified UTC offset, and shall normalize time values before executing the search.

 4. Given the same search request, configuration, and TLE dataset, the system shall return the same ranked results.

 5. The software shall include unit tests covering the core search logic, input validation, time conversion, constraint evaluation, pass-duration scoring, pass-timing scoring, satellite-group validation, and ranking behavior.

 6. The software shall include integration tests covering the Python modules and the API, including simple-search default request conversion and advanced-search satellite-group handling.

 7. The system shall be validated against representative benchmark cases to confirm candidate-pass detection, constraint filtering, and ranking behavior.

 8. The core search engine shall be separable from the GUI and API so that it can be reused and tested independently.
