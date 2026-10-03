import pygame

# --- CONFIGURATION & CONSTANTS ---
WINDOW_WIDTH = 1805
WINDOW_HEIGHT = 786
PIXELS_PER_METER = 195

# Panel physical dimensions in meters (62x82 cm)
PANEL_WIDTH_M = 0.62
PANEL_HEIGHT_M = 0.82

# --- ADJUSTABLE ORIGIN CONFIGURATION ---
# Left Wall: World (0,0) is Bottom-Left
LEFT_WALL_ORIGIN_X = 0
LEFT_WALL_ORIGIN_Y = 786  # Screen Y coordinate of the floor/bottom baseline

# Right Wall: World (0,0) is Bottom-Right (Origin screen X coordinate for the right wall's right edge)
RIGHT_WALL_X_OFFSET = 1805
RIGHT_WALL_Y_OFFSET = 0

# Color Palette (RGBA)
COLOR_BG = (20, 20, 30)
COLOR_PANEL_DEFAULT = (0, 180, 255, 140)
COLOR_PANEL_ACTIVE = (255, 140, 0, 200)
COLOR_PANEL_BORDER = (255, 255, 255)
COLOR_TEXT = (255, 255, 255)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Panel Layout Calibrator - Flipped Right Wall X-Axis")
clock = pygame.time.Clock()

# Load background image
try:
  bg_image = pygame.image.load("layout.png")
  bg_image = pygame.transform.smoothscale(
      bg_image, (WINDOW_WIDTH, WINDOW_HEIGHT)
  )
except Exception as e:
  print(
      "Warning: Could not load 'layout.png'. Make sure it's in the same folder."
      f" Error: {e}"
  )
  bg_image = None

# Initial layout data: {'name': [x_meters, y_meters, is_vertical]}
layout_data = {
    'a': [0.34, 2.38, True],
    'b': [1.25, 2.51, True],
    'c': [2.2, 2.81, False],
    'd': [3.3, 2.61, True],
    'e': [2.08, 1.94, False],
    'f': [3.15, 1.73, False],
    'g': [1.06, 1.15, False],
    'h': [2.11, 0.85, True],
    'i': [3.01, 0.85, False],
    'm': [3.23, 2.81, False],
    'n': [2.31, 2.46, True],
    'o': [1.16, 2.81, False],
    'p': [0.23, 2.59, True],
    'q': [3.12, 1.91, False],
    'r': [1.31, 1.91, False],
    's': [0.13, 1.73, False],
    't': [3.23, 1.05, False],
    'u': [2.32, 1.18, True],
    'v': [1.14, 1.06, False],
}

font = pygame.font.SysFont(None, 22)
active_panel = None
drag_offset_x, drag_offset_y = 0, 0


def is_right_wall(panel_name: str) -> bool:
  """Determines if a panel belongs to the right wall based on its name."""
  return panel_name >= "m"


def get_panel_dimensions_px(is_vertical: bool) -> tuple[int, int]:
  """Returns width and height in pixels for a panel based on its orientation."""
  w_m = PANEL_WIDTH_M if is_vertical else PANEL_HEIGHT_M
  h_m = PANEL_HEIGHT_M if is_vertical else PANEL_WIDTH_M
  return int(w_m * PIXELS_PER_METER), int(h_m * PIXELS_PER_METER)


def get_wall_origins(panel_name: str) -> tuple[int, int]:
  """Returns the screen pixel origin baseline for the wall section."""
  is_right = is_right_wall(panel_name)
  ox = LEFT_WALL_ORIGIN_X + (RIGHT_WALL_X_OFFSET if is_right else 0)
  oy = LEFT_WALL_ORIGIN_Y + (RIGHT_WALL_Y_OFFSET if is_right else 0)
  return ox, oy


def world_to_screen(wx: float, wy: float, is_vertical: bool, panel_name: str) -> tuple[int, int]:
  """Converts world coordinates to Pygame screen coordinates.

  Left wall: (0,0) is bottom-left, X goes right (+). Right wall: (0,0) is
  bottom-right, X goes left (+).
  """
  ox, oy = get_wall_origins(panel_name)
  w_px, h_px = get_panel_dimensions_px(is_vertical)

  if is_right_wall(panel_name):
    # Flipped X-axis: 0,0 is bottom-right, positive wx extends leftwards from ox
    sx = ox - (wx * PIXELS_PER_METER) - w_px
  else:
    # Standard X-axis: 0,0 is bottom-left, positive wx extends rightwards from ox
    sx = ox + (wx * PIXELS_PER_METER)

  # World Y goes UP, so we subtract from baseline Oy in pixels
  sy = oy - (wy * PIXELS_PER_METER) - h_px
  return int(sx), int(sy)


def screen_to_world(sx: int, sy: int, is_vertical: bool, panel_name: str) -> tuple[float, float]:
  """Converts screen coordinates (pixels) back to world coordinates (meters)."""
  ox, oy = get_wall_origins(panel_name)
  w_px, h_px = get_panel_dimensions_px(is_vertical)

  if is_right_wall(panel_name):
    wx = (ox - sx - w_px) / PIXELS_PER_METER
  else:
    wx = (sx - ox) / PIXELS_PER_METER

  wy = (oy - sy - h_px) / PIXELS_PER_METER
  return round(max(0.0, wx), 2), round(max(0.0, wy), 2)


print("--- CALIBRATOR CONTROLS ---")
print("• Click & Drag: Move any panel.")
print("• Press 'R' while clicking a panel: Toggle vertical/horizontal rotation.")
print("• Press 'P': Print the updated layout dictionary to console.")
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
        for name, (wx, wy, is_vert) in layout_data.items():
          sw, sh = get_panel_dimensions_px(is_vert)
          sx, sy = world_to_screen(wx, wy, is_vert, name)

          if pygame.Rect(sx, sy, sw, sh).collidepoint(mx, my):
            active_panel = name
            drag_offset_x = sx - mx
            drag_offset_y = sy - my
            break

    elif event.type == pygame.MOUSEBUTTONUP:
      if event.button == 1:
        active_panel = None

    elif event.type == pygame.MOUSEMOTION:
      if active_panel:
        mx, my = event.pos
        new_sx = mx + drag_offset_x
        new_sy = my + drag_offset_y

        is_vert = layout_data[active_panel][2]
        new_wx, new_wy = screen_to_world(new_sx, new_sy, is_vert, active_panel)
        layout_data[active_panel][0] = new_wx
        layout_data[active_panel][1] = new_wy

    elif event.type == pygame.KEYDOWN:
      if event.key == pygame.K_p:
        print("\n--- NEW CALIBRATED LAYOUT ---")
        print("self.layout = {")
        for name, data in layout_data.items():
          print(f"    '{name}': [{data[0]}, {data[1]}, {str(data[2])}],")
        print("}\n")
      elif event.key == pygame.K_r and active_panel:
        layout_data[active_panel][2] = not layout_data[active_panel][2]
        print(f"Toggled rotation for panel '{active_panel}'")

  # Render all panel boxes
  for name, (wx, wy, is_vert) in layout_data.items():
    sw, sh = get_panel_dimensions_px(is_vert)
    sx, sy = world_to_screen(wx, wy, is_vert, name)

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