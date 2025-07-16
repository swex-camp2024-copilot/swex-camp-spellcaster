# Spellcasters Hackathon 2.0 Specification

## Overview

A backend-driven wizard-themed strategy game where participants submit Python bots that battle in a turn-based 10x10 arena. This system supports Playground, Arena, and Tournament modes with HTTP API endpoints and real-time streaming. Bot execution uses server-side evaluation with security restrictions.

---

## Architecture

### Technology Stack
* **Backend:** FastAPI with sse-starlette for Server-Sent Events
* **Database:** SQLite for player and match data
* **Bot Execution:** Python `exec()` in `RestrictedPython` sandbox
* **Visualizer:** PyGame (launched via subprocess)
* **Frontend:** Web-based admin UI with real-time updates

### Execution Models

* **Playground Mode:**
  * HTTP API-driven with SSE streaming for real-time updates
  * Session-based match execution with configurable tick delays
  * Async/await architecture for concurrent match handling
  * Bot actions submitted via HTTP endpoints with timeout handling

* **Tournament Mode:**
  * Batch processing of round-robin matches
  * Direct bot instance execution (no HTTP layer)
  * Automated match scheduling and result recording

* **Bot Management:**
  * UUID-based player registration system
  * Bot validation pipeline with syntax and interface checking
  * Persistent storage with metadata tracking
  * Sprite upload and management system

---

## Player Registration

### Registration Process
Players must register before participating in matches:

```http
POST /players/register
Content-Type: application/json

{
  "player_name": "FireMage",
  "submitted_from": "pasted"
}
```

**Response:**
```json
{
  "player_id": "e7f2c8a1-...",
  "player_name": "FireMage"
}
```

### Player Database Schema
```sql
CREATE TABLE players (
    player_id UUID PRIMARY KEY,
    player_name VARCHAR(50) UNIQUE NOT NULL,
    submitted_from VARCHAR(10) NOT NULL,
    total_matches INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Registration Rules
* Player names must be unique (case-insensitive)
* UUIDs generated server-side for player identification
* Stats automatically updated after each match completion
* No authentication required (hackathon context)

---

## Bot Interface (Python)

Each bot must implement `BotInterface` with the following structure:

```python
class BotInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def sprite_path(self) -> Optional[str]: return None

    @property
    def minion_sprite_path(self) -> Optional[str]: return None

    @abstractmethod
    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]: ...
```

### Bot Execution Context
* `decide()` method must return a valid `BotAction` dict
* **Time Limits:**
  * Playground mode: 5 seconds HTTP response timeout
  * Tournament mode: 100ms bot logic execution limit
* **Allowed Resources:** `math`, `random`, `collections` modules only
* **Restricted:** Filesystem, network, system calls blocked via `RestrictedPython`

---

## Playground Mode

### Session Management
Playground matches run as independent sessions with real-time streaming:

```http
POST /playground/start
Content-Type: application/json

