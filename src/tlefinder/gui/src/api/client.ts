/**
 * Typed fetch client for the TLE Finder API.
 *
 * Endpoints (see `src/tlefinder/api/routers/`):
 *   GET  /api/v1/stations           → StationListResponse
 *   PUT  /api/v1/stations           ← StationListRequest      → StationListResponse
 *   POST /api/v1/search/simple      ← SimpleSearchRequest     → SearchResponse
 *   POST /api/v1/search/advanced    ← AdvancedSearchRequest   → SearchResponse
 *
 * The base URL defaults to `/api/v1` so it works behind any reverse proxy or
 * when the GUI is served by the FastAPI app itself. Override with the env
 * variable `VITE_API_BASE_URL` (e.g. `http://127.0.0.1:2626/api/v1`).
 */

import type {
  AdvancedSearchRequest,
  ApiErrorBody,
  ErrorResponse,
  SearchResponse,
  SimpleSearchRequest,
  StationListRequest,
  StationListResponse,
} from "./types";

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";

/** Thrown for any non-2xx response. Mirrors the API ErrorResponse envelope. */
export class ApiError extends Error {
  readonly body: ApiErrorBody;
  readonly status: number;
  constructor(body: ApiErrorBody, status: number) {
    super(body.message);
    this.name = "ApiError";
    this.body = body;
    this.status = status;
  }
}

async function request<T>(
  method: "GET" | "POST" | "PUT",
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const init: RequestInit = {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  };
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch (cause) {
    throw new ApiError(
      {
        code: "internal_error",
        message:
          cause instanceof Error
            ? `Network error: ${cause.message}`
            : "Network error.",
        details: {},
        field_errors: [],
      },
      0,
    );
  }

  if (!res.ok) {
    let envelope: ErrorResponse | null = null;
    try {
      envelope = (await res.json()) as ErrorResponse;
    } catch {
      /* non-JSON body */
    }
    const body: ApiErrorBody = envelope?.error ?? {
      code: "internal_error",
      message: res.statusText || `Request failed with status ${res.status}`,
      details: {},
      field_errors: [],
    };
    throw new ApiError(body, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  listStations(signal?: AbortSignal): Promise<StationListResponse> {
    return request("GET", "/stations", undefined, signal);
  },
  putStations(
    body: StationListRequest,
    signal?: AbortSignal,
  ): Promise<StationListResponse> {
    return request("PUT", "/stations", body, signal);
  },
  simpleSearch(
    body: SimpleSearchRequest,
    signal?: AbortSignal,
  ): Promise<SearchResponse> {
    return request("POST", "/search/simple", body, signal);
  },
  advancedSearch(
    body: AdvancedSearchRequest,
    signal?: AbortSignal,
  ): Promise<SearchResponse> {
    return request("POST", "/search/advanced", body, signal);
  },
} as const;
