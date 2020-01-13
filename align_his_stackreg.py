# ------------------------------------------------------------------ #
# Align ROIs (points) that were found on one dataset to the coordinate
# system of another dataset (for instance, a day later)
#
# The script roughly does the following
# * load reference .his file and compute the average
# * load reference regions of interest
# * export an overview of this (red)
# * load each .his file that needs moving (registering)
# * find the transformation that is needed to match the file to the reference
# * apply the same transformation on the original ROIs
# * export an overview of the match (blue)
# * export the registered rois
#
# Hence, back in netcal, one can import the original .his stack without
# alteration and load the ROIs produced by this script to get matching
# ROIs across multi-day recordings.
# ------------------------------------------------------------------ #

# provide one image or his file as reference to which the others are aligned
ref_img_file = "I:/PAUL/191218_3_div10_prestim.HIS"

# provide the set of ROIs that were found in the ref_img_file
ref_roi_file = "D:/experiments/paul/register/dat/191218_3_div10_prestim_ROI_centers_everything.orig.roi.csv"

# the list of files for which aligned ROIs are wanted
mov_img_file_list = [
    "I:/PAUL/191218_3_div10_instim_off.HIS",
    "I:/PAUL/191218_3_div10_instim_on.HIS",
    "I:/PAUL/191218_3_div12_instim_on.HIS",
    "I:/PAUL/191218_3_div12_poststim.HIS",
    "I:/PAUL/191218_3_div12_prestim.HIS",
    "I:/PAUL/191218_3_div13_instim_on.HIS",
    "I:/PAUL/191218_3_div13_poststim.HIS",
    "I:/PAUL/191218_3_div13_pretstim.HIS",
    "I:/PAUL/191218_3_div15_instim_on.HIS",
    "I:/PAUL/191218_3_div15_poststim.HIS",
    "I:/PAUL/191218_3_div15_pretstim.HIS",
    "I:/PAUL/191218_3_div16_instim_on.HIS",
    "I:/PAUL/191218_3_div16_poststim.HIS",
    "I:/PAUL/191218_3_div16_pretstim.HIS",
    "I:/PAUL/191218_3_div8_instim_on.HIS",
    "I:/PAUL/191218_3_div8_instim_off.HIS",
    "I:/PAUL/191218_3_div8_prestim.HIS",
]

# where to save the aligned ROIs.
mov_roi_saveto = "D:/experiments/paul/register/dat/roi/"
# size of the square to assign to each roi
roi_width = 10

# where to save the image previews with aligned rois drawn.
# this folder is checked for existing files and if the target is found,
# it will not be overwritten. Therefore, you can just delete the incorrectly matched
# images and run again with different parameters
mov_img_saveto = "D:/experiments/paul/register/dat/img/"


# use only the first frame of each stack or compute an average. average takes longer
# as the whole stack might have to be checked but produces much better results.
use_average = True

# how many frames to draw from the whole stack (spread evenly from beginning to end)
frames_for_average = 1000

import numpy as np
import utility as ut

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
from skimage import exposure
from pystackreg import StackReg  # pip install pystackreg

import os
import os.path as op
from his_opener import HisOpener

try:
    import matplotlib
    import matplotlib.pyplot as plt

    plt.ioff()  # turn off interactive so figures dont pop up, show with plt.show()
except ImportError:
    plt = None

# check which files to produce
mov_roi_saveto_list = []
mov_img_saveto_list = []
mov_img_already_done = []
for idx, file in enumerate(mov_img_file_list):
    base = ut.base_name(file)
    roi_path = op.join(op.abspath(mov_roi_saveto), base) + "_roi.csv"
    img_path = op.join(op.abspath(mov_img_saveto), base) + "_roi.png"
    mov_roi_saveto_list.append(roi_path)
    mov_img_saveto_list.append(img_path)
    mov_img_already_done.append(op.exists(img_path))

# create output folders
os.makedirs(mov_img_saveto, mode=0o777, exist_ok=True)
os.makedirs(mov_roi_saveto, mode=0o777, exist_ok=True)

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

