import math
import sys

import pygame

from lib.arion_lights import LightConfig


class VirtualRig:

  def __init__(self, width=1450, height=600):
    pygame.init()
    self.width = width
    self.height = height
    self.screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Virtual Lighting Setup - 2D Visualizer")
    self.clock = pygame.time.Clock()

    # Should be able to fit 10 m width
    self.scale = width / 9 # px/m

    # bottom of screen is at floor height
    self.floor_height = 0.4

    # Panel physical dimensions in meters (62x82 cm)
    self.panel_w_m = 0.62
    self.panel_h_m = 0.82

    # Calibrated layout configuration
    self.layout = {
        # left panels (Bottom-left origin, X grows right)
        'a': [0.34, 2.38, True],
        'b': [1.25, 2.51, True],
        'c': [2.2, 2.81, False],
        'd': [3.3, 2.61, True],
        'e': [2.08, 1.94, False],
        'f': [3.15, 1.73, False],
        'g': [1.06, 1.15, False],
        'h': [2.11, 0.85, True],
        'i': [3.01, 0.85, False],
        # right panels (Bottom-right origin, X grows left due to 3D rotation)
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

  def _is_right_wall(self, name: str) -> bool:
    return name >= "m"

  def _get_dimensions_px(self, is_vertical: bool):
    w_m = self.panel_w_m if is_vertical else self.panel_h_m
    h_m = self.panel_h_m if is_vertical else self.panel_w_m
    return int(w_m * self.scale), int(h_m * self.scale)

  def _world_to_screen(self, wx, wy, is_vertical, name):
    is_right = self._is_right_wall(name)
    w_px, h_px = self._get_dimensions_px(is_vertical)

    if is_right:
      # Flipped X axis: 0,0 is bottom-right, positive wx extends leftwards
      sx = self.width - (wx * self.scale) - w_px
    else:
      # Standard X axis: 0,0 is bottom-left, positive wx extends rightwards
      sx = wx * self.scale

    # World Y goes UP, Pygame screen Y goes down
    sy = self.height - ((wy - self.floor_height) * self.scale) - h_px
    return int(sx), int(sy)

  def update_display(self, lights: LightConfig):
    """Call this in your callback loop to refresh the visualizer window."""
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()

    self.screen.fill((25, 25, 35))  # Dark studio background
    font = pygame.font.SysFont(None, 24)

    # Draw Wall Headers
    lw_label = font.render("Left Wall", True, (180, 180, 180))
    rw_label = font.render("Right Wall", True, (180, 180, 180))
    self.screen.blit(lw_label, (self.width / 5, 20))
    self.screen.blit(rw_label, (4 * self.width / 5 - 100, 20))

    panels = lights.panels

    for name, (wx, wy, is_vertical) in self.layout.items():
      panel = getattr(panels, name, None)
      
      color = (panel.r, panel.g, panel.b)

      # Get coordinates and dimensions based on wall system
      screen_x, screen_y = self._world_to_screen(wx, wy, is_vertical, name)
      sw, sh = self._get_dimensions_px(is_vertical)

      # Draw panel rectangle and border
      rect = pygame.Rect(screen_x, screen_y, sw, sh)
      pygame.draw.rect(self.screen, color, rect)
      pygame.draw.rect(self.screen, (150, 150, 150), rect, 2)

      # Draw panel name inside
      lbl = font.render(name.upper(), True, (255, 255, 255))
      self.screen.blit(lbl, (screen_x + 6, screen_y + 6))

    pygame.display.flip()
    self.clock.tick(60)


# --- Example Integration Test ---
if __name__ == "__main__":
  rig = VirtualRig()

  # Quick test loop animating panel colors
  config = LightConfig()
  i = 0
  while True:
    i += 2
    config.panels.a.r = int((math.sin(math.radians(i)) + 1) * 127)
    config.panels.m.g = int((math.cos(math.radians(i)) + 1) * 127)

    rig.update_display(config)