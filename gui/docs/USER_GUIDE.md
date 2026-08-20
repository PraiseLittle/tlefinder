# GUI User Guide

## Open TLE Finder

Start the complete application from the repository root:

~~~powershell
./scripts/dev.ps1
~~~

Then open <http://127.0.0.1:2627>. Docker users open the same address after \`docker compose up --detach --build --wait\`.

The GUI must be able to reach the API before it can load or save stations. The header and error panels indicate whether the initial API request succeeded.

## Manage ground stations

The left panel contains the persisted optical ground stations.

- Select a station to use its coordinates for the next search.
- Add a station with a unique name, latitude, longitude, and elevation.
- Edit a station to replace its saved values.
- Delete a station after confirming the action.

Latitude must be between -90 and 90 degrees, longitude between -180 and 180 degrees, and elevation between -500 and 8000 metres. Changes are saved by the API and survive container recreation through the station-data volume.

## Set the time window

Choose UTC or Local + offset:

- UTC accepts an ISO-8601 value ending in \`Z\` or containing an explicit offset.
- Local mode combines the selected wall-clock value with the offset shown next to it.
- The offset is not inferred from the station.
- Now + 5 min fills both representations with a start five minutes from the current instant.
- Duration must be greater than zero and no more than 30 minutes.

The default form starts at the next whole UTC hour and uses a 15-minute window.

## Choose TLE freshness

\`24H\` accepts TLE records whose epochs are at most 24 hours from the search time. \`1W\` allows records up to one week old. A wider limit can return more candidates but uses older orbital data.

## Choose a search mode

Simple mode searches the active satellite group with broad standard ranges, a zero score threshold, and up to 10 results.

Advanced mode adds:

- Active, visual, or amateur satellite group.
- Result limit and score threshold.
- Culmination-altitude minimum and maximum.
- Sun-proximity minimum and maximum.
- Satellite-altitude minimum and maximum.
- Start, culmination, and end azimuth targets with tolerances.

Each geometry or metric section has its own enable switch. A value in a disabled section is not sent to the API.

## Read the results

Run search sends the validated request to the API. The result panel shows progress, a field/API error, a no-result explanation, or ranked candidates.

Each result summary contains:

- Rank, match score, satellite name, group, and NORAD identifier.
- Start and end time plus pass duration.
- Culmination altitude and azimuth.
- Satellite altitude and Sun proximity when available.

Open a result card for its complete pass geometry, metrics, exact TLE, and sky chart. The first result opens automatically.

The sky chart uses:

- North at the top and east at the right.
- The outer circle for the horizon and the centre for the zenith.
- An orange path from pass start through culmination to pass end.
- A filled orange point for culmination.
- A yellow Sun and 10-degree and 20-degree angular halos when applicable.

The chart keeps the ground-station coordinates used for that completed search even if another station is selected later.

## Copy times and TLE data

The Start, Culmination, and End copy buttons emit scheduler-ready ISO 8601:

- UTC example: \`2026-08-20T18:20:00Z\`
- Offset example: \`2026-08-20T20:20:00+02:00\`

The copied value always contains \`T\` between the date and time. The TLE copy button writes the satellite name followed by line 1 and line 2 on separate lines.

## Resolve common problems

- If stations cannot load, confirm the API is running on port 2626 or that \`VITE_API_BASE_URL\` points to the correct versioned base.
- If Run search is disabled by validation, review the messages beside the time window and enabled criteria.
- If the API reports stale or unavailable TLE data, verify network access and retry or select the one-week age limit when appropriate.
- If no result matches, widen the window, loosen enabled criteria, lower the score threshold, or try another satellite group in Advanced mode.
