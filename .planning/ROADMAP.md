# Roadmap: NPM CLI

## Overview

Transform Nginx Proxy Manager administration from manual multi-step operations (SQL queries, file editing, docker exec commands) into a single-command CLI tool. The journey starts with NPM API discovery and basic CLI structure, builds connection and authentication capabilities, implements the core trinity of proxy management, SSL automation, and configuration templates, then finishes with testing infrastructure and documentation for public release.

## Domain Expertise

None

## Phases

- [x] **Phase 1: Foundation** - Project setup, NPM API discovery, and basic CLI structure
- [x] **Phase 2: NPM Connection & Authentication** - Docker container discovery, API authentication, and connection management
- [ ] **Phase 3: Proxy Host Management** - Core CRUD operations for proxy hosts via NPM API
- [ ] **Phase 4: SSL Certificate Automation** - End-to-end certificate creation and attachment workflow
- [ ] **Phase 5: Configuration Templates** - Reusable templates for common patterns (Authentik, VPN-only, API bypass)
- [ ] **Phase 6: Testing & Documentation** - Reproducible test suite and user-friendly docs for public release

## Phase Details

### Phase 1: Foundation
**Goal**: Establish project structure with uv, CLI framework, and comprehensive NPM API discovery
**Depends on**: Nothing (first phase)
**Research**: Completed
**Research topics**: NPM API architecture, available endpoints, authentication mechanisms, response formats
**Plans**: 1/1 complete
**Status**: Complete
**Completed**: 2026-01-04

Plans:
- [x] 01-01: Foundation setup (uv project, API discovery, CLI structure) — 8 min

### Phase 2: NPM Connection & Authentication
**Goal**: Implement Docker container discovery and NPM API authentication
**Depends on**: Phase 1
**Research**: Completed
**Research topics**: NPM API authentication (token/session-based), Docker API for container discovery, connection configuration
**Plans**: 3/3 complete
**Status**: Complete
**Completed**: 2026-01-04

Plans:
- [x] 02-01: Configuration Setup (dependencies, settings module with TDD) — 7 min
- [x] 02-02: Connection Core (Docker discovery, NPM API client) — 5 min
- [x] 02-03: CLI Commands (connect, auth, status commands) — 22 min

### Phase 3: Proxy Host Management
**Goal**: Implement complete proxy host lifecycle (create, list, update, delete) via NPM API
**Depends on**: Phase 2
**Research**: Completed
**Research topics**: NPM proxy host API endpoints, data structures, CRUD operations, validation requirements
**Plans**: 3 planned, 1 complete
**Status**: In progress

Plans:
- [x] 03-01: API Foundation (exceptions + Pydantic models, TDD) — 7 min
- [ ] 03-02: API Client CRUD (NPMClient methods, TDD)
- [ ] 03-03: CLI Commands (proxy commands + verification checkpoint)

### Phase 4: SSL Certificate Automation
**Goal**: End-to-end SSL certificate workflow from creation to NPM integration to proxy host attachment
**Depends on**: Phase 3
**Research**: Likely (external API, certificate management)
**Research topics**: NPM certificate API, Let's Encrypt integration, certificate attachment workflows
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

### Phase 5: Configuration Templates
**Goal**: Implement reusable template system for common patterns (Authentik forward auth, VPN-only access, API bypass paths)
**Depends on**: Phase 4
**Research**: Unlikely (internal patterns based on established API knowledge from phases 3-4)
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

### Phase 6: Testing & Documentation
**Goal**: Reproducible test suite with dedicated NPM container, ZSH autocomplete, and user-friendly documentation for public release
**Depends on**: Phase 5
**Research**: Unlikely (standard testing and documentation of established patterns)
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

## Progress

**Execution Order:**
Phases execute sequentially: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2026-01-04 |
| 2. NPM Connection & Authentication | 3/3 | Complete | 2026-01-04 |
| 3. Proxy Host Management | 1/3 | In progress | - |
| 4. SSL Certificate Automation | 0/TBD | Not started | - |
| 5. Configuration Templates | 0/TBD | Not started | - |
| 6. Testing & Documentation | 0/TBD | Not started | - |
