# Match Visualization Requirements

## 1. Introduction

This document specifies requirements for integrating real-time pygame-based match visualization with the FastAPI backend server for the Spellcasters hackathon project. The feature enables opt-in live visualization of matches during demos and presentations by spawning separate visualizer processes that consume game events via the existing SSE infrastructure.

### 1.1 Scope

This feature is designed for **local development and demo environments only**. It requires a display-capable environment and is not intended for headless server deployments or remote visualization scenarios.

### 1.2 Related Documents

- Backend Specification: `docs/specs/spellcasters-backend/spellcasters-backend-spec_final.md`
- Visualizer Implementation: `simulator/visualizer.py`

---

## 2. Functional Requirements

### 2.1 Opt-in Visualization Control

**User Story**: As a hackathon demo presenter, I want to optionally enable visualization when starting a match, so that I can show live gameplay during presentations without affecting regular API usage.

**Acceptance Criteria**:

1. **WHILE** creating a new playground session **IF** the request includes a `visualize` parameter **THEN** the system shall accept this parameter as a boolean value
2. **WHERE** the `visualize` parameter is omitted **THEN** the system shall default to `false` (no visualization)
3. **WHERE** the `visualize` parameter is set to `true` **THEN** the system shall attempt to spawn a visualizer process for that specific session
4. **WHERE** the `visualize` parameter is set to `false` **THEN** the system shall operate in headless mode as currently implemented

### 2.2 Visualizer Process Management

**User Story**: As a backend service, I want to spawn independent visualizer processes for each visualized session, so that multiple matches can run concurrently without visualization conflicts.

**Acceptance Criteria**:

1. **WHEN** a session is created with `visualize=true` **THEN** the system shall spawn a new Python process running the visualizer
2. **WHERE** a visualizer process is spawned **THEN** the system shall use Python's `multiprocessing` module to create an isolated process
3. **WHEN** spawning a visualizer **THEN** the system shall establish an IPC mechanism (queue or pipe) for sending game events to the visualizer process
4. **WHERE** the visualizer process is running **THEN** the system shall track the process ID and IPC channel in the session state
5. **WHERE** multiple sessions have `visualize=true` **THEN** the system shall spawn separate visualizer processes for each session
6. **WHEN** a visualizer process is created **THEN** the system shall pass initial configuration including player names, sprites, and board size

### 2.3 Event Communication to Visualizer

**User Story**: As a visualizer process, I want to receive game state updates in real-time, so that I can render smooth animations and accurate game progression.

**Acceptance Criteria**:

1. **WHEN** the backend broadcasts a `turn_update` SSE event **IF** the session has an active visualizer **THEN** the system shall send the same event data to the visualizer via IPC
2. **WHEN** the backend broadcasts a `game_over` SSE event **IF** the session has an active visualizer **THEN** the system shall send the game over event to the visualizer
3. **WHERE** sending an event to the visualizer **THEN** the system shall include the complete event payload as defined in the SSE event contract (turn number, state, actions, events, log_line)
4. **WHEN** the visualizer process starts **THEN** the system shall send the initial game state before the first turn
5. **WHERE** the IPC channel send operation fails **THEN** the system shall log the error and continue match execution without raising exceptions

### 2.4 Visualizer Rendering Behavior

**User Story**: As a hackathon attendee, I want to see the match visualized with proper animations and game state, so that I can understand what's happening in the game.

**Acceptance Criteria**:

1. **WHEN** the visualizer process receives the initial state **THEN** it shall render the game board, wizards, and initial entities
2. **WHEN** the visualizer receives a `turn_update` event **THEN** it shall animate the transition from the current state to the new state
3. **WHEN** the visualizer receives a `game_over` event **THEN** it shall display the winner or draw result with an overlay message
4. **WHERE** the game ends **THEN** the visualizer shall show a "CONTINUE" or "EXIT" button as per current behavior
5. **WHERE** the visualizer window is closed by the user **THEN** the visualizer process shall terminate gracefully

### 2.5 Resilient Error Handling

**User Story**: As a backend service operator, I want the backend to continue serving match data even if visualization fails, so that API consumers are not affected by visualization issues.

**Acceptance Criteria**:

1. **WHERE** spawning the visualizer process fails **THEN** the system shall log an error and continue with match creation
2. **WHERE** the visualizer process crashes during the match **THEN** the system shall detect the termination and log it without affecting the match
3. **WHERE** sending events to the visualizer fails **THEN** the system shall log the error and continue broadcasting to SSE clients
4. **WHEN** any visualization error occurs **THEN** the system shall NOT raise exceptions that would terminate the match or return API errors
5. **WHERE** visualization is requested but pygame dependencies are missing **THEN** the system shall log a warning and proceed without visualization
6. **WHEN** visualization fails **THEN** the API response shall still return success (200 OK) with the session_id

### 2.6 Process Cleanup and Lifecycle

**User Story**: As a system administrator, I want visualizer processes to be properly cleaned up when matches end or sessions are deleted, so that system resources are not leaked.

**Acceptance Criteria**:

1. **WHEN** a match ends naturally (game_over) **THEN** the system shall signal the visualizer process to prepare for shutdown
2. **WHERE** a session is manually deleted via `/playground/{session_id}` **THEN** the system shall terminate the associated visualizer process
3. **WHEN** the backend server shuts down **THEN** the system shall terminate all active visualizer processes gracefully
4. **WHERE** a visualizer process has been idle after game end for more than 30 seconds **THEN** the system may force-terminate the process
5. **WHERE** terminating a visualizer process **THEN** the system shall close the IPC channel and remove references from session state
6. **WHEN** the visualizer user clicks "EXIT" or "CONTINUE" **THEN** the visualizer process shall exit cleanly and notify the parent if possible

