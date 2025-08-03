from simplex_noise import SimplexNoise
import math
import random
from collections import deque

class MapGenerator:
    def __init__(self, width, height, scale=20.0):
        """Initialize map generator with dimensions and noise scale."""
        self.width = width
        self.height = height
        self.scale = scale
        # One noise generator for elevation, another for climate
        self.elevation_noise = SimplexNoise()
        self.climate_noise = SimplexNoise()
        # Initialize color palette for different terrain types
        self.initialize_color_palette()
        
        # River generation parameters
        self.min_river_length = 14
        self.river_source_elevation_threshold = 0.7
        self.water_level = 0.3  # Elevation below which is water

    def initialize_color_palette(self):
        """Initialize the 64-color palette for terrain types."""
        # Deep Ocean (8 colors)
        self.deep_ocean = [
            "#000033", "#000040", "#00004D", "#000059",
            "#000066", "#000073", "#000080", "#00008C"
        ]
        
        # Shallow Water (6 colors)
        self.shallow_water = [
            "#000099", "#0000B2", "#0000CC", "#0000E6",
            "#0000FF", "#1A1AFF"
        ]
        
        # River colors (4 colors) - Much lighter blues, distinct from ocean
        self.river = [
            "#99CCFF",  # Light sky blue
            "#66B2FF",  # Bright sky blue
            "#3399FF",  # Azure blue
            "#0080FF"   # Bright blue
        ]
        
        # Beach/Coast (4 colors)
        self.beach = [
            "#FFE5B2", "#FFD480", "#FFC74D", "#FFBA1A"
        ]
        
        # Tundra (6 colors)
        self.tundra = [
            "#E0E0E0", "#D1D1D1", "#C2C2C2", "#B3B3B3",
            "#A4A4A4", "#959595"
        ]
        
        # Desert (8 colors)
        self.desert = [
            "#FFE5B2", "#FFDB99", "#FFD180", "#FFC766",
            "#FFBD4D", "#FFB333", "#FFA91A", "#FF9F00"
        ]
        
        # Plains (6 colors)
        self.plains = [
            "#90EE90", "#7CEB7C", "#68E868", "#54E554",
            "#40E240", "#2CDF2C"
        ]
        
        # Forest (6 colors)
        self.forest = [
            "#228B22", "#1E7B1E", "#1A6B1A", "#165B16",
            "#124B12", "#0E3B0E"
        ]
        
        # Jungle (6 colors)
        self.jungle = [
            "#004D00", "#004000", "#003300", "#002600",
            "#001900", "#000C00"
        ]
        
        # Hills (6 colors)
        self.hills = [
            "#8B4513", "#7A3D11", "#69350F", "#582D0D",
            "#47250B", "#361D09"
        ]
        
        # Mountains (6 colors)
        self.mountains = [
            "#696969", "#5A5A5A", "#4B4B4B", "#3C3C3C",
            "#2D2D2D", "#1E1E1E"
        ]
        
        # Snow Peaks (2 colors)
        self.snow_peaks = [
            "#FFFFFF", "#F2F2F2"
        ]

    def get_biome_type(self, elevation, climate):
        """Determine base biome type from elevation and climate."""
        if elevation < 0.2:
            return "deep_ocean"
        elif elevation < 0.3:
            return "shallow_water"
        elif elevation < 0.35:
            return "beach"
        
        # Quantize climate value to create distinct regions
        climate_value = math.floor(climate * 5) / 5  # Creates 5 distinct climate zones
        
        if elevation >= 0.85:
            return "snow_peaks"
        elif elevation >= 0.75:
            return "mountains"
        elif elevation >= 0.65:
            return "hills"
        
        # Main biome determination based on quantized climate
        if climate_value < 0.2:
            return "tundra"
        elif climate_value < 0.4:
            return "desert"
        elif climate_value < 0.6:
            return "plains"
        elif climate_value < 0.8:
            return "forest"
        else:
            return "jungle"

    def smooth_noise(self, x, y, noise_gen, octaves=3):
        """Generate smoother noise by combining multiple octaves."""
        value = 0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0
        
        for _ in range(octaves):
            value += noise_gen.normalized_noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2
            
        return value / max_value

    def get_biome_and_color(self, elevation, climate, x, y):
        """Determine biome and color based on elevation and climate values."""
        # Get base biome type
        biome_type = self.get_biome_type(elevation, climate)
        
        # Select color palette based on biome type
        color_palette = getattr(self, biome_type)
        
        # Calculate color index based on local variation
        if biome_type in ["deep_ocean", "shallow_water"]:
            # Water areas use elevation for color variation
            color_index = min(int(elevation * len(color_palette)), len(color_palette) - 1)
        else:
            # Land areas use a combination of elevation and position for variation
            local_var = self.smooth_noise(x/5, y/5, self.elevation_noise, octaves=2)
            color_index = min(int(local_var * len(color_palette)), len(color_palette) - 1)
        
        return biome_type, color_palette[color_index]

    def get_neighbors(self, x, y):
        """Get valid neighboring cells including diagonals."""
        # Check orthogonal neighbors first, then diagonals
        neighbors = []
        # Orthogonal neighbors (NSEW)
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append((new_x, new_y))
        # Diagonal neighbors
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append((new_x, new_y))
        return neighbors

    def find_flow_direction(self, x, y, elevation_map, visited):
        """Find the best direction for water to flow, handling flat areas."""
        current_elevation = elevation_map[y][x]
        neighbors = self.get_neighbors(x, y)
        
        # First, try to find any lower neighbors
        best_drop = 0
        best_pos = None
        flat_neighbors = []
        
        for nx, ny in neighbors:
            if (nx, ny) in visited:
                continue
                
            neighbor_elevation = elevation_map[ny][nx]
            elevation_drop = current_elevation - neighbor_elevation
            
            # If it's a lower neighbor
            if elevation_drop > 0:
                if elevation_drop > best_drop or (elevation_drop == best_drop and abs(nx - x) + abs(ny - y) == 1):
                    best_drop = elevation_drop
                    best_pos = (nx, ny)
            # If it's a flat neighbor
            elif elevation_drop == 0:
                flat_neighbors.append((nx, ny))
        
        # If we found a lower neighbor, use that
        if best_pos:
            return best_pos
            
        # If we're in a flat area, try to find a path to lower ground
        if flat_neighbors:
            # Use BFS to find the nearest lower ground
            queue = deque([(x, y, [])])
            flat_visited = {(x, y)}
            
            while queue:
                cx, cy, path = queue.popleft()
                for nx, ny in self.get_neighbors(cx, cy):
                    if (nx, ny) in flat_visited:
                        continue
                        
                    # If we found lower ground, return the first step in its direction
                    if elevation_map[ny][nx] < current_elevation:
                        return path[0] if path else (nx, ny)
                        
                    # If it's flat, add it to the queue
                    if elevation_map[ny][nx] == current_elevation:
                        new_path = path + [(nx, ny)] if path else [(nx, ny)]
                        queue.append((nx, ny, new_path))
                        flat_visited.add((nx, ny))
            
            # If no path to lower ground found, pick the best flat neighbor
            if flat_neighbors:
                # Prefer orthogonal neighbors over diagonal ones
                orthogonal_neighbors = [(nx, ny) for nx, ny in flat_neighbors if abs(nx - x) + abs(ny - y) == 1]
                if orthogonal_neighbors:
                    return random.choice(orthogonal_neighbors)
                return random.choice(flat_neighbors)
        
        return None

    def trace_river_path(self, start_x, start_y, elevation_map):
        """Trace a river path from source to water body or map edge."""
        path = [(start_x, start_y)]
        current_x, current_y = start_x, start_y
        visited = {(start_x, start_y)}
        last_elevation = elevation_map[start_y][start_x]
        
        while True:
            # Find the next position using the improved flow direction logic
            next_pos = self.find_flow_direction(current_x, current_y, elevation_map, visited)
            
            # If no valid next position found or we've reached water, stop
            if not next_pos:
                break
                
            next_x, next_y = next_pos
            next_elevation = elevation_map[next_y][next_x]
            
            # Handle diagonal movements by adding intermediate points
            dx = next_x - current_x
            dy = next_y - current_y
            
            # If moving diagonally, add intermediate points to ensure continuity
            if abs(dx) == 1 and abs(dy) == 1:
                # Try both possible intermediate points and choose the one with the better elevation
                option1 = (current_x + dx, current_y)
                option2 = (current_x, current_y + dy)
                
                # Check which intermediate point has a better elevation gradient
                elev1 = elevation_map[current_y][current_x + dx] if option1[0] >= 0 and option1[0] < self.width else float('inf')
                elev2 = elevation_map[current_y + dy][current_x] if option2[1] >= 0 and option2[1] < self.height else float('inf')
                
                # Choose the intermediate point with the smoother elevation transition
                if abs(elev1 - last_elevation) < abs(elev2 - last_elevation):
                    if option1 not in visited:
                        path.append(option1)
                        visited.add(option1)
                elif option2 not in visited:
                    path.append(option2)
                    visited.add(option2)
            # For longer jumps (which shouldn't happen often but just in case)
            elif abs(dx) > 1 or abs(dy) > 1:
                steps = max(abs(dx), abs(dy))
                for i in range(1, steps):
                    ix = current_x + int(dx * i / steps)
                    iy = current_y + int(dy * i / steps)
                    if (ix, iy) not in visited:
                        path.append((ix, iy))
                        visited.add((ix, iy))
            
            # Add the next position to the path
            path.append(next_pos)
            visited.add(next_pos)
            
            # Stop if we've reached water level
            if next_elevation < self.water_level:
                break
                
            # Update current position and elevation
            current_x, current_y = next_x, next_y
            last_elevation = next_elevation
            
        return path if len(path) >= self.min_river_length else []

    def find_river_sources(self, elevation_map):
        """Find suitable river source points (high elevation areas)."""
        sources = []
        for y in range(self.height):
            for x in range(self.width):
                if elevation_map[y][x] > self.river_source_elevation_threshold:
                    # Add some randomness to source selection
                    if random.random() < 0.1:  # 10% chance for eligible cells
                        sources.append((x, y))
        return sources

    def generate_rivers(self, elevation_map):
        """Generate rivers starting from high elevation points."""
        river_paths = []
        river_cells = set()  # Keep track of cells that are part of rivers
        
        # Find potential river sources
        sources = self.find_river_sources(elevation_map)
        
        # Sort sources by elevation (highest first)
        sources.sort(key=lambda pos: elevation_map[pos[1]][pos[0]], reverse=True)
        
        # Generate rivers from each source
        for source_x, source_y in sources:
            # Skip if this cell is already part of a river
            if (source_x, source_y) in river_cells:
                continue
                
            # Trace the river path
            path = self.trace_river_path(source_x, source_y, elevation_map)
            
            # If path is long enough and doesn't overlap too much with existing rivers
            if path:
                overlap = sum(1 for pos in path if pos in river_cells)
                if overlap < len(path) * 0.3:  # Allow 30% overlap
                    river_paths.append(path)
                    river_cells.update(path)
        
        return river_paths

    def apply_rivers_to_map(self, map_data, river_paths):
        """Apply rivers to the map data with improved connectivity."""
        # Create a river width map (some rivers are wider)
        river_widths = {}
        river_cells = set()
        
        # First pass: Mark all river cells and calculate initial widths
        for path in river_paths:
            # Longer rivers are wider
            base_width = min(len(path) / 20, 3)  # Max width of 3
            
            # Apply graduated widths - rivers get wider as they flow downstream
            for i, pos in enumerate(path):
                # Rivers get slightly wider as they progress (downstream)
                progress = i / len(path)  # 0 at source, 1 at mouth
                width = base_width * (0.5 + 0.5 * progress)  # Width increases gradually
                river_widths[pos] = max(river_widths.get(pos, 0), width)
                river_cells.add(pos)
        
        # Second pass: Ensure connectivity and smooth transitions
        gaps_filled = True
        while gaps_filled:
            gaps_filled = False
            new_river_cells = set()
            
            for x, y in river_cells:
                # Check all 8 neighboring cells
                for dx, dy in [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
                    nx, ny = x + dx, y + dy
                    
                    # Skip if out of bounds
                    if not (0 <= nx < self.width and 0 <= ny < self.height):
                        continue
                    
                    # If this is a diagonal neighbor
                    if abs(dx) == 1 and abs(dy) == 1:
                        # Check if there's a river cell diagonally adjacent
                        if (nx, ny) in river_cells:
                            # Add intermediate cells to ensure connectivity
                            if (x + dx, y) not in river_cells and (x, y + dy) not in river_cells:
                                # Choose the better intermediate point based on elevation
                                if map_data[y][x + dx]['elevation'] < map_data[y + dy][x]['elevation']:
                                    new_river_cells.add((x + dx, y))
                                else:
                                    new_river_cells.add((x, y + dy))
                                gaps_filled = True
            
            # Add new river cells and calculate their widths
            for pos in new_river_cells:
                if pos not in river_cells:
                    # Calculate width based on neighboring river cells
                    x, y = pos
                    neighbor_widths = [river_widths[nx, ny] 
                                     for nx, ny in self.get_neighbors(x, y)
                                     if (nx, ny) in river_widths]
                    if neighbor_widths:
                        river_widths[pos] = sum(neighbor_widths) / len(neighbor_widths)
                    river_cells.add(pos)

        # Apply rivers to the map
        for pos in river_cells:
            x, y = pos
            # Ensure width_index is valid
            width = river_widths[pos]
            width_index = min(int(width), len(self.river) - 1)
            map_data[y][x]['color'] = self.river[width_index]
            map_data[y][x]['terrain_type'] = 'river'

    def generate_map(self):
        """Generate topographical map data with distinct biome regions and rivers."""
        # First pass: Generate base elevation and climate maps
        elevation_map = []
        climate_map = []
        
        for y in range(self.height):
            elevation_row = []
            climate_row = []
            for x in range(self.width):
                nx = x / self.scale
                ny = y / self.scale
                
                elevation = self.smooth_noise(nx, ny, self.elevation_noise, octaves=4)
                climate = self.smooth_noise(nx * 0.5, ny * 0.5, self.climate_noise, octaves=2)
                
                elevation_row.append(elevation)
                climate_row.append(climate)
            
            elevation_map.append(elevation_row)
            climate_map.append(climate_row)

        # Generate rivers
        river_paths = self.generate_rivers(elevation_map)
        
        # Second pass: Generate final map with biome information
        map_data = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                elevation = elevation_map[y][x]
                climate = climate_map[y][x]
                
                terrain_type, color = self.get_biome_and_color(elevation, climate, x, y)
                
                cell = {
                    "elevation": elevation,
                    "climate": climate,
                    "terrain_type": terrain_type,
                    "color": color
                }
                row.append(cell)
            map_data.append(row)

        # Apply rivers to the map
        self.apply_rivers_to_map(map_data, river_paths)
        
        return map_data 