#
# Copyright (c) 2015-2016 Javier G. Orlandi <javierorlandi@javierorlandi.com>
# - Universitat de Barcelona, 2015-2016
# - University of Calgary, 2016
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Based on the HISReader of The Open Microscopy Environment
# http://www.openmicroscopy.org/site/support/bio-formats5.2/formats/hamamatsu-his.html
#

# Hamamatsu HIS ImageJ VirtualStack Opener
# ----------------------------------------
# This script quickly opens as a VirtualStack the typical HIS files generated with
# Hokawo and Hamamatsu Orca cameras (tested on Orca Flash 2.8 and 4.0 and Hokawo
# versions 2.5 and 2.8). Note that if the number of frames is large the stack
# might be corrupted towards the end of the file (you will see that if the image starts
# to "travel"). This is due to a change in metadata length inside the HIS file and cannot
# be easily avoided without a sequential opening.
#



import struct
import os


imp = "/Users/paul/owncloud/mpi/analysis/ub/dat/format_test_his.HIS"

f = open(imp, "rb")
f.seek(2)
print(f"offset {f.tell()}")
offset = struct.unpack("<h", f.read(2))[0]
f.seek(14)
print(f"frames {f.tell()}")
frames = struct.unpack("<I", f.read(4))[0]
f.seek(2)
print(f"comment_bytes {f.tell()}")
comment_bytes = struct.unpack("<h", f.read(2))[0]
print(f"width {f.tell()}")
width = struct.unpack("<h", f.read(2))[0]
print(f"height {f.tell()}")
height = struct.unpack("<h", f.read(2))[0]
struct.unpack("<I", f.read(4))[0]
print(f"file_type {f.tell()}")
file_type = struct.unpack("<h", f.read(2))[0]
f.read(50)

print(f"meta {f.tell()}")
metadata = f.read(comment_bytes)
metadataSplit = metadata.decode('utf-8').split(";")
meta = dict()
for it in metadataSplit:
    sp = it.split("=")
    if len(sp) > 1:
        meta[sp[0]] =  sp[1]


# The second image metadata
# That's the gap (in case it is different)
f.seek(offset + 64 + width * height * (file_type) + 2, 0)
print(f.read(10))
f.seek(offset + 64 + width * height * (file_type) + 2, 0)
gap = struct.unpack("<h", f.read(2))[0]
print(gap)

# Now let's check the metadata size across several frames to see if it's consistent
vals = range(1, frames, int(frames / 100))
md_old = gap
metadataInconsistency = 0
for it in range(0, len(vals)):
    if metadataInconsistency > 0:
        break
    cFrame = vals[it]
    if cFrame < 3:
        continue
    cPixel = (
        (width * height * (file_type) + gap + 64) * (cFrame - 2)
        + offset
        + 64
        + width * height * (file_type)
        + 2
    )
    f.seek(cPixel)
    md_new = struct.unpack("<h", f.read(2))[0]
    # print(md_new)
    if md_new != md_old:
        # Let's narrow the search
        nvals = range(vals[it - 1], vals[it] + 1)
        print(nvals)
        for it2 in range(0, len(nvals)):
            cFrame = nvals[it2]
            if cFrame < 3:
                continue
            cPixel = (
                (width * height * (file_type) + gap + 64) * (cFrame - 2)
                + offset
                + 64
                + width * height * (file_type)
                + 2
            )
            f.seek(cPixel)
            md_new = struct.unpack("<h", f.read(2))[0]
            print(md_new)
            if md_new != md_old:
                metadataInconsistency = cFrame
                offset = cPixel + gap
                gap = md_new
                break
            md_old = md_new
    md_old = md_new


def addMetadataEntry(name, val):
    return (
        "<tr><td style='padding:0 25px 0 0px;'><b>"
        + name
        + "</b></td><td>"
        + val
        + "</td></tr>"
    )


def beginMetadata():
    return "<table border=0 cellspacing=0>"


def endMetadata():
    return "</table>"