{
  "player_id": "e7f2c8a1-...",
  "opponent_type": "builtin",
  "opponent_id": null,
  "tick_delay_ms": 1000
}
```

### Match Execution Flow
1. **Session Creation:** Generate session_id, initialize game state
2. **Async Match Loop:** 
   - Collect actions from both players (HTTP or builtin)
   - Apply turn logic via game engine
   - Broadcast state updates via SSE
   - Continue until game over or 100 turns max
3. **Action Submission:**
   ```http
   POST /playground/{session_id}/action
   Content-Type: application/json

   {
     "player_id": "e7f2c8a1-...",
     "turn": 6,
     "action": { "move": [1,0], "spell": "fireball", "target": [6,5] }
   }
   ```

### Real-time Updates (SSE)
* **Event Stream:** `/playground/{session_id}/events`
* **Turn Events:** Game state, actions, and logs
* **Game Over Events:** Winner determination and final stats
* **Replay Support:** Cached events for session replay

### Timeout Handling
* **Default Timeout:** 5 seconds per action
* **Timeout Behavior:** Missing actions treated as "no action"
* **Logging:** Timeout events recorded in match logs

---

## Game Rules & Constraints

* **Board:** 10x10 grid
* **Game ends when:**
  * One bot reaches HP <= 0 (win/loss)
  * Max 100 turns reached (draw)
* **Turn Execution Order:**
  * Bot A moves and acts
  * Bot B moves and acts
* **Actions per turn:** Move + (Spell OR Melee attack)
* **Failure Handling:** Bot errors/timeouts result in skipped turns

---

## Bot Submission & Validation

### Submission Process
1. **Player Registration:** Obtain player_id via registration endpoint
2. **Bot Upload:** Submit Python code via admin UI (upload `.py` or paste)
3. **Validation Pipeline:**
   - Syntax checking
   - Interface compliance verification
   - Instantiation testing
   - Security scanning
4. **Storage:** Validated bots stored with metadata
5. **Availability:** Bots available for playground and tournament use

### Validation Rules
* Must subclass `BotInterface`
* All abstract methods implemented
* No restricted imports or operations
* Code must instantiate without errors
* One active bot per player (overwrites allowed until locked)

### Sprite Management
* **Format:** PNG only, max 256x256, max 200KB
* **Validation:** Pillow-based image verification
* **Storage:** `assets/custom/{player_name}/wizard.png`
* **Fallback:** Default sprites for missing uploads

---

## Tournament Mode

### Tournament Structure
* **Format:** Round-robin (every unique pair)
* **Execution:** Direct bot instance calls (no HTTP layer)
* **Scoring:** Win = 3 points, Draw = 1 point, Loss = 0 points
* **Tie-breaking:** More wins > alphabetical order

### Tournament Controls
* **Admin Actions:**
  * Start/stop tournament
  * Manual match advancement
  * Reset tournament (preserve bot code)
  * Lock/unlock submissions
* **Match Failure Handling:**
  * Retry once on failure
  * Persistent failures marked as losses
  * All matches logged for audit

### Leaderboard
* **Public Display:** Auto-refresh every 10 seconds
* **Columns:** Rank, Player, W/L/D, Points, Matches, Sprite, Last Updated
* **Sorting:** Rank only (no column sorting)
* **Real-time Updates:** Tournament progress reflected immediately

---

## Session Management & Cleanup

### Session Lifecycle
* **Creation:** On playground match start
* **Active State:** During match execution
* **Idle State:** Post-match with TTL (default 30 minutes)
* **Cleanup:** Automatic or manual via admin endpoints

### Admin Endpoints
```http
GET /playground/active          # List active sessions
DELETE /playground/{session_id} # Force session cleanup
GET /playground/{session_id}/replay # Replay match events
```

### Log Management
* **Playground Logs:** `logs/playground/{session_id}.log`
* **Tournament Logs:** `logs/tournament/{match_id}.log`
* **Format:** Structured turn-by-turn event logging
* **Retention:** Configurable via environment variables

---

## Security & Execution

### Bot Sandboxing
* **RestrictedPython:** Compile-time security restrictions
* **Execution Context:** Controlled globals and builtins
* **Resource Limits:** Memory and CPU constraints
* **Import Restrictions:** Whitelist of allowed modules

### Input Validation
* **Sprite Uploads:** File type, size, and content validation
* **Bot Code:** Syntax and security scanning
* **API Inputs:** Schema validation and sanitization
* **Player Names:** Length and character restrictions

### Error Handling
* **Bot Failures:** Graceful degradation with logging
* **System Errors:** Proper HTTP status codes and messages
* **Timeout Recovery:** Automatic retry mechanisms
* **Data Integrity:** Transaction-based database operations

---

## Implementation Notes

### Performance Considerations
* **Concurrent Sessions:** Configurable limit via `PLAYGROUND_MAX_SESSIONS`
* **Memory Management:** Session cleanup and garbage collection
* **Database Optimization:** Indexed queries and connection pooling
* **Caching:** Bot validation results and static assets

### Monitoring & Observability
* **Metrics:** Match completion rates, bot performance, system resource usage
* **Logging:** Structured logging with correlation IDs
* **Health Checks:** API endpoint monitoring
* **Alerting:** Error rate and performance thresholds

### Configuration Management
* **Environment Variables:** All configurable parameters externalized
* **Feature Flags:** Toggle validation, visualization, and other features
* **Resource Limits:** Configurable timeouts, memory limits, session counts
* **Database Settings:** Connection strings and pool configurations

---

## Open Implementation Questions

### Resolved by Backend Spec
1. ✅ Player registration and identification system
2. ✅ HTTP API structure and SSE streaming
3. ✅ Session management and cleanup procedures
4. ✅ Timeout handling and error recovery

### Remaining Open Points
1. **Visualizer Integration:** How does PyGame visualizer connect to HTTP/SSE system?
2. **Arena Mode:** Relationship between playground and arena modes unclear
3. **Bot Storage:** Integration between submission UI and playground system
4. **Authentication:** Role-based access for admin functions
5. **Scaling:** Multi-instance deployment and load balancing
6. **Backup/Recovery:** Database backup and disaster recovery procedures

### Suggested Enhancements
1. **WebSocket Alternative:** Consider WebSocket for bidirectional real-time communication
2. **Match History:** Persistent storage of all match results and replays
3. **Bot Analytics:** Performance metrics and win/loss analysis per bot
4. **Rate Limiting:** Prevent abuse of API endpoints
5. **Containerization:** Docker deployment for consistent environments
6. **Testing Framework:** Automated testing for bot validation and match execution

---

## Next Steps for Development

### Phase 1: Core Infrastructure
1. Implement FastAPI backend with SSE support
2. Set up SQLite database with player schema
3. Build bot validation and execution pipeline
4. Create session management system

### Phase 2: Playground Features
1. HTTP API endpoints for match control
2. Real-time streaming implementation
3. Timeout handling and error recovery
4. Admin dashboard for session monitoring

### Phase 3: Tournament System
1. Round-robin tournament engine
2. Leaderboard generation and display
3. Match scheduling and result tracking
4. Tournament administration controls

### Phase 4: Polish & Security
1. Security hardening and testing
2. Performance optimization
3. Monitoring and alerting setup
4. Documentation and deployment guides
