# Match Visualization Implementation Tasks

## Overview

This document provides a step-by-step implementation plan for the match visualization feature. Each task is designed to be incremental, testable, and builds on previous work. Tasks reference specific requirements from the requirements document.

---

## Implementation Tasks

### Task 1: Core Model Setup

- [x] **1. Extend data models and add configuration for visualization support**
  - **Model Changes**:
    - Add `visualize: bool = Field(default=False)` to `SessionCreationRequest` in `backend/app/models/sessions.py`
    - Extend `SessionContext` dataclass with visualizer fields: `visualizer_process`, `visualizer_queue`, `visualizer_enabled`
    - Add type hints for `multiprocessing.Process` and `multiprocessing.Queue`
  - **Configuration**:
    - Add visualization config options to `backend/app/core/config.py`:
      - `PLAYGROUND_ENABLE_VISUALIZATION` (default True)
      - `PLAYGROUND_MAX_VISUALIZED_SESSIONS` (default 10)
      - `VISUALIZER_QUEUE_SIZE` (default 100)
      - `VISUALIZER_SHUTDOWN_TIMEOUT` (default 5.0)
  - **Testing**:
    - Write unit tests in `backend/tests/test_models.py` to verify model validation
    - Test that `visualize` defaults to `False`
    - Test that config values load correctly
  - **Validation**:
    - Run `uv run pytest backend/tests/test_models.py -v`
    - Run `uv run ruff check backend/app/models/ backend/app/core/config.py`
    - Fix any linting errors and ensure all tests pass
  - **Requirements**: 2.1.1 (accept visualize parameter), 2.2.4 (track process ID and IPC channel), 3.3.1-3.3.3 (environment requirements)
  - **Files**: `backend/app/models/sessions.py`, `backend/app/services/session_manager.py`, `backend/app/core/config.py`, `backend/tests/test_models.py`

### Task 2: Implement VisualizerService

- [x] **2. Implement complete VisualizerService with process lifecycle management**
  - **Service Implementation**:
    - Create `backend/app/services/visualizer_service.py` module
    - Implement `VisualizerService.__init__()` with logger setup
    - Implement `is_visualization_available()` to check pygame and config
    - Implement `spawn_visualizer()` to create process and queue with error handling
    - Implement `send_event()` using `queue.put_nowait()` with non-blocking semantics
    - Implement `terminate_visualizer()` with graceful shutdown and force-kill fallback
    - Implement static `_visualizer_process_main()` as process entry point
    - Add comprehensive logging for all operations (spawn, send, terminate, errors)
  - **Error Handling**:
    - Return `(None, None)` on spawn failure without raising exceptions
    - Handle `queue.Full` gracefully in `send_event()`
    - Wrap all operations in try-except blocks
    - Log all errors with session_id and context
  - **Testing**:
    - Create `backend/tests/test_visualizer_service.py`
    - Test successful process spawn with mocked multiprocessing
    - Test graceful failure when pygame unavailable
    - Test `send_event()` success and queue full scenarios
    - Test graceful and force termination
    - Test `is_visualization_available()` with various configs
    - Verify all error paths log appropriately
    - Verify no exceptions propagate to caller
  - **Validation**:
    - Run `uv run pytest backend/tests/test_visualizer_service.py -v`
    - Run `uv run ruff check backend/app/services/visualizer_service.py`
    - Ensure test coverage >90% for new service
    - Fix any issues and ensure all tests pass
  - **Requirements**: 2.2.1-2.2.3 (spawn process with IPC), 2.3.1-2.3.3 (send events), 2.5.1-2.5.5 (error handling), 2.6.1-2.6.5 (process cleanup), 3.1.2 (non-blocking), 3.4.1-3.4.4 (logging)
  - **Files**: `backend/app/services/visualizer_service.py`, `backend/tests/test_visualizer_service.py`

### Task 3: Implement VisualizerAdapter

