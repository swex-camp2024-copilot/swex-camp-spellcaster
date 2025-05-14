# Kevin Link Bot Decision Structure

The new Kevin Link bot implements an advanced decision structure that significantly improves upon both sample bots:

## Advanced Features
1. **Enemy Movement Prediction** - Tracks and predicts opponent's position to aim spells more effectively
2. **Tactical Distance Management** - Maintains optimal combat distance based on health and mana
3. **Intelligent Artifact Selection** - Scores artifacts based on need and tactical advantage
4. **Strafing Movement** - Uses unpredictable movement patterns to avoid enemy attacks
5. **State Memory** - Remembers artifact positions and enemy movements over time

## Decision Priority Order
1. **First Round Shield** - Always shield on first turn for early protection
2. **Preemptive Defense** - Shield when opponent is close and HP ≤ 70%
3. **Predictive Fireball** - Cast at predicted enemy position or current position if in range
4. **Tactical Blink** - Use blink for:
   - Escaping when low health and enemy is close
   - Quickly reaching valuable artifacts
5. **Melee Attack** - Attack adjacent enemies, prioritizing those with lowest HP
6. **Aggressive Healing** - Heal when HP ≤ 75% (more aggressive than sample bots)
7. **Strategic Minion Summoning** - Summon when mana ≥ 60 and no existing minion
8. **Smart Teleport** - Teleport to best artifact based on:
   - Critical resource needs
   - Strategic positioning
   - Enemy distance
9. **Intelligent Movement**:
   - Move toward scored artifacts based on needs
   - Maintain optimal 4-square distance for fireball range
   - Strafe unpredictably when at optimal range
   - Back away from too-close enemies
   - Close distance when enemy is too far

This bot significantly improves on the sample bots through tactical awareness, resource management, and position prediction while maintaining the core strengths of both sample implementations.