# Macro decided to automate farming within a pattern, meaning it will go from right, forward, left. etc(You will need to setup a farm suitable for it)
# Code is not made for any server, instead singleplayer. Meaning it does not have failsafes against checks.
# Getting banned, warned. etc is your own fault.

import minescript as ms
import time
import random
import sys

# ===== CONFIGURATION =====
CONFIG = {
    # Movement settings
    "forward_blocks": 4,  # How many blocks to move forward after reaching an end
    "initial_direction": "right",  # Initial direction: "right" or "left"
    
    # Randomization settings (makes movement look more human)
    "position_variance": 0.15,  # Random position offset (0.0-0.3 recommended)
    "pause_between_rows": (0.3, 0.8),  # Random pause duration (min, max) in seconds
    "pause_during_movement": (0.05, 0.15),  # Small pauses while moving
    "movement_duration_variance": 0.1,  # Variance in movement timing (0.0-0.3)
    
    # Detection settings
    "check_interval": 0.1,  # How often to check position (seconds)
    "stuck_threshold": 0.05,  # Movement less than this is considered "stuck"
    "stuck_checks": 3,  # Number of checks before considering stuck
    
    # Safety
    "max_iterations": 1000,  # Maximum number of rows before auto-stop
    "enable_sprint": True,  # Whether to enable sprinting
}

class FarmAutomation:
    def __init__(self):
        self.running = False
        self.current_direction = CONFIG["initial_direction"]
        self.iterations = 0
        self.last_positions = []
        
    def log(self, message):
        """Log message to chat"""
        ms.echo(f"[AutoFarm] {message}")
        
    def get_position(self):
        """Get current player position"""
        player = ms.player()
        return player.position
        
    def add_human_variance(self, base_value):
        """Add random variance to make movement more human-like"""
        variance = random.uniform(-CONFIG["position_variance"], CONFIG["position_variance"])
        return base_value + variance
        
    def random_pause(self, pause_type="between_rows"):
        """Add a random pause to simulate human reaction time"""
        if pause_type == "between_rows":
            min_pause, max_pause = CONFIG["pause_between_rows"]
        else:  # during_movement
            min_pause, max_pause = CONFIG["pause_during_movement"]
        
        pause_duration = random.uniform(min_pause, max_pause)
        time.sleep(pause_duration)
        
    def is_stuck(self):
        """Check if player is stuck (not moving)"""
        if len(self.last_positions) < CONFIG["stuck_checks"]:
            return False
            
        # Check if all recent positions are very close together
        recent_positions = self.last_positions[-CONFIG["stuck_checks"]:]
        for i in range(1, len(recent_positions)):
            x_diff = abs(recent_positions[i][0] - recent_positions[i-1][0])
            z_diff = abs(recent_positions[i][2] - recent_positions[i-1][2])
            
            # If any position shows significant movement, not stuck
            if x_diff > CONFIG["stuck_threshold"] or z_diff > CONFIG["stuck_threshold"]:
                return False
                
        return True
        
    def move_direction(self, direction):
        """Move in specified direction until stuck"""
        self.log(f"Moving {direction}...")
        
        # Press the movement key
        if direction == "right":
            ms.player_press_right(True)
        elif direction == "left":
            ms.player_press_left(True)
        elif direction == "forward":
            ms.player_press_forward(True)
        elif direction == "backward":
            ms.player_press_backward(True)
            
        # Enable sprinting if configured
        if CONFIG["enable_sprint"] and direction in ["forward", "backward"]:
            ms.player_press_sprint(True)
            
        # Track positions to detect when stuck
        self.last_positions = []
        
        try:
            while self.running:
                time.sleep(CONFIG["check_interval"])
                
                # Add occasional micro-pauses to simulate human movement
                if random.random() < 0.1:  # 10% chance
                    self.random_pause("during_movement")
                
                # Record position
                current_pos = self.get_position()
                self.last_positions.append(current_pos)
                
                # Keep only recent positions
                if len(self.last_positions) > CONFIG["stuck_checks"]:
                    self.last_positions.pop(0)
                
                # Check if stuck - need enough position samples first
                if len(self.last_positions) >= CONFIG["stuck_checks"]:
                    if self.is_stuck():
                        self.log(f"Reached end (stuck detected)")
                        break
                    
        finally:
            # Release movement keys
            if direction == "right":
                ms.player_press_right(False)
            elif direction == "left":
                ms.player_press_left(False)
            elif direction == "forward":
                ms.player_press_forward(False)
            elif direction == "backward":
                ms.player_press_backward(False)
                
            if CONFIG["enable_sprint"]:
                ms.player_press_sprint(False)
                
    def move_forward_blocks(self, blocks):
        """Move forward a specific number of blocks"""
        self.log(f"Moving forward {blocks} blocks...")
        
        start_pos = self.get_position()
        target_distance = blocks
        
        # Add human-like variance to target distance
        target_distance = self.add_human_variance(target_distance)
        
        ms.player_press_forward(True)
        if CONFIG["enable_sprint"]:
            ms.player_press_sprint(True)
        
        # Track positions for stuck detection
        self.last_positions = []
            
        try:
            while self.running:
                time.sleep(CONFIG["check_interval"])
                
                current_pos = self.get_position()
                
                # Record position for stuck detection
                self.last_positions.append(current_pos)
                if len(self.last_positions) > CONFIG["stuck_checks"]:
                    self.last_positions.pop(0)
                
                # Check distance moved
                distance_moved = abs(current_pos[2] - start_pos[2])
                
                # Check if stuck (can't move forward anymore)
                if len(self.last_positions) >= CONFIG["stuck_checks"]:
                    if self.is_stuck():
                        self.log(f"Can't move forward further.")
                        break
                
                # Check if we've moved far enough
                if distance_moved >= target_distance:
                    break
                    
                # Add occasional micro-pauses
                if random.random() < 0.05:  # 5% chance
                    self.random_pause("during_movement")
                    
        finally:
            ms.player_press_forward(False)
            if CONFIG["enable_sprint"]:
                ms.player_press_sprint(False)
                
    def swap_direction(self):
        """Swap between left and right direction"""
        if self.current_direction == "right":
            self.current_direction = "left"
        else:
            self.current_direction = "right"
        return self.current_direction
        
    def run(self):
        """Main automation loop"""
        self.running = True
        self.iterations = 0
        
        start_pos = self.get_position()
        self.log(f"Starting automation from position: ({start_pos[0]:.1f}, {start_pos[1]:.1f}, {start_pos[2]:.1f})")
        self.log(f"Initial direction: {self.current_direction}")
        self.log(f"Forward blocks per row: {CONFIG['forward_blocks']}")
        self.log("Press ESC and run '\\jobs' then '\\kill <job_id>' to stop")
        
        try:
            while self.running and self.iterations < CONFIG["max_iterations"]:
                self.iterations += 1
                self.log(f"Row {self.iterations} - Moving {self.current_direction}")
                
                # Move in current direction until end
                self.move_direction(self.current_direction)
                
                # Add human-like pause before changing direction
                self.random_pause("between_rows")
                
                # Move forward
                self.move_forward_blocks(CONFIG["forward_blocks"])
                
                # Add another pause before next row
                self.random_pause("between_rows")
                
                # Swap direction for next row
                self.swap_direction()
                
            if self.iterations >= CONFIG["max_iterations"]:
                self.log(f"Reached maximum iterations ({CONFIG['max_iterations']}). Stopping.")
            else:
                self.log("Automation stopped.")
                
        except KeyboardInterrupt:
            self.log("Interrupted by user.")
        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Release all keys and clean up"""
        self.running = False
        ms.player_press_right(False)
        ms.player_press_left(False)
        ms.player_press_forward(False)
        ms.player_press_backward(False)
        ms.player_press_sprint(False)
        self.log("Cleanup complete.")

# ===== COMMAND LINE INTERFACE =====
def print_help():
    """Print help information"""
    help_text = """
