# BattleTech MUD

A web-based graphical MUD (Multi-User Dungeon) based on the BattleTech universe. Players create MechWarrior characters, explore procedurally generated hex maps, engage in encounters, and purchase BattleMechs and vehicles.

## Features

- **Character Creation**: Create MechWarrior characters with Gunnery and Piloting skills
- **Hex Map Exploration**: Navigate procedurally generated terrain with different biomes
- **Encounter System**: Face pirates, salvage opportunities, and mercenary contracts
- **Mech Shop**: Purchase iconic BattleMechs from Technical Readout 3025
- **Credit Economy**: Earn credits through successful encounters and missions
- **Real-time Interface**: Interactive map with text output window

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python init_data.py
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to `http://localhost:5000`

## How to Play

### Character Creation
1. Enter a character name
2. Set your Gunnery skill (0 = best, 8 = worst)
3. Set your Piloting skill (0 = best, 8 = worst)
4. Click "Create Character" or "Load Character" for existing characters

### Gameplay
- **Movement**: Click on hexes on the map to move your character
- **Encounters**: Random encounters occur based on terrain type
- **Combat**: Choose to "Engage" or "Flee" when encounters appear
- **Shopping**: Use the "Mech Shop" to purchase BattleMechs with earned credits
- **Progression**: Gain experience and credits to improve your character

### Game Mechanics

#### MechWarrior Skills
- **Gunnery**: Affects weapon accuracy and encounter success rates
- **Piloting**: Influences mech control and maneuverability bonuses
- **Experience**: Gained through successful encounters, improves success rates

#### Terrain Types
- **Plains**: Easy movement, moderate encounter chance
- **Forest**: Slower movement, higher encounter chance
- **Mountains**: Difficult movement, lower encounter chance
- **Desert**: Moderate movement cost
- **Water**: Expensive movement, low encounter chance
- **Deep Ocean**: Impassable terrain

#### Encounters
- **Pirate Patrol**: Common enemy encounters
- **Salvage Opportunity**: Find abandoned equipment
- **Mercenary Contract**: Higher-paying missions

#### Economy
- Start with 1,000 credits
- Earn credits through successful encounters
- Purchase BattleMechs ranging from 1,000 to 10,000+ credits
- Mech prices based on tonnage and battle value

## Available BattleMechs

The game includes 10 iconic BattleMechs from Technical Readout 3025:

### Light Mechs (20-35 tons)
- **Locust LCT-1V** (20t): Fast scout with machine guns and medium laser
- **Wasp WSP-1A** (20t): Jump-capable light mech with medium laser
- **Spider SDR-5V** (30t): Highly mobile with dual medium lasers
- **Jenner JR7-D** (35t): Kurita light striker with SRM-4 and lasers

### Medium Mechs (40-55 tons)
- **Phoenix Hawk PXH-1** (45t): Versatile jump-capable mech
- **Trebuchet TBT-5N** (50t): Long-range missile support

### Heavy Mechs (60-75 tons)
- **Warhammer WHM-6R** (70t): Classic heavy with dual PPCs

### Assault Mechs (80-100 tons)
- **Awesome AWS-8Q** (80t): PPC boat with triple particle cannons
- **Battlemaster BLR-1G** (85t): Command mech with mixed weapons
- **Atlas AS7-D** (100t): Iconic assault mech with AC/20 and LRM-20

## Technical Details

### Architecture
- **Backend**: Flask web framework with SQLAlchemy ORM
- **Frontend**: HTML5 Canvas for hex map rendering, JavaScript for game logic
- **Database**: SQLite for character and game data persistence
- **Map Generation**: Procedural hex map using Simplex noise

### File Structure
```
battletech/
├── app.py              # Main Flask application
├── models.py           # Database models
├── game_logic.py       # Game mechanics and encounters
├── map_generator.py    # Procedural map generation
├── init_data.py        # Database initialization
├── data/
│   └── mechs.json      # BattleMech specifications
├── templates/
│   └── index.html      # Main game interface
├── static/
│   └── styles.css      # CSS styling
└── README.md           # This file
```

## Development

### Adding New Mechs
1. Add mech data to `data/mechs.json`
2. Include all required fields: name, model, tonnage, battle_value, etc.
3. Restart the application to load new data

### Adding New Encounters
1. Edit the `encounters` dictionary in `game_logic.py`
2. Define encounter parameters: rewards, difficulty, success chance
3. Encounters are automatically available based on player level

### Customizing Terrain
1. Modify terrain types in `map_generator.py`
2. Adjust movement costs and encounter rates in `game_logic.py`
3. Update terrain colors and generation parameters as needed

## License

This project is for educational and entertainment purposes. BattleTech is a trademark of Topps Company, Inc. and Catalyst Game Labs.

## Contributing

Feel free to submit issues and pull requests to improve the game! 