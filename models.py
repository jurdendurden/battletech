from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Player(db.Model):
    """Player character model with MechWarrior stats."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    
    # MechWarrior stats
    gunnery = db.Column(db.Integer, default=8)  # Lower is better (0-8)
    piloting = db.Column(db.Integer, default=8)  # Lower is better (0-8)
    guts = db.Column(db.Integer, default=8)     # Lower is better (0-8)
    tactics = db.Column(db.Integer, default=8)  # Lower is better (0-8)
    
    # Additional skills (JSON field for flexibility)
    skills = db.Column(db.Text, default='{}')  # JSON string
    
    # Game progression
    credits = db.Column(db.Integer, default=1000)  # Starting credits
    experience = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    
    # Current position
    map_x = db.Column(db.Integer, default=32)  # Center of 64x64 map
    map_y = db.Column(db.Integer, default=32)
    
    # Fractional position for half-hex movement
    map_x_frac = db.Column(db.Float, default=0.0)  # 0.0 to 0.5 fractional part
    map_y_frac = db.Column(db.Float, default=0.0)  # 0.0 to 0.5 fractional part
    
    # Turn-based movement tracking
    movement_points_remaining = db.Column(db.Float, default=0.0)
    turn_number = db.Column(db.Integer, default=1)
    active_mech_id = db.Column(db.Integer, db.ForeignKey('player_mech.id'), nullable=True)
    
    # Mission tracking
    declined_missions = db.Column(db.Text, default='[]')  # JSON array of declined mission IDs
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    mechs = db.relationship('PlayerMech', backref='owner', lazy=True, foreign_keys='PlayerMech.player_id')
    vehicles = db.relationship('PlayerVehicle', backref='owner', lazy=True)
    active_mech = db.relationship('PlayerMech', foreign_keys=[active_mech_id], post_update=True)
    
    def get_skills(self):
        """Get skills as dictionary."""
        return json.loads(self.skills) if self.skills else {}
    
    def set_skills(self, skills_dict):
        """Set skills from dictionary."""
        self.skills = json.dumps(skills_dict)
    
    def add_skill(self, skill_name, level=1):
        """Add or update a skill."""
        skills = self.get_skills()
        skills[skill_name] = level
        self.set_skills(skills)
    
    def get_skill(self, skill_name):
        """Get skill level (0 if not present)."""
        skills = self.get_skills()
        return skills.get(skill_name, 0)
    
    def get_declined_missions(self):
        """Get list of declined mission IDs."""
        return json.loads(self.declined_missions) if self.declined_missions else []
    
    def add_declined_mission(self, mission_id):
        """Add a mission ID to the declined list."""
        declined = self.get_declined_missions()
        if mission_id not in declined:
            declined.append(mission_id)
            self.declined_missions = json.dumps(declined)
    
    def clear_declined_missions(self):
        """Clear all declined missions (when moving or ending turn)."""
        self.declined_missions = '[]'
    
    def can_afford(self, cost):
        """Check if player can afford something."""
        return self.credits >= cost
    
    def spend_credits(self, amount):
        """Spend credits if available."""
        if self.can_afford(amount):
            self.credits -= amount
            return True
        return False
    
    def earn_credits(self, amount):
        """Earn credits."""
        self.credits += amount
    
    def gain_experience(self, amount):
        """Gain experience and check for level up."""
        self.experience += amount
        # Simple level progression: 1000 XP per level
        new_level = (self.experience // 1000) + 1
        if new_level > self.level:
            self.level = new_level
            return True  # Leveled up
        return False
    
    def get_exact_position(self):
        """Get exact position including fractional part."""
        return {
            'x': self.map_x + self.map_x_frac,
            'y': self.map_y + self.map_y_frac
        }
    
    def set_exact_position(self, x, y):
        """Set exact position, splitting into integer and fractional parts."""
        self.map_x = int(x)
        self.map_y = int(y)
        self.map_x_frac = x - self.map_x
        self.map_y_frac = y - self.map_y
    
    def get_active_mech(self):
        """Get the currently active mech."""
        if self.active_mech_id:
            return PlayerMech.query.get(self.active_mech_id)
        elif self.mechs:
            # Default to first operational mech
            for mech in self.mechs:
                if mech.is_operational():
                    return mech
        return None
    
    def get_movement_points(self):
        """Get movement points for the active mech."""
        active_mech = self.get_active_mech()
        if not active_mech:
            return 0
        
        specs = active_mech.template.get_specs()
        movement = specs.get('movement_points', {})
        
        # Use walking speed as base movement points
        return movement.get('walking', 0)
    
    def start_turn(self):
        """Start a new turn and refresh movement points."""
        self.movement_points_remaining = self.get_movement_points()
        self.turn_number += 1
    
    def can_move_to(self, target_x, target_y, terrain_cost=1):
        """Check if player can move to target position."""
        current_pos = self.get_exact_position()
        
        # Calculate distance in half-hexes
        distance = abs(target_x - current_pos['x']) + abs(target_y - current_pos['y'])
        
        # Movement cost is distance * terrain cost
        move_cost = distance * terrain_cost
        
        return move_cost <= self.movement_points_remaining
    
    def move_to(self, target_x, target_y, terrain_cost=1):
        """Move to target position if possible."""
        if not self.can_move_to(target_x, target_y, terrain_cost):
            return False
        
        current_pos = self.get_exact_position()
        
        # Calculate distance and cost
        distance = abs(target_x - current_pos['x']) + abs(target_y - current_pos['y'])
        move_cost = distance * terrain_cost
        
        # Update position and movement points
        self.set_exact_position(target_x, target_y)
        self.movement_points_remaining -= move_cost
        
        return True
    
    def to_dict(self):
        """Convert player to dictionary for JSON serialization."""
        active_mech = self.get_active_mech()
        exact_pos = self.get_exact_position()
        
        return {
            'id': self.id,
            'name': self.name,
            'gunnery': self.gunnery,
            'piloting': self.piloting,
            'guts': self.guts,
            'tactics': self.tactics,
            'skills': self.get_skills(),
            'credits': self.credits,
            'experience': self.experience,
            'level': self.level,
            'position': {'x': self.map_x, 'y': self.map_y},  # Integer position for compatibility
            'exact_position': exact_pos,  # Exact position with fractional part
            'movement_points_remaining': self.movement_points_remaining,
            'movement_points_total': self.get_movement_points(),
            'turn_number': self.turn_number,
            'declined_missions': self.get_declined_missions(),
            'active_mech': active_mech.to_dict() if active_mech else None,
            'mechs': [mech.to_dict() for mech in self.mechs],
            'vehicles': [vehicle.to_dict() for vehicle in self.vehicles]
        }

class MechTemplate(db.Model):
    """Template for available mechs (loaded from mechs.json)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    tonnage = db.Column(db.Integer, nullable=False)
    battle_value = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)  # Purchase price
    
    # Technical specs (JSON for flexibility)
    specs = db.Column(db.Text, nullable=False)  # JSON string with all mech data
    
    def get_specs(self):
        """Get specs as dictionary."""
        return json.loads(self.specs)
    
    def set_specs(self, specs_dict):
        """Set specs from dictionary."""
        self.specs = json.dumps(specs_dict)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'tonnage': self.tonnage,
            'battle_value': self.battle_value,
            'price': self.price,
            'specs': self.get_specs()
        }

