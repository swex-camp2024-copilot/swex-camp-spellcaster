# Kevin Link Bot Strategy: Adaptive Combat System

## Core Principles & State Tracking

Kevin Link is an adaptive wizard bot that employs sophisticated state tracking and tactical decision-making to outmaneuver opponents. The bot maintains:

- **Dynamic State Tracking**: Monitors own/opponent HP, mana, cooldowns, positions, shield status, active minions, and artifacts
- **Movement Pattern Analysis**: Tracks both opponent and self-movement patterns for better prediction and positioning
- **Opponent Behavior Classification**: Categorizes opponents as aggressive, defensive, minion-focused, or balanced by turn 3
- **Adaptive Strategy**: Adjusts tactics based on opponent behavior and current game state
- **Game Phase Awareness**: Implements distinct strategies for early game (turns 1-5), mid game (6-15) and late game (16+)

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

- **`_classify_opponent`**: Identifies opponent behavior by turn 3
  - Aggressive: If damage taken ≥ 30 in early game
  - Defensive: If opponent uses shield
  - Minion-focused: If opponent maintains minions
  - Balanced: Default classification

- **`_adapt_strategy`**: Adjusts tactics based on opponent classification
  - Against aggressive opponents: Defensive positioning, prioritize shield
  - Against defensive opponents: More aggressive, focus on resource control
  - Against minion-focused opponents: Counter with targeted attacks

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

By combining these strategic elements, Kevin Link adapts to different opponents and situations, making it a formidable and unpredictable wizard in the arena.