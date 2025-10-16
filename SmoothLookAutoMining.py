# Macro decided to automate mining with a smooth loo, meaning it will smoothly go to blocks. 
# Cluster detection by default on, meaning it looks at clustered blocks first(toggleable from that to distance based)
# Code is not made for any server, instead singleplayer. Meaning it does not have failsafes against checks.
# Getting banned, warned. etc is your own fault.

import minescript
import math
import time


CONFIG = {
    # Block type to search for and break (use Minecraft block ID)
    # Examples: 'minecraft:iron_block', 'minecraft:diamond_ore', 
    #           'minecraft:wheat[age=7]'
    'target_block': 'minecraft:diamond_block',
    
    # Search distance in blocks (4.5 is typical survival reach, 5.0 for creative)
    'search_distance': 4.5,
    
    # Rotation speed: duration in seconds for camera rotation
    # Lower = faster, Higher = slower and smoother
    'rotation_duration': 0.5,
    
    # Smoothness: number of steps for interpolation
    # Higher = smoother but more CPU intensive (30-120 recommended)
    'rotation_steps': 60,
    
    # Cooldown in seconds before moving to next block
    'block_cooldown': 0.1,
    
    # If True, visit blocks based on angular proximity (more realistic)
    # If False, visit blocks based on distance
    'use_cluster_mode': True,
    
    # If True, break blocks after looking at them
    'break_blocks': True,
    
    # Pause in seconds after looking at block before breaking it
    'break_delay': 0,
    
    # Time in seconds to hold attack button (for breaking blocks)
    # Increase this for blocks that take longer to break
    'break_hold_time': 0,
}
# ============================================

def find_all_blocks(max_distance=5, block_type='minecraft:iron_block'):
    """Find all blocks of specified type within max_distance (player hit range)."""
    player_pos = minescript.player_position()
    px, py, pz = player_pos
    
    minescript.echo(f"Searching for {block_type} within {max_distance} blocks...")
    
    # Search in a smaller cube around the player (within reach)
    search_range = max_distance
    blocks_found = []
    
    # Generate list of positions to check
    positions_to_check = []
    for x in range(int(px - search_range), int(px + search_range + 1)):
        for y in range(int(py - search_range), int(py + search_range + 1)):
            for z in range(int(pz - search_range), int(pz + search_range + 1)):
                distance = math.sqrt((x - px)**2 + (y - py)**2 + (z - pz)**2)
                if distance <= max_distance:
                    positions_to_check.append([x, y, z])
    
    minescript.echo(f"Checking {len(positions_to_check)} positions...")
    
    # Use getblocklist for batch checking (much faster)
    if positions_to_check:
        block_types = minescript.getblocklist(positions_to_check)
        
        for i, found_block_type in enumerate(block_types):
            if found_block_type == block_type:
                x, y, z = positions_to_check[i]
                distance = math.sqrt((x - px)**2 + (y - py)**2 + (z - pz)**2)
                blocks_found.append({
                    'position': (x, y, z),
                    'distance': distance
                })
        
        minescript.echo(f"Search complete. Found {len(blocks_found)} block(s)")
    
    return blocks_found

def calculate_look_angles(player_pos, target_pos):
    """Calculate yaw and pitch to look at target position from player position."""
    px, py, pz = player_pos
    tx, ty, tz = target_pos
    
    # Calculate differences
    dx = tx - px
    dy = ty - (py + 1.62)  # Add player eye height
    dz = tz - pz
    
    # Calculate distance in horizontal plane
    horizontal_distance = math.sqrt(dx**2 + dz**2)
    
    # Calculate pitch (vertical angle)
    pitch = -math.degrees(math.atan2(dy, horizontal_distance))
    
    # Calculate yaw (horizontal angle)
    yaw = math.degrees(math.atan2(-dx, dz))
    
    return yaw, pitch

def normalize_angle(angle):
    """Normalize angle to be between -180 and 180."""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def angle_difference(current, target):
    """Calculate the shortest difference between two angles."""
    diff = normalize_angle(target - current)
    return diff

