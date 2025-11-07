import minescript
import math
import time

# Try to import Minescript-Plus (optional). If not available, fall back.
try:
    import minescript_plus as mp
    HAS_PLUS = True
except Exception:
    mp = None
    HAS_PLUS = False

# ============================================
# CONFIGURATION
# ============================================
CONFIG = {
    'target_block': 'select',
    'ignore_block_state': False,
    'search_distance': 4.5,
    'rotation_duration': 0.5,
    'rotation_steps': 90,
    'block_cooldown': 0.1,
    'continuous_scan': True,
    'rescan_key': 89,
    'use_cluster_mode': True,
    'break_blocks': True,
    'break_delay': 0.1,
    'break_hold_time': 1.2,
    'cluster_distance': 1.5,
    'debug': False,      # <-- Set to True to enable detailed in-game messages
    'hud_position': ( -10, 10 ),  # (x, y) relative; anchor will be applied when using Minescript-Plus
}
# ============================================

PASSABLE_BLOCKS = {
    "minecraft:air", "minecraft:cave_air", "minecraft:void_air",
    "minecraft:water", "minecraft:lava", "minecraft:vine", "minecraft:web",
    "minecraft:grass", "minecraft:tall_grass", "minecraft:large_fern",
    "minecraft:torch", "minecraft:wall_torch", "minecraft:snow", "minecraft:grass_block",
    "minecraft:fern", "minecraft:sea_grass", "minecraft:kelp", "minecraft:seagrass",
}

# ===== helpers for messaging / HUD =====
_hud_index = None
_total_broken = 0

def debug_msg(text):
    """Show debug messages only if debug enabled. Uses Minescript-Plus actionbar if present."""
    if not CONFIG['debug']:
        return
    try:
        if HAS_PLUS and mp is not None:
            try:
                mp.Gui.set_actionbar(str(text))
                return
            except Exception:
                pass
        # fallback to chat/echo
        minescript.echo(str(text))
    except Exception:
        pass

def summary_update():
    """Update HUD counter (only minimal info when debug=False)."""
    global _hud_index, _total_broken
    text = f"Mined: {_total_broken}"
    try:
        if HAS_PLUS and mp is not None:
            try:
                # create HUD text once
                if _hud_index is None:
                    # add_text(text, x, y, color=(r,g,b), alpha=255, scale=1.0, shadow=False, italic=False, underline=False,
                    #         strikethrough=False, obfsucated=False, anchorX=0, anchorY=0, justifyX=-1, justifyY=-1, screens="all")
                    # We'll place near top-right using anchorX=1.0 and justifyX=1
                    x, y = CONFIG['hud_position']
                    _hud_index = mp.Hud.add_text(text, int(x), int(y),
                                                 color=(255, 255, 255), alpha=255, scale=1.1,
                                                 shadow=False, italic=False, underline=False, strikethrough=False,
                                                 obfsucated=False, anchorX=1.0, anchorY=0.0,
                                                 justifyX=1.0, justifyY=-1.0, screens="all")
                else:
                    mp.Hud.set_text_string(_hud_index, text)
                return
            except Exception:
                # fall through to echo
                pass
        # fallback: minimal chat echo (will spam chat; used only if plus missing)
        minescript.echo(text)
    except Exception:
        pass

# -----------------------------------------------
# Safe wrappers for block queries
# -----------------------------------------------
def get_block_id_at(x, y, z):
    try:
        return minescript.getblock(x, y, z)
    except Exception:
        return None

def get_blocklist_for_positions(pos_list):
    try:
        return minescript.getblocklist(pos_list)
    except Exception as e:
        debug_msg(f"[debug] getblocklist failed: {e}")
        return None

