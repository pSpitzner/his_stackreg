# About

[align_his_stackreg.py](align_his_stackreg.py) is simple python script to align ROIs (points) that were found on one dataset to the coordinate system of another dataset (for instance, a day later).

For now, in only works with propriatary Hamamtsu Hokawo `.his` image stacks but should
be easy to adapt.

The script roughly does the following

* load reference .his file and compute the average
* load reference regions of interest
* export an overview of this (red)
* load each .his file that needs moving (registering)
* find the transformation that is needed to match the file to the reference
* apply the same transformation on the original ROIs
* export an overview of the match (blue)
* export the registered rois

Hence, back in netcal, one can import the original .his stack without
alteration and load the ROIs produced by this script to get matching
ROIs across multi-day recordings.

[Demo images with aligned ROIs](https://makeitso.one/files/align_his_stackreg_output.zip)

# Dependencies

```
pip install numpy scikit-image matplotlib pystackreg
```

# Author Information
The importer to open the `.his` files is adapted from [Netcal](http://www.itsnetcal.com/) and the [Open Microscopy Environment](https://www.openmicroscopy.org/bio-formats/).

The registration and alignment uses [pystackreg](https://pypi.org/project/pystackreg/), a python implementation of [TurboReg](http://bigwww.epfl.ch/thevenaz/turboreg/)/[StackReg](http://bigwww.epfl.ch/thevenaz/stackreg/).

All credit goes to the respective original authors.
