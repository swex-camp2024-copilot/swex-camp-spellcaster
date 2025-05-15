# Kevin Link Bot Strategy: Adaptive Combat System

The Kevin Link bot implements an advanced adaptive decision structure with dynamic strategies to counter all types of opponents:

## Core Strategies

1. **Opponent Classification** - Identifies opponent behavior (aggressive, defensive, minion-focused, balanced)
2. **Dynamic Adaptation** - Adjusts tactics every 5 turns based on opponent behavior and game state
3. **Emergency Response System** - Highest priority given to immediate threats and critical situations
4. **Optimal Positioning** - Maintains combat distance based on health, mana, and spell availability
5. **Intelligent Resource Management** - Risk-reward assessment for artifact collection

## Advanced Features

1. **Combat State Analysis** - Tracks damage taken, attack sources, and under-attack status
2. **Predictive Positioning** - Predicts opponent movement patterns for better targeting
3. **Safe Retreat Calculation** - Intelligently retreats while avoiding board edges and obstacles
4. **Strategic Artifact Scoring** - Evaluates artifacts based on need, risk, and tactical advantage
5. **Intelligent Strafing** - Uses perpendicular movement to maintain combat distance while avoiding obstacles
6. **Minion Strategy Adaptation** - Adjusts minion usage based on opponent classification

## Decision Priority Order

1. **Emergency Response** - Immediate shield/heal/escape when under heavy attack or at critical health
2. **Offensive Opportunity** - Capitalize on health advantage with targeted fireballs and tactical positioning
3. **Resource Acquisition** - Smart artifact collection based on need and risk assessment
4. **Minion Management** - Strategic minion deployment based on opponent behavior
5. **Positional Advantage** - Maintain optimal combat distance with preemptive shielding and healing
6. **Movement Optimization** - Intelligent path planning considering obstacles, artifacts, and tactical positioning

## Tactical Considerations

1. **Enemy Distance Management**:
   - Maintains 6+ squares when critically low on health
   - Keeps 4-5 squares when fireball is ready
   - Closes to 2-3 squares when shielded with high health
   
2. **Resource Priority**:
   - Teleports to critical health artifacts when below 30 HP
   - Uses blink for efficient artifact collection
   - Avoids contested artifacts when enemy is closer
   
3. **Combat Adaptation**:
   - Against aggressive opponents: prioritizes defense and shielding
   - Against defensive opponents: takes offensive approach
   - Against minion-focused opponents: adopts counter strategies
   - Against balanced opponents: adapts based on resource advantage

4. **Board Positioning**:
   - Avoids board edges during retreat
   - Uses intelligent strafing to maintain unpredictability
   - Considers artifact positions in movement decisions

This strategy provides a robust framework that adapts to any opponent type, not just predefined patterns, making it effective against a wide variety of opponents.