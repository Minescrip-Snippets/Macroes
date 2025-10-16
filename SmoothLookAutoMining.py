# Macro decided to automate mining with a smooth loo, meaning it will smoothly go to blocks. 
# Cluster detection by default on, meaning it looks at clustered blocks first(toggleable from that to distance based)
# Code is not made for any server, instead singleplayer. Meaning it does not have failsafes against checks.
# Getting banned, warned. etc is your own fault.

import minescript
import math
import time

# ============================================
# CONFIGURATION OPTIONS
# ============================================
CONFIG = {
    # Block type to search for and break (use Minecraft block ID)
    # Examples: 'minecraft:iron_block', 'minecraft:diamond_ore', 
    #           'minecraft:gold_block', 'minecraft:stone', etc.
    # For crops, use base name like 'minecraft:wheat' (will match all ages)
    'target_block': 'minecraft:iron_block',
    
    # If True, match blocks ignoring their state (useful for crops with age)
    # e.g., 'minecraft:wheat' will match 'minecraft:wheat[age=0]' through 'minecraft:wheat[age=7]'
    'ignore_block_state': False,
    
    # Search distance in blocks (4.5 is typical survival reach, 5.0 for creative)
    'search_distance': 4.5,
    
    # Rotation speed: duration in seconds for camera rotation
    # Lower = faster, Higher = slower and smoother
    'rotation_duration': 1.5,
    
    # Smoothness: number of steps for interpolation
    # Higher = smoother but more CPU intensive (30-120 recommended)
    'rotation_steps': 90,
    
    # Cooldown in seconds before moving to next block
    'block_cooldown': 0.8,
    
    # If True, continuously scan for new blocks after completing a batch
    # Will keep running until no new blocks are found
    'continuous_scan': True,
    
    # Key to press to trigger a new scan (uses GLFW key codes)
    # Common keys: 89 = Y, 82 = R, 71 = G, 84 = T
    # See: https://www.glfw.org/docs/3.3/group__keys.html
    'rescan_key': 89,  # Y key
    
    # If True, visit blocks based on angular proximity (more realistic)
    # If False, visit blocks based on distance
    'use_cluster_mode': True,
    
    # If True, break blocks after looking at them
    'break_blocks': True,
    
    # Pause in seconds after looking at block before breaking it
    'break_delay': 0.3,
    
    # Time in seconds to hold attack button (for breaking blocks)
    # Increase this for blocks that take longer to break
    'break_hold_time': 0.1,
}
# ============================================

