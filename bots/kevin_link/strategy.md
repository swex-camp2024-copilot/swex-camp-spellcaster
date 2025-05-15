# Kevin Link Bot Decision Structure

The Kevin Link bot implements an advanced decision structure with adaptive strategies to counter different opponent types:

## Advanced Features
1. **Opponent Strategy Detection** - Identifies aggressive fireball-focused opponents like SampleBot3
2. **Attack Detection System** - Tracks health changes to detect when under attack
3. **Enemy Movement Prediction** - Tracks and predicts opponent's position to aim spells more effectively
4. **Tactical Distance Management** - Maintains optimal combat distance based on opponent type
5. **Intelligent Artifact Selection** - Scores artifacts based on need, tactical advantage, and defensive positioning
6. **Strafing Movement** - Uses unpredictable movement patterns to avoid enemy attacks
7. **Turn-Based Strategy Adjustment** - Adapts strategy based on game phase
8. **Path Blocking Analysis** - Identifies artifacts that provide defensive positioning benefits

## Decision Priority Order
1. **Emergency Shield** - Immediate shield when under active attack (highest priority)
2. **First Round Shield** - Shield on first turn for early protection
3. **Adaptive Counter Strategy**:
   - Against aggressive opponents: Earlier healing (HP ≤ 85%) and shielding (HP ≤ 80%)
   - Against standard opponents: Normal defensive shielding when close and HP ≤ 70%
4. **Predictive Fireball** - Cast at predicted enemy position or current position if in range
5. **Resource Management** - Prioritized artifact collection when resources are low:
   - Blink toward critical artifacts
   - Teleport to artifacts when critically low on resources
6. **Tactical Blink** - Use blink for:
   - Escaping when low health and enemy is close
   - Advancing toward opponent when healthy for tactical advantage
7. **Melee Attack** - Attack adjacent enemies, prioritizing those with lowest HP
8. **Adaptive Healing** - Healing threshold adjusts based on opponent type:
   - HP ≤ 60% against aggressive opponents
   - HP ≤ 75% against standard opponents
9. **Context-Aware Minion Summoning**:
   - More aggressive summoning in early game
   - Summon when mana ≥ 75% in mid/late game
10. **Strategic Teleport** - Teleport to best artifact based on:
    - Critical resource needs
    - Strategic positioning
    - Enemy distance
    - Blocking potential
11. **Intelligent Movement**:
    - Against aggressive opponents: Maintain safer 5-square distance
    - Against standard opponents: Maintain optimal 4-square distance
    - Retreat when critically low on health
    - Use strafing to avoid predictability
    - Prioritize artifacts that block line of sight to opponent

This updated bot significantly improves on the previous version by adapting its strategy based on opponent behavior, with specific counters for aggressive fireball-focused opponents like SampleBot3.