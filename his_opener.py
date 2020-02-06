# ------------------------------------------------------------------------------ #
# @Author:        F. Paul Spitzner
# @Email:         paul.spitzner@ds.mpg.de
# @Created:       2020-01-17 15:42:14
# @Last Modified: 2020-02-06 14:06:13
# ------------------------------------------------------------------------------ #

import struct
import re
import os
import numpy as np


class HisOpener:
    """
        Helper class to open Hamamatsu .HIS files,
        frame by frame as a 2d numpy array that should work with scikit-image.
        Adapted from https://github.com/orlandi/hamamatsuOrcaTools
        and https://docs.openmicroscopy.org/bio-formats/5.9.2/formats/hamamatsu-his.html

        Not tested much.

        Attributes:
            head_offset : byte length of the propriatary Hamamatsu header
            base_offset : byte length of all infromation at the file beginning, before content of first frame starts
            frame_offset : byte length of all additional information (base_offset, for every except the first frame)
            img_size : total bytes of image data: w * h * pixel_size,
            num_frames : number of rames in the stack
            width :
            height :
            file_path :
            pixel_size : size of each pixel, in bytes
            pixel_type : e.g. 'uint8'

        Example:
            .. code-block:: python
                import numpy as np
                from skimage import io
                from his_opener import *

                his_file = HisOpener(
                    "~/testdir/testfile.HIS",
                    skip_consistency_check=False
                )

                # display file details
                print(his_file.__dict__)

                img = his_file.read_frame(0)
                io.imshow(img)
            ..

    """

    def __init__(self, file_path, skip_consistency_check=False):
        file_path = os.path.expanduser(file_path)
        # print(f"Opening .his file: {file_path}")
        f = open(file_path, "rb")

        # proprietary header
        f.seek(2)
        base_offset = struct.unpack("<h", f.read(2))[0]
        f.seek(4)
        width = struct.unpack("<h", f.read(2))[0]
        f.seek(6)
        height = struct.unpack("<h", f.read(2))[0]
        f.seek(12)
        pixel_size = struct.unpack("<h", f.read(2))[0]
        f.seek(14)
        num_frames = struct.unpack("<I", f.read(4))[0]

        # size of the propriatery header
        head_offset = 64

        # meta data
        f.seek(head_offset)
        meta_data = dict()
        # I guess utf-8 works
        meta_data_str = f.read(base_offset).decode("utf-8")
        tmp = re.search("@Hokawo@(.*)~Hokawo~", meta_data_str).group(1)
        for pair in tmp.split(";"):
            sp = pair.split("=")
            if len(sp) > 1:
                meta_data[sp[0]] = sp[1]

        # image size (actual pixels) in bytes
        img_size = width * height * pixel_size

        # first frame at pos 0 has different size, let's get the offset for all the others
        f.seek(base_offset + head_offset + img_size)
        # header begins after a check string "IM"
        check_string = f.read(2).decode("utf-8")
        # the short after the check string contains the offset to the next frame's header
        frame_offset = struct.unpack("<h", f.read(2))[0]

        # assign instance variables
        self.f = f
        self.head_offset = head_offset
        self.base_offset = base_offset
        self.frame_offset = frame_offset
        self.img_size = img_size
        self.num_frames = num_frames
        self.width = width
        self.height = height
        self.file_path = file_path
        self.pixel_size = pixel_size
        if pixel_size == 1:
            self.pixel_type = "uint8"
        else:
            self.pixel_type = "uint16"

        # self.meta_data_str = meta_data_str
        self.meta_data = meta_data
        self.f_is_open = True
        self.is_consistent = None
        if not skip_consistency_check:
            self.check_consistency()

        self.lookup_pos = None  # positions for f seek
        self.lookup_offset = None  # header size

    def get_frame_pos(self, i):
        """
            Helper function to get the position of a frame to supply to f.seek.
            To access the image data, the header still has to be skipped.

            Either uses the loopup table if check_consistency was performed or
            the simple way when meta data is (assumed) consistent
        """
        if self.lookup_pos is not None:
            return self.lookup_pos[i]
        if self.is_consistent is None or self.is_consistent == True:
            if i == 0:
                return 0
            else:
                foo = np.int64(i - 1) * (
                    self.frame_offset + self.head_offset + self.img_size
                ) + (self.base_offset + self.head_offset + self.img_size)
                return foo
        else:
            raise ValueError

    def check_consistency_slow(self):
        """
            Goes through all frames in the stack and checks the meta data size length.
            Creates a lookup table, so frames can be accessed even if meta data
            size varies.

            Takes about 10sec to check a 45GB file, loaded from SSD
        """
        print(f"Thorough check of {self.file_path}")
        if self.is_consistent is not None:
            return
        head_offset = self.head_offset
        old_offset = self.base_offset
        img_size = self.img_size

        lookup_pos = np.ones((self.num_frames), dtype=np.int64) * -1
        lookup_offset = np.ones((self.num_frames), dtype=np.int16) * -1
        inconsistent = 0
        pos = 0

        for i in range(0, self.num_frames):
            lookup_pos[i] = pos
            lookup_offset[i] = old_offset
            self.f.seek(pos)
            check_string = self.f.read(2).decode("utf-8")
            new_offset = struct.unpack("<h", self.f.read(2))[0]
            pos = pos + new_offset + head_offset + img_size
            if (i > 1 and i < self.num_frames - 1) and (
                check_string != "IM" or new_offset != old_offset
            ):
                inconsistent += 1
                print(
                    f"  Offset inconsistency at frame {i-1} -> {i}: "
                    + f"{old_offset} -> {new_offset}"
                )
            old_offset = new_offset
        self.is_consistent = inconsistent == 0
        self.lookup_pos = lookup_pos
        print(f"inconsistent {inconsistent}")

    def check_consistency(self):
        """
            Goes through some frames in the stack and checks the meta data size length.
            Creates a lookup table.
            However, if (unluckily) the changes in meta data size exactly compensate,
            this will not work and we will not detect it.
            When in doubt, use check_consistency_slow()
        """
        print(f"Quick check of {self.file_path}")
        head_offset = self.head_offset
        num_frames = self.num_frames
        img_size = self.img_size

        lookup_pos = np.ones((num_frames), dtype=np.int64) * -1
        lookup_offset = np.ones((num_frames), dtype=np.int16) * -1

        default_jump = 2000
        inconsistent = 0

        # take care of first frame
        self.f.seek(0)
        check_string = self.f.read(2).decode("utf-8")
        assert check_string == "IM"
        old_offset = struct.unpack("<h", self.f.read(2))[0]
        lookup_pos[0] = 0
        lookup_offset[0] = old_offset

        done = False
        last_good_frame_id = 0

        while not done:
            jump = default_jump
            frame_is_good = False

            while not frame_is_good:
                frame_id = last_good_frame_id + jump
                if frame_id >= num_frames:
                    frame_id = num_frames - 1
                    jump = num_frames - last_good_frame_id

                old_offset = lookup_offset[last_good_frame_id]
                pos = lookup_pos[last_good_frame_id]
                pos = pos + jump * (old_offset + head_offset + img_size)

                self.f.seek(pos)
                check_string = self.f.read(2).decode("utf-8")
                if check_string == "IM":
                    frame_is_good = True
                    new_offset = struct.unpack("<h", self.f.read(2))[0]
                    if new_offset != old_offset and last_good_frame_id > 0:
                        inconsistent += 1
                        print(
                            f"  Offset inconsistency at frame {frame_id}: "
                            + f"{old_offset} -> {new_offset}"
                        )
                    break
                else:
                    jump = int(np.fmax(1, jump / 2))
            lookup_pos[frame_id] = pos
            lookup_offset[frame_id] = new_offset
            last_good_frame_id = frame_id
            if last_good_frame_id == num_frames - 1:
                done = True

        # fill all remaining entries in the lookup tables
        checked = np.where(lookup_offset != -1)[0]
        for idx in range(1, len(checked)):
            start = checked[idx - 1]
            stop = checked[idx]
            offset = lookup_offset[start]
            lookup_offset[start:stop] = offset
            last_pos = lookup_pos[start]
            for j in range(start, stop):
                lookup_pos[j] = last_pos + np.int64(j - start) * (
                    offset + head_offset + img_size
                )

        self.is_consistent = inconsistent == 0
        self.lookup_offset = lookup_offset
        self.lookup_pos = lookup_pos

    # in case you dont want to keep the buffer open all the time
    def close_file(self):
        self.f.close()
        self.f_is_open = False

    def reopen_file(self):
        self.f = open(self.file_path, "rb")
        self.f_is_open = True

    def read_frame(self, frame):
        """
            Reads the frame at the provided index into a 2d numpy array
        """
        if not self.f_is_open:
            self.reopen_file()

        pos = self.get_frame_pos(frame)
        self.f.seek(pos)
        check_string = self.f.read(2).decode("utf-8")
        if check_string != "IM":
            # print("Invalid frame found. Run check_consistency to create the lookup table.")
            raise IndexError
        offset = struct.unpack("<h", self.f.read(2))[0]
        pos = int(pos + offset + self.head_offset)
        self.f.seek(pos)
        img = np.frombuffer(self.f.read(self.img_size), dtype=self.pixel_type)
        return img.reshape((self.width, self.height))

    def read_frame_stack(self, frames):
        """
            Reads multiple frames from file and returns a 3d numpy array
            frame_number * width * height
        """
        if not self.f_is_open:
            self.reopen_file()
        assert (frames >= 0).all() and (frames < self.num_frames).all()
        stack = np.empty(
            shape=(len(frames), self.width, self.height), dtype=self.pixel_type
        )

        for idx, i in enumerate(frames):
            try:
                stack[idx] = self.read_frame(i)
            except IndexError:
                self.check_consistency()
                stack[idx] = self.read_frame(i)

        return stack

    def read_frame_average(self, frames=200, func=np.nanmax):
        """
            Reads some frames from across the file and computes the average
            by using the provided funcion. defaul np.nanmax
        """

        try:
            assert not isinstance(frames, list)
            frames = float(frames)
            incr = int(np.fmax(1, self.num_frames / frames))
            frames = np.arange(0, self.num_frames, incr)
        except:
            assert isinstance(frames, np.ndarray)

        stack = self.read_frame_stack(frames)
        return func(stack, axis=0).astype(self.pixel_type)

    # printed representation
    def __repr__(self):
        return "<%s object at %s> use .__dict__ to get more details" % (
            self.__class__.__name__,
            hex(id(self)),
        )

    # used to compare instances in lists
    def __eq__(self, other):
        return self is other

    def __del__(self):
        self.f.close()
