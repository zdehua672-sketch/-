# -*- coding: utf-8 -*-
from scientific_visualization_agent import VisualizationAgent
import inspect

for n in sorted(dir(VisualizationAgent)):
    if not n.startswith('_') and 'plot' in n:
        try:
            fn = getattr(VisualizationAgent, n)
            sig = inspect.signature(fn)
            print(f'{n}: {sig}')
        except Exception as e:
            print(f'{n}: ERROR {e}')