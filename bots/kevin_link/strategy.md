# Kevin Link Bot Strategy: Tactical Combat System

## Core Principles & State Tracking

Kevin Link is a tactical wizard bot that employs sophisticated state tracking and decision-making to outmaneuver opponents. The bot maintains:

- **Dynamic State Tracking**: Monitors own/opponent HP, mana, cooldowns, positions, shield status, active minions, and artifacts
- **Movement Pattern Analysis**: Tracks both opponent and self-movement patterns for better prediction and positioning
- **Game Phase Awareness**: Implements distinct strategies for early game (turns 1-10) and late game (11+)

## Decision Priority Hierarchy

The bot follows a strict decision priority system:

1. **First-Turn Shield**: Always attempts to shield on first turn
   - Provides early protection against aggressive opponents
   - Enables safer positioning in early game

2. **Early Artifact Racing** (Turns 1-3)
   - Teleports or blinks to high-value artifacts if not in safe range
   - Prioritizes mana artifacts when mana < 60 to ensure spell availability

3. **Emergency Response** (`_emergency_response`)
   - Shield if HP ≤ 60 and not already shielded
   - Emergency heal when HP ≤ 30
   - Emergency blink when opponent distance ≤ 3
   - Emergency teleport to health artifacts when HP ≤ 35

4. **Offensive Opportunity** (`_offensive_opportunity`)
   - Fireball when opponent is in range (≤ 5) and not shielded
   - Melee attack when adjacent to opponent
   - Aggressive blink to close distance when healthy

5. **Resource Acquisition** (`_resource_strategy`)
   - Teleport to critical resources when HP ≤ 30 or mana ≤ 30
   - Blink toward resources when distance > 1
   - Move toward best artifact based on weighted scoring system

6. **Minion Management**
   - Summon first minion by turn 2
   - Position minions at least 2 squares away diagonally, avoiding board edges (1-8 range)
   - Maintain safe distance between wizard and minions to prevent collisions
   - Favor positions that maximize distance from opponent

7. **Positional Advantage** (`_positional_advantage`)
   - Proactive shielding when opponent is close or in fireball range
   - Healing when moderately damaged and not under immediate threat
   - Blink to maintain optimal combat distance

8. **Movement Strategy** (`_calculate_move`)
   - Prioritize artifact collection when resources are low
   - Defensive retreat when low health
   - Maintain optimal distance based on situation
   - Intelligent strafing to avoid predictable movement patterns

## Helper Strategies & Algorithms

- **`_calculate_optimal_distance`**: Dynamically determines ideal spacing
  - 7 units when at very low health
  - 6 units when low health without shield
  - 5 units when fireball ready and opponent not shielded
  - 3 units when shielded and healthy
  - 5 units as default

- **`_safe_retreat_direction`**: Advanced retreat calculation
  - Weights distances from all threats
  - Favors perpendicular movement away from threats
  - Avoids board edges and corners
  - Penalizes backtracking to previous positions

- **`_intelligent_strafe`**: Unpredictable lateral movement
  - Prefers perpendicular movement to main axis of distance
  - Avoids minions and dangerous positions
  - Includes randomization to reduce predictability
  - Considers proximity to valuable artifacts

- **`_predict_position`**: Anticipates opponent movement
  - Analyzes consistent movement patterns
  - Predicts likely next position for targeting
  - Ensures predictions stay within board boundaries

- **`_choose_best_artifact`**: Sophisticated artifact evaluation
  - Scores artifacts based on current needs (health/mana)
  - Considers distance and risk of collection
  - Evaluates whether opponent might reach artifact first
  - Adjusts value based on game phase

By combining these strategic elements, Kevin Link employs consistent tactical decision-making, making it a formidable and unpredictable wizard in the arena.