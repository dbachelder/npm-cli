# Roadmap: NPM CLI

## Overview

Transform Nginx Proxy Manager administration from manual multi-step operations (SQL queries, file editing, docker exec commands) into a single-command CLI tool. The journey starts with NPM API discovery and basic CLI structure, builds connection and authentication capabilities, implements the core trinity of proxy management, SSL automation, and configuration templates, then finishes with testing infrastructure and documentation for public release.

## Domain Expertise

None

## Phases

- [ ] **Phase 1: Foundation** - Project setup, NPM API discovery, and basic CLI structure
- [ ] **Phase 2: NPM Connection & Authentication** - Docker container discovery, API authentication, and connection management
- [ ] **Phase 3: Proxy Host Management** - Core CRUD operations for proxy hosts via NPM API
- [ ] **Phase 4: SSL Certificate Automation** - End-to-end certificate creation and attachment workflow
- [ ] **Phase 5: Configuration Templates** - Reusable templates for common patterns (Authentik, VPN-only, API bypass)
- [ ] **Phase 6: Testing & Documentation** - Reproducible test suite and user-friendly docs for public release

## Phase Details

### Phase 1: Foundation
**Goal**: Establish project structure with uv, CLI framework, and comprehensive NPM API discovery
**Depends on**: Nothing (first phase)
**Research**: Likely (NPM API discovery required)
**Research topics**: NPM API architecture, available endpoints, authentication mechanisms, response formats
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

### Phase 2: NPM Connection & Authentication
**Goal**: Implement Docker container discovery and NPM API authentication
**Depends on**: Phase 1
**Research**: Likely (external integration)
**Research topics**: NPM API authentication (token/session-based), Docker API for container discovery, connection configuration
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

### Phase 3: Proxy Host Management
**Goal**: Implement complete proxy host lifecycle (create, list, update, delete) via NPM API
**Depends on**: Phase 2
**Research**: Likely (external API)
**Research topics**: NPM proxy host API endpoints, data structures, CRUD operations, validation requirements
**Plans**: TBD

Plans:
- [ ] TBD during phase planning

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
| 1. Foundation | 0/TBD | Not started | - |
| 2. NPM Connection & Authentication | 0/TBD | Not started | - |
| 3. Proxy Host Management | 0/TBD | Not started | - |
| 4. SSL Certificate Automation | 0/TBD | Not started | - |
| 5. Configuration Templates | 0/TBD | Not started | - |
| 6. Testing & Documentation | 0/TBD | Not started | - |
