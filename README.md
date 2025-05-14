# 🧙 Spellcasters

**Spellcasters** is a hackathon game challenge where participants program bots to battle in a turn-based, wizard-themed strategy arena. Each bot controls a wizard who can move, cast spells, summon minions, and collect artifacts — all on a 10x10 battlefield.

This repo includes:
- A full game engine
- Bot development framework
- Visualizer with animations (using Pygame)
- Sample smart bots

---

## 🎮 How It Works

Each wizard-bot competes by:
- Moving across a grid (like a chess king)
- Casting spells (fireball, shield, teleport, etc.)
- Summoning minions
- Collecting artifacts for health, mana, or cooldown boosts

Bots receive structured game state input each turn and return an action (move + optional spell).

---

## 🚀 Quick Start

### 1. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 2. Install pip-tools and Compile Requirements

```bash
pip install pip-tools
pip-compile requirements.in 
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🧠 Bot Interface

To participate in the game, each bot must implement a decide(state) method. This method is called every turn and must return an action dict.
Ask your AI assistant to give you more details.

---

## 📥 State Input Format

The state dictionary includes everything your bot needs to make decisions - your AI assistant can provide you more details on this.

---

## ✍️ Add Your Own Bot

Create a new folder/module in bots/, and implement the required decide(state) logic.
Your main task is to implement how decide method works for your bot. Method needs to return an object like this:
```python
{
    "move": move,
    "spell": spell
}
```
Move must be an array of two integers where one represent your movement on x-axis and another one movement on y-axis. Numbers must be in range from -1 to 1.

Spell format is defined as below:
```python 
{
    "name": spell_name,
    "target": position
}
```
Spell name must be one of the values defined in rules.py. Position is a tuple representing coordinates on the board.

Spells shield and heal do not require target to be provided.

---

## 📥 Add Sprites
Place custom assets in assets/:

```
assets/
├── wizards/
├── minions/
```

Use PNGs with transparent backgrounds. Add the path to your sprite using the respective properties in the bot class.
NOTE: It is not necessary to add sprites to play the game - if the custom sprite is not provided then the default one(s) will be used.