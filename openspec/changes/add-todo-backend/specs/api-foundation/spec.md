## Purpose

Defines the cross-cutting HTTP contract every endpoint of the Todo backend honours: how the API is versioned, how errors are reported, how malformed input is rejected, and how operators check that the service and its database are alive.

## ADDED Requirements

### Requirement: Versioned API surface
All functional endpoints SHALL be served under the `/api/v1` path prefix. Operational endpoints (health) SHALL be served outside the version prefix so they remain stable across API versions.

#### Scenario: Functional endpoint is versioned
- **WHEN** a client requests a functional resource such as the todo collection
- **THEN** the resource is available at a path beginning with `/api/v1`

#### Scenario: Unknown path
- **WHEN** a client requests a path that no route matches
- **THEN** the API responds with status `404` and the uniform error envelope

### Requirement: Uniform error envelope
Every non-2xx response produced by the API SHALL have a JSON body of the shape `{"error": {"code": <string>, "message": <string>, "details": <object|null>}}`. The `code` field SHALL be a stable, machine-readable, UPPER_SNAKE_CASE identifier that does not change when the human-readable `message` changes.

#### Scenario: Domain rule violation is reported with a stable code
- **WHEN** a request is rejected because it violates a business rule
- **THEN** the response body contains `error.code` identifying the rule and `error.message` describing it in human-readable form

#### Scenario: Unexpected failure does not leak internals
- **WHEN** an unhandled exception occurs while serving a request
- **THEN** the API responds with status `500` and body `error.code` of `INTERNAL_ERROR`
- **AND** the response contains no stack trace, SQL text, driver message, or connection string

### Requirement: Request validation
The API SHALL reject syntactically or structurally invalid requests before any business logic executes, responding with status `422` and error code `VALIDATION_ERROR`. The `details` field SHALL enumerate the offending fields and the reason each was rejected.

#### Scenario: Missing required field
- **WHEN** a client submits a request body that omits a required field
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`
- **AND** `error.details` names the missing field

#### Scenario: Wrong field type
- **WHEN** a client submits a field whose value has the wrong type or fails a declared constraint
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`
- **AND** no state change is persisted

### Requirement: Domain independence from transport
API request and response payloads SHALL be defined separately from the internal domain model, so that renaming or restructuring internal domain fields does not change the wire contract unless the contract is deliberately changed.

#### Scenario: Response exposes only contract fields
- **WHEN** any endpoint returns a resource representation
- **THEN** the payload contains only fields declared by this API contract
- **AND** internal-only fields such as password hashes are never present

### Requirement: Health reporting
The service SHALL expose `GET /health`, which reports service liveness and database reachability without requiring authentication.

#### Scenario: Service and database are healthy
- **WHEN** a client requests `GET /health` and the database accepts a connectivity check
- **THEN** the API responds with status `200` and a body reporting overall status `ok` and database status `ok`

#### Scenario: Database is unreachable
- **WHEN** a client requests `GET /health` and the database connectivity check fails
- **THEN** the API responds with status `503` and a body reporting overall status `degraded` and database status `error`

### Requirement: Configuration is externalised
The service SHALL read its database connection string, token signing secret, token lifetime, and environment name from the process environment, and SHALL fail to start with a clear message when a required setting is absent or empty.

#### Scenario: Missing required setting
- **WHEN** the service starts without a database connection string configured
- **THEN** startup fails with an error naming the missing setting
- **AND** the service does not begin accepting HTTP requests

#### Scenario: Secrets are never echoed
- **WHEN** the service logs its startup configuration
- **THEN** the database password and token signing secret are absent or masked in the log output
