from game.rules import MAX_HP, MAX_MANA, MANA_REGEN, SPELLS

class Wizard:
    def __init__(self, name, position):
        self.name = name
        self.hp = MAX_HP
        self.mana = MAX_MANA
        self.position = position
        self.cooldowns = {spell: 0 for spell in SPELLS}
        self.shield_active = False

    def regen_mana(self):
        self.mana = min(MAX_MANA, self.mana + MANA_REGEN)

    def reduce_cooldowns(self):
        for spell in self.cooldowns:
            if self.cooldowns[spell] > 0:
                self.cooldowns[spell] -= 1

    def can_cast(self, spell):
        return self.mana >= SPELLS[spell]["cost"] and self.cooldowns[spell] == 0

    def cast_spell(self, spell):
        self.mana -= SPELLS[spell]["cost"]
        self.cooldowns[spell] = SPELLS[spell]["cooldown"]

    def to_dict(self):
        return {
            "name": self.name,
            "hp": self.hp,
            "mana": self.mana,
            "position": self.position,
            "cooldowns": self.cooldowns.copy(),
            "shield_active": self.shield_active
        }
