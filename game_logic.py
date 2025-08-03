import random
import json
from datetime import datetime
from models import db, MechTemplate, PlayerMech

class BattleTechGame:
    """Simplified BattleTech game logic."""
    
    def __init__(self):
        self.encounters = {
            'pirate_patrol': {
                'name': 'Pirate Patrol',
                'description': 'A small pirate patrol blocks your path.',
                'reward_credits': (500, 1000),
                'reward_experience': (50, 150),
                'success_chance': 0.7
            },
            'salvage_opportunity': {
                'name': 'Salvage Opportunity', 
                'description': 'You discover abandoned military equipment.',
                'reward_credits': (1500, 4000),
                'reward_experience': (25, 75),
                'success_chance': 0.8
            },
            'mercenary_contract': {
                'name': 'Mercenary Contract',
                'description': 'A local faction offers you a contract.',
                'reward_credits': (2500, 10000),
                'reward_experience': (100, 300),
                'success_chance': 0.6
            }
        }
        self.starting_mechs = self._load_starting_mechs()
    
    def _load_starting_mechs(self):
        """Load starting mechs from mechs.json."""
        try:
            with open('data/mechs.json', 'r') as f:
                data = json.load(f)
            
            # Handle the "mechs" wrapper array
            all_mechs = data.get('mechs', [])
            
            # Filter for starting mechs: Locust, Wasp, Stinger
            starting_mech_names = ['Locust', 'Wasp', 'Stinger']
            starting_mechs = []
            
            for mech in all_mechs:
                if mech['name'] in starting_mech_names:
                    # Calculate price if not present
                    if 'price' not in mech:
                        base_price = mech.get('tonnage', 20) * 1000
                        mech['price'] = base_price
                    starting_mechs.append(mech)
            
            return starting_mechs
        except Exception as e:
            print(f"Error loading starting mechs: {e}")
            return []
    
    def get_starting_mechs(self):
        """Get available starting mechs."""
        return self.starting_mechs
    
    def assign_starting_mech(self, player, mech_name):
        """Assign a starting mech to a player."""
        try:
            # Find the mech template
            mech_template = None
            for mech in self.starting_mechs:
                if mech['name'] == mech_name:
                    mech_template = mech
                    break
            
            if not mech_template:
                return {'success': False, 'message': f'Starting mech "{mech_name}" not found.'}
            
            # Check if MechTemplate exists, create if not
            template = MechTemplate.query.filter_by(name=mech_name).first()
            if not template:
                template = MechTemplate(
                    name=mech_name,
                    model=mech_template['model'],
                    tonnage=mech_template['tonnage'],
                    battle_value=mech_template.get('battle_value', 0),
                    price=mech_template.get('price', mech_template['tonnage'] * 1000),
                    specs=json.dumps(mech_template)
                )
                db.session.add(template)
                db.session.flush()
            
            # Create PlayerMech instance
            player_mech = PlayerMech(
                player_id=player.id,
                template_id=template.id,
                custom_name=f"{player.name}'s {mech_name}"
            )
            
            db.session.add(player_mech)
            db.session.flush()
            
            # Set as active mech
            player.active_mech_id = player_mech.id
            
            return {'success': True, 'message': f'Successfully assigned {mech_name} to {player.name}.'}
            
        except Exception as e:
            return {'success': False, 'message': f'Error assigning starting mech: {str(e)}'}
    
    def calculate_success_chance(self, player, encounter_type):
        """Calculate success chance for an encounter."""
        base_chance = self.encounters[encounter_type]['success_chance']
        
        # Skill modifiers (lower is better in BattleTech)
        gunnery_bonus = (8 - player.gunnery) * 0.05    # Combat accuracy
        piloting_bonus = (8 - player.piloting) * 0.03  # Mech control
        guts_bonus = (8 - player.guts) * 0.02          # Morale and staying power
        tactics_bonus = (8 - player.tactics) * 0.03    # Strategic thinking
        
        # Experience modifier
        experience_bonus = min(player.level * 0.02, 0.1)
        
        # Mech advantage
        mech_bonus = 0.1 if player.mechs else 0.0
        
        total_chance = base_chance + gunnery_bonus + piloting_bonus + guts_bonus + tactics_bonus + experience_bonus + mech_bonus
        
        return max(0.1, min(0.95, total_chance))
    
    def generate_encounter(self, terrain_type):
        """Generate a random encounter."""
        encounter_id = random.choice(list(self.encounters.keys()))
        encounter = self.encounters[encounter_id].copy()
        encounter['id'] = encounter_id
        return encounter
    
    def resolve_encounter(self, player, encounter):
        """Resolve an encounter."""
        success_chance = self.calculate_success_chance(player, encounter['id'])
        success = random.random() <= success_chance
        
        if success:
            credit_range = encounter['reward_credits']
            exp_range = encounter['reward_experience']
            
            credits = random.randint(credit_range[0], credit_range[1])
            experience = random.randint(exp_range[0], exp_range[1])
            
            player.earn_credits(credits)
            leveled_up = player.gain_experience(experience)
            
            message = f"Victory! You earned {credits} credits and {experience} XP."
            if leveled_up:
                message += f" You leveled up to level {player.level}!"
            
            return {
                'success': True,
                'message': message,
                'rewards': {'credits': credits, 'experience': experience},
                'leveled_up': leveled_up
            }
        else:
            credits_lost = random.randint(50, 200)
            player.spend_credits(credits_lost)
            
            message = f"Defeat! You lost {credits_lost} credits."
            
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
            'deep_ocean': 10,
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