def find_all_blocks(max_distance=5, block_type='minecraft:iron_block', ignore_state=False):
    """Find all blocks of specified type within max_distance (player hit range)."""
    player_pos = minescript.player_position()
    px, py, pz = player_pos
    
    search_mode = "with state ignored" if ignore_state else "exact match"
    minescript.echo(f"Searching for {block_type} within {max_distance} blocks ({search_mode})...")
    
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
            # Check if block matches
            is_match = False
            
            if ignore_state:
                # Extract base block name (before '[' if present)
                found_base = found_block_type.split('[')[0]
                target_base = block_type.split('[')[0]
                is_match = (found_base == target_base)
            else:
                # Exact match
                is_match = (found_block_type == block_type)
            
            if is_match:
                x, y, z = positions_to_check[i]
                distance = math.sqrt((x - px)**2 + (y - py)**2 + (z - pz)**2)
                blocks_found.append({
                    'position': (x, y, z),
                    'distance': distance,
                    'full_type': found_block_type  # Store the full block type with state
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
    
    # Calculate total angular distance
    angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
    
    # Scale duration based on angular distance (closer = faster)
    if angular_distance < 15:
        duration_scale = 0.3 + (angular_distance / 15) * 0.7  # 30% to 100% of duration
        actual_duration = duration * duration_scale
    else:
        actual_duration = duration
    
    # Perform smooth interpolation
    step_delay = actual_duration / steps
    
    for i in range(steps + 1):
        # Base interpolation parameter (0.0 to 1.0)
        t = i / steps
        
        # Apply smoothstep for ease-in-out
        smooth_t = t * t * (3 - 2 * t)
        
        # Direct linear interpolation
        new_yaw = current_yaw + yaw_diff * smooth_t
        new_pitch = current_pitch + pitch_diff * smooth_t
        
        # Set orientation
        minescript.player_set_orientation(new_yaw, new_pitch)
        
        # Wait between steps
        if i < steps:
            time.sleep(step_delay)
    
    # Break block if enabled
    if CONFIG['break_blocks']:
        if CONFIG['break_delay'] > 0:
            time.sleep(CONFIG['break_delay'])
        
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
                   f"break_blocks={CONFIG['break_blocks']}, " +
                   f"ignore_state={CONFIG['ignore_block_state']}")
    
    # Get key name for display
    key_names = {89: 'Y', 82: 'R', 71: 'G', 84: 'T'}
    rescan_key_name = key_names.get(CONFIG['rescan_key'], f"key {CONFIG['rescan_key']}")
    minescript.echo(f"\nPress '{rescan_key_name}' to start scanning | Open any GUI to exit")
    
    total_blocks_processed = 0
    processed_positions = set()  # Track blocks we've already looked at
    is_active = False  # Whether we're actively processing blocks
    
    # Setup event queue for key and screen events
    event_queue = minescript.EventQueue()
    event_queue.register_key_listener()
    
    try:
        while True:
            # Check for exit condition (GUI opened)
            current_screen = minescript.screen_name()
            if current_screen is not None:
                minescript.echo(f"GUI opened ({current_screen}) - Exiting script...")
                break
            
            # Check for scan key press to start/restart
            try:
                while True:
                    event = event_queue.get(block=False)
                    if event.type == "key":
                        # Key down event (action == 1) and matches rescan key
                        if event.action == 1 and event.key == CONFIG['rescan_key']:
                            minescript.echo(f"\n'{rescan_key_name}' pressed - Starting new scan session!")
                            processed_positions.clear()  # Clear processed list
                            is_active = True
            except:
                pass  # No events in queue
            
            # Only process if active
            if not is_active:
                time.sleep(0.1)
                continue
            
            player_pos = minescript.player_position()
            
            # Scan for all target blocks
            blocks = find_all_blocks(
                max_distance=CONFIG['search_distance'],
                block_type=CONFIG['target_block'],
                ignore_state=CONFIG['ignore_block_state']
            )
            
            # Filter out already processed blocks
            unprocessed_blocks = [b for b in blocks if b['position'] not in processed_positions]
            
            if not unprocessed_blocks:
                minescript.echo(f"✓ No more unprocessed blocks found!")
                minescript.echo(f"Total blocks processed in this session: {total_blocks_processed}")
                minescript.echo(f"Press '{rescan_key_name}' to start new scan session or open GUI to exit")
                is_active = False
                total_blocks_processed = 0
                time.sleep(0.1)
                continue
            
            # Sort blocks based on configuration
            if CONFIG['use_cluster_mode']:
                sorted_blocks = sort_blocks_by_viewing_order(unprocessed_blocks, player_pos)
            else:
                sorted_blocks = sorted(unprocessed_blocks, key=lambda b: b['distance'])
            
            # Process only the first block in the sorted list
            block_info = sorted_blocks[0]
            
            # Check for exit condition before processing
            current_screen = minescript.screen_name()
            if current_screen is not None:
                minescript.echo(f"GUI opened ({current_screen}) - Exiting script...")
                break
            
            x, y, z = block_info['position']
            distance = block_info['distance']
            full_type = block_info.get('full_type', CONFIG['target_block'])
            
            total_remaining = len(unprocessed_blocks)
            minescript.echo(f"[{total_remaining} remaining] Looking at {full_type} at ({x}, {y}, {z}) - {distance:.1f}m away")
            
            # Smooth look with configured duration and steps
            smooth_look_at((x + 0.5, y + 0.5, z + 0.5), 
                         duration=CONFIG['rotation_duration'], 
                         steps=CONFIG['rotation_steps'])
            
            # Mark this block as processed
            processed_positions.add(block_info['position'])
            total_blocks_processed += 1
            
            # Pause before next scan/block
            time.sleep(CONFIG['block_cooldown'])
            
            # Loop continues, will rescan automatically for next block
    
    finally:
        minescript.echo(f"✓ Script ended. Total blocks processed: {total_blocks_processed}")


# Run the script
if __name__ == "__main__":
    main()
