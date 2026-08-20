# TLE Finder GUI

\`tlefinder-gui\` is the React and TypeScript interface for TLE Finder. It lets users manage optical ground stations, configure simple or advanced searches, inspect ranked passes and sky charts, and copy scheduler-ready times and TLE data.

## Install and run

~~~powershell
cd gui
npm ci
npm run dev
~~~

Open <http://127.0.0.1:2627>. During development, Vite proxies \`/api\` to the API at <http://127.0.0.1:2626>.

To start the API and GUI together, run this from the repository root:

~~~powershell
./scripts/dev.ps1
~~~

## Use the interface

1. Add or select a ground station.
2. Choose a UTC or local start time and a search duration.
3. Select the TLE age limit.
4. Use Simple mode for a standard active-satellite search, or Advanced mode for group, geometry, altitude, Sun-proximity, result-limit, and score controls.
5. Run the search and expand a result to inspect its pass chart, times, metrics, and TLE.

Copied start, culmination, and end times are ISO 8601 values with a \`T\` between the date and time. The display can use UTC or the explicit offset selected for the search.

See the [user guide](docs/USER_GUIDE.md) for the complete workflow.

## Change the help content

Edit \`content/how-it-works.json\` to change the How it works button label, dialog title, introduction, steps, section lists, or close button. The React component contains only the modal layout and behavior.

Vite reloads the content during local development. Rebuild the GUI image or production bundle after changing the file for a deployed installation.

## Connect to another API

The browser client uses the relative \`/api/v1\` base URL by default. Copy \`.env.example\` to \`.env.local\` and set \`VITE_API_BASE_URL\` only when the API is hosted elsewhere:

~~~text
VITE_API_BASE_URL=http://192.168.1.42:2626/api/v1
~~~

## Test and build

~~~powershell
npm test
npm run typecheck
npm run build
~~~

The tests use jsdom, React Testing Library, and stubbed HTTP responses, so they do not require a running API or browser server.

## More documentation

- [Architecture](docs/ARCHITECTURE.md)
- [User guide](docs/USER_GUIDE.md)
