"""
Publieke interface voor instrument-drivers.

Exporteert de belangrijkste klassen en biedt een simpele factory
op basis van *IDN?* zodat gebruikers niet hoeven te weten welk
concrete driver-class bij een instrument hoort.
"""
from .rigol_dg1022 import set_fixed_sine
from .rigol_dm3058e import measure_vrms, measure_vrms_n
from .hardware import open_instruments, close_instruments
 
__all__ = ["set_fixed_sine", "measure_vrms", "measure_vrms_n", "open_instruments", "close_instruments"]