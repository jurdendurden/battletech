import random
import json
from datetime import datetime
from models import db, Player, MechTemplate, PlayerMech, VehicleTemplate, PlayerVehicle

class GameEngine:
    """Main game engine for BattleTech MUD."""
    
    def __init__(self):
        self.encounters = self._load_encounters()
        self.missions = self._load_missions()
    
    def _load_encounters(self):
        """Load encounter data."""
        return {
            'pirate_patrol': {
                'name': 'Pirate Patrol',
                'description': 'A small pirate patrol blocks your path.',
                'difficulty': 'easy',
                'reward_credits': (100, 300),
                'reward_experience': (50, 150),
                'success_chance': 0.7,
                'terrain_modifier': {
                    'forest': 0.1,
                    'mountains': -0.1,
                    'desert': 0.05
                }
            },
            'salvage_opportunity': {
                'name': 'Salvage Opportunity',
                'description': 'You discover abandoned military equipment.',
                'difficulty': 'easy',
                'reward_credits': (200, 500),
                'reward_experience': (25, 75),
                'success_chance': 0.8,
                'terrain_modifier': {
                    'hills': 0.1,
                    'plains': 0.05
                }
            },
            'mercenary_contract': {
                'name': 'Mercenary Contract',
                'description': 'A local faction offers you a contract.',
                'difficulty': 'medium',
                'reward_credits': (500, 1000),
                'reward_experience': (100, 300),
                'success_chance': 0.6,
                'terrain_modifier': {
                    'plains': 0.1,
                    'desert': 0.05
                }
            },
            'bandit_ambush': {
                'name': 'Bandit Ambush',
                'description': 'Bandits attempt to ambush you!',
                'difficulty': 'hard',
                'reward_credits': (300, 800),
                'reward_experience': (150, 400),
                'success_chance': 0.5,
                'terrain_modifier': {
                    'forest': -0.2,
                    'jungle': -0.15,
                    'mountains': -0.1
                }
            },
            'mech_duel': {
                'name': 'Mech Duel Challenge',
                'description': 'Another MechWarrior challenges you to single combat.',
                'difficulty': 'hard',
                'reward_credits': (800, 1500),
                'reward_experience': (200, 500),
                'success_chance': 0.4,
                'terrain_modifier': {
                    'plains': 0.1,
                    'desert': 0.05
                }
            }
        }
    
    def _load_missions(self):
        """Load mission data from JSON file."""
        try:
            with open('data/missions.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: missions.json not found, using default missions")
            return {
                'escort_mission': {
                    'name': 'Escort Mission',
                    'description': 'Escort a convoy through dangerous territory.',
                    'duration': 3,
                    'base_reward_credits': 1500,
                    'base_reward_experience': 300,
                    'level_scaling': {
                        'credits_per_level': 500,
                        'experience_per_level': 100
                    },
                    'requirements': {
                        'min_level': 2,
                        'mechs_required': 1
                    }
                }
            }
        except json.JSONDecodeError as e:
            print(f"Error parsing missions.json: {e}")
            return {}
    
    def calculate_success_chance(self, player, encounter_type, terrain_type):
        """Calculate success chance for an encounter."""
        encounter = self.encounters.get(encounter_type)
        if not encounter:
            return 0.0

        base_chance = encounter['success_chance']
        
        # Skill modifiers (lower is better in BattleTech)
        gunnery_bonus = (8 - player.gunnery) * 0.05    # Combat accuracy
        piloting_bonus = (8 - player.piloting) * 0.03  # Mech control
        guts_bonus = (8 - player.guts) * 0.02          # Morale and staying power
        tactics_bonus = (8 - player.tactics) * 0.03    # Strategic thinking
        
        # Experience modifier
        experience_bonus = min(player.level * 0.02, 0.1)  # Max 10% bonus
        
        # Terrain modifier
        terrain_modifier = encounter.get('terrain_modifier', {}).get(terrain_type, 0.0)
        
        # Mech advantage
        mech_bonus = 0.1 if player.mechs else 0.0
        
        total_chance = base_chance + gunnery_bonus + piloting_bonus + guts_bonus + tactics_bonus + experience_bonus + terrain_modifier + mech_bonus
        
        return max(0.1, min(0.95, total_chance))  # Clamp between 10% and 95%

    def calculate_mission_rewards(self, mission, player_level):
        """Calculate mission rewards based on player level."""
        base_credits = mission.get('base_reward_credits', 0)
        base_experience = mission.get('base_reward_experience', 0)
        
        # Get level scaling parameters
        level_scaling = mission.get('level_scaling', {})
        credits_per_level = level_scaling.get('credits_per_level', 0)
        experience_per_level = level_scaling.get('experience_per_level', 0)
        
        # Calculate scaled rewards
        # Use (player_level - 1) so level 1 players get base rewards
        level_bonus = max(0, player_level - 1)
        
        scaled_credits = base_credits + (credits_per_level * level_bonus)
        scaled_experience = base_experience + (experience_per_level * level_bonus)
        
        return {
            'credits': int(scaled_credits),
            'experience': int(scaled_experience)
        }
    
    def generate_encounter(self, player, terrain_type):
        """Generate a random encounter based on terrain and player level."""
        # Filter encounters by difficulty vs player level
        available_encounters = []
        
        for encounter_id, encounter in self.encounters.items():
            if encounter['difficulty'] == 'easy' or player.level >= 2:
                if encounter['difficulty'] == 'medium' and player.level < 3:
                    continue
                if encounter['difficulty'] == 'hard' and player.level < 4:
                    continue
                available_encounters.append(encounter_id)
        
        if not available_encounters:
            return None
        
        encounter_id = random.choice(available_encounters)
        encounter = self.encounters[encounter_id].copy()
        encounter['id'] = encounter_id
        encounter['success_chance'] = self.calculate_success_chance(player, encounter_id, terrain_type)
        
        return encounter
    
    def resolve_encounter(self, player, encounter, choice='engage'):
        """Resolve an encounter and return results."""
        if choice == 'flee':
            return {
                'success': True,
                'message': f"You successfully fled from the {encounter['name']}.",
                'rewards': {'credits': 0, 'experience': 0}
            }
        
        # Roll for success
        success_roll = random.random()
        success = success_roll <= encounter['success_chance']
        
        if success:
            # Calculate rewards
            credit_range = encounter['reward_credits']
            exp_range = encounter['reward_experience']
            
            credits = random.randint(credit_range[0], credit_range[1])
            experience = random.randint(exp_range[0], exp_range[1])
            
            # Apply rewards
            player.earn_credits(credits)
            leveled_up = player.gain_experience(experience)
            
            # Damage mechs slightly on success
            if player.mechs:
                for mech in player.mechs:
                    if mech.is_operational():
                        damage = random.uniform(0.01, 0.05)  # 1-5% damage
                        mech.take_damage(armor_damage=damage)
            
            message = f"Victory! You defeated the {encounter['name']} and earned {credits} credits and {experience} XP."
            if leveled_up:
                message += f" You leveled up to level {player.level}!"
            
            return {
                'success': True,
                'message': message,
                'rewards': {'credits': credits, 'experience': experience},
                'leveled_up': leveled_up
            }
        else:
            # Failure - take damage and lose some credits
            credits_lost = random.randint(50, 200)
            player.spend_credits(credits_lost)
            
            # Damage mechs more on failure
            if player.mechs:
                for mech in player.mechs:
                    if mech.is_operational():
                        armor_damage = random.uniform(0.05, 0.15)  # 5-15% armor damage
                        internal_damage = random.uniform(0.01, 0.05)  # 1-5% internal damage
                        mech.take_damage(armor_damage=armor_damage, internal_damage=internal_damage)
            
            message = f"Defeat! The {encounter['name']} got the better of you. You lost {credits_lost} credits and your mechs took damage."
            
            return {
                'success': False,
                'message': message,
                'rewards': {'credits': -credits_lost, 'experience': 0}
            }
    
    def get_available_missions(self, player):
        """Get missions available to the player."""
        available = []
        
        for mission_id, mission in self.missions.items():
            requirements = mission.get('requirements', {})
            
            # Check level requirement
            if player.level < requirements.get('min_level', 1):
                continue
            
            # Check mech requirement
            operational_mechs = sum(1 for mech in player.mechs if mech.is_operational())
            if operational_mechs < requirements.get('mechs_required', 0):
                continue
            
            mission_copy = mission.copy()
            mission_copy['id'] = mission_id
            
            # Add level-scaled rewards for display
            rewards = self.calculate_mission_rewards(mission, player.level)
            mission_copy['scaled_reward_credits'] = rewards['credits']
            mission_copy['scaled_reward_experience'] = rewards['experience']
            
            available.append(mission_copy)
        
        return available
    
    def start_mission(self, player, mission_id):
        """Start a mission for the player."""
        mission = self.missions.get(mission_id)
        if not mission:
            return {'success': False, 'message': 'Mission not found.'}
        
        # Check requirements again
        requirements = mission.get('requirements', {})
        if player.level < requirements.get('min_level', 1):
            return {'success': False, 'message': 'You do not meet the level requirement.'}
        
        operational_mechs = sum(1 for mech in player.mechs if mech.is_operational())
        if operational_mechs < requirements.get('mechs_required', 0):
            return {'success': False, 'message': 'You do not have enough operational mechs.'}
        
        # For now, auto-complete missions (could be expanded to multi-turn missions)
        success_chance = 0.6 + (player.level * 0.05) + (operational_mechs * 0.1)
        success_chance = min(0.9, success_chance)
        
        success = random.random() <= success_chance
        
        if success:
            # Calculate level-scaled rewards
            rewards = self.calculate_mission_rewards(mission, player.level)
            
            player.earn_credits(rewards['credits'])
            leveled_up = player.gain_experience(rewards['experience'])
            
            # Light damage to mechs
            if player.mechs:
                for mech in player.mechs:
                    if mech.is_operational():
                        damage = random.uniform(0.02, 0.08)  # 2-8% damage
                        mech.take_damage(armor_damage=damage)
            
            message = f"Mission '{mission['name']}' completed successfully! Earned {rewards['credits']:,} credits and {rewards['experience']:,} XP."
            if leveled_up:
                message += f" You leveled up to level {player.level}!"
            
            return {
                'success': True,
                'message': message,
                'rewards': rewards,
                'leveled_up': leveled_up
            }
        else:
            # Mission failed
            credits_lost = random.randint(100, 300)
            player.spend_credits(credits_lost)
            
            # More damage on failure
            if player.mechs:
                for mech in player.mechs:
                    if mech.is_operational():
                        armor_damage = random.uniform(0.1, 0.2)  # 10-20% armor damage
                        internal_damage = random.uniform(0.02, 0.08)  # 2-8% internal damage
                        mech.take_damage(armor_damage=armor_damage, internal_damage=internal_damage)
            
            message = f"Mission '{mission['name']}' failed. You lost {credits_lost} credits and your mechs took heavy damage."
            
            return {
                'success': False,
                'message': message,
                'rewards': {'credits': -credits_lost, 'experience': 0}
            }
    
    def get_terrain_movement_cost(self, terrain_type):
        """Get movement cost for different terrain types."""
        costs = {
            'plains': 1,
            'forest': 2,
            'hills': 2,
            'mountains': 3,
            'desert': 2,
            'jungle': 3,
            'tundra': 2,
            'beach': 1,
            'shallow_water': 4,
            'deep_ocean': 10,  # Very expensive
            'snow_peaks': 5
        }
        return costs.get(terrain_type, 1)
    
    def can_move_to_terrain(self, terrain_type):
        """Check if terrain is passable."""
        impassable = ['deep_ocean']
        return terrain_type not in impassable
    
    def get_encounter_chance(self, terrain_type):
        """Get encounter chance for terrain type."""
        chances = {
            'plains': 0.3,
            'forest': 0.4,
            'hills': 0.35,
            'mountains': 0.25,
            'desert': 0.3,
            'jungle': 0.45,
            'tundra': 0.2,
            'beach': 0.1,
            'shallow_water': 0.1,
            'deep_ocean': 0.05,
            'snow_peaks': 0.15
        }
        return chances.get(terrain_type, 0.2) 