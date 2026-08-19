# TLE Finder GUI

`tlefinder-gui` is the independent React, TypeScript, and Vite frontend. It communicates with the TLE Finder API only through the typed HTTP client in `src/api/client.ts`; it contains no Python search or persistence implementation.

Install exactly from the committed npm lockfile, then run the component-owned checks:

```powershell
cd gui
npm ci
npm test
npm run typecheck
npm run build
```

Start the local development server with:

```powershell
npm run dev
```

For non-container development, start the API separately from `api/` on port 2626. Vite runs on port 2627 and proxies `/api` to `http://127.0.0.1:2626`.

For the complete containerized application, run this from the repository root:

```powershell
docker compose up --detach --build --wait
```

Open `http://127.0.0.1:2627`. The GUI container serves only the production build and reaches the API through the private Compose network. See [`../docs/CONTAINERS.md`](../docs/CONTAINERS.md) for lifecycle, direct Swagger access, persistence, and troubleshooting commands.

The client defaults to the relative `/api/v1` base URL. Set `VITE_API_BASE_URL` in `.env.local` only when the API is hosted elsewhere, for example:

```text
VITE_API_BASE_URL=http://192.168.1.42:2626/api/v1
```

`src/api/types.ts` mirrors the public Pydantic models in `../api/src/tlefinder/api/schemas.py`. Contract changes must update both components and their owning tests.

The Vitest suite uses jsdom and React Testing Library. API behavior is stubbed, so GUI unit tests require neither Python, a browser server, nor live network access.

