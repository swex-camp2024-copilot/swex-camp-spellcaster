import os
import json
import random
import time
from typing import Dict, List, Tuple, Any, Optional
import requests
import hashlib

# Simple cache to store API responses and avoid redundant calls
decision_cache = {}

def create_openai_prompt(state, bot_name):
    """
    Create a detailed prompt for the OpenAI API based on the current game state.
    
    Args:
        state: The current game state
        bot_name: The name of our bot
    
    Returns:
        A structured prompt for the OpenAI API
    """
    # Extract relevant information from state
    turn = state["turn"]
    board_size = state["board_size"]
    self_data = state["self"]
    opp_data = state["opponent"]
    artifacts = state.get("artifacts", [])
    minions = state.get("minions", [])
    
    # Our position and stats
    self_pos = self_data["position"]
    self_hp = self_data["hp"]
    self_mana = self_data["mana"]
    self_cooldowns = self_data["cooldowns"]
    
    # Opponent position and stats
    opp_pos = opp_data["position"]
    opp_hp = opp_data["hp"]
    opp_name = opp_data["name"]
    
    # Sort minions by owner
    our_minions = [m for m in minions if m["owner"] == bot_name]
    enemy_minions = [m for m in minions if m["owner"] != bot_name]
    
    # Construct the rules and system prompt - optimized for conciseness and speed
    system_prompt = f"""
You are the AI control system for a wizard named {bot_name} in a turn-based magical battle game. Your goal is to defeat the opposing wizard.

GAME RULES SUMMARY:
- Game on {board_size}x{board_size} grid, positions from [0,0] to [{board_size-1},{board_size-1}]
- Move one square any direction (including diagonally) + optional spell
- Spells: 
  * fireball(30 mana,2cd,20dmg,range 5) - REQUIRES target
  * shield(20 mana,3cd,blocks 20) - NO target needed
  * teleport(20 mana,4cd) - REQUIRES target 
  * summon(50 mana,5cd) - REQUIRES target
  * heal(25 mana,3cd,heals 20) - NO target needed
  * melee_attack(0 mana,1cd,10dmg,range 1) - REQUIRES target position adjacent

CURRENT STATE (Turn {turn}):
- You: pos {self_pos}, HP {self_hp}/100, mana {self_mana}/100
- Cooldowns: {json.dumps(self_cooldowns)}
- Your minions: {len(our_minions)} {', '.join([f"[{m['position'][0]},{m['position'][1]}]hp{m['hp']}" for m in our_minions]) if our_minions else ""}
- Opponent: {opp_name} at {opp_pos}, HP {opp_hp}/100
- Enemy minions: {len(enemy_minions)} {', '.join([f"[{m['position'][0]},{m['position'][1]}]hp{m['hp']}" for m in enemy_minions]) if enemy_minions else ""}
- Artifacts: {len(artifacts)} {', '.join([f"[{a['position'][0]},{a['position'][1]}]{a['type']}" for a in artifacts]) if artifacts else ""}

Return a command that would maximize your chances of winning having in mind the opponent, artifacts, minions, current mana, health, cooldowns, positions and any other relevant factors.

INSTRUCTIONS:
Return JSON with:
- "move": Array of 2 integers [-1,1] for x,y movement
- "spell": null or a spell object with name and optional target

IMPORTANT: fireball, teleport, summon, and melee_attack REQUIRE target [x,y] coordinates
shield and heal DON'T need targets

Examples:
{{"move": [1, 0], "spell": {{"name": "fireball", "target": [5, 5]}}}}
{{"move": [0, -1], "spell": {{"name": "heal"}}}}
{{"move": [-1, -1], "spell": null}}
{{"move": [0, 1], "spell": {{"name": "melee_attack", "target": [2, 3]}}}}
"""
    
    return system_prompt

