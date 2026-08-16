## Purpose

Gives each authenticated user a private list of todos they can create, browse, refine, progress, and remove, with enough structure — status, priority, due date — to actually plan work rather than just record it.

## ADDED Requirements

### Requirement: Todo attributes
A todo SHALL have a system-assigned identifier, an owner, a title, an optional description, a status, a priority, an optional due date, a creation timestamp, and a last-updated timestamp. Title SHALL be a non-empty string of at most 200 characters after trimming surrounding whitespace; description SHALL be at most 2000 characters when present.

#### Scenario: Defaults on creation
- **WHEN** a user creates a todo supplying only a title
- **THEN** the todo is created with status `todo`, priority `medium`, no description, no due date, and creation and update timestamps set to the creation time

#### Scenario: Title is trimmed
- **WHEN** a user creates a todo with a title padded by leading and trailing whitespace
- **THEN** the stored and returned title has that whitespace removed

#### Scenario: Blank title rejected
- **WHEN** a user submits a title that is empty or consists only of whitespace
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`
- **AND** no todo is created

#### Scenario: Oversized field rejected
- **WHEN** a user submits a title longer than 200 characters or a description longer than 2000 characters
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`

### Requirement: Todo status values and transitions
A todo's status SHALL be exactly one of `todo`, `in_progress`, or `done`. Any status SHALL be reachable from any other status, including reopening a completed todo. A todo SHALL record a completion timestamp when it enters `done`, and SHALL clear that timestamp when it leaves `done`.

#### Scenario: Progressing a todo
- **WHEN** an owner changes a todo's status from `todo` to `in_progress`
- **THEN** the API responds with status `200` and the todo's status is `in_progress`
- **AND** its completion timestamp remains unset

#### Scenario: Completing a todo
- **WHEN** an owner changes a todo's status to `done`
- **THEN** the todo's status is `done` and its completion timestamp is set to the time of the change

#### Scenario: Reopening a completed todo
- **WHEN** an owner changes a `done` todo's status back to `todo` or `in_progress`
- **THEN** the todo carries the new status and its completion timestamp is cleared

#### Scenario: Unknown status rejected
- **WHEN** a user submits a status value outside the permitted set
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`
- **AND** the todo is unchanged

### Requirement: Todo priority values
A todo's priority SHALL be exactly one of `low`, `medium`, or `high`.

#### Scenario: Priority is set
- **WHEN** an owner creates or updates a todo with priority `high`
- **THEN** the returned todo has priority `high`

#### Scenario: Unknown priority rejected
- **WHEN** a user submits a priority value outside the permitted set
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`

### Requirement: Todo creation
An authenticated user SHALL be able to create a todo, which is owned by that user. The owner SHALL be taken from the authenticated request and SHALL NOT be accepted from the request body.

#### Scenario: Successful creation
- **WHEN** an authenticated user creates a todo with a valid title
- **THEN** the API responds with status `201` and a body containing the created todo including its assigned id and owner-independent representation

#### Scenario: Owner cannot be spoofed
- **WHEN** a user submits a create request that includes an owner or user identifier in the body
- **THEN** the created todo is owned by the authenticated user, not by the identifier supplied in the body

### Requirement: Owner-scoped access isolation
A todo SHALL be readable and mutable only by its owner. A request from any other user for that todo SHALL be answered exactly as if the todo did not exist, so that existence is not disclosed.

#### Scenario: Reading another user's todo
- **WHEN** an authenticated user requests a todo owned by a different user
- **THEN** the API responds with status `404` and error code `TODO_NOT_FOUND`

#### Scenario: Updating another user's todo
- **WHEN** an authenticated user attempts to update a todo owned by a different user
- **THEN** the API responds with status `404` and error code `TODO_NOT_FOUND`
- **AND** the target todo is unchanged

#### Scenario: Deleting another user's todo
- **WHEN** an authenticated user attempts to delete a todo owned by a different user
- **THEN** the API responds with status `404` and error code `TODO_NOT_FOUND`
- **AND** the target todo still exists for its owner