- [x] **3. Implement VisualizerAdapter for pygame integration and event processing**
  - **Adapter Implementation**:
    - Create `backend/app/services/visualizer_adapter.py` module
    - Implement `VisualizerAdapter.__init__()` to store configuration (session_id, player names, sprites, queue)
    - Implement `initialize_visualizer()` to create pygame window and Visualizer instance immediately
    - Implement `process_events()` main loop to consume from IPC queue
    - Implement `handle_turn_event()` to render each turn in real-time with animation
    - Implement `handle_game_over_event()` to display end game message
    - Implement `_handle_pygame_events()` with guard check for `pygame.display.get_init()` to prevent errors
    - Implement `shutdown()` to clean up pygame
    - Use `queue.get(timeout=0.1)` for non-blocking polling
    - Handle pygame QUIT events during processing (only if display initialized)
    - Instantiate `Visualizer` class from `simulator/visualizer.py` in `initialize_visualizer()`
    - Use `Visualizer.animate_transition()` for smooth turn-by-turn rendering
    - Use `Visualizer.display_end_game_message()` to show winner
    - Create `run_visualizer_adapter()` entry point function for multiprocessing
  - **Error Handling**:
    - Gracefully handle pygame import errors
    - Catch and log all exceptions in event loop
    - Exit cleanly on any error
  - **Logging**:
    - Log adapter initialization
    - Log event processing start/stop
    - Log pygame errors
    - Include session_id in all logs
  - **Testing**:
    - Create `backend/tests/test_visualizer_adapter.py`
    - Mock pygame to avoid display requirement
    - Test adapter initialization
    - Test event queue consumption
    - Test state accumulation from turn events
    - Test game over event handling
    - Test graceful handling of pygame unavailability
    - Create integration test in `backend/tests/test_visualizer_integration.py`
    - Test full process spawn → event flow → termination cycle
  - **Validation**:
    - Run `uv run pytest backend/tests/test_visualizer_adapter.py backend/tests/test_visualizer_integration.py -v`
    - Run `uv run ruff check backend/app/services/visualizer_adapter.py`
    - Ensure test coverage >85% for adapter
    - Fix any issues and ensure all tests pass
  - **Requirements**: 2.2.6 (pass initial config), 2.3.1-2.3.4 (receive and process events), 2.4.1-2.4.5 (rendering behavior), 2.5.5 (handle pygame unavailability)
  - **Files**: `backend/app/services/visualizer_adapter.py`, `backend/tests/test_visualizer_adapter.py`, `backend/tests/test_visualizer_integration.py`

### Task 4: Integrate VisualizerService into SessionManager

- [x] **4. Integrate visualization into SessionManager lifecycle**
  - **SessionManager Changes**:
    - Modify `SessionManager.__init__()` to accept `visualizer_service` parameter (default to new instance)
    - Add `visualize: bool = False` parameter to `create_session()` method
    - In `create_session()`, spawn visualizer if `visualize=True` and store in context
    - In `_run_match_loop()`, send turn events to visualizer after SSE broadcast
    - In `_run_match_loop()`, send game over events to visualizer after SSE broadcast
    - In `_run_match_loop()` finally block, terminate visualizer on completion
    - In `cleanup_session()`, terminate visualizer before cancelling task
    - Wrap all visualizer operations in try-except to prevent exceptions
  - **Logging**:
    - Log visualizer spawn success with session_id and PID
    - Log spawn failures as warnings
    - Log event send failures
    - Log visualizer termination
  - **Testing**:
    - Update existing tests in `backend/tests/test_session_manager.py`:
      - Add `visualizer_service` parameter to SessionManager instantiation
      - Mock visualizer service to return `(None, None)` by default
    - Add new tests for visualizer integration:
      - Test session creation with `visualize=True` spawns visualizer
      - Test session creation with `visualize=False` does not spawn visualizer
      - Test graceful handling when visualizer spawn fails
      - Test session creation succeeds even if visualizer fails
      - Test turn events sent to visualizer during match loop
      - Test game over events sent to visualizer
      - Test visualizer terminated after match completion
      - Test visualizer terminated on session cleanup
    - Create `backend/tests/test_session_manager_visualizer.py` for comprehensive integration tests
  - **Validation**:
    - Run `uv run pytest backend/tests/test_session_manager.py backend/tests/test_session_manager_visualizer.py -v`
    - Run `uv run ruff check backend/app/services/session_manager.py`
    - Ensure all existing tests still pass
    - Ensure new visualization tests pass
    - Fix any issues
  - **Requirements**: 2.1.3 (spawn visualizer when visualize=true), 2.3.1-2.3.2 (send events), 2.5.1-2.5.4 (error handling), 2.6.1-2.6.2 (cleanup), 3.2.2-3.2.3 (compatibility), 3.4.1 (logging)
  - **Files**: `backend/app/services/session_manager.py`, `backend/tests/test_session_manager.py`, `backend/tests/test_session_manager_visualizer.py`

### Task 5: Update API and StateManager Integration

