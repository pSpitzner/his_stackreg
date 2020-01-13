import numpy as np
import os


def paint_roi(col, row, width, img, channel=0, alpha=123):
    """
        add a square to the img to mark provided coordinate
    """
    row = int(row)
    col = int(col)
    d = int(np.floor(width / 2))
    grid = np.mgrid[col - d : col + d, row - d : row + d]
    grid[grid < 0] = 0
    grid[0][grid[0] >= img.shape[0]] = img.shape[0] - 1
    grid[1][grid[1] >= img.shape[1]] = img.shape[1] - 1
    for idx in range(0, grid.shape[1]):
        c = grid[0, idx]
        r = grid[1, idx]
        img[r, c, channel] = 255
        img[r, c, 3] = alpha


def cartesian_to_image_coordinates(x, y, width):
    col = x
    row = width - y + 1
    return col, row

def base_name(source_file, extension_delim="."):
    """
        only keep the last part of the folder hierarchy and remove the last extension
    """
    file_name = os.path.basename(source_file)
    # file_name = source_file.split(folder_delim)[-1]
    base_name = file_name.split(extension_delim)[:-1]
    if len(base_name) == 0:
        base_name.append(file_name)
    base_name = '.'.join(map(str, base_name))
    return base_name

def save_rois(fname, roi_id, x, y, roi_width, img_width=1024):
    """
        save in the format that works with netcal (legacy): id | x | y | roi_width
        netcal does not like floats fort the coordinates and
        comments have to be indicated with %
    """
    flagged = np.zeros_like(x, dtype=bool)
    flagged[np.where(x > img_width-roi_width/2)] = True
    flagged[np.where(y > img_width-roi_width/2)] = True
    flagged[np.where(x < roi_width/2)] = True
    flagged[np.where(y < roi_width/2)] = True
    for idx, roi in enumerate(roi_id[flagged]):
        print(f"ROI {roi} at {x[idx]} | {y[idx]} might be out of the image")
    out_dat = np.vstack((roi_id, x, y, np.ones_like(x) * roi_width)).T
    np.savetxt(fname, out_dat, fmt="%d,%.0f,%.0f,%d", header="ROI,X,Y,Width", comments="%"
    )
