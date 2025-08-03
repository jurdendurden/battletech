#!/usr/bin/env python3
"""
Initialize the BattleTech MUD database with basic data.
"""

from app import app
from models import db, VehicleTemplate
import json

def init_vehicles():
    """Initialize vehicle templates."""
    vehicles = [
        {
            'name': 'Scorpion Tank',
            'vehicle_type': 'tank',
            'tonnage': 25,
            'battle_value': 564,
            'price': 1500,
            'specs': {
                'armor': 45,
                'movement': {'walking': 6, 'running': 9},
                'weapons': [
                    {'type': 'AC/5', 'location': 'turret', 'quantity': 1}
                ],
                'description': 'Light reconnaissance tank'
            }
        },
        {
            'name': 'Vedette Tank',
            'vehicle_type': 'tank',
            'tonnage': 30,
            'battle_value': 621,
            'price': 1800,
            'specs': {
                'armor': 50,
                'movement': {'walking': 5, 'running': 8},
                'weapons': [
                    {'type': 'AC/5', 'location': 'turret', 'quantity': 1}
                ],
                'description': 'Medium support tank'
            }
        },
        {
            'name': 'Saladin Assault Hover',
            'vehicle_type': 'hovercraft',
            'tonnage': 35,
            'battle_value': 739,
            'price': 2200,
            'specs': {
                'armor': 42,
                'movement': {'walking': 8, 'running': 12},
                'weapons': [
                    {'type': 'AC/10', 'location': 'turret', 'quantity': 1}
                ],
                'description': 'Fast attack hovercraft'
            }
        },
        {
            'name': 'Bulldog Tank',
            'vehicle_type': 'tank',
            'tonnage': 60,
            'battle_value': 1071,
            'price': 3500,
            'specs': {
                'armor': 89,
                'movement': {'walking': 4, 'running': 6},
                'weapons': [
                    {'type': 'Large Laser', 'location': 'turret', 'quantity': 1},
                    {'type': 'SRM-2', 'location': 'front', 'quantity': 2}
                ],
                'description': 'Heavy support tank'
            }
        }
    ]
    
    for vehicle_data in vehicles:
        # Check if vehicle already exists
        existing = VehicleTemplate.query.filter_by(
            name=vehicle_data['name']
        ).first()
        
        if not existing:
            vehicle = VehicleTemplate(
                name=vehicle_data['name'],
                vehicle_type=vehicle_data['vehicle_type'],
                tonnage=vehicle_data['tonnage'],
                battle_value=vehicle_data['battle_value'],
                price=vehicle_data['price']
            )
            vehicle.set_specs(vehicle_data['specs'])
            db.session.add(vehicle)
            print(f"Added vehicle: {vehicle_data['name']}")
        else:
            print(f"Vehicle already exists: {vehicle_data['name']}")
    
    db.session.commit()
    print("Vehicle initialization complete.")

def main():
    """Main initialization function."""
    with app.app_context():
        print("Initializing BattleTech MUD database...")
        
        # Create all tables
        db.create_all()
        print("Database tables created.")
        
        # Initialize vehicles
        init_vehicles()
        
        print("Database initialization complete!")

if __name__ == '__main__':
    main() 