import os
import sys
# Add language-tools to path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
from . import config

cfg = config.Config()

for d in [cfg.run_dir, cfg.tmp_dir]:
    if not os.path.isdir(d):
        os.makedirs(d)