# =========================================
# FIND / SCAN BLOCKS
# =========================================
def find_all_blocks(max_distance=5, block_type='minecraft:redstone_block', ignore_state=False):
    player_pos = minescript.player_position()
    px, py, pz = player_pos

    debug_msg(f"Searching for {block_type} within {max_distance} blocks...")
    search_range = max_distance
    positions_to_check = []

    for x in range(int(px - search_range), int(px + search_range + 1)):
        for y in range(int(py - search_range), int(py + search_range + 1)):
            for z in range(int(pz - search_range), int(pz + search_range + 1)):
                d = math.sqrt((x - px)**2 + (y - py)**2 + (z - pz)**2)
                if d <= max_distance:
                    positions_to_check.append((x, y, z))

    blocks_found = []
    if positions_to_check:
        block_types = get_blocklist_for_positions(positions_to_check)
        if block_types is None:
            return []

        for i, found_block_type in enumerate(block_types):
            if found_block_type is None:
                continue
            is_match = False
            if ignore_state:
                found_base = str(found_block_type).split('[')[0]
                target_base = block_type.split('[')[0]
                is_match = (found_base == target_base)
            else:
                is_match = (found_block_type == block_type)

            if is_match:
                x, y, z = positions_to_check[i]
                distance = math.sqrt((x - px)**2 + (y - py)**2 + (z - pz)**2)
                blocks_found.append({
                    'position': (x, y, z),
                    'distance': distance,
                    'full_type': found_block_type
                })

    debug_msg(f"Search complete. Found {len(blocks_found)} block(s)")
    return blocks_found

# =========================================
# ANGLES / ROTATION HELPERS
# =========================================
def calculate_look_angles(player_pos, target_pos):
    px, py, pz = player_pos
    tx, ty, tz = target_pos
    dx = tx - px
    dy = ty - (py + 1.62)
    dz = tz - pz
    horizontal_distance = math.sqrt(dx**2 + dz**2)
    pitch = -math.degrees(math.atan2(dy, horizontal_distance))
    yaw = math.degrees(math.atan2(-dx, dz))
    return yaw, pitch

def normalize_angle(angle):
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def angle_difference(current, target):
    diff = normalize_angle(target - current)
    return diff

def calculate_angular_distance(yaw1, pitch1, yaw2, pitch2):
    yaw1_rad = math.radians(yaw1)
    pitch1_rad = math.radians(pitch1)
    yaw2_rad = math.radians(yaw2)
    pitch2_rad = math.radians(pitch2)
    x1 = math.cos(pitch1_rad) * math.sin(yaw1_rad)
    y1 = math.sin(pitch1_rad)
    z1 = math.cos(pitch1_rad) * math.cos(yaw1_rad)
    x2 = math.cos(pitch2_rad) * math.sin(yaw2_rad)
    y2 = math.sin(pitch2_rad)
    z2 = math.cos(pitch2_rad) * math.cos(yaw2_rad)
    dot_product = x1*x2 + y1*y2 + z1*z2
    dot_product = max(-1.0, min(1.0, dot_product))
    return math.degrees(math.acos(dot_product))

