from timeit import timeit

from lib.arion_lights import LightConfig

lights = LightConfig()

ligths2 = lights.copy()
ligths2.panels.a.setLight(255,255,255)
assert lights.panels.a.r == 0

setup = """
from copy import deepcopy
from lib.arion_lights import LightConfig 
lights = LightConfig()
"""

# print(timeit("deepcopy(lights)", setup, number=10000))
print(timeit("lights.copy()", setup, number=10000))