from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from map_generator import MapGenerator
from models import db, Player, MechTemplate, PlayerMech, VehicleTemplate, PlayerVehicle
from game_logic import BattleTechGame
import json
import os
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'battletech-mud-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///battletech_mud.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
game_engine = BattleTechGame()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/generate_map')
def generate_map():
    """Generate and return map data."""
    map_gen = MapGenerator(64, 64)
    map_data = map_gen.generate_map()
    return jsonify(map_data)

@app.route('/create_character', methods=['POST'])
def create_character():
    """Create a new player character."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    gunnery = int(data.get('gunnery', 8))
    piloting = int(data.get('piloting', 8))
    guts = int(data.get('guts', 8))
    tactics = int(data.get('tactics', 8))
    skills = data.get('skills', {})
    
    # Validate input
    if not name or len(name) < 2:
        return jsonify({'success': False, 'message': 'Name must be at least 2 characters long.'})
    
    if any(skill < 0 or skill > 8 for skill in [gunnery, piloting, guts, tactics]):
        return jsonify({'success': False, 'message': 'All skills must be between 0 and 8.'})
    
    # Validate point allocation (skills start at 8 each, spend 10 points to improve)
    total_points = gunnery + piloting + guts + tactics
    points_spent = 32 - total_points  # Started with 32 total (8 each), spent points reduce total
    if points_spent != 10:
        return jsonify({'success': False, 'message': 'You must spend exactly 10 points to improve your skills.'})
    
    # Check if name already exists
    existing_player = Player.query.filter_by(name=name).first()
    if existing_player:
        return jsonify({'success': False, 'message': 'A character with that name already exists.'})
    
    # Create new player
    try:
        player = Player(
            name=name,
            gunnery=gunnery,
            piloting=piloting,
            guts=guts,
            tactics=tactics
        )
        player.set_skills(skills)
        
        # Initialize movement system (no mech yet, so 0 movement points)
        player.movement_points_remaining = 0.0
        player.turn_number = 1
        
        db.session.add(player)
        db.session.commit()
        
        # Store player ID in session
        session['player_id'] = player.id
        
        return jsonify({
            'success': True,
            'message': f'Character {name} created successfully! Purchase a mech to start moving.',
            'player': player.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error creating character. Please try again.'})

@app.route('/load_character', methods=['POST'])
def load_character():
    """Load an existing character."""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': 'Please enter a character name.'})
    
    player = Player.query.filter_by(name=name).first()
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    # Update last active time
    player.last_active = datetime.utcnow()
    db.session.commit()
    
    # Store player ID in session
    session['player_id'] = player.id
    
    return jsonify({
        'success': True,
        'message': f'Welcome back, {name}!',
        'player': player.to_dict()
    })

@app.route('/get_player_info')
def get_player_info():
    """Get current player information."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    return jsonify({
        'success': True,
        'player': player.to_dict()
    })

@app.route('/move_player', methods=['POST'])
def move_player():
    """Move player to a new location using turn-based movement."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    # Check if player has an active mech
    active_mech = player.get_active_mech()
    if not active_mech:
        return jsonify({'success': False, 'message': 'No operational mech available for movement.'})
    
    data = request.get_json()
    target_x = float(data.get('x', player.map_x))
    target_y = float(data.get('y', player.map_y))
    terrain_type = data.get('terrain_type', 'plains')
    
    # Validate movement
    if not game_engine.can_move_to_terrain(terrain_type):
        return jsonify({'success': False, 'message': f'Cannot move to {terrain_type}.'})
    
    # Calculate terrain movement cost
    terrain_cost = game_engine.get_terrain_movement_cost(terrain_type)
    
    # Check if player can move to target
    if not player.can_move_to(target_x, target_y, terrain_cost):
        remaining = player.movement_points_remaining
        return jsonify({
            'success': False, 
            'message': f'Insufficient movement points. {remaining:.1f} remaining.'
        })
    
    # Perform the move
    current_pos = player.get_exact_position()
    if player.move_to(target_x, target_y, terrain_cost):
        player.last_active = datetime.utcnow()
        
        # Calculate distance moved
        distance = abs(target_x - current_pos['x']) + abs(target_y - current_pos['y'])
        move_cost = distance * terrain_cost
        
        # Check for encounter (only on full hex moves)
        encounter = None
        if target_x == int(target_x) and target_y == int(target_y):
            encounter_chance = game_engine.get_encounter_chance(terrain_type)
            if random.random() < encounter_chance:
                encounter = game_engine.generate_encounter(terrain_type)
        
        db.session.commit()
        
        terrain_name = terrain_type.replace('_', ' ').title()
        exact_pos = player.get_exact_position()
        
        response = {
            'success': True,
            'message': f'Moved to ({exact_pos["x"]:.1f}, {exact_pos["y"]:.1f}) - {terrain_name}. Used {move_cost:.1f} movement points.',
            'player': player.to_dict(),
            'movement_cost': move_cost,
            'distance_moved': distance
        }
        
        if encounter:
            response['encounter'] = encounter
        
        return jsonify(response)
    else:
        return jsonify({'success': False, 'message': 'Movement failed.'})
    
@app.route('/end_turn', methods=['POST'])
def end_turn():
    """End current turn and start a new one."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    # Start new turn
    player.start_turn()
    player.last_active = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Turn {player.turn_number} started. Movement points refreshed.',
        'player': player.to_dict()
    })