# =========================================
# VISIBILITY CHECK (raymarch + batch getblocklist)
# =========================================
def is_block_visible(player_pos, block_pos, step=0.25, ignore_last=0.5):
    eye = list(player_pos)
    eye[1] += 1.62  # eye height
    tx = block_pos[0] + 0.5
    ty = block_pos[1] + 0.5
    tz = block_pos[2] + 0.5

    dx = tx - eye[0]
    dy = ty - eye[1]
    dz = tz - eye[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    if dist <= 0.0:
        return True

    eff_dist = max(0.0, dist - ignore_last)
    steps = max(1, int(eff_dist / step))
    positions = []
    x = eye[0]; y = eye[1]; z = eye[2]
    dirx = dx / dist * step
    diry = dy / dist * step
    dirz = dz / dist * step
    for i in range(1, steps + 1):
        x += dirx; y += diry; z += dirz
        bx = math.floor(x); by = math.floor(y); bz = math.floor(z)
        if (bx, by, bz) == (block_pos[0], block_pos[1], block_pos[2]):
            continue
        positions.append((bx, by, bz))

    if not positions:
        return True

    block_types = get_blocklist_for_positions(positions)
    if block_types is None:
        return True

    for bt in block_types:
        if bt is None:
            continue
        if bt not in PASSABLE_BLOCKS:
            return False
    return True

# =========================================
# SMOOTH LOOK
# =========================================
def smooth_look_at(target_pos, block_pos, obstructed_set, duration=1.0, steps=60):
    player_pos = minescript.player_position()
    current_yaw, current_pitch = minescript.player_orientation()
    target_yaw, target_pitch = calculate_look_angles(player_pos, target_pos)
    yaw_diff = angle_difference(current_yaw, target_yaw)
    pitch_diff = angle_difference(current_pitch, target_pitch)
    angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
    if angular_distance < 15:
        duration_scale = 0.3 + (angular_distance / 15) * 0.7
        actual_duration = duration * duration_scale
    else:
        actual_duration = duration
    step_delay = actual_duration / steps
    for i in range(steps + 1):
        t = i / steps
        smooth_t = t * t * (3 - 2 * t)
        new_yaw = current_yaw + yaw_diff * smooth_t
        new_pitch = current_pitch + pitch_diff * smooth_t
        minescript.player_set_orientation(new_yaw, new_pitch)
        if i < steps:
            time.sleep(step_delay)

    if CONFIG['break_blocks']:
        if CONFIG['break_delay'] > 0:
            time.sleep(CONFIG['break_delay'])

        is_correctly_targeted = False
        final_targeted_block = None
        for _ in range(3):
            targeted = minescript.player_get_targeted_block(max_distance=6.0)
            final_targeted_block = targeted
            if targeted and tuple(targeted.position) == block_pos:
                is_correctly_targeted = True
                break
            time.sleep(0.05)

        if is_correctly_targeted:
            minescript.player_press_attack(True)
            time.sleep(CONFIG['break_hold_time'])
            minescript.player_press_attack(False)
            return True
        else:
            if final_targeted_block:
                debug_msg(f"OBSTRUCTION: Expected {block_pos}, but looking at {final_targeted_block.position}. Ignoring.")
            else:
                debug_msg(f"OBSTRUCTION: Expected {block_pos}, but looking at nothing. Ignoring.")
            obstructed_set.add(block_pos)
            return False

    return False

# =========================================
# CLUSTER HELPERS
# =========================================
def euclidean_distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def cluster_blocks(blocks, threshold=1.5):
    positions = [b['position'] for b in blocks]
    visited = set()
    clusters = []
    for i, bpos in enumerate(positions):
        if i in visited:
            continue
        queue = [i]
        cluster_idxs = []
        while queue:
            idx = queue.pop(0)
            if idx in visited:
                continue
            visited.add(idx)
            cluster_idxs.append(idx)
            for j, opos in enumerate(positions):
                if j in visited:
                    continue
                if euclidean_distance(positions[idx], opos) <= threshold:
                    queue.append(j)
        cluster = [blocks[cidx] for cidx in cluster_idxs]
        clusters.append(cluster)
    return clusters

def cluster_tightness(cluster):
    coords = [c['position'] for c in cluster]
    if len(coords) <= 1:
        return 0.0
    maxd = 0.0
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            d = euclidean_distance(coords[i], coords[j])
            if d > maxd:
                maxd = d
    return maxd

def cluster_center(cluster):
    coords = [c['position'] for c in cluster]
    n = len(coords)
    sx = sy = sz = 0.0
    for x,y,z in coords:
        sx += x; sy += y; sz += z
    return (sx/n, sy/n, sz/n)

def sort_clusters(clusters, player_pos):
    info = []
    for c in clusters:
        t = cluster_tightness(c)
        center = cluster_center(c)
        dist = euclidean_distance(player_pos, center)
        info.append((t, dist, c))
    info.sort(key=lambda x: (x[0], x[1]))
    return [c for _,_,c in info]

# =========================================
# MAIN LOOP
# =========================================
def main():
    global _total_broken, _hud_index

    if CONFIG['target_block'] == 'select':
        # pick target by looking at it
        minescript.echo("Look at a block to select it...")
        initial_target = None
        while True:
            t = minescript.player_get_targeted_block()
            if t and t.type not in ["minecraft:air", "minecraft:bedrock"]:
                initial_target = t
                break
            time.sleep(0.1)
        CONFIG['target_block'] = initial_target.type
        minescript.echo(f"[AutoMine] Target: {CONFIG['target_block']}")
        time.sleep(0.5)

    debug_msg("=== Smooth Block Camera (Clustered Mode) ===")
    debug_msg(f"Target: {CONFIG['target_block']}")

    processed_positions = set()
    obstructed_positions = set()

    # initialize HUD counter immediately (so it's visible even before mining)
    _total_broken = 0
    summary_update()

    try:
        while True:
            # exit on GUI open
            current_screen = minescript.screen_name()
            if current_screen is not None:
                debug_msg(f"GUI opened ({current_screen}) - Exiting script...")
                break

            player_pos = minescript.player_position()
            blocks = find_all_blocks(
                max_distance=CONFIG['search_distance'],
                block_type=CONFIG['target_block'],
                ignore_state=CONFIG['ignore_block_state']
            )

            # filter out processed and obstructed
            unprocessed = [b for b in blocks if b['position'] not in processed_positions and b['position'] not in obstructed_positions]

            if not unprocessed:
                if CONFIG['debug']:
                    debug_msg("All visible blocks processed or obstructed. Resetting cycle...")
                processed_positions.clear()
                obstructed_positions.clear()
                time.sleep(1.0)
                continue

            # clustering
            if CONFIG['use_cluster_mode']:
                clusters = cluster_blocks(unprocessed, threshold=CONFIG['cluster_distance'])
                sorted_clusters = sort_clusters(clusters, player_pos)
                ordered_blocks = []
                for cluster in sorted_clusters:
                    center = cluster_center(cluster)
                    members = sorted(cluster, key=lambda b: euclidean_distance(b['position'], center))
                    ordered_blocks.extend(members)
            else:
                ordered_blocks = sorted(unprocessed, key=lambda b: b['distance'])

            # pick first block
            block_info = ordered_blocks[0]
            x, y, z = block_info['position']
            distance_to_block = block_info['distance']
            debug_msg(f"Targeting {block_info.get('full_type', CONFIG['target_block'])} at ({x},{y},{z}) - {distance_to_block:.1f}m")

            # visibility pre-check
            if not is_block_visible(player_pos, (x, y, z), step=0.25, ignore_last=0.5):
                debug_msg(f"BLOCK OBSTRUCTED (raymarch): ({x},{y},{z}) -> skipping and marking obstructed")
                obstructed_positions.add((x, y, z))
                time.sleep(CONFIG['block_cooldown'])
                continue

            # smooth look + attempt break
            ok = smooth_look_at((x + 0.5, y + 0.5, z + 0.5), (x, y, z), obstructed_positions,
                           duration=CONFIG['rotation_duration'], steps=CONFIG['rotation_steps'])

            if ok:
                _total_broken += 1
                processed_positions.add((x, y, z))
                # update HUD (minimal info mode)
                if CONFIG['debug']:
                    debug_msg(f"✓ Block broken. Total: {_total_broken}")
                summary_update()

            time.sleep(CONFIG['block_cooldown'])

    finally:
        # cleanup: remove HUD entry if plus available
        try:
            if HAS_PLUS and mp is not None and _hud_index is not None:
                mp.Hud.remove_text(_hud_index)
        except Exception:
            pass
        minescript.echo("Script ended.")

if __name__ == "__main__":
    main()