- [x] **5. Update API endpoint and integrate into StateManager**
  - **API Changes**:
    - Update `start_playground_match()` in `backend/app/api/sessions.py`
    - Extract `visualize` from `payload.visualize`
    - Pass `visualize` parameter to `session_manager.create_session()`
    - Ensure endpoint returns 200 OK even if visualization fails
  - **StateManager Integration**:
    - Modify `StateManager.__init__()` in `backend/app/core/state.py` to add `_visualizer_service` field
    - Add `visualizer_service` property getter
    - Implement `_initialize_visualizer_service()` method
    - Call initialization in `initialize()` method (before session manager)
    - Add service status tracking for visualizer service
    - Update `_initialize_session_manager()` to pass `visualizer_service` parameter
    - In `shutdown()`, iterate through active sessions and terminate visualizers
    - Handle errors gracefully during shutdown
  - **Logging**:
    - Log visualizer service initialization
    - Log shutdown operations
  - **Testing**:
    - Update `backend/tests/test_sessions_api.py`:
      - Test POST with `visualize=true` creates session successfully
      - Test POST with `visualize=false` creates session successfully
      - Test POST without `visualize` defaults to false
      - Test endpoint returns 200 OK even if visualizer fails
    - Update StateManager tests to verify visualizer service initialization
    - Mock session manager and visualizer service to avoid real execution
  - **Validation**:
    - Run `uv run pytest backend/tests/test_sessions_api.py backend/tests/test_system_integration.py -v`
    - Run `uv run ruff check backend/app/api/sessions.py backend/app/core/state.py`
    - Ensure all tests pass
    - Fix any issues
  - **Requirements**: 2.1.1 (accept visualize parameter), 2.5.6 (return 200 OK on failure), 2.6.3 (terminate on shutdown), 3.2.3 (integrate with StateManager)
  - **Files**: `backend/app/api/sessions.py`, `backend/app/core/state.py`, `backend/tests/test_sessions_api.py`

### Task 6: Comprehensive Testing and Validation

- [x] **6. End-to-end testing, resilience testing, and final validation**
  - **E2E Testing**:
    - Create `backend/tests/test_visualized_match_e2e.py`
    - Test complete visualized match from session creation to completion
    - Mock pygame to avoid display requirement
    - Verify session creation, match execution, SSE events, and cleanup
  - **Resilience Testing**:
    - Create `backend/tests/test_visualizer_resilience.py`
    - Test visualizer crash mid-match (kill process)
    - Verify match continues and SSE clients unaffected
    - Verify no exceptions raised
    - Verify appropriate error logging
  - **Concurrent Testing**:
    - Create `backend/tests/test_concurrent_visualizers.py`
    - Test 3 concurrent sessions with `visualize=true`
    - Verify independent execution and no interference
    - Verify all matches complete successfully
  - **Full Test Suite**:
    - Run `uv run pytest backend/tests/ -v --cov=backend.app --cov-report=html`
    - Verify all tests pass (existing + new)
    - Ensure test coverage for new code >80%
    - Fix any failing tests
  - **Code Quality**:
    - Run `uv run ruff check .`
    - Run `uv run ruff format .`
    - Fix any linting errors
    - Ensure code follows project style guidelines
  - **Manual Verification** (optional, for local testing):
    - Start backend with `uv run uvicorn backend.app.main:app --reload`
    - Create session with `visualize=true` via API
    - Verify pygame window opens (if display available)
    - Verify match completes successfully
  - **Requirements**: All requirements (comprehensive validation), 2.5.2 (crash resilience), 2.2.5 (concurrent sessions), 3.1.3 (independent performance)
  - **Files**: `backend/tests/test_visualized_match_e2e.py`, `backend/tests/test_visualizer_resilience.py`, `backend/tests/test_concurrent_visualizers.py`, all modified files

### Task 7: Update Visualizer Lifecycle for Manual Termination

- [x] **7. Modify visualizer to remain open after game completion for manual termination**
  - **Behavior Changes**:
    - Remove automatic visualizer termination in `SessionManager._run_match_loop()` finally block
    - Visualizer window remains open after game completion to display final game state
    - Window only closes when:
      - Admin calls `DELETE /playground/{session_id}` API (triggers `cleanup_session()`)
      - User closes pygame window (pygame.QUIT event)
      - Explicit shutdown signal sent via IPC queue
  - **Code Changes**:
    - Modify `backend/app/services/session_manager.py`:
      - Replace visualizer termination in finally block with comment documenting new behavior
      - Keep `cleanup_session()` unchanged - it will handle manual termination
    - Modify `backend/app/services/visualizer_adapter.py`:
      - Remove `self._running = False` from game_over event handler
      - Update `process_events()` docstring to reflect persistent window behavior
      - Window continues handling pygame events after game over
  - **Documentation Updates**:
    - Update `docs/specs/match-visualization/design.md`:
      - Section 2.2: Update "Game Over with Visualization" flow
      - Section 2.3: Update child process description
      - Section 3.4: Add key design decision #9 about persistent window
      - Section 3.5: Update SessionManager integration code examples
      - Section 5.3: Update cleanup triggers list
  - **Test Updates**:
    - Rename and update test in `backend/tests/test_session_manager_visualizer.py`:
      - Change `test_visualizer_terminated_after_match_completion` to `test_visualizer_not_terminated_after_match_completion`
      - Verify visualizer is NOT called during match completion
      - Verify visualizer IS terminated during cleanup_session()
    - Update `backend/tests/test_visualizer_adapter.py`:
      - Add shutdown event to `test_process_events_handles_turn_update` to exit loop
      - Verify game_over event no longer exits the loop
    - Update `backend/tests/test_visualizer_integration.py`:
      - Increase timeout and add retry logic for process termination check
  - **Validation**:
    - Run `uv run pytest backend/tests/ -v`
    - Verify all 147 tests pass (2 skipped)
    - Verify no breaking changes to existing functionality
    - Confirm visualizer stays open in manual testing
  - **Rationale**: Allows users to review final game state and provides more control over visualizer lifecycle. Admin retains ability to terminate via API when needed.
  - **Files**: `backend/app/services/session_manager.py`, `backend/app/services/visualizer_adapter.py`, `docs/specs/match-visualization/design.md`, `backend/tests/test_session_manager_visualizer.py`, `backend/tests/test_visualizer_adapter.py`, `backend/tests/test_visualizer_integration.py`

