# API Architecture Findings

## 1. Simple-search scoring requires a broader core/API model decision

`APIRequirement.md` requires simple search to rank neutral/default requests using pass duration and pass timing with equal weight:

- longer pass duration ranks better than an otherwise equivalent shorter pass duration
- earlier pass start time within the search window ranks better than an otherwise equivalent later pass start time
- pass duration and pass timing have equal weight

This is broader than a local API adapter change. `APIArchitecture.md` currently only maps simple-search defaults into filter, limit, and threshold fields before calling the core. `ARCHITECTURE.md` keeps scoring and ranking inside the core, so the API must not implement this ranking behavior itself.

Recommended resolution:

- define how the shared core `SearchCriteria` represents the simple-search default scoring behavior, or define a core-owned default scoring profile
- document that the API only selects this core-supported behavior for simple search
- keep pass-duration scoring, pass-timing scoring, weighting, tie-breaking, thresholding, ranking, and limiting inside the core workflow
- add API tests only to prove the adapter submits the correct core request; add core tests for the actual scoring and ranking behavior

## 2. Advanced search should explicitly define `satellite_group`

`APIArchitecture.md` exposes `satellite_group` for advanced search and defaults it to `active` when omitted. That is useful because clients may need to select the TLE source group, but `APIRequirement.md` does not currently list `satellite_group` as a supported advanced-search input.

Recommended resolution:

- add an API requirement stating that advanced search may define the satellite group / TLE source group
- define the supported values, currently `active`, `visual`, and `amateur`
- define the default value when omitted, currently `active`
- state that unsupported `satellite_group` values are rejected with a machine-readable validation error
- keep simple search fixed to the default group unless a future requirement explicitly exposes group selection there