def calculate_angular_distance(yaw1, pitch1, yaw2, pitch2):
    """
    Calculate angular distance between two orientations.
    Returns a value representing how far apart two look directions are.
    """
    # Convert to radians
    yaw1_rad = math.radians(yaw1)
    pitch1_rad = math.radians(pitch1)
    yaw2_rad = math.radians(yaw2)
    pitch2_rad = math.radians(pitch2)
    
    # Convert to 3D unit vectors
    x1 = math.cos(pitch1_rad) * math.sin(yaw1_rad)
    y1 = math.sin(pitch1_rad)
    z1 = math.cos(pitch1_rad) * math.cos(yaw1_rad)
    
    x2 = math.cos(pitch2_rad) * math.sin(yaw2_rad)
    y2 = math.sin(pitch2_rad)
    z2 = math.cos(pitch2_rad) * math.cos(yaw2_rad)
    
    # Dot product gives cosine of angle between vectors
    dot_product = x1*x2 + y1*y2 + z1*z2
    # Clamp to avoid floating point errors
    dot_product = max(-1.0, min(1.0, dot_product))
    
    # Return angle in degrees
    return math.degrees(math.acos(dot_product))

def sort_blocks_by_viewing_order(blocks, player_pos):
    """
    Sort blocks by natural viewing order (cluster-aware).
    Looks at nearest block first, then blocks close to current view direction.
    """
    if not blocks:
        return []
    
    # Start with the nearest block
    sorted_blocks = []
    remaining = blocks.copy()
    
    # Sort remaining by distance initially
    remaining.sort(key=lambda b: b['distance'])
    
    # Pick the nearest as first block
    current_block = remaining.pop(0)
    sorted_blocks.append(current_block)
    
    current_yaw, current_pitch = minescript.player_orientation()
    
    # For each subsequent block, pick the one closest to current view angle
    while remaining:
        current_pos = current_block['position']
        current_yaw, current_pitch = calculate_look_angles(player_pos, 
                                                           (current_pos[0] + 0.5, 
                                                            current_pos[1] + 0.5, 
                                                            current_pos[2] + 0.5))
        
        # Find block with minimum angular distance from current view
        best_block = None
        best_angular_distance = float('inf')
        
        for block in remaining:
            block_pos = block['position']
            target_yaw, target_pitch = calculate_look_angles(player_pos,
                                                             (block_pos[0] + 0.5,
                                                              block_pos[1] + 0.5,
                                                              block_pos[2] + 0.5))
            
            angular_dist = calculate_angular_distance(current_yaw, current_pitch,
                                                      target_yaw, target_pitch)
            
            if angular_dist < best_angular_distance:
                best_angular_distance = angular_dist
                best_block = block
        
        remaining.remove(best_block)
        sorted_blocks.append(best_block)
        current_block = best_block
    
    return sorted_blocks

def smooth_look_at(target_pos, duration=1.0, steps=60):
    """
    Smoothly rotate camera to look at target position.
    
    Args:
        target_pos: (x, y, z) tuple of target block position
        duration: Time in seconds for the smooth rotation
        steps: Number of interpolation steps
    
    Returns:
        Final (yaw, pitch) orientation after rotation
    """
    player_pos = minescript.player_position()
    current_yaw, current_pitch = minescript.player_orientation()
    
    target_yaw, target_pitch = calculate_look_angles(player_pos, target_pos)
    
    # Calculate shortest path for angles
    yaw_diff = angle_difference(current_yaw, target_yaw)
    pitch_diff = angle_difference(current_pitch, target_pitch)
    
    minescript.echo(f"Rotating from ({current_yaw:.1f}, {current_pitch:.1f}) to ({target_yaw:.1f}, {target_pitch:.1f})")
    
    # Perform smooth interpolation
    step_delay = duration / steps
    
    for i in range(steps + 1):
        # Ease-in-out interpolation (smooth acceleration and deceleration)
        t = i / steps
        # Smoothstep function for natural motion
        smooth_t = t * t * (3 - 2 * t)
        
        # Interpolate angles
        new_yaw = current_yaw + yaw_diff * smooth_t
        new_pitch = current_pitch + pitch_diff * smooth_t
        
        # Set orientation
        minescript.player_set_orientation(new_yaw, new_pitch)
        
        # Wait between steps
        if i < steps:
            time.sleep(step_delay)
    
    minescript.echo("Camera rotation complete!")
    
    # Break block if enabled
    if CONFIG['break_blocks']:
        if CONFIG['break_delay'] > 0:
            minescript.echo(f"  Pausing {CONFIG['break_delay']}s before breaking...")
            time.sleep(CONFIG['break_delay'])
        
        minescript.echo("  ⛏ Breaking block...")
        # Press and hold attack
        minescript.player_press_attack(True)
        time.sleep(CONFIG['break_hold_time'])
        minescript.player_press_attack(False)
    
    return (target_yaw, target_pitch)

