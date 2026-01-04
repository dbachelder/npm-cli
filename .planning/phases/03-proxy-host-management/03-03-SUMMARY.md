# Phase 3 Plan 3: CLI Commands Summary

**Complete proxy host CRUD CLI with Rich-formatted tables, panels, domain-based lookup, and robust NPM API integration**

## Performance

- **Duration:** 22 min
- **Started:** 2026-01-04T21:03:36Z
- **Completed:** 2026-01-04T21:26:12Z
- **Tasks:** 4 (3 auto + 1 checkpoint)
- **Files modified:** 3

## Accomplishments

- Complete proxy CLI with 5 commands: list, create, show, update, delete
- Rich-formatted output with color-coded tables, panels, and status indicators
- Enhanced show command accepts domain name OR ID for flexible lookup
- Interactive confirmation for destructive delete operations
- Comprehensive error handling with helpful messages for connection, API, and validation errors
- Fixed critical update bug - changes now persist correctly to NPM

## Files Created/Modified

- `src/npm_cli/cli/proxy.py` - Complete proxy command suite (331 lines)
  - list: Rich table with ID, domains, forward config, SSL status, enabled/disabled
  - create: Interactive proxy host creation with options for SSL, WebSocket, HTTP/2
  - show: Detailed panel view with domain OR ID lookup
  - update: Partial updates for configuration changes
  - delete: Safe deletion with confirmation prompt
- `src/npm_cli/__main__.py` - Registered proxy commands (already present from earlier work)
- `src/npm_cli/api/client.py` - Fixed update_proxy_host method for correct NPM API integration
- `src/npm_cli/api/models.py` - Changed extra="forbid" to extra="ignore" for API flexibility

## Decisions Made

**Domain lookup enhancement:** Added domain name lookup to show command in addition to ID-based lookup. Rationale: UX improvement - users often remember domains better than numeric IDs. Implementation searches domain_names field and warns if multiple matches found.

**Update strategy:** Implemented GET-merge-PUT pattern for updates instead of direct partial PUT. Rationale: NPM API requires full object but rejects read-only fields (id, created_on, modified_on, owner_user_id). Solution extracts only writable fields from current state, merges updates, normalizes null locations to empty array, then sends complete writable object.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NPM API update rejected partial objects**
- **Found during:** Task 2 (update command testing during checkpoint)
- **Issue:** NPM PUT /api/nginx/proxy-hosts/{id} requires full object but rejects read-only fields. Sending updates.model_dump(exclude_none=True) resulted in 400 errors: "data must NOT have additional properties"
- **Fix:** Implemented GET-merge-PUT pattern:
  1. GET current proxy host
  2. Extract only ProxyHostCreate fields (exclude id, created_on, modified_on, owner_user_id)
  3. Normalize null locations to empty array (API requires array)
  4. Merge updates into writable fields
  5. PUT merged writable object back
- **Files modified:** src/npm_cli/api/client.py
- **Verification:** Created test proxy host 20, updated with --ssl flag, verified "SSL Forced: Yes" in show output
- **Impact:** Critical fix - update command was non-functional without this

**2. [Rule 2 - Missing Critical] Pydantic validation too strict for undocumented API**
- **Found during:** Task 1 (list command initial testing)
- **Issue:** ProxyHostCreate and ProxyHostUpdate used extra="forbid", causing validation errors when NPM API returns additional fields like "certificate" object
- **Fix:** Changed extra="forbid" to extra="ignore" in both models
- **Files modified:** src/npm_cli/api/models.py
- **Verification:** List command works without validation errors
- **Rationale:** NPM API is undocumented and may return extra fields. Using extra="ignore" still validates required fields but won't break on API additions.

**3. [Rule 1 - Bug] NPM API returns locations as null, rejects null on PUT**
- **Found during:** Task 2 (update command testing during checkpoint)
- **Issue:** GET returns locations: null, but PUT requires locations: [] (array). API returned 400: "data/locations must be array"
- **Fix:** Added normalization in update_proxy_host: if locations is None, convert to empty array before PUT
- **Files modified:** src/npm_cli/api/client.py
- **Verification:** Update command succeeds after normalization
- **Impact:** Blocking fix for update functionality

### Enhancements Beyond Plan

**4. [User Request] Domain-based lookup for show command**
- **Requested during:** Checkpoint verification
- **Enhancement:** show command now accepts domain name OR ID
- **Implementation:**
  - Check if identifier is numeric (ID) or string (domain)
  - If domain: list all hosts, filter by domain_names field
  - Warn if multiple matches, use first match
- **Files modified:** src/npm_cli/cli/proxy.py
- **Verification:** `npm-cli proxy show vpn.codesushi.com` works, displays host 14
- **Rationale:** UX improvement - domain names more memorable than IDs

---

**Total deviations:** 3 auto-fixed bugs (API integration issues), 1 user-requested enhancement
**Impact on plan:** All auto-fixes essential for correct NPM API integration with undocumented API. Enhancement improves UX without scope creep.

## Issues Encountered

**NPM API undocumented behavior:** The NPM API's PUT endpoint behavior was discovered through testing:
- Requires full resource representation (not partial updates)
- Rejects read-only fields that GET returns
- Inconsistent null handling (returns null, requires array)

**Resolution:** Implemented robust GET-merge-PUT pattern with field filtering and null normalization. Documented findings for future API work.

## Next Phase Readiness

**Phase 3 complete!** Proxy host management fully implemented and verified against live NPM instance.

Ready for Phase 4: SSL Certificate Automation

Dependencies met:
- ✓ Proxy host CRUD operations via NPM API
- ✓ Rich CLI output for user-friendly interaction
- ✓ Comprehensive error handling
- ✓ Verification against live NPM instance
- ✓ Domain-based lookup for better UX
- ✓ Robust handling of undocumented API quirks

Learnings for Phase 4:
- NPM API requires full objects for PUT (not PATCH-style partial updates)
- Use extra="ignore" for Pydantic models (undocumented API may add fields)
- Normalize null to appropriate defaults before sending to API
- Test against live NPM early to discover API quirks

---
*Phase: 03-proxy-host-management*
*Completed: 2026-01-04*
