"""
Useful colormaps in the context of seismic data.

Author & Copyright: Dr. Thomas Hertweck, geophysics@email.de

License: GNU Lesser General Public License, Version 3
         https://www.gnu.org/licenses/lgpl-3.0.html
"""

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def seismic_blwr(version=1):
    """
    Seismic black-white-red colormap.

    Parameters
    ----------
    version : int, optional (default: 1)
        Which version to return. Version 1 equals Matplotlib's standard 'RdGy',
        while version 2 has a brighter 'red' component.

    Returns
    -------
    Colormap
    """
    if version == 1:
        return plt.get_cmap(name="RdGy")
    else:
        _seismic_blwr_colors = [[1, 0, 0], [1, 1, 1], [0, 0, 0]]
        _seismic_blwr_nodes = [0, 0.5019607843137255, 1.0]
        return LinearSegmentedColormap.from_list("seismic_blwr", list(zip(_seismic_blwr_nodes, _seismic_blwr_colors)))

#: Seismic black-white-red colormap.
cm_blwr = seismic_blwr()

def seismic_blwr_r(version=1):
    """
    Reversed seismic black-white-red colormap.

    Parameters
    ----------
    version : int, optional (default: 1)
        Which version to return. Version 1 equals Matplotlib's standard 'RdGy',
        while version 2 has a brighter 'red' component.

    Returns
    -------
    Colormap
    """
    return seismic_blwr(version=version).reversed()

#: Reversed seismic black-white-red colormap.
cm_blwr_r = seismic_blwr_r()

def seismic_bwr():
    """
    Seismic blue-white-red colormap.

    Returns
    -------
    Colormap
    """
    _seismic_bwr_colors = [[0, 0, 1], [1, 1, 1], [1, 0, 0]]
    _seismic_bwr_nodes = [0, 0.5019607843137255, 1.0]
    return LinearSegmentedColormap.from_list("seismic_bwr", list(zip(_seismic_bwr_nodes, _seismic_bwr_colors)))

#: Seismic blue-white-red colormap.
cm_bwr = seismic_bwr()

def seismic_bwr_r():
    """
    Reversed seismic blue-white-red colormap.

    Returns
    -------
    Colormap
    """
    return seismic_bwr().reversed()

#: Reversed seismic blue-white-red colormap.
cm_bwr_r = seismic_bwr_r()

def bwr(alpha=0.5):
    """
    Blue-white-red colormap with optional transparency in the center.

    Parameters
    ----------
    alpha : float, optional (default: 0.5)
        Transparency (alpha) value between 0 and 1.

    Returns
    -------
    Colormap
    """
    bwr_dict = {'red': ((0, 0, 0), (0.25, 0, 0), (0.5, 1, 1), (0.75, 0.8314, 0.8314), (1, 0.5, 0.5)),
                'green': ((0, 0, 0), (0.25, 0.375, 0.375), (0.5, 1, 1), (0.75, 0.375, 0.375), (1, 0, 0)),
                'blue': ((0, 0.5, 0.5), (0.25, 0.8314, 0.8314), (0.5, 1, 1), (0.75, 0, 0), (1, 0, 0)),
                'alpha': ((0, 1, 1), (0.5, alpha, alpha), (1, 1, 1)),}
    return LinearSegmentedColormap("bwr", bwr_dict)

def bwr_r(alpha=0.5):
    """
    Reversed blue-white-red colormap with optional transparency in the center.

    Parameters
    ----------
    alpha : float, optional (default: 0.5)
        Transparency (alpha) value between 0 and 1.

    Returns
    -------
    Colormap
    """
    return bwr(alpha=alpha).reversed()

def opendtect():
    """
    Seismic colormap similar to opendtect's default seismic colormap.

    Returns
    -------
    Colormap
    """
    _opendtect_colors = [[0.0078431372549020, 0.0078431372549020, 0.01568627450980392],
                         [0.1960784313725490, 0.2823529411764706, 0.50588235294117640],
                         [0.9529411764705882, 0.9490196078431372, 0.93725490196078430],
                         [1.0000000000000000, 0.7764705882352941, 0.00000000000000000],
                         [0.9921568627450981, 0.1058823529411765, 0.00000000000000000],
                         [0.6823529411764706, 0.0078431372549020, 0.00000000000000000]]
    _opendtect_nodes = [0, 0.13725490196078433, 0.5019607843137255, 0.7764705882352941, 0.9372549019607843, 1.0]
    return LinearSegmentedColormap.from_list("opendtect", list(zip(_opendtect_nodes, _opendtect_colors)))

