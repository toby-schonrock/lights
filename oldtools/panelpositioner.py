import pygame

# --- CONFIGURATION & CONSTANTS ---
PIXELS_PER_METER = 250 # left wall
# PIXELS_PER_METER = 215 # right wall

# Panel physical dimensions in meters (62x82 cm)
PANEL_WIDTH_M = 0.62
PANEL_HEIGHT_M = 0.82

# --- FIXED ANCHOR PANEL CONFIGURATION ---
# Known world position (meters) for the center of the fixed anchor panel
FIXED_PANEL = "a"
FIXED_PANEL_WORLD_X = 0.9
FIXED_PANEL_WORLD_Y = 2.5 + 0.4

# FIXED_PANEL = "p"
# FIXED_PANEL_WORLD_X = 0.9
# FIXED_PANEL_WORLD_Y = 2.5 + 0.5

# Color Palette (RGBA)
COLOR_BG = (20, 20, 30)
COLOR_PANEL_DEFAULT = (0, 180, 255, 140)
COLOR_PANEL_ACTIVE = (255, 140, 0, 200)
COLOR_PANEL_BORDER = (255, 255, 255)
COLOR_TEXT = (255, 255, 255)

# Load background image
try:
    bg_image = pygame.image.load("left_wall.jpeg")
    # half the size of bg image
    bg_image = pygame.transform.smoothscale(
        bg_image, (bg_image.get_width() / 2, bg_image.get_height() / 2)
    )
except Exception as e:
    print(
        "Warning: Could not load background image. Make sure it's in the same folder."
        f" Error: {e}"
    )
    bg_image = None

WINDOW_WIDTH = bg_image.get_width() if bg_image else 1200
WINDOW_HEIGHT = bg_image.get_height() if bg_image else 800

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Panel Layout Calibrator - Center-Based Pixel Space")
clock = pygame.time.Clock()

def get_panel_dimensions_px(is_vertical: bool) -> tuple[int, int]:
    """Returns width and height in pixels for a panel based on its orientation."""
    w_m = PANEL_WIDTH_M if is_vertical else PANEL_HEIGHT_M
    h_m = PANEL_HEIGHT_M if is_vertical else PANEL_WIDTH_M
    return int(w_m * PIXELS_PER_METER), int(h_m * PIXELS_PER_METER)

# Helper function to convert initial world center meters to screen pixel centers for startup
def world_to_pixel(wx: float, wy: float, is_vertical: bool, ref_wx: float, ref_wy: float, ref_cx: int, ref_cy: int) -> tuple[int, int]:
    dx_m = wx - ref_wx
    dy_m = wy - ref_wy
    cx = ref_cx + int(dx_m * PIXELS_PER_METER)
    cy = ref_cy - int(dy_m * PIXELS_PER_METER)
    return cx, cy

# Initial raw world data to pre-populate pixel positions on startup
initial_world_data = {
    'a': [0.90, 2.90, True],
    'b': [1.76, 2.86, True],
    'c': [2.70, 2.96, False],
    'd': [3.62, 2.95, True],
    'e': [2.60, 2.15, False],
    'f': [3.59, 2.14, False],
    'g': [1.63, 1.59, True],
    'h': [2.43, 1.38, False],
    'i': [3.47, 1.38, False],
    'm': [3.54, 3.00, False],
    'n': [2.68, 2.98, True],
    'o': [1.80, 3.05, False],
    'p': [0.90, 3.00, True],
    'q': [3.42, 2.28, False],
    'r': [1.96, 2.29, False],
    's': [0.70, 2.14, False],
    't': [3.56, 1.49, False],
    'u': [2.67, 1.55, True],
    'v': [1.78, 1.54, False],
}

# --- STORE IN-BETWEEN POSITIONS AS CENTER PIXELS ---
# layout_data format: {'name': [center_x, center_y, is_vertical]}
layout_data = {}

# Arbitrary initial screen anchor center for panel 'p'
ref_cx, ref_cy = 200, 200
for name, (wx, wy, is_vert) in initial_world_data.items():
    if name == FIXED_PANEL:
        layout_data[name] = [ref_cx, ref_cy, is_vert]

for name, (wx, wy, is_vert) in initial_world_data.items():
    if name != FIXED_PANEL:
        cx, cy = world_to_pixel(
            wx, wy, is_vert, 
            FIXED_PANEL_WORLD_X, FIXED_PANEL_WORLD_Y, 
            layout_data[FIXED_PANEL][0], layout_data[FIXED_PANEL][1]
        )
        layout_data[name] = [cx, cy, is_vert]

font = pygame.font.SysFont(None, 22)
active_panel = None
drag_offset_x, drag_offset_y = 0, 0

print("--- CALIBRATOR CONTROLS ---")
print("• Click & Drag: Move any panel.")
print("• Press 'R' while clicking/hovering a panel: Toggle vertical/horizontal rotation around center.")
print("• Press 'P': Calculate center-based world coordinates and print layout dictionary.")
print("---------------------------")

running = True
while running:
    screen.fill(COLOR_BG)
    if bg_image:
        screen.blit(bg_image, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mx, my = event.pos
                for name, (cx, cy, is_vert) in layout_data.items():
                    sw, sh = get_panel_dimensions_px(is_vert)
                    sx = cx - sw // 2
                    sy = cy - sh // 2
                    if pygame.Rect(sx, sy, sw, sh).collidepoint(mx, my):
                        active_panel = name
                        drag_offset_x = cx - mx
                        drag_offset_y = cy - my
                        break

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                active_panel = None

        elif event.type == pygame.MOUSEMOTION:
            if active_panel:
                mx, my = event.pos
                # Directly update stored screen center pixel position
                layout_data[active_panel][0] = mx + drag_offset_x
                layout_data[active_panel][1] = my + drag_offset_y

        elif event.key == pygame.KEYDOWN if hasattr(event, 'key') else False: # handled properly below
            pass

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                print("\n--- CALIBRATED WORLD LAYOUT (CENTER-BASED) ---")
                if FIXED_PANEL in layout_data:
                    ref_cx, ref_cy, _ = layout_data[FIXED_PANEL]
                    print("self.layout = {")
                    for name, (cx, cy, is_vert) in layout_data.items():
                        # Calculate world coordinates relative to fixed panel center anchor
                        dx_m = (cx - ref_cx) / PIXELS_PER_METER
                        dy_m = (ref_cy - cy) / PIXELS_PER_METER # Screen Y down vs World Y up
                        
                        wx = round(FIXED_PANEL_WORLD_X + dx_m, 2)
                        wy = round(FIXED_PANEL_WORLD_Y + dy_m, 2)
                        print(f"    '{name}': [{wx:.2f}, {wy:.2f}, {str(is_vert)}],")
                    print("}\n")
            elif event.key == pygame.K_r and active_panel:
                layout_data[active_panel][2] = not layout_data[active_panel][2]
                print(f"Toggled rotation for panel '{active_panel}'")

    # Render all panel boxes using center pixel positions
    for name, (cx, cy, is_vert) in layout_data.items():
        sw, sh = get_panel_dimensions_px(is_vert)
        sx = cx - sw // 2
        sy = cy - sh // 2
        rect = pygame.Rect(sx, sy, sw, sh)
        color = COLOR_PANEL_DEFAULT if name != active_panel else COLOR_PANEL_ACTIVE

        # Draw semi-transparent background surface
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        surf.fill(color)
        screen.blit(surf, (sx, sy))
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, rect, 2)

        # Render label
        lbl = font.render(name.upper(), True, COLOR_TEXT)
        screen.blit(lbl, (sx + 6, sy + 6))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()