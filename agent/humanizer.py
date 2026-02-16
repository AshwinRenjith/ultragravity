
import time
import random
import math
import numpy as np
from typing import Tuple, List

def bezier_curve(start: Tuple[int, int], end: Tuple[int, int], control_points: List[Tuple[int, int]], num_points: int = 100) -> List[Tuple[int, int]]:
    """Calculates points along a Bezier curve."""
    trajectory = []
    n = len(control_points) + 1 # Degree of curve + 1
    # Simple Quadratic or Cubic logic manually or general formula
    # For mouse, cubic is usually good (start, control1, control2, end)
    
    # Let's assume start and end are part of the points passed to general algo if we want, 
    # but here we'll do a Cubic Bezier explicit for simplicity
    
    p0 = start
    p1 = control_points[0]
    p2 = control_points[1]
    p3 = end
    
    p3 = end
    
    # Easing function for realistic movement (slow start/end, fast middle)
    def ease_in_out_quad(x):
        return 2 * x * x if x < 0.5 else 1 - pow(-2 * x + 2, 2) / 2

    for i in range(num_points):
        t_linear = i / (num_points - 1)
        t = ease_in_out_quad(t_linear)
        
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        trajectory.append((x, y))
        
    return trajectory

def generate_human_path(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Generates a list of coordinates representing a human-like mouse path."""
    dist = math.hypot(end[0] - start[0], end[1] - start[1])
    
    # Random control points
    # Control points should be somewhat along the path but deviated
    # P1 is closer to start, P2 is closer to end
    
    dev_x = dist * 0.2
    dev_y = dist * 0.2
    
    ctrl1 = (
        start[0] + (end[0] - start[0]) * 0.33 + random.uniform(-dev_x, dev_x),
        start[1] + (end[1] - start[1]) * 0.33 + random.uniform(-dev_y, dev_y)
    )
    
    ctrl2 = (
        start[0] + (end[0] - start[0]) * 0.66 + random.uniform(-dev_x, dev_x),
        start[1] + (end[1] - start[1]) * 0.66 + random.uniform(-dev_y, dev_y)
    )
    
    # Calculate number of steps based on distance/speed
    # Speed isn't constant in human movement (Fitt's Law), but linear for now is okay with ease-in/out in timing
    steps = max(20, int(dist / 5)) 
    
    return bezier_curve(start, end, [ctrl1, ctrl2], steps)

def random_sleep(min_seconds=0.1, max_seconds=0.5):
    """Sleeps for a random duration."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def typing_delay():
    """Simulate keypress delay with variable pauses to mimic human behavior."""
    # Slower typing: 0.2s to 0.5s per key (approx 120-300 CPM, very deliberate)
    base_delay = random.uniform(0.2, 0.5)
    
    # Occasional variance (simulating thinking or finding the key)
    # 15% chance of a longer pause
    if random.random() < 0.15:
        base_delay += random.uniform(0.3, 0.8)
        
    time.sleep(base_delay)
