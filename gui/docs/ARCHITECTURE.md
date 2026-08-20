# GUI Architecture

## Responsibility

The GUI owns browser interaction and presentation. It does not reproduce search or persistence logic from Python. All backend access goes through the typed HTTP client in \`src/api/client.ts\`.

The application is a Vite-built React single page. Development uses port 2627 and proxies \`/api\` to the API on port 2626. The production image serves static files through Nginx and proxies the same paths to the private Compose API service.

## Application state

\`App.tsx\` is the state owner for:

- Loaded stations and current station selection.
- Simple or advanced mode and the current form.
- Search lifecycle: idle, loading, ready, or error.
- Search response and API error.
- The station coordinates used for the completed search.
- Station editor state and transient toast notifications.

The completed-search station is copied when a response succeeds. Selecting or editing another station afterward therefore does not move the Sun on an existing result chart.

On startup, the application requests the station list and selects the first station when one exists. Add, edit, and delete operations send a replacement station list to the API. Search and station failures are kept in UI state and displayed without discarding the current form.

## Component structure

| Component | Responsibility |
| --- | --- |
| \`Header\` and \`HelpModal\` | Branding, connection indicators, and rendering of external help content |
| \`StationSidebar\` | Station selection and add/edit/delete actions |
| \`StationModal\` | Station form and validation feedback |
| \`SearchPanel\` | Time window, TLE age, mode, criteria, and submission |
| \`ResultsPanel\` | Idle, loading, error, no-result, and result states |
| \`ResultCard\` | Ranked result summary and expandable details |
| \`SkyChart\` | Pass arc, culmination, Sun position, and angular halos |
| \`TimeBlock\` | Display and ISO-8601 clipboard behavior |
| \`TleBlock\` | Three-line TLE display and clipboard behavior |
| \`ToastStack\` | Short-lived success, information, and error messages |

The first result card starts expanded. Result order is the order supplied by the API and is not re-ranked in the browser.

The text rendered by \`Header\` and \`HelpModal\` lives in \`content/how-it-works.json\`. This keeps editable wording and list structure separate from React behavior. A production bundle or image must be rebuilt after the JSON changes.

## API boundary

\`src/api/types.ts\` mirrors the public Pydantic schemas. Contract changes must update both the API and GUI types and tests.

\`src/api/client.ts\`:

- Uses \`VITE_API_BASE_URL\` when configured and otherwise \`/api/v1\`.
- Sends and accepts JSON.
- Converts non-success responses into \`ApiError\`.
- Exposes station-list, station-replacement, simple-search, and advanced-search calls.
- Supports abort signals for lifecycle-safe requests.

## Forms and validation

\`src/lib/form.ts\` defines serializable input state and initial values. The default start is the next whole UTC hour, the duration is 15 minutes, the TLE age is 24 hours, and advanced criteria are disabled.

\`src/lib/validation.ts\` validates stations and converts the form into the exact API request:

- UTC input requires ISO 8601 with \`Z\` or an explicit offset.
- Local input is combined with the selected offset; station longitude does not infer a timezone.
- Duration must be greater than zero and at most 30 minutes.
- Range, target/tolerance, score, result-limit, and coordinate bounds match the API.
- Disabled advanced sections are omitted from the request.

Simple mode sends only station, window, and TLE age. Advanced mode additionally sends the selected group and criteria.

## Formatting and sky geometry

\`src/lib/format.ts\` formats coordinates, azimuth, duration, UTC times, and explicit-offset times. \`isoCopyText\` converts the displayed time into an ISO-8601 clipboard value with \`T\` between date and time and no space before its offset.

\`src/lib/sky.ts\` contains framework-independent geometry:

- \`passArc\` creates one continuous spherical curve through rise, culmination, and set.
- \`sunPosition\` estimates apparent solar altitude and azimuth for the result station at culmination.
- \`haloRing\` creates great-circle rings at an angular distance from the Sun.

\`SkyChart\` projects those points onto a polar SVG where north is up, the outer edge is the horizon, and the centre is the zenith. It draws 10-degree and 20-degree Sun halos when they intersect the visible plot and draws the Sun itself when it is above the horizon.

## Styling, tests, and build

\`src/styles.css\` owns desktop and narrow responsive layouts. No component library or runtime CSS dependency is used.

Vitest and React Testing Library cover application state, header/modal interaction, HTTP behavior, validation, time formatting, station propagation, and sky geometry. Container-contract tests protect proxy and build assumptions. \`npm run typecheck\` checks browser and Vite configuration types; \`npm run build\` creates the production \`dist\` directory without source maps.