def break_block_at_position(x, y, z):
    """
    Break a block at the specified position by simulating player attack.
    
    Args:
        x, y, z: Block coordinates to break
    
    Returns:
        True if block was successfully targeted and attack initiated
    """
    try:
        # First, ensure the camera is looking at the block center
        player_pos = minescript.player_position()
        target_yaw, target_pitch = calculate_look_angles(
            player_pos, 
            (x + 0.5, y + 0.5, z + 0.5)
        )
        minescript.player_set_orientation(target_yaw, target_pitch)
        
        # Small delay to ensure orientation is set
        time.sleep(0.05)
        
        # Verify we're looking at the correct block
        targeted = minescript.player_get_targeted_block(max_distance=6)
        if targeted and targeted.position == (x, y, z):
            # Press and hold attack button
            minescript.player_press_attack(True)
            time.sleep(CONFIG['break_hold_time'])  # Hold to initiate breaking
            minescript.player_press_attack(False)
            
            minescript.echo(f"  ⛏ Breaking block at ({x}, {y}, {z})")
            return True
        else:
            if targeted:
                minescript.echo(f"  ✗ Targeted wrong block: {targeted.position} instead of ({x}, {y}, {z})")
            else:
                minescript.echo(f"  ✗ No block in crosshairs at ({x}, {y}, {z})")
            return False
            
    except Exception as e:
        minescript.echo(f"  ✗ Failed to break block: {e}")
        return False

def main():
    """Main function to find and look at all target blocks sequentially."""
    minescript.echo("=== Smooth Block Camera ===")
    minescript.echo(f"Target: {CONFIG['target_block']}")
    minescript.echo(f"Config: distance={CONFIG['search_distance']}m, " +
                   f"speed={CONFIG['rotation_duration']}s, " +
                   f"cooldown={CONFIG['block_cooldown']}s, " +
                   f"cluster_mode={CONFIG['use_cluster_mode']}, " +
                   f"break_blocks={CONFIG['break_blocks']}")
    
    player_pos = minescript.player_position()
    
    # Find all target blocks
    blocks = find_all_blocks(
        max_distance=CONFIG['search_distance'],
        block_type=CONFIG['target_block']
    )
    
    if blocks:
        # Sort blocks based on configuration
        if CONFIG['use_cluster_mode']:
            minescript.echo("Using cluster mode (angular proximity sorting)...")
            sorted_blocks = sort_blocks_by_viewing_order(blocks, player_pos)
        else:
            minescript.echo("Using distance mode (nearest first)...")
            sorted_blocks = sorted(blocks, key=lambda b: b['distance'])
        
        minescript.echo(f"Found {len(sorted_blocks)} block(s). Starting smooth camera tour...")
        
        for i, block_info in enumerate(sorted_blocks):
            x, y, z = block_info['position']
            distance = block_info['distance']
            
            minescript.echo(f"[{i+1}/{len(sorted_blocks)}] Looking at block at ({x}, {y}, {z}) - {distance:.1f}m away")
            
            # Smooth look with configured duration and steps
            # Breaking happens inside smooth_look_at function
            smooth_look_at((x + 0.5, y + 0.5, z + 0.5), 
                         duration=CONFIG['rotation_duration'], 
                         steps=CONFIG['rotation_steps'])
            
            # Pause between blocks (except after the last one)
            if i < len(sorted_blocks) - 1:
                minescript.echo(f"Pausing {CONFIG['block_cooldown']}s before next block...")
                time.sleep(CONFIG['block_cooldown'])
        
        minescript.echo(f"✓ Tour complete! Visited {len(sorted_blocks)} block(s).")
    else:
        minescript.echo(f"✗ No {CONFIG['target_block']} found within reach ({CONFIG['search_distance']} blocks)!")

# Run the script
if __name__ == "__main__":
    main()
