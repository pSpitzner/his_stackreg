import numpy as np
from skimage import io
from his_opener import *

his_file = HisOpener(
    "~/owncloud/mpi/analysis/ub/dat/format_test_his.HIS", skip_consistency_check=False
)

# display file details
print(his_file.__dict__)

img = his_file.load_frame(0)
io.imshow(img)
