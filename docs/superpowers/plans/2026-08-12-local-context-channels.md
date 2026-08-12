# Local Context and Source Channels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve and cache county-first merchant geography, refresh it after address changes, and derive publishing guidance from domains actually cited by Ark web search.

**Architecture:** Add a one-to-one merchant local-context record with pending/completed/failed states. The existing worker processes pending context jobs through the Ark adapter; query generation consumes the finest confirmed region. Dashboard actions aggregate citation domains from the latest scan and label unknown publishing access conservatively.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Pydantic, Ark Responses API, Next.js.

## Global Constraints

- Geography falls back county → city → province; no province-only scope when county exists.
- Never infer airports, stations, landmarks, or editable platform access without cited evidence.
- Address changes enqueue one refresh; unrelated profile changes do not.
- Unknown citation domains are “仅作参照”.

### Task 1: Local context persistence and county scope

- [ ] Add failing tests for county-first fallback and address-change invalidation.
- [ ] Add the model, migration, schemas and service.
- [ ] Make query generation overlay the completed county/city/province facts.
- [ ] Run focused tests.

### Task 2: Ark background resolver

- [ ] Add failing parser and worker tests for cited structured local context.
- [ ] Implement the constrained lookup prompt, parser and pending-job worker.
- [ ] Add a refresh/read endpoint.
- [ ] Run focused tests.

### Task 3: Citation-led channels

- [ ] Add a failing dashboard test for real citation domains and conservative access labels.
- [ ] Aggregate latest-scan citations into action channels and update the UI contract.
- [ ] Run all API/web tests, build, migrate, restart and verify the real merchant.