class PlayerMech(db.Model):
    """Player-owned mech instance."""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('mech_template.id'), nullable=False)
    
    # Mech condition
    armor_condition = db.Column(db.Float, default=1.0)  # 0.0 to 1.0
    internal_condition = db.Column(db.Float, default=1.0)  # 0.0 to 1.0
    
    # Custom name
    custom_name = db.Column(db.String(100))
    
    # Timestamps
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    template = db.relationship('MechTemplate', backref='instances')
    
    def get_display_name(self):
        """Get display name (custom name or template name)."""
        return self.custom_name or self.template.name
    
    def get_repair_cost(self):
        """Calculate repair cost based on damage."""
        armor_damage = 1.0 - self.armor_condition
        internal_damage = 1.0 - self.internal_condition
        base_cost = self.template.price * 0.1  # 10% of purchase price for full repair
        return int(base_cost * (armor_damage + internal_damage * 2))
    
    def repair(self, amount=1.0):
        """Repair mech (amount from 0.0 to 1.0)."""
        self.armor_condition = min(1.0, self.armor_condition + amount)
        self.internal_condition = min(1.0, self.internal_condition + amount)
    
    def take_damage(self, armor_damage=0.0, internal_damage=0.0):
        """Take damage to mech."""
        self.armor_condition = max(0.0, self.armor_condition - armor_damage)
        self.internal_condition = max(0.0, self.internal_condition - internal_damage)
    
    def is_operational(self):
        """Check if mech is operational."""
        return self.internal_condition > 0.0
    
    def get_movement_points(self):
        """Get movement points for this mech."""
        specs = self.template.get_specs()
        movement = specs.get('movement_points', {})
        return {
            'walking': movement.get('walking', 0),
            'running': movement.get('running', 0),
            'jumping': movement.get('jumping', 0)
        }
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'template': self.template.to_dict(),
            'display_name': self.get_display_name(),
            'armor_condition': self.armor_condition,
            'internal_condition': self.internal_condition,
            'repair_cost': self.get_repair_cost(),
            'operational': self.is_operational(),
            'movement_points': self.get_movement_points(),
            'purchased_at': self.purchased_at.isoformat()
        }