Auto Farm Movement Script
Usage: \\farm_auto_move [options]

Options:
  --forward <blocks>    : Set blocks to move forward (default: 4)
  --start-right        : Start moving right (default)
  --start-left         : Start moving left
  --no-sprint          : Disable sprinting
  --max-iter <n>       : Maximum iterations (default: 1000)
  --help               : Show this help message

Examples:
  \\farm_auto_move                    - Start with default settings
  \\farm_auto_move --forward 3        - Move 3 blocks forward per row
  \\farm_auto_move --start-left       - Start by moving left
  \\farm_auto_move --forward 5 --no-sprint
"""
    print(help_text)

def main():
    """Main entry point"""
    args = sys.argv[1:]
    
    # Parse command line arguments
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ["--help", "-h"]:
            print_help()
            return
        elif arg == "--forward":
            if i + 1 < len(args):
                CONFIG["forward_blocks"] = int(args[i + 1])
                i += 1
        elif arg == "--start-right":
            CONFIG["initial_direction"] = "right"
        elif arg == "--start-left":
            CONFIG["initial_direction"] = "left"
        elif arg == "--no-sprint":
            CONFIG["enable_sprint"] = False
        elif arg == "--max-iter":
            if i + 1 < len(args):
                CONFIG["max_iterations"] = int(args[i + 1])
                i += 1
        
        i += 1
    
    # Create and run automation
    automation = FarmAutomation()
    automation.run()

if __name__ == "__main__":
    main()
