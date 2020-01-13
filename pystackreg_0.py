from pystackreg import StackReg
from skimage import io
import os

os.chdir(os.path.dirname(__file__))

# img0 = io.imread('some_multiframe_image.tif') # 3 dimensions : frames x width x height
img0 = io.concatenate_images(io.imread_collection('../dat/1/*.png'))

# we only use rigid body, gives: x shift, y shift, rotation
sr = StackReg(StackReg.RIGID_BODY)

# register each frame to the previous (already registered) one
# this is what the original StackReg ImageJ plugin uses
# out_previous = sr.register_transform_stack(img0, reference='previous')

# register to first image
out_first = sr.register_transform_stack(img0, reference='first')

for idx, png in enumerate(out_first):
    io.imsave(f"../dat/foo_{idx}.png", png)

# register to mean image
# out_mean = sr.register_transform_stack(img0, reference='mean')

# register to mean of first 10 images
# out_first10 = sr.register_transform_stack(img0, reference='first', n_frames=10)

# calculate a moving average of 10 images, then register the moving average to the mean of
# the first 10 images and transform the original image (not the moving average)
# out_moving10 = sr.register_transform_stack(img0, reference='first', n_frames=10, moving_average = 10)