@app.route('/set_active_mech', methods=['POST'])
def set_active_mech():
    """Set the active mech for movement."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    mech_id = data.get('mech_id')
    
    if not mech_id:
        return jsonify({'success': False, 'message': 'No mech ID provided.'})
    
    # Find the mech
    mech = next((m for m in player.mechs if m.id == mech_id), None)
    if not mech:
        return jsonify({'success': False, 'message': 'Mech not found.'})
    
    if not mech.is_operational():
        return jsonify({'success': False, 'message': 'Mech is not operational.'})
    
    # Set active mech and refresh movement points
    player.active_mech_id = mech_id
    player.movement_points_remaining = player.get_movement_points()
    player.last_active = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Active mech set to {mech.get_display_name()}. Movement points refreshed.',
        'player': player.to_dict()
    })

@app.route('/resolve_encounter', methods=['POST'])
def resolve_encounter():
    """Resolve an encounter."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    encounter = data.get('encounter')
    
    if not encounter:
        return jsonify({'success': False, 'message': 'No encounter data provided.'})
    
    # Resolve the encounter
    result = game_engine.resolve_encounter(player, encounter)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'result': result,
        'player': player.to_dict()
    })

@app.route('/get_mech_shop')
def get_mech_shop():
    """Get available mechs for purchase."""
    # For now, return mechs from our JSON file
    try:
        with open('data/mechs.json', 'r') as f:
            mechs_data = json.load(f)
        
        # Use existing value if available, otherwise calculate price
        for mech in mechs_data['mechs']:
            # Use value from Excel if available, otherwise calculate price
            if 'value' in mech:
                mech['price'] = mech['value']
            else:
                # Price formula: tonnage * 50 + battle_value * 2
                base_price = mech['tonnage'] * 50 + mech['battle_value'] * 2
                mech['price'] = base_price
        
        return jsonify({
            'success': True,
            'mechs': mechs_data['mechs']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error loading mech shop data.'})

@app.route('/get_weapons_shop')
def get_weapons_shop():
    """Get available weapons for purchase."""
    try:
        with open('data/weapons.json', 'r') as f:
            weapons_data = json.load(f)
        
        return jsonify({
            'success': True,
            'weapons': weapons_data['weapons']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error loading weapons shop data.'})

@app.route('/get_equipment_shop')
def get_equipment_shop():
    """Get available equipment for purchase."""
    try:
        with open('data/equipment.json', 'r') as f:
            equipment_data = json.load(f)
        
        return jsonify({
            'success': True,
            'equipment': equipment_data['equipment']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error loading equipment shop data.'})

@app.route('/purchase_mech', methods=['POST'])
def purchase_mech():
    """Purchase a mech."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    mech_name = data.get('mech_name')
    
    # Load mech data
    try:
        with open('data/mechs.json', 'r') as f:
            mechs_data = json.load(f)
        
        # Find the mech
        selected_mech = None
        for mech in mechs_data['mechs']:
            if mech['name'] == mech_name:
                selected_mech = mech
                break
        
        if not selected_mech:
            return jsonify({'success': False, 'message': 'Mech not found.'})
        
        # Use value from Excel if available, otherwise calculate price
        if 'value' in selected_mech:
            price = selected_mech['value']
        else:
            price = selected_mech['tonnage'] * 50 + selected_mech['battle_value'] * 2
        
        # Check if player can afford it
        if not player.can_afford(price):
            return jsonify({'success': False, 'message': f'Not enough credits. Need {price}, have {player.credits}.'})
        
        # Create or find mech template
        template = MechTemplate.query.filter_by(name=selected_mech['name'], model=selected_mech['model']).first()
        if not template:
            template = MechTemplate(
                name=selected_mech['name'],
                model=selected_mech['model'],
                tonnage=selected_mech['tonnage'],
                battle_value=selected_mech['battle_value'],
                price=price
            )
            template.set_specs(selected_mech)
            db.session.add(template)
            db.session.flush()  # Get the ID
        
        # Purchase the mech
        player.spend_credits(price)
        
        player_mech = PlayerMech(
            player_id=player.id,
            template_id=template.id
        )
        db.session.add(player_mech)
        db.session.flush()  # Get the mech ID
        
        # If this is the first mech, set it as active
        is_first_mech = not player.active_mech_id
        if is_first_mech:
            player.active_mech_id = player_mech.id
            player.movement_points_remaining = player.get_movement_points()
        
        db.session.commit()
        
        message = f'Successfully purchased {mech_name} for {price} credits!'
        if is_first_mech:
            message += ' Set as active mech - you can now move!'
        
        return jsonify({
            'success': True,
            'message': message,
            'player': player.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error purchasing mech. Please try again.'})

@app.route('/get_available_missions')
def get_available_missions():
    """Get missions available to the player."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    # Get available missions with level-scaled rewards
    available_missions = game_engine.get_available_missions(player)
    
    return jsonify({
        'success': True,
        'missions': available_missions
    })

@app.route('/start_mission', methods=['POST'])
def start_mission():
    """Start a mission."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    mission_id = data.get('mission_id')
    
    if not mission_id:
        return jsonify({'success': False, 'message': 'No mission ID provided.'})
    
    # Start the mission
    result = game_engine.start_mission(player, mission_id)
    
    if result['success']:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'rewards': result.get('rewards', {}),
            'leveled_up': result.get('leveled_up', False),
            'player': player.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        })

@app.route('/get_hangar')
def get_hangar():
    """Get player's hangar with all owned mechs and vehicles."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    # Calculate hangar stats
    total_mechs = len(player.mechs)
    operational_mechs = sum(1 for mech in player.mechs if mech.is_operational())
    total_vehicles = len(player.vehicles)
    operational_vehicles = sum(1 for vehicle in player.vehicles if vehicle.is_operational())
    
    # Calculate total hangar value
    mech_value = sum(mech.template.price for mech in player.mechs)
    vehicle_value = sum(vehicle.template.price for vehicle in player.vehicles)
    total_value = mech_value + vehicle_value
    
    # Calculate total repair costs
    total_repair_cost = sum(mech.get_repair_cost() for mech in player.mechs)
    total_repair_cost += sum(vehicle.get_repair_cost() for vehicle in player.vehicles)
    
    return jsonify({
        'success': True,
        'hangar': {
            'stats': {
                'total_mechs': total_mechs,
                'operational_mechs': operational_mechs,
                'total_vehicles': total_vehicles,
                'operational_vehicles': operational_vehicles,
                'total_value': total_value,
                'total_repair_cost': total_repair_cost
            },
            'mechs': [mech.to_dict() for mech in player.mechs],
            'vehicles': [vehicle.to_dict() for vehicle in player.vehicles]
        }
    })

@app.route('/repair_unit', methods=['POST'])
def repair_unit():
    """Repair a mech or vehicle."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    unit_type = data.get('unit_type')  # 'mech' or 'vehicle'
    unit_id = data.get('unit_id')
    repair_amount = data.get('repair_amount', 1.0)  # Default to full repair
    
    if unit_type == 'mech':
        unit = PlayerMech.query.filter_by(id=unit_id, player_id=player.id).first()
    elif unit_type == 'vehicle':
        unit = PlayerVehicle.query.filter_by(id=unit_id, player_id=player.id).first()
    else:
        return jsonify({'success': False, 'message': 'Invalid unit type.'})
    
    if not unit:
        return jsonify({'success': False, 'message': 'Unit not found.'})
    
    repair_cost = int(unit.get_repair_cost() * repair_amount)
    
    if not player.can_afford(repair_cost):
        return jsonify({'success': False, 'message': f'Not enough credits. Need {repair_cost}, have {player.credits}.'})
    
    # Perform repair
    player.spend_credits(repair_cost)
    unit.repair(repair_amount)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Successfully repaired {unit.get_display_name()} for {repair_cost} credits.',
        'player': player.to_dict(),
        'unit': unit.to_dict()
    })

@app.route('/rename_unit', methods=['POST'])
def rename_unit():
    """Rename a mech or vehicle."""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'message': 'No character loaded.'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Character not found.'})
    
    data = request.get_json()
    unit_type = data.get('unit_type')
    unit_id = data.get('unit_id')
    new_name = data.get('new_name', '').strip()
    
    if not new_name:
        return jsonify({'success': False, 'message': 'Name cannot be empty.'})
    
    if len(new_name) > 50:
        return jsonify({'success': False, 'message': 'Name too long (max 50 characters).'})
    
    if unit_type == 'mech':
        unit = PlayerMech.query.filter_by(id=unit_id, player_id=player.id).first()
    elif unit_type == 'vehicle':
        unit = PlayerVehicle.query.filter_by(id=unit_id, player_id=player.id).first()
    else:
        return jsonify({'success': False, 'message': 'Invalid unit type.'})
    
    if not unit:
        return jsonify({'success': False, 'message': 'Unit not found.'})
    
    old_name = unit.get_display_name()
    unit.custom_name = new_name
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Renamed "{old_name}" to "{new_name}".',
        'unit': unit.to_dict()
    })

def init_database():
    """Initialize the database with tables."""
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_database()
    app.run(debug=True) 