# increase the image contrast. this improved the results from stackreg drastically
# https://scikit-image.org/docs/dev/auto_examples/color_exposure/plot_equalize.html#sphx-glr-auto-examples-color-exposure-plot-equalize-py
p2, p98 = np.percentile(ref_img, (2, 98))
ref_img = exposure.rescale_intensity(ref_img, in_range=(p2, p98))
# ref_img = exposure.equalize_hist(ref_img)

# save the original rois just for good measure
x, y, i = ref_points[:].T
temp = op.join(op.abspath(mov_roi_saveto), ut.base_name(ref_img_file))
ut.save_rois(fname=f"{temp}_roi.csv", roi_id=i, x=x, y=y, roi_width=roi_width)

# quick and dirty, export the original for comparison
if plt is not None:
    ref_mask = np.zeros(shape=(width, height, 4), dtype="uint8")
    for point in ref_points:
        ut.paint_roi(point[0], point[1], roi_width, ref_mask, channel=0)

    # create a figure, this involves some ugly code to get rid of the borders
    bbox = matplotlib.transforms.Bbox(((0, 0), (width / 100, height / 100)))
    fig = plt.figure(figsize=(width / 100, height / 100))  # using 100 dpi
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    fig.add_axes(ax)
    # here we plot both things
    ax.imshow(ref_img, cmap="gray")
    ax.imshow(ref_mask)
    temp = op.join(op.abspath(mov_img_saveto), ut.base_name(ref_img_file))
    plt.savefig(f"{temp}_roi.png", bbox_inches=bbox, pad_inches=0.0, dpi=100)


# process every target stack
for idx, mov_img_path in enumerate(mov_img_file_list):
    if mov_img_already_done[idx]:
        print(f"Skipping {mov_img_path}")
        continue
    mov_his = HisOpener(mov_img_path, skip_consistency_check=True)
    if use_average:
        mov_img = mov_his.read_frame_average(frames_for_average)
    else:
        mov_img = mov_his.read_frame(0)
    del mov_his

    print(f"Aligning {mov_img_path}")

    # increase the image contrast. this improved the results from stackreg drastically
    p2, p98 = np.percentile(mov_img, (2, 98))
    mov_img = exposure.rescale_intensity(mov_img, in_range=(p2, p98))

    # find the transformation matrix
    # we only use rigid body, gives: x shift, y shift, rotation
    sreg = StackReg(StackReg.RIGID_BODY)
    tmat = sreg.register(ref=ref_img, mov=mov_img)

    # if average_over_experiments:
    #     out_img = sreg.transform(mov=mov_img, tmat=tmat)
    #     ref_img = np.mean([ref_img, out_img], axis=0)

    # apply the matrix to the old ROIs
    # this is essentially just:
    # src = np.vstack((x, y, np.ones_like(x)))
    # dst = src.T @ matrix.T
    mov_points = np.copy(ref_points)
    mov_points[:, 0:2] = tf.matrix_transform(coords=ref_points[:, 0:2], matrix=tmat)

    # save in netcals image format. import via "load roi (legacy)"
    x, y, i = mov_points[:].T
    ut.save_rois(
        fname=mov_roi_saveto_list[idx], roi_id=i, x=x, y=y, roi_width=roi_width
    )

    # plot to check if alignment worked and compare
    if plt is not None:
        mov_mask = np.zeros(shape=(width, height, 4), dtype="uint8")
        for point in mov_points:
            ut.paint_roi(point[0], point[1], roi_width, mov_mask, channel=2)

        # create a figure, this involves some ugly code to get rid of the borders
        bbox = matplotlib.transforms.Bbox(((0, 0), (width / 100, height / 100)))
        fig = plt.figure(figsize=(width / 100, height / 100))  # using 100 dpi
        ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
        ax.set_axis_off()
        fig.add_axes(ax)
        # but here we plot both things
        ax.imshow(mov_img, cmap="gray")
        ax.imshow(mov_mask)
        plt.savefig(
            f"{mov_img_saveto_list[idx]}", bbox_inches=bbox, pad_inches=0.0, dpi=100
        )


# to transform an image
# tform = tf.AffineTransform(matrix=tmat)
# new_image = tf.warp(old_image, tform)
