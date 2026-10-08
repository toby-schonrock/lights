import sys
import time

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
        self.scale = width / 9  # px/m

        # bottom of screen is at floor height
        self.floor_height = 0.4

        # Panel physical dimensions in meters (62x82 cm)
        self.panel_w_m = 0.62
        self.panel_h_m = 0.82

        self.lights = LightConfig()

        def callback(lights: LightConfig):
            self.lights = lights

        self.callback = callback
        """Callback to save a light state"""

        # --- PERFORMANCE OPTIMIZATIONS: PRE-RENDER TEXT & STATIC GEOMETRY CACHE ---
        self.font = pygame.font.SysFont(None, 24)
        self.lw_label = self.font.render("Left Wall", True, (180, 180, 180))
        self.rw_label = self.font.render("Right Wall", True, (180, 180, 180))

        # Precompute positions, rects, and text labels once since panels never move
        self.panel_cache = {}
        for panel in self.lights.panels:
            name = panel.name
            is_vertical = panel.is_vertical
            wx, wy = panel.position

            screen_x, screen_y = self._world_to_screen(wx, wy, is_vertical, name)
            sw, sh = self._get_dimensions_px(is_vertical)

            self.panel_cache[name] = {
                "rect": pygame.Rect(screen_x, screen_y, sw, sh),
                "text_surface": self.font.render(name.upper(), True, (255, 255, 255)),
                "text_pos": (screen_x + 6, screen_y + 6),
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.screen.fill((25, 25, 35))  # Dark studio background

        # Blit static headers (Zero performance cost)
        self.screen.blit(self.lw_label, (self.width / 5, 20))
        self.screen.blit(self.rw_label, (4 * self.width / 5 - 100, 20))

        # High-speed loop: only handles color clamping and fast blitting
        for panel in lights.panels:
            name = panel.name
            cache = self.panel_cache.get(name)
            if not cache:
                continue

            color = (
                int(min(max(panel.r, 0), 255)),
                int(min(max(panel.g, 0), 255)),
                int(min(max(panel.b, 0), 255)),
            )

            # Draw precalculated panel rectangle, border, and cached text label
            pygame.draw.rect(self.screen, color, cache["rect"])
            pygame.draw.rect(self.screen, (150, 150, 150), cache["rect"], 2)
            self.screen.blit(cache["text_surface"], cache["text_pos"])

        pygame.display.flip()
        self.clock.tick(60)

    def run(self):
        """Blocking function which runs the display loop"""
        while True:
            if self.lights:
                self.update_display(self.lights)
            time.sleep(1 / 60)
