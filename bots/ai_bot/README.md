# AI Bot

A deep learning-based bot that uses Deep Q-Learning (DQN) to learn optimal strategies through self-play and curriculum learning.

## Features

1. **Deep Q-Learning Architecture**:
   - Neural network for Q-value approximation
   - Experience replay buffer for stable learning
   - Prioritized replay for important experiences
   - Epsilon-greedy exploration strategy

2. **Curriculum Learning**:
   - Progressive difficulty scaling
   - Starts with easy opponents
   - Gradually introduces harder opponents
   - Self-play in later stages

3. **State Representation**:
   - Game board state
   - Health and mana levels
   - Spell cooldowns
   - Relative positions
   - Minion locations
   - Artifact positions

4. **Reward Structure**:
   - Positive rewards for:
     * Damaging opponents
     * Winning matches
     * Collecting artifacts
     * Effective healing
     * Successful spell casts
   - Negative rewards for:
     * Taking damage
     * Losing matches
     * Inefficient healing
     * Missing spells

## Training Process

1. **Phase 1: Basic Training**
   - Trains against easy bots
   - Focuses on basic movement and spell usage
   - High exploration rate

2. **Phase 2: Intermediate**
   - Introduces medium difficulty bots
   - Reduces exploration rate
   - Starts learning tactical positioning

3. **Phase 3: Advanced**
   - Trains against hard bots
   - Low exploration rate
   - Complex strategy development

4. **Phase 4: Self-Play**
   - Trains against copies of itself
   - Very low exploration rate
   - Refines advanced strategies

## Visualization

The training process includes real-time visualization of:
- Win rates against different opponents
- Average rewards per episode
- Exploration rate decay
- Draw rates

## Model Architecture

- Input Layer: Game state features
- Hidden Layers: Dense neural networks
- Output Layer: Q-values for each possible action
- Activation: ReLU for hidden layers
- Optimizer: Adam
- Loss: Huber Loss (robust to outliers)

## Requirements

- Python 3.6+
- PyTorch
- NumPy
- Matplotlib (for visualization)
- Game engine with standard spell implementations
- Sprite assets (ai_bot.png and ai_minion.png)

## Training Commands

```bash
# Basic training
python train.py --episodes 1000 --matches 20

# Extended training with more episodes
python train.py --episodes 5000 --matches 20

# Quick training for testing
python train.py --episodes 100 --matches 10
```

## Performance Tips

1. **Resource Management**:
   - Monitor mana usage
   - Heal efficiently
   - Collect artifacts strategically

2. **Combat Tactics**:
   - Maintain optimal range
   - Use spells effectively
   - Control space with minions

3. **Training Optimization**:
   - Adjust exploration rate
   - Balance curriculum phases
   - Monitor reward signals 