---

## Task Execution Notes

- **Sequential Execution**: Complete tasks in order (1 → 2 → 3 → 4 → 5 → 6 → 7), as each builds on previous work
- **Test-Driven Development**: Each task includes testing steps that must pass before moving to next task
- **Validation Gate**: Each task ends with running tests and linting - task is not complete until all tests pass
- **Mocking Strategy**: Use mocking extensively to avoid requiring pygame/display during automated tests
- **Incremental Commits**: Commit after completing each task
- **Reference Documents**: Refer back to `requirements.md` and `design.md` when implementing

## Implementation Notes

### Key Implementation Details

1. **Immediate Pygame Window Creation**: The `initialize_visualizer()` method creates the pygame window and Visualizer instance immediately when the session starts, allowing real-time visualization of the match.

2. **Real-Time Rendering**: Each turn event is rendered immediately as it arrives using `Visualizer.animate_transition()` for smooth animations between states, providing live match visualization.

3. **Pygame Event Handling Guard**: The `_handle_pygame_events()` method includes a critical guard check:
   ```python
   if pygame.display.get_init():
       for event in pygame.event.get():
           # ... handle events
   ```
   This prevents "video system not initialized" errors when trying to handle events before the display is created.

4. **Error Isolation**: All visualizer operations in `SessionManager` are wrapped in try-except blocks to ensure visualization failures never crash the session or affect API responses.

5. **Non-Blocking Event Sends**: The `send_event()` method uses `queue.put_nowait()` to prevent blocking the match loop if the visualizer is slow or the queue is full.

6. **Graceful Termination**: The `terminate_visualizer()` method attempts graceful shutdown with a timeout before force-killing the process.

7. **State Manager Integration**: The `VisualizerService` is initialized in the `StateManager` and passed to `SessionManager` via dependency injection, ensuring proper lifecycle management.

8. **Animation Timing**: The visualizer waits 0.5 seconds (ANIMATION_DURATION) between turns to allow animations to complete, matching the original Visualizer behavior.

9. **Persistent Visualizer Window** (Added in Task 7): The visualizer window remains open after game completion to display the final game state. This allows users to review the match outcome and provides more control over the visualizer lifecycle. The window only closes when:
   - Admin manually terminates via `DELETE /playground/{session_id}` API
   - User closes the pygame window directly
   - Explicit shutdown signal is sent via IPC queue

### Bug Fixes Applied

1. **Fixed pygame "video system not initialized" error**: Added `pygame.display.get_init()` check before calling `pygame.event.get()` in the event processing loop.

2. **Fixed test failures in client tests**: Created `client/tests/conftest.py` with proper async fixture using `app.router.lifespan_context(app)` to ensure StateManager initialization in test environment.

3. **Added comprehensive error handling**: All visualizer operations log errors but never propagate exceptions to prevent session crashes.

---

## Requirements Coverage

All requirements from `requirements.md` are covered by the 7 implementation tasks:

- **Section 2.1** (Opt-in Control): Tasks 1, 4, 5
- **Section 2.2** (Process Management): Tasks 2, 3, 4, 7
- **Section 2.3** (Event Communication): Tasks 2, 3, 4
- **Section 2.4** (Rendering Behavior): Task 3
- **Section 2.5** (Error Handling): Tasks 2, 3, 4, 6
- **Section 2.6** (Process Cleanup): Tasks 2, 4, 5, 7
- **Section 3.1** (Performance): Tasks 2, 6
- **Section 3.2** (Compatibility): Tasks 4, 5
- **Section 3.3** (Environment): Tasks 1, 2
- **Section 3.4** (Logging): Tasks 2, 3, 4
