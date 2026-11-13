"""Public entry point for the conservative MODE0 full SoC regression."""
from pathlib import Path
import runpy
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('run_mode0.py')),run_name='__main__')
