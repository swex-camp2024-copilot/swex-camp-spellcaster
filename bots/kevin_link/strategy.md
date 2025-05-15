# Kevin Link Bot Strategy: Adaptive Combat System

The Kevin Link bot employs a prioritized decision-making process, integrating adaptive tactics, resource management, and predictive capabilities to engage opponents effectively.

## Core Principles & Tracking
- **Dynamic State Tracking**: Monitors own/opponent HP, mana, cooldowns, positions, shield status, active minions, and artifacts.
- **Opponent Analysis**:
    - `_classify_opponent`: Classifies opponent behavior (aggressive, defensive, minion-focused, balanced) based on damage taken, shield usage, and minion activity. Updated each turn.
    - `_adapt_strategy`: Modifies high-level `_minion_strategy` (defend, attack, counter) every 5 turns based on opponent classification.
- **Pattern Recognition**: Tracks own last 5 positions and opponent's last 10 positions to inform movement and prediction.
- **Game Phases**: Differentiates between early game (first 10 turns) and later game, potentially influencing decisions (though `_early_game` flag isn't heavily used yet).

## Decision Priority Order (Executed Sequentially)

1.  **Emergency Response (`_emergency_response`)**: Highest priority for immediate survival.
    *   **Critical Shield**: If HP <= 30, not shielded, shield available.
    *   **Emergency Heal**: If HP <= 20, heal available.
    *   **Under Attack Protocol** (if `_under_attack` is true and `_damage_taken` in last 3 turns >= 15):
        *   Shield if not active and available.
        *   **Emergency Blink**: If opponent distance <= 2, blink available. Uses `_safe_retreat_direction` considering all threats.
        *   **Emergency Teleport**: If HP <= 25, teleport available, and health artifact exists.

2.  **Offensive Opportunity (`_offensive_opportunity`)**: If HP > Opponent HP + 20.
    *   **Fireball**: If opponent not shielded, fireball available, distance <= 5. Targets `_predict_position` (based on opponent's last two moves if consistent).
    *   **Melee Attack**: If adjacent (Manhattan distance 1), melee available.
    *   **Aggressive Blink**: If distance > 2 and <= 5, opponent not shielded, blink available. Uses `_calculate_interception` (moves towards predicted or current opponent position).

3.  **Resource Acquisition (`_resource_strategy`)**: If HP <= 60 or Mana <= 50.
    *   **Artifact Selection**: `_choose_best_artifact` scores artifacts based on immediate need (HP/Mana thresholds), distance, and risk (opponent proximity and ability to reach first).
    *   **Teleport**: If (critical health/mana need or artifact distance >= 5), teleport available.
    *   **Blink**: If artifact distance > 1, blink available.
    *   **Move**: If no spell action, signals `move_only` towards the best artifact using `_calculate_move_toward_artifact`.

4.  **Minion Management**:
    *   **Summon**: If own minions < 1, summon available, mana >= 60.
        *   **Strategic Placement**: Minion is summoned to a target square calculated to be defensively positioned (1 step "behind" the wizard, relative to the opponent), avoiding wizard's own square and clamped to board.

5.  **Positional Advantage (`_positional_advantage`)**: Tactical adjustments and spell usage.
    *   **Defensive Shield**: If not shielded, opponent distance <= 4, shield available, and (HP <= 70 OR (opponent classified "aggressive" AND distance <= 3)).
    *   **Proactive Shield**: 30% chance to shield if not shielded, opponent distance <= 5, self mana >= 40, opponent not "defensive", shield available.
    *   **Heal**: If HP <= 65, opponent distance >= 4, heal available.
    *   **Positional Blink**: If ((opponent distance < 2 AND HP < 60) OR current distance deviates > 2 from `optimal_distance` (usually 4)), blink available.
        *   If HP < 60 and very close, uses `_safe_retreat_direction`.
        *   Otherwise, uses `_direction_to_optimal_distance`.

6.  **Movement Strategy (`_calculate_move`)**: Default move calculation if no spell was cast.
    *   **Artifact Priority**: If artifacts exist and (HP <= 70 or Mana <= 60), moves towards best artifact via `_calculate_move_toward_artifact`.
    *   **Defensive Retreat**: If HP <= 40 and opponent distance <= 3, uses `_safe_retreat_direction`.
    *   **Optimal Distance Maintenance**: Calculates `_optimal_distance` based on current state (HP, shields, fireball readiness).
        *   If not at optimal distance, moves towards/away from the opponent.
        *   If at optimal distance, executes `_intelligent_strafe`.

## Key Helper Strategies & Algorithms

-   **`_safe_retreat_direction(self_pos, primary_threat_pos, all_minions, opponent_pos)`**:
    *   Evaluates all 8 adjacent squares.
    *   Scores based on: distance to primary threat (weighted heavily), sum of distances to all other enemy units, penalties for edges/corners, small penalty for repeating last move.
    *   Selects the highest scoring, valid move.
-   **`_intelligent_strafe(self_data, self_pos, target_pos, minions, artifacts)`**:
    *   Chooses perpendicular strafe directions.
    *   Scores options based on: maintaining/adjusting distance to target, strong penalties for moving near any minions (especially opponent's), bonus for moving towards strategically valuable artifacts (re-evaluates `_choose_best_artifact`), strong penalties for board edges/corners, penalty for repeating last 1-step move.
    *   Randomly chooses among best-scoring options; has fallback logic.
-   **`_calculate_optimal_distance(self_data, opp_data, hp, mana)`**:
    *   Returns 6 if HP <= 30.
    *   Returns 5 if HP <= 50 and not shielded.
    *   Returns 4 if fireball ready and opponent not shielded (ideal attack range).
    *   Returns 2 if self is shielded and HP > 70 (aggressive posture).
    *   Default is 4.
-   **`_direction_to_optimal_distance(self_data, self_pos, target_pos, optimal_distance)`**:
    *   If already at optimal distance, calls `_intelligent_strafe`.
    *   Otherwise, moves towards or away from the target to reach optimal distance.
-   **Movement (`move_toward`, `_direction_away_from`, `_direction_toward`)**: Basic 1-step movement utilities with boundary checks.

This detailed strategy aims for a balance of aggression, defense, and resource management, adapting dynamically to the opponent and game situation.