def call_openai_api(prompt):
    """
    Call the OpenAI API with the given prompt and return the decision.
    Uses caching to avoid redundant API calls for the same prompt.
    
    Args:
        prompt: The detailed game state and instructions prompt
    
    Returns:
        A dictionary with the 'move' and 'spell' decisions
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    # Create a hash of the prompt to use as a cache key
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    
    # Check if we have a cached response for this prompt
    if prompt_hash in decision_cache:
        print("Using cached decision")
        return decision_cache[prompt_hash]
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-4o",  # Using the more powerful model for better strategic reasoning
        "messages": [
            {"role": "system", "content": "You are a strategic AI helping a wizard in a turn-based magical battle game. Think several moves ahead like a chess grandmaster. Prioritize winning strategies, including effective use of minions, mana management, collecting artifacts, and tactical positioning. Analyze the opponent's likely moves and counter them."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,  # Slightly higher temperature for more strategic creativity
        "max_tokens": 300,  # Increased token count to allow for more complex reasoning
        "response_format": {"type": "json_object"}  # Force JSON response format
    }
    
    # Track time for performance monitoring
    start_time = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Calculate and print the response time
        response_time = time.time() - start_time
        print(f"OpenAI API response time: {response_time:.2f} seconds")
        
        response_data = response.json()
        
        # Extract the assistant's message content
        assistant_message = response_data["choices"][0]["message"]["content"]
        
        try:
            # Parse the JSON response
            decision = json.loads(assistant_message)
            
            # Validate the response format
            if "move" not in decision:
                raise ValueError("Response is missing 'move' field")
            
            # Ensure move is a list of 2 integers in range [-1, 1]
            move = decision["move"]
            if not isinstance(move, list) or len(move) != 2:
                raise ValueError("'move' must be a list with 2 elements")
            
            move[0] = max(-1, min(1, int(move[0])))  # Ensure x is in range [-1, 1]
            move[1] = max(-1, min(1, int(move[1])))  # Ensure y is in range [-1, 1]
            
            # Ensure spell format is correct if present
            if "spell" in decision and decision["spell"] is not None:
                spell = decision["spell"]
                if not isinstance(spell, dict) or "name" not in spell:
                    raise ValueError("'spell' must be null or a dict with a 'name' field")
                
                # Validate spell name against available spells
                spell_name = spell["name"]
                available_spells = ["fireball", "shield", "teleport", "summon", "heal", "melee_attack"]
                if spell_name not in available_spells:
                    raise ValueError(f"Spell '{spell_name}' is not a valid spell")
                
                # If spell requires a target but none is provided, raise error
                target_required_spells = ["fireball", "teleport", "summon", "melee_attack"]
                if spell_name in target_required_spells and "target" not in spell:
                    raise ValueError(f"Spell '{spell_name}' requires a target")
                
                # Ensure the target is a valid position (if provided)
                if "target" in spell:
                    target = spell["target"]
                    if not isinstance(target, list) or len(target) != 2:
                        raise ValueError(f"Spell target must be a list with 2 elements")
                    
                    # Convert target coordinates to integers
                    spell["target"] = [int(target[0]), int(target[1])]
            
            # Cache the decision for future use with the same prompt
            decision_cache[prompt_hash] = decision
            
            return decision
            
        except json.JSONDecodeError as e:
            # If we can't parse the response as JSON, create a fallback response
            print(f"Error parsing API response as JSON: {e}")
            print(f"Raw response: {assistant_message}")
            return {"move": [0, 0], "spell": None}  # Default no-op
            
        except Exception as e:
            print(f"Error processing API response: {e}")
            print(f"Raw response: {assistant_message}")
            
            # Try to safely extract and correct any partial information
            try:
                partial_decision = json.loads(assistant_message)
                move = partial_decision.get("move", [0, 0])
                
                # If we have a move but spell is invalid, use the move with no spell
                if isinstance(move, list) and len(move) == 2:
                    print(f"Using partial decision with move {move} but no spell")
                    return {"move": [max(-1, min(1, int(move[0]))), max(-1, min(1, int(move[1])))], "spell": None}
            except:
                pass
                
            return {"move": [0, 0], "spell": None}  # Default no-op
    
    except Exception as e:
        print(f"Error connecting to OpenAI API: {e}")
        return {"move": [0, 0], "spell": None}  # Default no-op in case of API connection error
