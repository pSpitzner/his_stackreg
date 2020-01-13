import struct
import os
import re
import skimage
import numpy as np
from skimage import io
import utility as ut
from his_opener import HisOpener

os.chdir(os.path.dirname(__file__))

file_path = "/Volumes/exfat/experiments/paul/stacks/191218_3_div12_prestim.HIS"

his = HisOpener(file_path, skip_consistency_check=True)
his.check_consistency()

his.read_frame_average(200)


