# Kevin Link Bot Strategy: Improved Adaptive Combat System

## Game Log Analysis Insights & Improvement Areas (Post-Analysis)

Analysis of game logs against various sample bots revealed several key issues impacting win rate:

1.  **Minion Management & Survivability**:
    *   **Issue**: Minions are often destroyed quickly and sometimes collide with Kevin Link itself, wasting mana and creating positional vulnerabilities.
    *   **Improvement**:
        *   Maintain greater distance between wizard and summoned minions to avoid collisions
        *   Implement more strategic minion placement (diagonal from wizard, away from enemy)
        *   Summon minions earlier in the game to build tactical advantage
        *   Use minions as a defensive buffer between wizard and opponent

2.  **Spell Decision Making**:
    *   **Issue**: Shield usage is often reactive rather than proactive, allowing opponents to deal significant damage
    *   **Improvement**:
        *   Shield preemptively when opponent is in fireball range (<=5 distance)
        *   Prioritize shield at game start like Sample Bot 2 does successfully
        *   More aggressive fireball usage when opponent shield is down
        *   Implement a simple cooldown tracking system for opponent spells

3.  **Resource Management**:
    *   **Issue**: Bot sometimes conserves mana too cautiously or spends unnecessarily
    *   **Improvement**:
        *   Lower mana threshold for critical spells (shield, heal)
        *   More aggressive heal usage when above 60 HP (currently waits until too low)
        *   Better artifact prioritization - cooldown artifacts often undervalued

4.  **Positioning & Movement**:
    *   **Issue**: Bot often maintains suboptimal distance from opponents, allowing them to control engagement
    *   **Improvement**:
        *   Increase default optimal distance from 4 to 5 (fireball range but safer)
        *   Improve retreating logic to consider board edges and corners more thoroughly
        *   Implement better obstacle avoidance to prevent getting trapped

5.  **Situational Awareness & Prediction**:
    *   **Issue**: Bot doesn't effectively anticipate opponent movements, especially for offensive spells
    *   **Improvement**:
        *   Enhance position prediction accuracy for fireball targeting
        *   Track opponent spell usage patterns to anticipate their next move
        *   Better calculate interception paths for optimal positioning

## Core Principles & Tracking
- **Dynamic State Tracking**: Monitors own/opponent HP, mana, cooldowns, positions, shield status, active minions, and artifacts.
- **Opponent Analysis**:
    - `_classify_opponent`: Improved classification to detect patterns earlier (by turn 3)
    - `_adapt_strategy`: Modified to be more responsive to opponent tactics
- **Pattern Recognition**: Track opponent positions and predict movements with greater accuracy
- **Game Phase Awareness**: Implement distinct strategies for early game (turns 1-5), mid game (6-15) and late game (16+)

## Decision Priority Order (Revised)

1.  **First-Turn Shield**: Always shield on first turn if possible (like Sample Bot 2)
    *   Provides early protection against aggressive bots
    *   Enables safer positioning in early game

2.  **Emergency Response (`_emergency_response`)**: Critical survival tactics
    *   **Shield Threshold Raised**: Shield if HP <= 60, not shielded, shield available (up from 30)
    *   **Emergency Heal**: If HP <= 30, heal available (up from 20)
    *   **Emergency Blink**: If opponent distance <= 3, blink available (up from 2)
    *   **Emergency Teleport**: If HP <= 35, teleport available (up from 25)

3.  **Offensive Opportunity (`_offensive_opportunity`)**: Improved targeting
    *   **Fireball**: More aggressive usage when opponent HP <= 50
    *   **Enhanced Prediction**: Improve position prediction for fireball targeting
    *   **Melee Attack**: Calculate damage potential before committing

4.  **Resource Acquisition (`_resource_strategy`)**: Better artifact evaluation
    *   **Health Prioritization**: Higher weight on health artifacts when HP < 50
    *   **Mana Prioritization**: Higher weight on mana artifacts when mana < 40
    *   **Cooldown Value**: Increase value of cooldown artifacts, particularly when offensive spells are ready

5.  **Minion Management**: Strategic deployment
    *   **Early Game Summon**: Summon first minion by turn 3 if possible
    *   **Positioning**: Summon minions 2 squares away diagonally between wizard and opponent
    *   **Avoidance**: Stronger checks to prevent self-collision with minions
    *   **Multiple Minions**: Support for maintaining 2 minions when mana allows

6.  **Positional Advantage (`_positional_advantage`)**: Tactical positioning
    *   **Proactive Shield**: Shield when opponent distance <= 5 and may have fireball ready
    *   **Heal Earlier**: Heal at HP <= 75 when safe (up from 65)
    *   **Optimal Distance**: Maintain 5 units from opponent (up from 4)
    *   **Edge Avoidance**: Stronger penalties for positions near board edges

## Key Improvements to Helper Strategies & Algorithms

-   **`_safe_retreat_direction`**: 
    *   Increased weight for perpendicular movement away from threats
    *   Better edge avoidance logic to prevent getting trapped
    *   Stronger penalties for backtracking to previous positions

-   **`_intelligent_strafe`**:
    *   More unpredictable movement patterns to avoid fireball tracking
    *   Better evaluation of potential collision risks
    *   Consider opponent's range when choosing strafe direction

-   **`_calculate_optimal_distance`**:
    *   Default distance increased to 5 (from 4)
    *   Situational awareness for different opponent types:
      *   Distance 6-7 against fireball-focused opponents
      *   Distance 2-3 against shielded opponents with melee focus
      *   Distance 5-6 as default against balanced opponents

-   **`_predict_position`**:
    *   Improved movement pattern detection
    *   Consider opponent's available paths based on board state
    *   Factor in likely destinations (artifacts, minions) in predictions

-   **Artifact Value Calculation**:
    *   Dynamic value adjustment based on current game state
    *   Higher value for health artifacts in late game
    *   Incorporate cooldown artifacts into offensive strategy

These improvements address the key weaknesses observed in game logs while maintaining Kevin Link's adaptive combat style. By implementing more preemptive decision-making and improving positional awareness, the bot should perform more consistently against the sample bots.