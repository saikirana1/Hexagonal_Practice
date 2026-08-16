## Purpose

Lets people create an account for the Todo service and prove who they are on later requests, so that every todo can be attributed to and protected for exactly one owner.

## ADDED Requirements

### Requirement: User registration
The system SHALL allow a visitor to register with an email address and a password. Email addresses SHALL be unique across users, compared case-insensitively and stored in normalised (lower-cased, trimmed) form. A successful registration SHALL create exactly one user account and return that account's public representation.

#### Scenario: Successful registration
- **WHEN** a visitor submits a well-formed, unused email address and an acceptable password
- **THEN** the API responds with status `201` and a body containing the new user's id, email, and creation timestamp
- **AND** the response contains no password or password hash

#### Scenario: Email already registered
- **WHEN** a visitor submits an email address that already belongs to an account, in any letter casing
- **THEN** the API responds with status `409` and error code `EMAIL_ALREADY_REGISTERED`
- **AND** no second account is created

#### Scenario: Malformed email
- **WHEN** a visitor submits a value that is not a valid email address
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`

#### Scenario: Password too weak
- **WHEN** a visitor submits a password shorter than 8 characters or longer than 128 characters
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`
- **AND** no account is created

### Requirement: Password storage
Passwords SHALL be stored only as a salted, computationally expensive one-way hash. The system SHALL never store, log, or return a plaintext password.

#### Scenario: Stored credential is not reversible
- **WHEN** a user account has been created
- **THEN** the persisted credential is a hash that differs from the submitted password
- **AND** two accounts registered with the same password have different stored hashes

### Requirement: Login issues an access token
The system SHALL allow a registered user to exchange a valid email and password for a signed access token. The response SHALL include the token, its token type, and its lifetime in seconds.

#### Scenario: Successful login
- **WHEN** a registered user submits their correct email and password
- **THEN** the API responds with status `200` and a body containing an access token, token type `bearer`, and an expiry duration in seconds

#### Scenario: Wrong password
- **WHEN** a registered user submits an incorrect password
- **THEN** the API responds with status `401` and error code `INVALID_CREDENTIALS`

#### Scenario: Unknown email
- **WHEN** a login is attempted for an email address that has no account
- **THEN** the API responds with status `401` and error code `INVALID_CREDENTIALS`
- **AND** the message is identical to the wrong-password message, so the response does not reveal whether the account exists

### Requirement: Access token contents and lifetime
An issued access token SHALL identify the subject user, SHALL carry an issued-at and an expiry timestamp, and SHALL be signed such that any modification invalidates it. Tokens SHALL expire after the configured lifetime.

#### Scenario: Token identifies its user
- **WHEN** a token issued to a user is presented on a protected request
- **THEN** the request is processed as that user and no other

#### Scenario: Expired token
- **WHEN** a request presents a token whose expiry timestamp is in the past
- **THEN** the API responds with status `401` and error code `TOKEN_EXPIRED`

#### Scenario: Tampered token
- **WHEN** a request presents a token whose payload or signature has been altered
- **THEN** the API responds with status `401` and error code `INVALID_TOKEN`

### Requirement: Authenticated access to protected resources
Every endpoint other than registration, login, and health SHALL require a valid access token supplied as an `Authorization: Bearer <token>` header, and SHALL resolve it to the acting user before any business logic executes.

#### Scenario: Missing credentials
- **WHEN** a client calls a protected endpoint with no `Authorization` header
- **THEN** the API responds with status `401` and error code `NOT_AUTHENTICATED`

#### Scenario: Malformed authorization header
- **WHEN** a client sends an `Authorization` header that is not of the form `Bearer <token>`
- **THEN** the API responds with status `401` and error code `NOT_AUTHENTICATED`

#### Scenario: Token for a deleted user
- **WHEN** a client presents a structurally valid, unexpired token whose subject no longer has an account
- **THEN** the API responds with status `401` and error code `INVALID_TOKEN`

### Requirement: Current user retrieval
The system SHALL allow an authenticated user to retrieve their own account representation.

#### Scenario: Authenticated user reads own profile
- **WHEN** an authenticated user requests their current account
- **THEN** the API responds with status `200` and a body containing their id, email, and creation timestamp
