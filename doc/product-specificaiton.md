# Spellcasters Hackathon 2.0 Specification

## Overview

A backend-driven wizard-themed strategy game where participants submit Python bots that battle in a turn-based 10x10 arena. This system supports Playground, Arena, and Tournament modes. Execution is server-side with restricted bot code evaluation.

---

## Architecture

* **Bot Execution:**

  * Python-only bots
  * Executed on backend using `exec()` in a `RestrictedPython` sandbox
  * Each bot runs in a shared, single-threaded match engine
  * Bots maintain internal state across turns via persistent object instances

* **Modes:**

  * **Playground:** Local test vs. built-in bots, headless or visualized
  * **Arena:** One-off matches via web admin with visualizer auto-launch
  * **Tournament:** Round-robin between all registered bots; leaderboard maintained

* **Visualizer:**

  * Built with PyGame
  * Supports CLI switch `--headless` for log-only mode
  * Launched via subprocess by backend

---

## Bot Interface (Python)

* Each bot must implement `BotInterface` with the following structure:

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

* `decide()` must return a valid `BotAction` dict

---

## Game Rules & Constraints

* **Board:** 10x10 grid

* **Game ends when:**

  * One bot reaches HP <= 0 (win/loss)
  * Max 100 turns (draw)

* **Turn Execution Order:**

  * Bot A moves and acts
  * Bot B moves and acts

* **Actions per turn:** Move + Spell or Melee attack

* **Bot time limit per turn:** 100ms

* **Bot failure (error/timeout/invalid output):** Turn skipped

---

## Allowed Resources

* Standard Python libs: `math`, `random`, `collections`
* Access to filesystem, network, system calls: **blocked**
* Predefined constants (exposed): `BOARD_SIZE`, `SPELLS`, `DIRECTIONS`, etc.

---

## Match Logging (Headless)

* Console output format:

```
Turn 1
- BotA moves to [4,5]
- BotA casts fireball at [6,5] (HIT)
- BotB takes 20 damage
----------------------
```

* Spell cast events, damage, movement, and results included
* Optional flag to save to file

---

## Bot Submission

* Players submit Python code via admin UI (upload `.py` or paste)

* Metadata per bot:

  * `player_name`, `bot_code`, `last_updated`, `sprite_path`, `minion_sprite_path`
  * `submitted_from`, `wins`, `losses`, `draws`, `total_matches`

* Sprite Upload:

  * PNG only, max 256x256, max 200 KB
  * Validated via Pillow
  * Stored as `assets/custom/{player_name}/wizard.png`

* Submission Rules:

  * One active bot per player
  * Submissions can overwrite previous until manually locked
  * Name collision rejected
  * Validation errors (syntax/class/interface): Rejected with detailed message

---

## Tournament Logic

* Format: Round-robin

* Match pairings: Every unique pair

* Leaderboard scoring: Win = 3, Draw = 1, Loss = 0

* Tie-breaker: More wins > alphabetical order

* Match Failures:

  * Retry once
  * If failure persists: mark as loss

* Admin Controls:

  * Start tournament
  * Advance match manually ("Next Match")
  * Reset match history and leaderboard (preserve bot code)
  * Lock/unlock submissions

---

## Leaderboard

* Public webpage (e.g. projected on screen)
* Auto-refresh every 10 seconds
* Columns:

  * Rank
  * Player Name
  * Wins / Losses / Draws
  * Total Points
  * Matches Played
  * Sprite Thumbnail
  * Last Updated Time
* Sorted by rank only (no column sorting)

---

## Security & Execution Notes

* Bot code executed via `exec()` with controlled globals
* All sprite paths and user input sanitized
* Tournament matches logged for audit
* No login required; identity managed via manual name entry

---

## Next Steps for Dev Team

1. Implement restricted bot runner with validation logic
2. Hook PyGame visualizer launch to backend triggers
3. Build admin UI for submission, tournament control, and leaderboard
4. Integrate database for bot storage
5. Implement round-robin tournament engine
6. Prepare static assets and default fallback sprites
