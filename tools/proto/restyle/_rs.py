"""restyle.py's module, whether it was loaded as a script's neighbour ('restyle') or from tools/proto as
the package's ('restyle.restyle'): R, the one already loaded, so its caches and data are shared."""
import importlib, sys
R = sys.modules.get('restyle.restyle')
if R is None:
    R = importlib.import_module('restyle')
    if not hasattr(R, 'restyle_frames'):
        R = importlib.import_module('restyle.restyle')
