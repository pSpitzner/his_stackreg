# ------------------------------------------------------------------ #
# Uses his_opener to load the first frame of each .HIS stack.
# Then use stackreg to align them to the chosen reference image
# and obtains the transformations to apply on provided extracted ROIs
#
# ------------------------------------------------------------------ #

import numpy as np

# provide one image or his file as reference to which the others are aligned
ref_img_file = "/Volumes/exfat/experiments/paul/stacks/191218_3_div12_prestim.HIS"

# provide the set of ROIs that were found in the ref_img_file
ref_roi_file = "/Volumes/exfat/experiments/paul/stacks/191218_3_div10_instim_off_ROI_centers_everything_image.csv"

# the list of files for which aligned ROIs are wanted
mov_img_file_list = [
    "/Volumes/exfat/experiments/paul/stacks/191218_3_div12_instim_on.HIS",
    "/Volumes/exfat/experiments/paul/stacks/191218_3_div12_poststim.HIS",
    "/Volumes/exfat/experiments/paul/stacks/191218_3_div13_instim_on.HIS",
]

# where to save the aligned ROIs.
mov_roi_save_to = "/Volumes/exfat/experiments/paul/stacks/roi/"

# where to save the image previews with aligned rois drawn
# this folder is checked for existing files and if the target is found,
# it will not be overwritten. Therefore, you can just delete the incorrectly matched
# images and run again with different parameters
mov_img_save_to = "/Volumes/exfat/experiments/paul/stacks/img/"


# use only the first frame of each stack or compute an average. average takes longer
# as the whole stack might have to be checked. In my tests, the check took around
# 10sec for a 45GB from SSD, from HD avoid this
use_average = True
# frames_for_average = 'auto'
frames_for_average = np.arange(0, 100)

# load the regions of interest. we are using image coordinates!
ref_roi_dat = np.loadtxt(ref_roi_file, delimiter=",", skiprows=1)
cols = ref_roi_dat[:, 2]  # image coordinates, left to right
rows = ref_roi_dat[:, 1]  # image coordinates, top to bottom
roid = ref_roi_dat[:, 0]  # id of the region of interest
# to transform from netcals cartestian coordinates, you can do this:
# cols, rows = ut.cartesian_to_image_coordinates(x=ref_roi_dat[:, 1], y=ref_roi_dat[:, 2], width=1024)

# ------------------------------------------------------------------ #
# main script
# ------------------------------------------------------------------ #

from skimage import io
from skimage import transform as tf
from pystackreg import StackReg  # pip install pystackreg

import utility as ut
import os.path as op
from his_opener import HisOpener

try:
    import matplotlib
    import matplotlib.pyplot as plt

    plt.ioff()  # turn off interactive so figures dont pop up, show with plt.show()
except ImportError:
    plt = None

# check which files to produce
mov_roi_save_to_list = []
mov_img_save_to_list = []
mov_img_already_done = []
for idx, file in enumerate(mov_img_file_list):
    base = ut.base_name(file)
    roi_path = op.join(op.abspath(mov_roi_save_to), base) + "_roi.csv"
    img_path = op.join(op.abspath(mov_img_save_to), base) + "_roi.png"
    mov_roi_save_to_list.append(roi_path)
    mov_img_save_to_list.append(img_path)
    mov_img_already_done.append(op.exists(img_path))

# create list of points from the original ROIs
ref_points = np.vstack((cols, rows, roid)).T

# load source image
ref_his = HisOpener(ref_img_file, skip_consistency_check=True)
if use_average:
    ref_img = ref_his.read_frame_average(frames_for_average)
else:
    ref_img = ref_his.read_frame(0)
width = ref_his.width
height = ref_his.height

# meh quick and dirty
if plt is not None:
    ref_mask = np.zeros(shape=(width, height, 4), dtype="uint8")
    for point in ref_points:
        ut.paint_roi(point[0], point[1], 20, ref_mask, channel=0)

    # create a figure, this involves some ugly code to get rid of the borders
    bbox = matplotlib.transforms.Bbox(((0, 0), (width / 100, height / 100)))
    fig = plt.figure(figsize=(width / 100, height / 100))  # using 100 dpi
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    fig.add_axes(ax)
    # here we plot both things
    ax.imshow(ref_img, cmap="gray")
    ax.imshow(ref_mask)
    temp = op.join(op.abspath(mov_img_save_to), ut.base_name(ref_img_file))
    plt.savefig(f"{temp}.png", bbox_inches=bbox, pad_inches=0.0, dpi=100)

# save the original rois just for good measure

# process every target stack
for idx, file_path in enumerate(mov_img_file_list):
    if mov_img_already_done[idx]:
        print(f"Skipping {file_path}")
        continue
    mov_his = HisOpener(file_path, skip_consistency_check=True)
    if use_average:
        mov_img = mov_his.read_frame_average(frames_for_average)
    else:
        mov_img = mov_his.read_frame(0)
    del mov_his

    print(f"Aligning {file_path}")

    # find the transformation matrix
    # we only use rigid body, gives: x shift, y shift, rotation
    sreg = StackReg(StackReg.RIGID_BODY)
    tmat = sreg.register(ref=ref_img, mov=mov_img)

    # apply the matrix to the old ROIs
    # this is essentially just:
    # src = np.vstack((x, y, np.ones_like(x)))
    # dst = src.T @ matrix.T
    mov_points = np.copy(ref_points)
    mov_points[:, 0:2] = tf.matrix_transform(coords=ref_points[:, 0:2], matrix=tmat)

    # save in the format that works with netcal (legacy): id | x | y | roi_width
    x, y, i = mov_points[:].T
    out_dat = np.vstack((i, x, y, np.ones_like(x) * 10)).T
    np.savetxt(
        f"{out_path}.roi.csv", out_dat, fmt="%d,%.2f,%.2f,%d", header="ROI,X,Y,Width"
    )

    # plot to check if alignment worked and compare
    if plt is not None:
        mov_mask = np.zeros(shape=(width, height, 4), dtype="uint8")
        for point in mov_points:
            ut.paint_roi(point[0], point[1], 20, mov_mask, channel=2)

        # create a figure, this involves some ugly code to get rid of the borders
        bbox = matplotlib.transforms.Bbox(((0, 0), (width / 100, height / 100)))
        fig = plt.figure(figsize=(width / 100, height / 100))  # using 100 dpi
        ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
        ax.set_axis_off()
        fig.add_axes(ax)
        # but here we plot both things
        ax.imshow(mov_img, cmap="gray")
        ax.imshow(mov_mask)
        plt.savefig(f"{out_path}.png", bbox_inches=bbox, pad_inches=0.0, dpi=100)


# to transform an image
# tform = tf.AffineTransform(matrix=tmat)
# new_image = tf.warp(old_image, tform)
