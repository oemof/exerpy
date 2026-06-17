"""
Solar thermal components: heliostat field, parabolic trough, and solar tower.

These components are currently produced only by the Ebsilon parser
(:meth:`exerpy.ExergyAnalysis.from_ebsilon`). They rely on synthetic ``<name>_Q`` solar heat
connections created by that parser; the TESPy and Aspen parsers do not yet emit them.
"""

# Effective temperature of the sun's photosphere [K]. Used to convert solar radiation to
# exergy via the Petela/Spanner factor: alpha = 1 - (4/3) * T0 / T_SUN.
T_SUN = 5778.0
