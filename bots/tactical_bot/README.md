# Tactical Bot

A sophisticated bot that uses a state machine and heuristics to make tactical decisions in combat.

## Features

1. **State Machine**: The bot operates in four distinct states:
   - AGGRESSIVE: Focus on dealing damage when in a strong position
   - DEFENSIVE: Focus on survival when threatened or low on health
   - GATHERING: Focus on collecting artifacts when low on resources
   - CONTROLLING: Focus on space control when minions are active

2. **Tactical Decision Making**:
   - Threat assessment based on enemy proximity and minion positions
   - Resource management (HP and mana)
   - Position evaluation for movement and teleportation
   - Spell combinations for effective combat

3. **Combat Strategies**:
   - Maintains optimal range for fireball attacks
   - Uses minions for space control
   - Prioritizes targets based on health and threat level
   - Smart resource gathering when needed

## State Transitions

The bot transitions between states based on:
- Current HP and mana levels
- Presence of threats
- Availability of artifacts
- Presence of friendly minions

## Spell Usage

- **Fireball**: Primary damage spell, used at optimal range
- **Shield**: Used when threatened or in defensive state
- **Heal**: Used when HP is low and in a safe position
- **Teleport**: Used to escape danger or quickly reach artifacts
- **Melee Attack**: Used opportunistically when adjacent to enemies
- **Summon**: Used to create minions for space control

## Movement Strategy

- Maintains optimal distance based on current state
- Uses both Manhattan and Chebyshev distance calculations
- Smart pathfinding to avoid threats and reach objectives
- Tactical repositioning for spell effectiveness

## Requirements

- Python 3.6+
- Game engine with standard spell implementations
- Sprite assets (tactical_bot.png and tactical_minion.png) 