class VehicleTemplate(db.Model):
    """Template for available vehicles."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # tank, hovercraft, etc.
    tonnage = db.Column(db.Integer, nullable=False)
    battle_value = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    
    # Technical specs
    specs = db.Column(db.Text, nullable=False)  # JSON string
    
    def get_specs(self):
        """Get specs as dictionary."""
        return json.loads(self.specs)
    
    def set_specs(self, specs_dict):
        """Set specs from dictionary."""
        self.specs = json.dumps(specs_dict)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'vehicle_type': self.vehicle_type,
            'tonnage': self.tonnage,
            'battle_value': self.battle_value,
            'price': self.price,
            'specs': self.get_specs()
        }

class PlayerVehicle(db.Model):
    """Player-owned vehicle instance."""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('vehicle_template.id'), nullable=False)
    
    # Vehicle condition
    condition = db.Column(db.Float, default=1.0)  # 0.0 to 1.0
    
    # Custom name
    custom_name = db.Column(db.String(100))
    
    # Timestamps
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    template = db.relationship('VehicleTemplate', backref='instances')
    
    def get_display_name(self):
        """Get display name (custom name or template name)."""
        return self.custom_name or self.template.name
    
    def get_repair_cost(self):
        """Calculate repair cost based on damage."""
        damage = 1.0 - self.condition
        base_cost = self.template.price * 0.08  # 8% of purchase price for full repair
        return int(base_cost * damage)
    
    def repair(self, amount=1.0):
        """Repair vehicle."""
        self.condition = min(1.0, self.condition + amount)
    
    def take_damage(self, damage=0.0):
        """Take damage."""
        self.condition = max(0.0, self.condition - damage)
    
    def is_operational(self):
        """Check if vehicle is operational."""
        return self.condition > 0.2  # Vehicles need 20% condition to operate
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'template': self.template.to_dict(),
            'display_name': self.get_display_name(),
            'condition': self.condition,
            'repair_cost': self.get_repair_cost(),
            'operational': self.is_operational(),
            'purchased_at': self.purchased_at.isoformat()
        }

class GameSession(db.Model):
    """Track game sessions for persistence."""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    session_data = db.Column(db.Text)  # JSON string for session state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    player = db.relationship('Player', backref='sessions')
    
    def get_data(self):
        """Get session data as dictionary."""
        return json.loads(self.session_data) if self.session_data else {}
    
    def set_data(self, data_dict):
        """Set session data from dictionary."""
        self.session_data = json.dumps(data_dict)
        self.updated_at = datetime.utcnow() 