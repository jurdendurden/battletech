#!/usr/bin/env python3
"""
Migration script to add movement system columns to the Player table.
"""

from app import app, db
from models import Player
from sqlalchemy import text

def migrate_movement_system():
    """Add movement system columns to existing Player table."""
    with app.app_context():
        try:
            # Check if columns exist
            result = db.session.execute(text("PRAGMA table_info(player)"))
            columns = [row[1] for row in result]
            
            # Add missing columns
            if 'map_x_frac' not in columns:
                db.session.execute(text("ALTER TABLE player ADD COLUMN map_x_frac FLOAT DEFAULT 0.0"))
                print("Added map_x_frac column")
            
            if 'map_y_frac' not in columns:
                db.session.execute(text("ALTER TABLE player ADD COLUMN map_y_frac FLOAT DEFAULT 0.0"))
                print("Added map_y_frac column")
            
            if 'movement_points_remaining' not in columns:
                db.session.execute(text("ALTER TABLE player ADD COLUMN movement_points_remaining FLOAT DEFAULT 0.0"))
                print("Added movement_points_remaining column")
            
            if 'turn_number' not in columns:
                db.session.execute(text("ALTER TABLE player ADD COLUMN turn_number INTEGER DEFAULT 1"))
                print("Added turn_number column")
            
            if 'active_mech_id' not in columns:
                db.session.execute(text("ALTER TABLE player ADD COLUMN active_mech_id INTEGER"))
                print("Added active_mech_id column")
            
            db.session.commit()
            
            # Initialize movement system for existing players
            players = Player.query.all()
            for player in players:
                if player.movement_points_remaining is None:
                    player.movement_points_remaining = 0.0
                if player.turn_number is None:
                    player.turn_number = 1
                if player.map_x_frac is None:
                    player.map_x_frac = 0.0
                if player.map_y_frac is None:
                    player.map_y_frac = 0.0
                
                # Set first operational mech as active if none set
                if not player.active_mech_id and player.mechs:
                    for mech in player.mechs:
                        if mech.is_operational():
                            player.active_mech_id = mech.id
                            player.movement_points_remaining = player.get_movement_points()
                            break
            
            db.session.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_movement_system() 