#: Seismic colormap similar to opendtect's default seismic colormap.
cm_odtect = opendtect()

def opendtect_r():
    """
    Reversed seismic colormap similar to opendtect's default seismic colormap.

    Returns
    -------
    Colormap
    """
    return opendtect().reversed()

#: Reversed seismic colormap similar to opendtect's default seismic colormap.
cm_odtect_r = opendtect_r()

def seismic_clip():
    """
    Seismic colormap with clipped extreme values.

    Returns
    -------
    Colormap
    """
    _seismic_clip_colors = [[0.2235294117647059, 0.803921568627451, 0.8509803921568627],
                            [0.0000000000000000, 0.000000000000000, 1.0000000000000000],
                            [1.0000000000000000, 1.000000000000000, 1.0000000000000000],
                            [1.0000000000000000, 0.000000000000000, 0.0000000000000000],
                            [0.9333333333333333, 0.800000000000000, 0.2313725490196079]]
    _seismic_clip_nodes = [0, 0.00392156862745098, 0.5019607843137255, 0.996078431372549, 1.0]
    return LinearSegmentedColormap.from_list("seismic_clip", list(zip(_seismic_clip_nodes, _seismic_clip_colors)))

#: Seismic colormap with clipped extreme values.
cm_clip = seismic_clip()

def seismic_clip_r():
    """
    Reversed seismic colormap with clipped extreme values.

    Returns
    -------
    Colormap
    """
    return seismic_clip().reversed()

#: Reversed seismic colormap with clipped extreme values.
cm_clip_r = seismic_clip_r()

def banded():
    """
    Banded colormap.

    Returns
    -------
    Colormap
    """
    _banded_colors = [[0.5372549019607843, 0.0, 0.7764705882352941],
                      [0.0, 0.0, 0.45098039215686275],
                      [0.0, 0.0, 1.0],
                      [0.0, 0.1607843137254902, 0.5333333333333333],
                      [0.0, 0.5803921568627451, 1.0],
                      [0.0, 0.3137254901960784, 0.37254901960784315],
                      [0.0, 1.0, 1.0],
                      [0.0, 0.3843137254901961, 0.2549019607843137],
                      [0.5019607843137255, 1.0, 0.5019607843137255],
                      [0.3411764705882353, 0.4666666666666667, 0.0],
                      [1.0, 1.0, 0.0],
                      [0.47058823529411764, 0.34901960784313724, 0.0],
                      [1.0, 0.5098039215686274, 0.0],
                      [0.48627450980392156, 0.13725490196078433, 0.0],
                      [1.0, 0.0, 0.0],
                      [0.5058823529411764, 0.0, 0.0],
                      [0.7294117647058823, 0.0, 0.0],
                      [0.2901960784313726, 0.0, 0.0],
                      [0.5019607843137255, 0.0, 0.0]]
    _banded_nodes = [0.0, 0.054901960784313725, 0.10980392156862745,
                     0.16862745098039217, 0.2235294117647059, 0.2784313725490196,
                     0.3333333333333333, 0.38823529411764707, 0.44313725490196076,
                     0.5019607843137255, 0.5568627450980392, 0.611764705882353,
                     0.6666666666666666, 0.7215686274509804, 0.7803921568627451,
                     0.8352941176470589, 0.8901960784313725, 0.9450980392156862, 1.0]
    return LinearSegmentedColormap.from_list("banded", list(zip(_banded_nodes, _banded_colors)))

#: Banded colormap.
cm_banded = banded()

def banded_r():
    """
    Reversed banded colormap.

    Returns
    -------
    Colormap
    """
    return banded().reversed()

#: Reverse banded colormap.
cm_banded_r = banded_r()

def spectrum():
    """
    Spectrum colormap.

    Returns
    -------
    Colormap
    """
    _spectrum_colors = [[0.0, 0.5568627450980392, 1.0],
                        [0.0, 1.0, 1.0],
                        [1.0, 1.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [0.5019607843137255, 0.0, 0.0]]
    _spectrum_nodes = [0.0, 0.24313725490196078, 0.6274509803921569, 0.8784313725490196, 1.0]
    return LinearSegmentedColormap.from_list("spectrum", list(zip(_spectrum_nodes, _spectrum_colors)))

#: Spectrum colormap.
cm_spec = spectrum()

def spectrum_r():
    """
    Reversed spectrum colormap.

    Returns
    -------
    Colormap
    """
    return spectrum().reversed()

#: Reversed spectrum colormap.
cm_spec_r = spectrum_r()