---

## 3. Non-Functional Requirements

### 3.1 Performance

**User Story**: As a backend service, I want visualization to have minimal performance impact, so that match execution remains responsive.

**Acceptance Criteria**:

1. **WHERE** visualization is enabled **THEN** the match turn processing overhead shall not exceed 50ms per turn
2. **WHERE** sending events via IPC **THEN** operations shall be non-blocking and use timeouts
3. **WHERE** multiple visualized sessions run concurrently **THEN** each shall maintain independent performance characteristics

### 3.2 Compatibility

**User Story**: As a developer, I want visualization to work with the existing backend architecture, so that minimal refactoring is required.

**Acceptance Criteria**:

1. **WHERE** visualization is integrated **THEN** the system shall reuse existing SSE event structures without modification
2. **WHERE** visualization is added **THEN** the existing `/playground/start` endpoint contract shall remain backward compatible
3. **WHERE** visualization code is added **THEN** it shall integrate with the existing StateManager and SessionManager architecture

### 3.3 Environment Requirements

**User Story**: As a hackathon participant, I want to know the system requirements for visualization, so that I can set up my environment correctly.

**Acceptance Criteria**:

1. **WHERE** visualization is used **THEN** the system shall require pygame to be installed
2. **WHERE** visualization is used **THEN** the system shall require a display-capable environment (X11, Wayland, or native window system)
3. **WHERE** pygame or display is unavailable **THEN** the system shall log appropriate warnings in startup logs or first visualize attempt

### 3.4 Logging and Observability

**User Story**: As a developer debugging visualization issues, I want detailed logs, so that I can diagnose problems quickly.

**Acceptance Criteria**:

1. **WHEN** a visualizer process is spawned **THEN** the system shall log the session_id and process ID
2. **WHEN** a visualizer process terminates **THEN** the system shall log the exit code and reason
3. **WHERE** IPC communication fails **THEN** the system shall log the error with session context
4. **WHEN** visualization is requested **THEN** the system shall log whether visualization was successfully enabled or fell back to headless mode

---

## 4. API Contract Changes

### 4.1 POST /playground/start

**Request Schema Addition**:

```json
{
  "player_1_config": { "..." },
  "player_2_config": { "..." },
  "visualize": false  // NEW: Optional boolean, defaults to false
}
```

**Response Schema**: No changes (existing `{ "session_id": "uuid" }`)

**Behavior Change**:
- When `visualize=true`, attempts to spawn visualizer process
- On visualization failure, still returns 200 OK (error logged only)

---

## 5. Edge Cases and Error Scenarios

### 5.1 Visualizer Startup Failure

**Scenario**: Pygame not installed or display not available

**Expected Behavior**:
- Log warning: "Visualization requested but failed to initialize: [error details]"
- Match proceeds in headless mode
- API returns 200 OK with session_id

### 5.2 Visualizer Crash Mid-Match

**Scenario**: Visualizer process crashes due to pygame error during animation

**Expected Behavior**:
- Backend detects process termination via IPC or periodic checks
- Log error: "Visualizer process terminated unexpectedly for session {session_id}"
- Match continues without visualization
- SSE clients still receive turn_update events

### 5.3 Concurrent Visualization Limit

**Scenario**: System resources exhausted from too many visualizer processes

**Expected Behavior**:
- No hard limit enforced in initial implementation (rely on `MAX_CONCURRENT_SESSIONS`)
- Consider adding a config option `MAX_VISUALIZED_SESSIONS` in future iterations
- Document recommended limits in deployment guide

### 5.4 User Closes Visualizer Window Early

**Scenario**: User clicks window close button during active match

**Expected Behavior**:
- Visualizer process exits gracefully
- Backend detects termination and logs it
- Match continues to completion
- No error returned to API consumers

---

## 6. Testing Requirements

### 6.1 Unit Tests

1. Test `visualize` parameter parsing in `/playground/start` request
2. Test visualizer process spawn logic with mocked multiprocessing
3. Test IPC event sending with error injection
4. Test cleanup logic when session is deleted

### 6.2 Integration Tests

1. Test end-to-end match with `visualize=true` (requires display or mocking)
2. Test multiple concurrent visualized sessions
3. Test graceful degradation when pygame is not available
4. Test visualizer process cleanup on backend shutdown

### 6.3 Manual Testing

1. Run visualized match locally and verify animations
2. Kill visualizer process manually during match, verify backend continues
3. Start 5 concurrent visualized matches, verify performance
4. Close visualizer window early, verify match completes

---

## 7. Out of Scope

The following are explicitly **not** included in this feature:

1. **Remote visualization**: Streaming visualizer output over network
2. **Headless rendering**: Generating video files or images without display
3. **Web-based visualization**: Browser-based real-time rendering
4. **Visualization replay**: Visualizing historical matches from logs
5. **Configuration UI**: Admin interface to control visualization settings
6. **Multiple viewers per match**: More than one visualizer process per session
7. **Visualization quality settings**: Adjustable FPS, resolution, or animation speed

---

## 8. Future Considerations

Items for potential future enhancement:

1. **Visualization recording**: Capture visualizer output to video file
2. **Web streaming**: Stream pygame display via WebRTC or similar
3. **Replay visualization**: Visualize matches from stored logs
4. **Configurable animations**: API to adjust animation speed and effects
5. **Resource limits**: Hard caps on concurrent visualized sessions
