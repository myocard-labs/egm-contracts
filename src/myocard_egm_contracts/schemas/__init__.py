"""Schemas package marker.

Exists so `importlib.resources.files("myocard_egm_contracts.schemas")` works
for loading the .schema.json files at runtime. No Python code lives here —
the schemas are the .schema.json files alongside this module.
"""