#### Scenario: Listing excludes other users' todos
- **WHEN** an authenticated user lists their todos while other users also have todos
- **THEN** every returned todo is owned by the requesting user

### Requirement: Todo retrieval by identifier
An owner SHALL be able to retrieve one of their todos by its identifier.

#### Scenario: Existing todo
- **WHEN** an owner requests a todo they own by its identifier
- **THEN** the API responds with status `200` and the todo's full representation

#### Scenario: Unknown identifier
- **WHEN** a user requests a todo identifier that does not exist
- **THEN** the API responds with status `404` and error code `TODO_NOT_FOUND`

### Requirement: Todo listing with filtering, sorting, and pagination
An owner SHALL be able to list their todos with optional filters on status, priority, due-date range, and a case-insensitive substring search over title. The result SHALL be sortable by creation time, update time, due date, or priority, in ascending or descending order, and SHALL be paginated with a caller-supplied limit and offset. The response SHALL report the items, the total number of matching todos, and the applied limit and offset. Ordering SHALL be deterministic: ties on the sort key SHALL be broken by identifier.

#### Scenario: Default listing
- **WHEN** an owner lists todos without specifying any parameters
- **THEN** the API responds with status `200`, returns at most 20 todos ordered by creation time descending, and reports the total count of the owner's todos

#### Scenario: Filter by status
- **WHEN** an owner lists todos filtered to status `done`
- **THEN** every returned todo has status `done`
- **AND** the reported total counts only todos matching that filter

#### Scenario: Filter by due-date range
- **WHEN** an owner lists todos with a due-date range
- **THEN** every returned todo has a due date within that range inclusive
- **AND** todos with no due date are excluded

#### Scenario: Search by title
- **WHEN** an owner lists todos with a search term
- **THEN** every returned todo has a title containing that term, matched without regard to letter case

#### Scenario: Pagination
- **WHEN** an owner requests a limit of 10 and an offset of 10 while 25 todos match
- **THEN** at most 10 todos are returned, they follow the first 10 in the applied order, and the reported total is 25

#### Scenario: Pagination bounds
- **WHEN** an owner requests a limit that is less than 1 or greater than 100, or a negative offset
- **THEN** the API responds with status `422` and error code `VALIDATION_ERROR`

#### Scenario: Empty result
- **WHEN** an owner lists todos and none match the applied filters
- **THEN** the API responds with status `200`, an empty item list, and a reported total of 0

### Requirement: Partial todo update
An owner SHALL be able to update a todo's title, description, status, priority, or due date, supplying only the fields being changed. Omitted fields SHALL retain their current values. Clearing an optional field SHALL be expressible and distinguishable from omitting it.

#### Scenario: Updating one field leaves others intact
- **WHEN** an owner updates only the priority of a todo that has a title, description, and due date
- **THEN** the priority changes and the title, description, and due date are unchanged

#### Scenario: Clearing an optional field
- **WHEN** an owner explicitly sets a todo's due date to null
- **THEN** the returned todo has no due date

#### Scenario: Update refreshes the update timestamp
- **WHEN** an owner successfully changes any field of a todo
- **THEN** the todo's last-updated timestamp is later than it was before the change
- **AND** its creation timestamp is unchanged

#### Scenario: Empty update
- **WHEN** an owner submits an update request that changes no fields
- **THEN** the API responds with status `200` and the todo's unchanged representation

### Requirement: Todo deletion
An owner SHALL be able to permanently delete one of their todos.

#### Scenario: Successful deletion
- **WHEN** an owner deletes a todo they own
- **THEN** the API responds with status `204` with an empty body
- **AND** a subsequent request for that todo responds with status `404` and error code `TODO_NOT_FOUND`

#### Scenario: Deleting an unknown todo
- **WHEN** an owner deletes a todo identifier that does not exist
- **THEN** the API responds with status `404` and error code `TODO_NOT_FOUND`

### Requirement: Todos are removed with their owner
When a user account is removed, that user's todos SHALL be removed with it, leaving no todo without an existing owner.

#### Scenario: Owner removed
- **WHEN** a user account is deleted from the system
- **THEN** no todo referencing that user remains
