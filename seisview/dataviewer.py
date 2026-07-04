"""
Interactive seismic data visualization.

Author & Copyright: Dr. Thomas Hertweck, geophysics@email.de

License: GNU General Public License, Version 3
         https://www.gnu.org/licenses/gpl-3.0.html
"""

import argparse
import ast
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import seisio
import threading
import tkinter as tk

from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import MultipleLocator, AutoLocator, MaxNLocator
from tkinter import ttk
# from ttkbootstrap_icons_fa import FAIcon
from ttkbootstrap_icons_bs import BootstrapIcon
from tktooltip import ToolTip

from . import __version__, __author__
from . import colormaps as cm


###############################################################################
# DataViewer
###############################################################################

class DataViewer:
    def __init__(self, root):
        """Initialize DataViewer class."""
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.root = root
        self.root.geometry("1400x900")

        # # set a base Tkinter scaling factor if on Linux/Unix
        # # (Windows ignores this if DPI awareness level 2 is active)
        # dpi = 0
        # try:
        #     # query the actual screen DPI using inches
        #     dpi = self.root.winfo_fpixels('1i')
        #     # set Tkinter's internal scaling factor (72 points per inch is standard)
        #     self.root.tk.call("tk", "scaling", dpi / 72.0)
        # except Exception:
        #     pass
        self.default_font = tk.font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Arial", weight="bold")

        # if dpi == 0:
        #     dpi = 96.0
        # scaling_factor = dpi / 96.0
        # self.log.debug("scaling_factor: %.2f", scaling_factor)
        # base_size = 12
        # scaled_size = int(round(base_size * scaling_factor))
        # self.log.debug("scaled_size: %d", scaled_size)
        # rcParams["font.size"] = scaled_size           # sets fallback default
        # rcParams["axes.titlesize"] = scaled_size + 2  # plot title size
        # rcParams["axes.labelsize"] = scaled_size      # x and y label size
        # rcParams["xtick.labelsize"] = scaled_size - 1 # axis tick numbers
        # rcParams["ytick.labelsize"] = scaled_size - 1
        # rcParams["lines.linewidth"] = 1.5 * scaling_factor
        rcParams["grid.color"] = "black"
        rcParams["grid.linestyle"] = "-"
        rcParams["grid.linewidth"] = 1

        # dpi = self.root.winfo_fpixels('1i')
        # scaling_factor = dpi / 96.0
        # base_size = 12
        # calculated_font_size = int(round(base_size * scaling_factor))
        # self.default_font = tk.font.nametofont("TkDefaultFont")
        # self.default_font.configure(size=calculated_font_size, family="Arial")
        # tk.font.nametofont("TkTextFont").configure(size=calculated_font_size)
        # tk.font.nametofont("TkCaptionFont").configure(size=calculated_font_size + 2, weight="bold")

        self.root.title(f"Interactive Seismic Data Viewer v{__version__} by {__author__}")
        # initialize variables
        self.sio = None
        self.ens_keys = []
        self.ensemble = None
        self.df = None
        self.t = None
        self.dt = None
        self.delay = None
        # I/O options
        self.filetype = None
        self.endian = None
        self.thdef = None
        self.format = None
        self.thext1 = False
        self.ntxtrec = None
        self.ntxtrail = None
        # plot-related variables
        self.fig = None
        self.ax = None
        self.canvas = None
        self.imshow = None
        self.cbar = None
        self.cbar_visible = tk.BooleanVar(value=True)
        self.wiggle = tk.BooleanVar(value=False)
        self.wiggle_hires = tk.BooleanVar(value=False)
        self.toolbar = None
        self.xlabel = None
        self.ylabel = None
        self.title = None
        self.clabel = None
        self.clabelpad = 0
        self.cbarbins = "auto"
        self.vmin = ""
        self.vmax = ""
        self.hmajorticks = ""
        self.hminorticks = ""
        self.vmajorticks = ""
        self.vminorticks = ""
        self.wiggleskip = 1
        self.wigglexcur = 1
        self.wiggle_lcolor = "black"
        self.wiggle_fill = "black"
        self.wiggle_negfill = ""
        self.wigglelw = 1
        self.perc_str = tk.StringVar(value="99.0")
        self.gather_options = ["FLDR / TRACF", "FLDR / OFFSET", "CDP / CDPT", "CDP / OFFSET",
                               "CDP", "XLINE / ILINE", "ILINE / XLINE",
                               "XLINE / ILINE / OFFSET", "ILINE / XLINE / OFFSET"]
        self.cmap_options = ["seismic", "Greys", "black-white-red", "red-white-black", "blue-white-red",
                             "red-white-blue", "opendtect", "opendtect-reversed", "clip", "clip-reversed",
                             "banded", "banded-reversed", "spectrum", "spectrum-reversed"]
        self.cmap_calls = ["seismic", "Greys", cm.seismic_blwr(version=2), cm.seismic_blwr_r(version=2),
                     cm.seismic_bwr(), cm.seismic_bwr_r(), cm.opendtect(), cm.opendtect_r(),
                     cm.seismic_clip(), cm.seismic_clip_r(), cm.banded(), cm.banded_r(),
                     cm.spectrum(), cm.spectrum_r()]
        # status updates
        self.red_style = ttk.Style()
        self.red_style.configure("RedText.TLabel", foreground="red")
        self.black_style = ttk.Style()
        self.black_style.configure("BlackText.TLabel", foreground="black")
        self.blue_style = ttk.Style()
        self.blue_style.configure("BlueText.TLabel", foreground="blue")
        self.green_style = ttk.Style()
        self.green_style.configure("GreenText.TLabel", foreground="green")
        # GUI layout setup
        # self._create_widgets(dpi)
        self._create_widgets()

    def _format_coord(self, x,y):
        if not self.imshow:
            return ""
        nt, ns = self.ensemble["data"].shape
        if self.h[-1] == self.h[0]:
            col_idx = 0
        else:
            # map physical X to column index
            col_pct = (x - self.h[0]) / (self.h[-1] - self.h[0])
            col_idx = int(round(col_pct * (nt - 1)))
        # map physical Y to row index
        row_pct = (y - self.t[0]) / (self.t[-1] - self.t[0])
        row_idx = int(round(row_pct * (ns - 1)))
        # boundary check to avoid IndexError when hovering near edges
        if 0 <= col_idx < nt and 0 <= row_idx < ns:
            amp = self.ensemble["data"].T[row_idx,col_idx]
            return f"V: {y:.3f} | H: {x:.3f}\nData[{col_idx},{row_idx}]: {amp:.3f}"
        return ""

    # def _create_widgets(self, dpi):
    def _create_widgets(self):
        """Create all GUI widgets."""
        class FilteredCombobox(ttk.Combobox):
            def set_completion_list(self, completion_list):
                self._completion_list = sorted(completion_list,
                                               key=lambda item: tuple(map(ast.literal_eval, item.strip().split(","))))
                self['values'] = self._completion_list
                self.bind('<KeyRelease>', self.check_input)

            def check_input(self, event):
                if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Shift_L", "Control_L"):
                    return
                typed = self.get().strip()

                if typed == "":
                    # if empty, show the entire sorted list
                    self["values"] = self._completion_list
                else:
                    # multi-character 'contains' filtering
                    filtered_hits = [element for element in self._completion_list if typed.lower() in element.lower()]
                    self["values"] = filtered_hits

                # keep the dropdown open so they see the matches
                self.event_generate('<Down>')
                # focus stays in entry field and cursor put back behind last character
                self.after(10, self._restore_focus)

            def _restore_focus(self):
                """Helper to safely reclaim focus after the OS opens the listbox."""
                self.focus_set()
                self.icursor(tk.END)

        class CustomToolbar(NavigationToolbar2Tk):
            """Customized Matplotlib toolbar."""
            # Only keep Home, Back, Forward, Pan, Zoom, and Save
            # Format: (Name, Tooltip, Icon_File_Name, Method_Name)
            toolitems = (
                ('Home', 'Reset original view', 'home', 'home'),
                ('Back', 'Back to previous view', 'back', 'back'),
                ('Forward', 'Forward to next view', 'forward', 'forward'),
                (None, None, None, None),  # Divider line
                ('Pan', 'Left button pans, Right button zooms', 'move', 'pan'),
                ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
                (None, None, None, None),
                ('Save', 'Save the figure', 'filesave', 'save_figure'),
                (None, None, None, None),
            )

        # top control panel
        control_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # open_img = FAIcon("folder-open", size=25, style="solid")
        open_img = BootstrapIcon("folder2-open", size=25, style="outline")
        self.open_btn = ttk.Button(control_frame, image=open_img.image, command=self._open_file)
        ToolTip(self.open_btn, msg="Open file", delay=1.0)
        self.open_btn.pack(side=tk.LEFT, padx=10, pady=5)

        # openopt_img = BootstrapIcon("gear", size=20, style="outline")
        # openopt_img = BootstrapIcon("tools", size=20, style="outline")
        openopt_img = BootstrapIcon("wrench", size=25, style="outline")
        self.openopt_btn = ttk.Button(control_frame, image=openopt_img.image, command=self._open_options)
        ToolTip(self.openopt_btn, msg="seisio options to open file", delay=1.0)
        self.openopt_btn.pack(side=tk.LEFT, padx=(0, 5), pady=5)

        # info_img = FAIcon("circle-info", size=25, style="solid")
        # info_img = BootstrapIcon("info-circle", size=25, style="outline")
        info_img = BootstrapIcon("binoculars", size=25, style="outline")
        self.info_btn = ttk.Button(control_frame, image=info_img.image, command=self._info_file)
        ToolTip(self.info_btn, msg="Trace header preview", delay=1.0)
        self.info_btn.pack(side=tk.LEFT, padx=(5, 5), pady=5)
        self.info_btn.configure(state="disabled")

        separator_1 = ttk.Separator(control_frame, orient="vertical")
        separator_1.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.gather_cbo = ttk.Combobox(control_frame, values=self.gather_options)
        ToolTip(self.gather_cbo, msg="Ensemble lookup keys", delay=1.0)
        self.gather_cbo.current(0)
        self.gather_cbo.pack(side=tk.LEFT, padx=(5, 10), pady=5)
        self.gather_cbo["state"] = "disabled"
        self.gather_cbo.bind("<<ComboboxSelected>>", self._gather_select)
        # self.gather_cbo.bind("<KeyRelease>", self._gather_select)
        self.gather_cbo.bind("<FocusOut>", self._gather_select)

        # index_img = FAIcon("arrow-down-short-wide", size=25, style="solid")
        # index_img = FAIcon("sort", size=25, style="solid")
        # index_img = BootstrapIcon("sort-up", size=25, style="outline")
        # index_img = BootstrapIcon("file-bar-graph", size=25, style="outline")
        # index_img = BootstrapIcon("key", size=25, style="outline")
        index_img = BootstrapIcon("list-ul", size=25, style="outline")
        # index_img = BootstrapIcon("clipboard-data", size=25, style="outline")
        self.index_btn = ttk.Button(control_frame, image=index_img.image, command=self._create_index)
        ToolTip(self.index_btn, msg="Create lookup index", delay=1.0)
        self.index_btn.pack(side=tk.LEFT, padx=(0, 5), pady=5)
        self.index_btn.configure(state="disabled")

        separator_2 = ttk.Separator(control_frame, orient="vertical")
        separator_2.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.keys_cbo = FilteredCombobox(control_frame)
        ToolTip(self.keys_cbo, msg="List of ensembles", delay=1.0)
        self.keys_cbo.set_completion_list(self.ens_keys)
        self.keys_cbo.pack(side=tk.LEFT, padx=(5, 10), pady=5)
        self.keys_cbo["state"] = "disabled"

        # load_img = FAIcon("paintbrush", size=25, style="solid")
        # load_img = BootstrapIcon("caret-right-square", size=25, style="outline")
        # load_img = BootstrapIcon("paint-bucket", size=25, style="outline")
        # load_img = BootstrapIcon("brush", size=25, style="outline")
        load_img = BootstrapIcon("image", size=25, style="outline")
        # load_img = BootstrapIcon("file-image", size=25, style="outline")
        self.load_btn = ttk.Button(control_frame, image=load_img.image, command=self._load_data)
        ToolTip(self.load_btn, msg="Load and display ensemble", delay=1.0)
        self.load_btn.pack(side=tk.LEFT, padx=(0, 5), pady=5)
        self.load_btn.configure(state="disabled")

        redraw_img = BootstrapIcon("arrow-counterclockwise", size=25, style="outline")
        redraw_btn = ttk.Button(control_frame, image=redraw_img.image, command=self._redraw)
        ToolTip(redraw_btn, msg="Redraw the canvas", delay=1.0)
        redraw_btn.pack(side=tk.LEFT, padx=(5, 5), pady=5)

        separator_3 = ttk.Separator(control_frame, orient="vertical")
        separator_3.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # exit_img = FAIcon("door-open", size=25, style="solid")
        exit_img = BootstrapIcon("door-open", size=25, style="outline")
        exit_btn = ttk.Button(control_frame, image=exit_img.image, command=self.root.destroy)
        ToolTip(exit_btn, msg="Exit", delay=1.0)
        exit_btn.pack(side=tk.RIGHT, padx=10, pady=5)

        self.status_lbl = ttk.Label(control_frame, text="Please open a SEGY/SU file to begin.", style="RedText.TLabel")
        self.status_lbl.pack(side=tk.RIGHT, padx=10)

        # main Plotting Area
        # self.fig, self.ax = plt.subplots(1, 1, dpi=dpi)
        self.fig, self.ax = plt.subplots(1, 1)
        self.fig.subplots_adjust(top=0.97, bottom=0.06, left=0.05, right=0.95)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = CustomToolbar(self.canvas, self.root)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # put the following widgets in the toolbar

        self.perc_slid = ttk.Scale(self.toolbar, from_=50.0, to=100.0, orient=tk.HORIZONTAL,
                                   length=160, command=self._perc_on_scale_drag)
        ToolTip(self.perc_slid, msg="Percentile clip", delay=1.0)
        self.perc_slid.set(99.0)
        self.perc_slid.pack(side=tk.LEFT, padx=(10, 5))
        # trigger update ONLY when the user releases the mouse button on the slider
        self.perc_slid.bind("<ButtonRelease-1>", self._perc_on_scale_release)
        self.perc_entry = ttk.Entry(self.toolbar, textvariable=self.perc_str, width=7, justify="center")
        self.perc_entry.pack(side=tk.LEFT, padx=(5, 10))
        # trigger update ONLY when the user presses the Enter key inside the text box
        self.perc_entry.bind("<Return>", self._perc_on_enter_pressed)

        toolbar_divider_1 = ttk.Separator(self.toolbar, orient="vertical")
        toolbar_divider_1.pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.wiggle_cbx = ttk.Checkbutton(self.toolbar, text="Wiggle?", compound="right", variable=self.wiggle, command=self._wiggle_toggle)
        ToolTip(self.wiggle_cbx, msg="Use wiggle display", delay=1.0)
        self.wiggle_cbx.pack(side=tk.LEFT, padx=(10, 5))

        self.cbar_cbx = ttk.Checkbutton(self.toolbar, text="Colorbar?", compound="right", variable=self.cbar_visible, command=self._cbar_toggle)
        ToolTip(self.cbar_cbx, msg="Display colorbar", delay=1.0)
        self.cbar_cbx.pack(side=tk.LEFT, padx=(5, 10))

        toolbar_divider_2 = ttk.Separator(self.toolbar, orient="vertical")
        toolbar_divider_2.pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.cmap_cbo = ttk.Combobox(self.toolbar, values=self.cmap_options)
        ToolTip(self.gather_cbo, msg="Colormap", delay=1.0)
        self.cmap_cbo.current(0)
        self.cmap_cbo.pack(side=tk.LEFT, padx=10)
        self.cmap_cbo.bind("<<ComboboxSelected>>", self._change_colormap)
        self.cmap_cbo.bind("<FocusOut>", self._change_colormap)

        toolbar_divider_3 = ttk.Separator(self.toolbar, orient="vertical")
        toolbar_divider_3.pack(side=tk.LEFT, fill=tk.Y, padx=2)

        # edit_img = FAIcon("gear", size=20, style="solid")
        # edit_img = BootstrapIcon("gear", size=20, style="outline")
        # edit_img = BootstrapIcon("tools", size=20, style="outline")
        edit_img = BootstrapIcon("palette", size=20, style="outline")
        # edit_img = BootstrapIcon("wrench", size=20, style="outline")
        self.edit_btn = ttk.Button(self.toolbar, image=edit_img.image, command=self._plot_options)
        ToolTip(self.edit_btn, msg="Plot options", delay=1.0)
        self.edit_btn.pack(side=tk.LEFT, padx=10)

        self.toolbar.update()

    def _open_options(self):
        """Display open options for seisio."""
        popup = tk.Toplevel(self.root)
        popup.title("Seisio options")
        # popup.geometry("300x180")
        popup.resizable(False, False)

        popup.grab_set()

        filetype_options = ["AUTOMATIC", "SEG-Y", "SU"]
        ttk.Label(popup, text="Type of input file:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        filetype_cbo = ttk.Combobox(popup, values=filetype_options)
        ToolTip(filetype_cbo, msg="Select type of input file", delay=1.0)
        filetype_cbo.current(0)
        filetype_cbo.grid(row=0, column=1, padx=10, pady=5)
        filetype_cbo["state"] = "readonly"
        # filetype_cbo.bind("<<ComboboxSelected>>", self._filetype_select)

        endianess_options = ["AUTOMATIC", "BIG ENDIAN", "LITTLE ENDIAN"]
        ttk.Label(popup, text="Endianess of input file:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        endianess_cbo = ttk.Combobox(popup, values=endianess_options)
        ToolTip(endianess_cbo, msg="Select endianess of input file", delay=1.0)
        endianess_cbo.current(0)
        endianess_cbo.grid(row=1, column=1, padx=10, pady=5)
        filetype_cbo["state"] = "readonly"

        def select_thdef():
            """Select trace header definition table."""
            thdef_path = tk.filedialog.askopenfilename(parent=popup, filetypes=[("Trace header definition table", "*.json"), ("All files", "*")])
            if not thdef_path:
                return
            thdef_entry.insert(0, thdef_path)
            # popup.lift()
            # popup.focus_force()

        ttk.Label(popup, text="Trace header definition table:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        thdef_entry = ttk.Entry(popup, width=25)
        thdef_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        thdef_btn = ttk.Button(popup, text="Select file", command=select_thdef)
        thdef_btn.grid(row=3, column=1, padx=10, pady=5)

        info_lbl = ttk.Label(popup, text="The following entries hold for SEG-Y files only:", justify="center")
        info_lbl.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        format_options = ["AUTOMATIC",
                          "1 :: 4-byte IBM float",
                          "2 :: 4-byte two's complement integer",
                          "3 :: 2-byte two's complement integer",
                          "5 :: 4-byte IEEE floating-point",
                          "6 :: 8-byte IEEE floating-point",
                          "8 :: 1-byte two's complement integer",
                          "9 :: 8-byte two's complement integer",
                          "10 :: 4-byte unsigned integer",
                          "11 :: 2-byte unsigned integer",
                          "12 :: 8-byte unsigned integer",
                          "16 :: 1-byte unsigned integer"]
        ttk.Label(popup, text="SEG-Y data format:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        format_cbo = ttk.Combobox(popup, values=format_options)
        ToolTip(filetype_cbo, msg="Select the SEG-Y data format", delay=1.0)
        format_cbo.current(0)
        format_cbo.grid(row=5, column=1, padx=10, pady=5)
        format_cbo["state"] = "readonly"

        thext1_bool = tk.BooleanVar(value=False)
        ttk.Label(popup, text="Trace header extension 1 used?").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        thext1_chk = tk.Checkbutton(popup, text="", variable=thext1_bool)
        ToolTip(thext1_chk, msg="Tick for 'yes'", delay=1.0)
        thext1_chk.grid(row=6, column=1, padx=10, pady=5)

        ttk.Label(popup, text="No. of add. textual header records:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        txtrec_entry = ttk.Entry(popup, width=25)
        ToolTip(txtrec_entry, msg="Enter integer number if not detected by automatically", delay=1.0)
        txtrec_entry.grid(row=7, column=1, padx=10, pady=5)

        ttk.Label(popup, text="No. of add. trailer records:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        txtrail_entry = ttk.Entry(popup, width=25)
        ToolTip(txtrail_entry, msg="Enter integer number if not detected by automatically", delay=1.0)
        txtrail_entry.grid(row=8, column=1, padx=10, pady=5)

        info2_lbl = ttk.Label(popup, text="Note: seisio has more parameters than can be set through this GUI.", justify="center", style="RedText.TLabel")
        info2_lbl.grid(row=9, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        info3_lbl = ttk.Label(popup, text="Under normal circumstances, none of these parameters are required.", justify="center", style="RedText.TLabel")
        info3_lbl.grid(row=10, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        def save_close():
            """Save changes from seisio options."""
            ft = filetype_cbo.get().strip()
            self.log.debug("selected filetype: %s", ft)
            if ft == filetype_options[0]:
                self.filetype = None
            else:
                self.filetype = ft

            end = endianess_cbo.get().strip()
            self.log.debug("selected endianess: %s", end)
            if end == endianess_options[0]:
                self.endian = None
            elif end == endianess_options[1]:
                self.endian = ">"
            else:
                self.endian = "<"

            thdef = thdef_entry.get().strip()
            self.log.debug("selected thdef file: %s", thdef)
            if len(thdef):
                self.thdef = thdef
            else:
                self.thdef = None

            fmt = format_cbo.get().strip()
            self.log.debug("selected format: %s", fmt)
            if fmt == format_options[0]:
                self.format = None
            else:
                val = fmt.split("::")
                self.format = self._safe_num(val[0].strip(), fallback=5)

            self.thext1 = thext1_bool.get()
            self.log.debug("selected thext1: %s", self.thext1)

            ntx = txtrec_entry.get().strip()
            if len(ntx):
                self.ntxtrec = self._safe_num(ntx)
            else:
                self.ntxtrec = None
            self.log.debug("selected ntxtrec: %s", self.ntxtrec)

            ntt = txtrail_entry.get().strip()
            if len(ntt):
                self.ntxtrail = self._safe_num(ntt)
            else:
                self.ntxtrail = None
            self.log.debug("selected ntxtrail: %s", self.ntxtrail)

            # close the popup
            popup.destroy()

        # cancel button
        cancel_btn = ttk.Button(popup, text="Cancel", command=popup.destroy)
        cancel_btn.grid(row=11, column=0, columnspan=1, pady=15)
        # apply button
        apply_btn = ttk.Button(popup, text="Save & Close", command=save_close)
        apply_btn.grid(row=11, column=1, columnspan=1, pady=15)

    def _plot_options(self):
        """Display plot options."""
        if not self.imshow:
            return

        popup = tk.Toplevel(self.root)
        popup.title("Plot options")
        # popup.geometry("300x180")
        popup.resizable(False, False)

        popup.grab_set()

        ttk.Label(popup, text="Plot title:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        title_entry = ttk.Entry(popup, width=25)
        title_entry.insert(0, self.ax.get_title())  # Pre-fill with current title
        title_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical label:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ylabel_entry = ttk.Entry(popup, width=25)
        ylabel_entry.insert(0, self.ax.get_ylabel()) # Pre-fill with current y-label
        ylabel_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal label:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        xlabel_entry = ttk.Entry(popup, width=25)
        xlabel_entry.insert(0, self.ax.get_xlabel()) # Pre-fill with current x-label
        xlabel_entry.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical major ticks:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        vmajor_entry = ttk.Entry(popup, width=25)
        ToolTip(vmajor_entry, msg="Draw major ticks along vert. axis at this interval.", delay=1.0)
        vmajor_entry.insert(0, self.vmajorticks)
        vmajor_entry.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical minor ticks:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        vminor_entry = ttk.Entry(popup, width=25)
        ToolTip(vminor_entry, msg="Draw minor ticks along vert. axis at this interval.", delay=1.0)
        vminor_entry.insert(0, self.vminorticks)
        vminor_entry.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal major ticks:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        hmajor_entry = ttk.Entry(popup, width=25)
        ToolTip(hmajor_entry, msg="Draw major ticks along horiz. axis at this interval.", delay=1.0)
        hmajor_entry.insert(0, self.hmajorticks)
        hmajor_entry.grid(row=5, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal minor ticks:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        hminor_entry = ttk.Entry(popup, width=25)
        ToolTip(hminor_entry, msg="Draw minor ticks along horiz. axis  at this interval.", delay=1.0)
        hminor_entry.insert(0, self.hminorticks)
        hminor_entry.grid(row=6, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Lower data clip value:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        vmin_entry = ttk.Entry(popup, width=25)
        ToolTip(vmin_entry, msg="Data value at which to clip at the lower end.\nUse 'auto' for smallest data value.", delay=1.0)
        vmin_entry.insert(0, self.vmin)
        vmin_entry.grid(row=7, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Upper data clip value:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        vmax_entry = ttk.Entry(popup, width=25)
        ToolTip(vmax_entry, msg="Data value at which to clip at the upper end.\nUse 'auto' for largest data value.", delay=1.0)
        vmax_entry.insert(0, self.vmax)
        vmax_entry.grid(row=8, column=1, padx=10, pady=5)

        ttk.Label(popup, text="First vertical axis value:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        delay_entry = ttk.Entry(popup, width=25)
        ToolTip(delay_entry, msg="Time or depth value where vertical axis starts (typically 0).", delay=1.0)
        delay_entry.insert(0, self.delay)
        delay_entry.grid(row=9, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical sampling interval:").grid(row=10, column=0, padx=10, pady=5, sticky="w")
        dt_entry = ttk.Entry(popup, width=25)
        ToolTip(dt_entry, msg="dt for time-domain data, dz for depth-domain data.", delay=1.0)
        dt_entry.insert(0, self.dt)
        dt_entry.grid(row=10, column=1, padx=10, pady=5)

        cclabel = self.cbar.ax.get_ylabel() if self.cbar else ""
        ttk.Label(popup, text="Colorbar label:").grid(row=11, column=0, padx=10, pady=5, sticky="w")
        clabel_entry = ttk.Entry(popup, width=25)
        clabel_entry.insert(0, cclabel)
        clabel_entry.grid(row=11, column=1, padx=10, pady=5)

        cclabelpad = self.cbar.ax.get_yaxis().labelpad if self.cbar else 0
        ttk.Label(popup, text="Colorbar label padding:").grid(row=12, column=0, padx=10, pady=5, sticky="w")
        clabelpad_entry = ttk.Entry(popup, width=25)
        ToolTip(clabelpad_entry, msg="Pos. values shift right, neg. values shift left.", delay=1.0)
        clabelpad_entry.insert(0, cclabelpad)
        clabelpad_entry.grid(row=12, column=1, padx=10, pady=5)

        ttk.Label(popup, text="No. of colorbar bins:").grid(row=13, column=0, padx=10, pady=5, sticky="w")
        cbarbins_entry = ttk.Entry(popup, width=25)
        ToolTip(cbarbins_entry, msg="Integer value or 'auto'.", delay=1.0)
        cbarbins_entry.insert(0, self.cbarbins)
        cbarbins_entry.grid(row=13, column=1, padx=10, pady=5)

        def apply_changes():
            """Apply changes from plot options."""
            # update the Matplotlib axes text properties
            self.title = title_entry.get().strip()
            self.xlabel = xlabel_entry.get().strip()
            self.ylabel = ylabel_entry.get().strip()
            self.ax.set_title(self.title)
            self.ax.set_xlabel(self.xlabel)
            self.ax.set_ylabel(self.ylabel)
            self.clabel = clabel_entry.get().strip()
            labelpad = clabelpad_entry.get().strip()
            if labelpad:
                self.clabelpad = self._safe_num(labelpad)
            cbarbins = cbarbins_entry.get().strip()
            if cbarbins == "auto":
                self.cbarbins = "auto"
            else:
                self.cbarbins = self._safe_num(cbarbins)
            dt = dt_entry.get().strip()
            if dt:
                self.dt = np.float32(self._safe_num(dt))
            delay = delay_entry.get().strip()
            if delay:
                self.delay = np.float32(self._safe_num(delay))
            if dt or delay:
                self.t = np.arange(self.delay, self.delay+(self.ns-1)*self.dt+self.dt/2, self.dt)
                self._update_extent()
            self.vmajorticks = vmajor_entry.get().strip()
            self.vminorticks = vminor_entry.get().strip()
            self.hmajorticks = hmajor_entry.get().strip()
            self.hminorticks = hminor_entry.get().strip()
            vmax = vmax_entry.get().strip()
            vmin = vmin_entry.get().strip()
            if vmax.lower() == "auto":
                self.vmax = np.max(self.ensemble["data"])
            else:
                self.vmax = vmax
            if vmin.lower() == "auto":
                self.vmin = np.min(self.ensemble["data"])
            else:
                self.vmin = vmin
            self._update_ticks()
            self._clip_apply(redraw=False)
            self._cbar_prop()
            self._redraw()
            # close the popup
            popup.destroy()

        # cancel button
        cancel_btn = ttk.Button(popup, text="Cancel", command=popup.destroy)
        cancel_btn.grid(row=14, column=0, columnspan=1, pady=15)
        # apply button
        apply_btn = ttk.Button(popup, text="Apply & Close", command=apply_changes)
        apply_btn.grid(row=14, column=1, columnspan=1, pady=15)

    def _wiggle_options(self):
        """Display plot options."""
        popup = tk.Toplevel(self.root)
        popup.title("Plot options")
        # popup.geometry("300x180")
        popup.resizable(False, False)

        popup.grab_set()

        ttk.Label(popup, text="Plot title:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        title_entry = ttk.Entry(popup, width=25)
        title_entry.insert(0, self.ax.get_title())  # Pre-fill with current title
        title_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical label:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ylabel_entry = ttk.Entry(popup, width=25)
        ylabel_entry.insert(0, self.ax.get_ylabel()) # Pre-fill with current y-label
        ylabel_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal label:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        xlabel_entry = ttk.Entry(popup, width=25)
        xlabel_entry.insert(0, self.ax.get_xlabel()) # Pre-fill with current x-label
        xlabel_entry.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical major ticks:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        vmajor_entry = ttk.Entry(popup, width=25)
        ToolTip(vmajor_entry, msg="Draw major ticks along vert. axis at this interval.", delay=1.0)
        vmajor_entry.insert(0, self.vmajorticks)
        vmajor_entry.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical minor ticks:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        vminor_entry = ttk.Entry(popup, width=25)
        ToolTip(vminor_entry, msg="Draw minor ticks along vert. axis at this interval.", delay=1.0)
        vminor_entry.insert(0, self.vminorticks)
        vminor_entry.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal major ticks:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        hmajor_entry = ttk.Entry(popup, width=25)
        ToolTip(hmajor_entry, msg="Draw major ticks along horiz. axis at this interval.", delay=1.0)
        hmajor_entry.insert(0, self.hmajorticks)
        hmajor_entry.grid(row=5, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Horizontal minor ticks:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        hminor_entry = ttk.Entry(popup, width=25)
        ToolTip(hminor_entry, msg="Draw minor ticks along horiz. axis  at this interval.", delay=1.0)
        hminor_entry.insert(0, self.hminorticks)
        hminor_entry.grid(row=6, column=1, padx=10, pady=5)

        ttk.Label(popup, text="First vertical axis value:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        delay_entry = ttk.Entry(popup, width=25)
        ToolTip(delay_entry, msg="Time or depth value where vertical axis starts (typically 0).", delay=1.0)
        delay_entry.insert(0, self.delay)
        delay_entry.grid(row=9, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Vertical sampling interval:").grid(row=10, column=0, padx=10, pady=5, sticky="w")
        dt_entry = ttk.Entry(popup, width=25)
        ToolTip(dt_entry, msg="dt for time-domain data, dz for depth-domain data.", delay=1.0)
        dt_entry.insert(0, self.dt)
        dt_entry.grid(row=10, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Trace decimation:").grid(row=11, column=0, padx=10, pady=5, sticky="w")
        skip_entry = ttk.Entry(popup, width=25)
        ToolTip(skip_entry, msg="Plot only every n-th trace.", delay=1.0)
        skip_entry.insert(0, self.wiggleskip)
        skip_entry.grid(row=11, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Wiggle excursion:").grid(row=12, column=0, padx=10, pady=5, sticky="w")
        xcur_entry = ttk.Entry(popup, width=25)
        ToolTip(xcur_entry, msg="Wiggle excursion (overlap).", delay=1.0)
        xcur_entry.insert(0, self.wigglexcur)
        xcur_entry.grid(row=12, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Wiggle linewidth:").grid(row=13, column=0, padx=10, pady=5, sticky="w")
        lw_entry = ttk.Entry(popup, width=25)
        ToolTip(lw_entry, msg="Linewidth of traces", delay=1.0)
        lw_entry.insert(0, self.wigglelw)
        lw_entry.grid(row=13, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Wiggle linecolor:").grid(row=14, column=0, padx=10, pady=5, sticky="w")
        lc_entry = ttk.Entry(popup, width=25)
        ToolTip(lc_entry, msg="Linecolor of traces", delay=1.0)
        lc_entry.insert(0, self.wiggle_lcolor)
        lc_entry.grid(row=14, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Wiggle pos. fillcolor:").grid(row=15, column=0, padx=10, pady=5, sticky="w")
        fill_entry = ttk.Entry(popup, width=25)
        ToolTip(fill_entry, msg="Color of filled pos. wiggles", delay=1.0)
        fill_entry.insert(0, self.wiggle_fill)
        fill_entry.grid(row=15, column=1, padx=10, pady=5)

        ttk.Label(popup, text="Wiggle neg. fillcolor:").grid(row=16, column=0, padx=10, pady=5, sticky="w")
        negfill_entry = ttk.Entry(popup, width=25)
        ToolTip(negfill_entry, msg="Color of filled neg. wiggles", delay=1.0)
        negfill_entry.insert(0, self.wiggle_negfill)
        negfill_entry.grid(row=16, column=1, padx=10, pady=5)

        hires_bool = tk.BooleanVar(value=False)
        ttk.Label(popup, text="Oversample traces?").grid(row=17, column=0, padx=10, pady=5, sticky="w")
        hires_chk = tk.Checkbutton(popup, text="", variable=hires_bool)
        ToolTip(hires_chk, msg="Tick to create high-resolution trace before plotting", delay=1.0)
        hires_chk.grid(row=17, column=1, padx=10, pady=5)

        def apply_changes():
            """Apply changes from plot options."""
            # update the Matplotlib axes text properties
            self.title = title_entry.get().strip()
            self.xlabel = xlabel_entry.get().strip()
            self.ylabel = ylabel_entry.get().strip()
            self.ax.set_title(self.title)
            self.ax.set_xlabel(self.xlabel)
            self.ax.set_ylabel(self.ylabel)
            dt = dt_entry.get().strip()
            if dt:
                self.dt = np.float32(self._safe_num(dt))
            delay = delay_entry.get().strip()
            if delay:
                self.delay = np.float32(self._safe_num(delay))
            if dt or delay:
                self.t = np.arange(self.delay, self.delay+(self.ns-1)*self.dt+self.dt/2, self.dt, dtype=np.float32)
            skip = skip_entry.get().strip()
            if skip:
                self.wiggleskip = int(self._safe_num(skip))
            xcur = xcur_entry.get().strip()
            if xcur:
                self.wigglexcur = self._safe_num(xcur)
            lw = lw_entry.get().strip()
            if lw:
                self.wigglelw = self._safe_num(lw)
            lc = lc_entry.get().strip()
            if lc:
                self.wiggle_lcolor = lc
            self.wiggle_fill = fill_entry.get().strip()
            self.wiggle_negfill = negfill_entry.get().strip()
            self.wigglehires = hires_bool.get()
            self.vmajorticks = vmajor_entry.get().strip()
            self.vminorticks = vminor_entry.get().strip()
            self.hmajorticks = hmajor_entry.get().strip()
            self.hminorticks = hminor_entry.get().strip()
            self._update_plot()
            # close the popup
            popup.destroy()

        # cancel button
        cancel_btn = ttk.Button(popup, text="Cancel", command=popup.destroy)
        cancel_btn.grid(row=18, column=0, columnspan=1, pady=15)
        # apply button
        apply_btn = ttk.Button(popup, text="Apply & Close", command=apply_changes)
        apply_btn.grid(row=18, column=1, columnspan=1, pady=15)

    def _open_file(self):
        """Open a file with seisio."""
        self.file_path = tk.filedialog.askopenfilename(filetypes=[("Seismic files", "*.sgy *.segy *.su"), ("All files", "*")])
        if not self.file_path:
            return

        try:
            self.log.debug("calling seisio with filetype: %s", self.filetype)
            self.log.debug("calling seisio with format: %s", self.format)
            self.log.debug("calling seisio with endian: %s", self.endian)
            self.log.debug("calling seisio with thdef: %s", self.thdef)
            self.log.debug("calling seisio with thext1: %s", self.thext1)
            self.log.debug("calling seisio with ntxtrec: %s", self.ntxtrec)
            self.log.debug("calling seisio with ntxtrail: %s", self.ntxtrail)
            self.sio = seisio.input(self.file_path, filetype=self.filetype, format=self.format,
                                    endian=self.endian, thdef=self.thdef, thext1=self.thext1,
                                    ntxtrec=self.ntxtrec, ntxtrail=self.ntxtrail)
            self.nt = self.sio.ntraces
            self.ns = self.sio.nsamples
            self.t = self.sio.vaxis
            self.delay = self.sio.delay*1e-3
            self.dt = self.sio.vsi*1e-6
            if self.dt == 0:
                self.dt = 1
                self.vaxis = np.arange(self.delay, self.delay+(self.ns-1)*self.dt+self.dt/2, self.dt)
            self.log.debug("ntraces: %d", self.nt)
            self.log.debug("nsamples: %d", self.ns)
            self.log.debug("sampling interval: %.3f", self.dt)
            self.log.debug("delay: %.3f", self.delay)
            self.log.debug("time axis: %.3f - %.3f", self.t[0], self.t[-1])
            self.status_lbl.configure(text=f"File: {os.path.basename(self.file_path)} | Traces: {self.nt} | Samples: {self.ns}", style="GreenText.TLabel")
            self.info_btn.configure(state="normal")
            self.gather_cbo["state"] = "normal"
            self.index_btn.configure(state="normal")
            self.keys_cbo["state"] = "disabled"
            self.load_btn.configure(state="disabled")
            self.perc_slid.configure(state="normal")
            self.perc_entry.configure(state="normal")
            # reset certain variables
            self.df = None
            self.xlabel = None
            self.ylabel = None
            self.clabel = None
            self.clabelpad = 0
            self.cbarbins = "auto"
            self.title = None
            self.vmin = ""
            self.vmax = ""
            self._reset_ticks()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to open file with seisio:\n{e}")

    def _info_file(self):
        """Create and display short header statistics."""
        if not self.sio:
            return

        ntmax = min(self.nt-1, 999)
        if self.df is None:
            self.df = self.sio.log_thstat(ntmax=ntmax)

        popup = tk.Toplevel(self.root)
        popup.title(f"Trace header preview ({ntmax} traces)")
        popup.grab_set()

        frame = tk.Frame(popup, bg="#cccccc", bd=1)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")

        index_col_name = self.df.index.name if self.df.index.name is not None else "Index"
        all_columns = [index_col_name] + list(self.df.columns)

        dataframe_row_count = max(1, len(self.df))
        tree = ttk.Treeview(frame, columns=all_columns, show="headings", height=dataframe_row_count, yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ensure the table expands nicely if the user resizes the window
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        max_widths = {col: len(str(col)) for col in all_columns}

        for idx in self.df.index:
            max_widths[index_col_name] = max(max_widths[index_col_name], len(str(idx)))

        for col in self.df.columns:
            max_len = self.df[col].astype(str).str.len().max()
            max_widths[col] = max(max_widths[col], max_len)

        for col in all_columns:
            tree.heading(col, text=col)
            calculated_width = (max_widths[col] * 9) + 30
            final_width = max(80, calculated_width)
            tree.column(col, width=final_width, anchor="center")

        for idx, row in self.df.iterrows():
            row_values = [str(idx)] + list(row.astype(str))
            tree.insert("", tk.END, values=row_values)

        txthead = []

        def _show_ebcdic():
            """
            header_lines: List of 40 strings, each max 80 characters.
            """
            window = tk.Toplevel(popup)
            window.title("SEG-Y Textual Header")
            window.geometry("750x600")

            lbl = tk.Label(window, text="ASCII / EBCDIC Textual Header (40 lines at 80 chars)",
                           font=("Arial", 11, "bold"))
            lbl.pack(pady=10)

            text_frame = ttk.Frame(window)
            text_frame.pack(expand=True, fill="both", padx=15, pady=5)

            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side="right", fill="y")

            # text widget (crucial settings: font, wrap, and width)
            # width=80 ensures the lines don't prematurely wrap if the window is resized
            header_text = tk.Text(
                text_frame,
                font=("Consolas", 10),  # monospaced font preserves alignment
                wrap="none",            # disable soft wrapping to keep the 80-char structure intact
                width=85,               # slightly wider than 80 to account for line numbers comfortably
                height=25,              # shows ~25 lines at a time
                yscrollcommand=scrollbar.set,
                bg="#f8f9fa",           # Off-white background for easier reading
                fg="#212529"
            )
            header_text.pack(side="left", expand=True, fill="both")
            scrollbar.config(command=header_text.yview)

            # joining with newlines ensures it renders line-by-line
            full_header_string = "\n".join(txthead)
            header_text.insert("1.0", full_header_string)

            header_text.config(state="disabled")
            btn_close = ttk.Button(window, text="Close", command=window.destroy)
            btn_close.pack(pady=10)

        try:
            txthead = self.sio.txthead
        except AttributeError:
            pass
        if len(txthead) > 0:
            show_btn = ttk.Button(popup, text="Show SEG-Y textual header", command=_show_ebcdic)
            show_btn.pack(pady=(0, 10))

        close_btn = ttk.Button(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=(0, 10))

        popup.update_idletasks()
        # pad the height slightly to account for the scrollbar and button layout
        required_width = popup.winfo_reqwidth() + 20
        required_height = popup.winfo_reqheight() + 20
        # sSet the initial opening size to fit the data perfectly
        popup.geometry(f"{required_width}x{required_height}")

    def _create_index(self):
        """Create a lookup index."""
        if not self.sio:
            return

        order = self.gather_cbo.get()
        self.headers = self._parse_slashes(order)
        nh = len(self.headers)
        self.log.debug("headers to create index: %s", self.headers)
        self.gather_cbo.selection_clear()
        self.xlabel = None
        self._reset_ticks(y=False)

        self.index_btn.configure(state="disabled")
        self.status_lbl.configure(text="Creating lookup index... Please wait", style="RedText.TLabel")
        # self.root.update_idletasks()

        # define what happens *after* the background thread finishes
        def on_indexing_complete():
            try:
                self.status_lbl.configure(
                    text=f"File: {os.path.basename(self.file_path)} | Lookup index: {order} | Ensembles: {self.sio.ne}",
                    style="GreenText.TLabel"
                )
                keys = self.sio.ensemble_keys
                self.ens_keys = [str(i[0])+","+str(i[1]) if len(i)==2 else str(i[0]) for i in keys]
                self.keys_cbo.set_completion_list(self.ens_keys)
                self.keys_cbo.current(0)
                if nh > 1:
                    self.keys_cbo["state"] = "normal"
                else:
                    self.keys_cbo["state"] = "disabled"
                self.load_btn.configure(state="normal")
                self.index_btn.configure(state="normal")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to finalize index creation:\n{e}")

        # define the heavy work to run inside the thread
        def worker_thread():
            try:
                # this heavy disk read runs safely in the background
                nh = len(self.headers)
                if nh == 1:
                    self.sio.create_index(group_by="ns", sort_by=self.headers[0])
                elif nh == 2:
                    self.sio.create_index(group_by=self.headers[0], sort_by=self.headers[1])
                elif nh == 3:
                    self.sio.create_index(group_by=self.headers[0:2], sort_by=self.headers[2])
                else:
                    raise ValueError(f"Unknown ensemble setup specified {order}.")
                # use .after() to safely jump back to the main thread for GUI updates
                self.root.after(0, on_indexing_complete)
            except Exception as e:
                # if the background task crashes, handle the error on the main thread
                self.root.after(0, lambda err=e: [
                    self.index_btn.configure(state="normal"),
                    tk.messagebox.showerror("Error", f"Failed to create lookup index:\n{err}")
                    ])

        # kick off the background thread
        threading.Thread(target=worker_thread, daemon=True).start()

    def _load_data(self):
        """Load and display an ensemble."""
        ens_to_load_str = self.keys_cbo.get().strip()
        ens_to_load_tpl = tuple(map(ast.literal_eval, ens_to_load_str.split(",")))
        self.log.debug("About to load ensemble: %s", ens_to_load_tpl)
        try:
            self.ensemble = self.sio.read_ensemble(ens_to_load_tpl)
            # convert non-native endianess to native endianess if necessary
            if not self.ensemble.dtype.isnative:
                self.ensemble = self.ensemble.view(self.ensemble.dtype.newbyteorder()).byteswap()
            if len(self.headers) == 1:
                self.status_lbl.configure(text="Loaded stack data / profile", style="GreenText.TLabel")
            else:
                self.status_lbl.configure(text=f"Loaded ensemble {ens_to_load_str}", style="GreenText.TLabel")
            self._update_plot()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to load ensemble {ens_to_load_str}:\n{e}")

    def _update_plot(self):
        """Update the Matplotlib imshow plot."""
        if self.ensemble is None:
            return

        self._cbar_toggle(redraw=False, force_remove=True)
        self.ax.clear()

        nh = len(self.headers)
        if nh == 1:
            xlabel = self.headers[0]
        elif nh == 2:
            xlabel = self.headers[1]
        elif nh == 3:
            xlabel = self.headers[2]
        self.h = self.ensemble[xlabel]

        if self.wiggle.get():
            self.imshow = None
            self._wiggle_plot()
        else:
            self._image_plot()

        if self.xlabel is None:
            self.ax.set_xlabel(xlabel)
        else:
            self.ax.set_xlabel(self.xlabel)
        if self.ylabel is None:
            self.ax.set_ylabel("time (s)")
        else:
            self.ax.set_ylabel(self.ylabel)
        if self.title is not None:
            self.ax.set_title(self.title)

        self._update_ticks()

        self._cbar_toggle(redraw=False)

        self._redraw()

    def _image_plot(self):
        """Create an image plot of the data."""
        self.cbar_cbx.configure(state="normal")
        self.cmap_cbo.configure(state="normal")
        self.edit_btn.config(command=self._plot_options)

        if self.h[0] == self.h[-1]:
            extent_gather = [self.h[0]-np.finfo(float).eps, self.h[-1]+np.finfo(float).eps, self.t[-1], self.t[0]]
        else:
            extent_gather = [self.h[0], self.h[-1], self.t[-1], self.t[0]]
        self.imshow = self.ax.imshow(self.ensemble["data"].T, aspect="auto", extent=extent_gather, interpolation="bilinear")
        self.imshow.format_cursor_data = lambda data: ""
        self.ax.format_coord = self._format_coord
        self._clip_apply(redraw=False)
        self._change_colormap(None)

    def _wiggle_plot(self):
        """Create a wiggle plopass"""
        self.cbar_cbx.configure(state="disabled")
        self.cmap_cbo.configure(state="disabled")
        self.edit_btn.config(command=self._wiggle_options)
        self.wiggle_cbx.configure(state="disabled")
        self.status_lbl.configure(text="Creating wiggle plot... Please wait", style="RedText.TLabel")
        self.root.update_idletasks()

        hpos = np.array(self.h[::self.wiggleskip])
        dataplt = self.ensemble["data"][::self.wiggleskip, :]

        nt = len(hpos)
        if nt > 1:
            spacing = np.min(np.abs(np.diff(hpos)))
        else:
            spacing = 1

        if self.wiggle_hires.get():
            ns = 10*self.ns
            itpl_vaxis = np.linspace(self.t[0], self.t[-1], ns)
        else:
            ns = self.ns
            itpl_vaxis = self.t

        perc = self.perc_slid.get()
        scale = np.percentile(np.fabs(dataplt), perc)
        if scale == 0:
            scale = np.percentile(np.fabs(dataplt), 100)

        total_slots = np.int64(ns+1)*np.int64(nt)
        nan_x = np.full(total_slots, np.nan)
        nan_y = np.full(total_slots, np.nan)
        fill_packets = []
        for i, (trace, curhpos) in enumerate(zip(dataplt, hpos)):
            start_idx = np.int64(i)*np.int64(ns+1)
            end_idx = start_idx + np.int64(ns)
            amp = trace / scale * spacing + curhpos
            if self.wiggle_hires.get():
                itpl_amp = np.interp(itpl_vaxis, self.t, amp)
            else:
                itpl_amp = amp
            # clip based on xcur parameter
            clipmin = curhpos-self.wigglexcur*spacing
            clipmax = curhpos+self.wigglexcur*spacing
            if clipmax < clipmin:
                clipmin, clipmax = clipmax, clipmin
            np.clip(itpl_amp, clipmin, clipmax, out=itpl_amp)
            nan_x[start_idx:end_idx] = itpl_amp
            nan_y[start_idx:end_idx] = itpl_vaxis

            fill_packets.append((curhpos, itpl_amp))

        if self.wiggle_fill:
            for x, amp_x in fill_packets:
                self.ax.fill_betweenx(itpl_vaxis, amp_x, x, lw=0,
                                      where=(amp_x > x), facecolor=self.wiggle_fill)
        if self.wiggle_negfill:
            for x, amp_x in fill_packets:
                self.ax.fill_betweenx(itpl_vaxis, amp_x, x, lw=0,
                                      where=(amp_x < x), facecolor=self.wiggle_negfill)

        self.ax.plot(nan_x, nan_y, linewidth=self.wigglelw, color=self.wiggle_lcolor)

        self.ax.set_ylim([self.t[-1], self.t[0]])
        self.ax.set_xlim([hpos[0]-0.99*spacing, hpos[-1]+0.99*spacing])

        ens_loaded = self.keys_cbo.get().strip()
        if len(self.headers) == 1:
            self.status_lbl.configure(text="Loaded stack data / profile", style="GreenText.TLabel")
        else:
            self.status_lbl.configure(text=f"Loaded ensemble {ens_loaded}", style="GreenText.TLabel")
        self.wiggle_cbx.configure(state="normal")
        self.root.update_idletasks()

    def _gather_select(self, event):
        pass

    def _redraw(self):
        """Redraw the canvas."""
        if not self.fig:
            return
        self.fig.tight_layout()
        self.canvas.draw()

    def _cbar_prop(self):
        if self.cbar:
            self.cbar.ax.set_ylabel(self.clabel)
            self.cbar.ax.get_yaxis().labelpad = self.clabelpad
            self.cbar.ax.yaxis.set_major_locator(MaxNLocator(nbins=self.cbarbins))

    def _wiggle_toggle(self):
        self._update_plot()

    def _cbar_toggle(self, redraw=True, force_remove=False):
        """Activate/deactivate colorbar."""
        is_checked = self.cbar_visible.get()
        if (not is_checked) or force_remove:
            if self.cbar:
                self.cbar.remove()
                self.cbar = None
        else:
            if self.imshow:
                self.cbar = self.fig.colorbar(self.imshow, ax=self.ax, location="right",
                                              fraction=0.03, shrink=1.0, aspect=40, pad=0.03)
                self._cbar_prop()
        if redraw:
            self._redraw()

    def _change_colormap(self, event):
        """Change colormap."""
        if not self.imshow:
            return
        try:
            selected_cmap = self.cmap_cbo.get()
            self.log.debug("selectec_cmap: %s", selected_cmap)
            if selected_cmap in self.cmap_options:
                idx = self.cmap_options.index(selected_cmap)
                self.imshow.set_cmap(self.cmap_calls[idx])
            else:
                self.imshow.set_cmap(selected_cmap)
            self.canvas.draw()
            self.cmap_cbo.selection_clear()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to set colormap:\n{e}")

    def _update_extent(self):
        """Update Matplotlib's imshow extent."""
        if self.imshow:
            left, right, current_bottom, current_top = self.imshow.get_extent()
        else:
            return
        self.log.debug("sampling interval now: %.3f", self.dt)
        self.log.debug("delay now: %.3f", self.delay)
        self.log.debug("time axis now: %.3f - %.3f", self.t[0], self.t[-1])
        new_bottom = self.t[-1]
        new_top = self.t[0]
        self.imshow.set_extent([left, right, new_bottom, new_top])
        self._reset_ticks(x=False)
        self.ax.relim()
        self.ax.autoscale_view()

    def _parse_slashes(self, order_string):
        """Parse user-provided lookup keys."""
        # split string
        parts = order_string.split("/")
        # remove white spaces and make lowercase
        parts = [part.strip().lower() for part in parts]
        return parts

    def _perc_on_scale_drag(self, value):
        """Update the text box numbers in real-time while dragging, without processing data."""
        val = float(value)
        self.perc_str.set(f"{val:.1f}")

    def _perc_on_scale_release(self, event):
        """Trigger exactly when the user lets go of the slider."""
        if self.imshow:
            self._clip_apply()
        elif self.wiggle.get():
            self._update_plot()

    def _perc_on_enter_pressed(self, event):
        """Trigger exactly when the user presses Enter in the text box."""
        try:
            val = float(self.perc_str.get())
            # enforce data boundaries
            clamped_val = max(50.0, min(100.0, val))
            # sync the UI elements
            self.perc_str.set(f"{clamped_val:.1f}")
            self.perc_slid.set(clamped_val)
            # execute the heavy calculation
            if self.imshow:
                self._clip_apply()
            elif self.wiggle.get():
                self._update_plot()
            # remove keyboard focus from entry box for clean UX
            self.root.focus_set()
        except ValueError:
            # if they entered garbage text, reset the box to the slider's current position
            self.perc_str.set(f"{self.perc_slid.get():.1f}")

    def _clip_apply(self, redraw=True):
        """Apply a percentile or user-provided clip."""
        if self.ensemble is None:
            return

        if self.imshow is not None:
            if self.vmin and self.vmax:
                self.imshow.set_clim(vmin=self.vmin, vmax=self.vmax)
                self.perc_slid.configure(state="disabled")
                self.perc_entry.configure(state="disabled")
            else:
                self.perc_slid.configure(state="normal")
                self.perc_entry.configure(state="normal")
                perc = self.perc_slid.get()
                self.log.debug("perc: %d", perc)
                if self.vmin and (not self.vmax):
                    clip = np.percentile(self.ensemble["data"], perc)
                    self.imshow.set_clim(vmin=self.vmin, vmax=clip)
                elif self.vmax and (not self.vmin):
                    clip = np.percentile(self.ensemble["data"], 100.0-perc)
                    self.imshow.set_clim(vmin=clip, vmax=self.vmax)
                else:
                    clip = np.percentile(np.fabs(self.ensemble["data"]), perc)
                    self.imshow.set_clim(vmin=-clip, vmax=clip)
            self._cbar_prop()
        if redraw:
            self.canvas.draw()

    def _reset_ticks(self, x=True, y=True):
        """Reset ticks."""
        if y:
            self.vmajorticks = ""
            self.vminorticks = ""
            self.ax.yaxis.set_major_locator(AutoLocator())
            self.ax.yaxis.set_minor_locator(AutoLocator())
        if x:
            self.hmajorticks = ""
            self.hminorticks = ""
            self.ax.xaxis.set_major_locator(AutoLocator())
            self.ax.xaxis.set_minor_locator(AutoLocator())

    def _update_ticks(self):
        """Update ticks."""
        if self.vmajorticks:
            self.ax.yaxis.set_major_locator(MultipleLocator(self._safe_num(self.vmajorticks)))
        if self.vminorticks:
            self.ax.yaxis.set_minor_locator(MultipleLocator(self._safe_num(self.vminorticks)))
        if self.hmajorticks:
            self.ax.xaxis.set_major_locator(MultipleLocator(self._safe_num(self.hmajorticks)))
        if self.hminorticks:
            self.ax.xaxis.set_minor_locator(MultipleLocator(self._safe_num(self.hminorticks)))

    def _safe_num(self, val, fallback=1):
        """Convert string to int or float number."""
        if val is None:
            return fallback
        # strip whitespace just in case
        val = str(val).strip()
        try:
            number = ast.literal_eval(val)
            if isinstance(number, (int, float)):
                return number
            raise ValueError("String is not a valid number.")
        except (ValueError, SyntaxError):
            # triggers if the string contains letters, symbols, or is empty
            return fallback

    # def _show_ttk_message(self, parent, title, message, icon_type="info"):
    #     """A fully themed custom alternative to tk.messagebox.showinfo."""
    #     # reate a modal popup window
    #     msg_box = tk.Toplevel(parent)
    #     msg_box.title(title)
    #     msg_box.resizable(False, False)
    #     msg_box.grab_set()  # Prevents interacting with the main window

    #     # outer container frame
    #     content_frame = ttk.Frame(msg_box, padding=20)
    #     content_frame.pack(fill=tk.BOTH, expand=True)

    #     # handle optional status styling based on 'icon_type'
    #     accent_color = "#333333"  # Default gray
    #     if icon_type == "error":
    #         accent_color = "#d32f2f"  # Soft red
    #     elif icon_type == "success":
    #         accent_color = "#388e3c"  # Soft green

    #     # message Label
    #     msg_label = ttk.Label(
    #         content_frame,
    #         text=message,
    #         wraplength=300,
    #         font=("Helvetica", 10)
    #     )
    #     msg_label.pack(pady=(0, 20), anchor="center")

    #     # OK / Dismiss Button
    #     ok_btn = ttk.Button(content_frame, text="OK", command=msg_box.destroy)
    #     ok_btn.pack(anchor="center")

    #     # focus the button so the user can just press 'Enter' or 'Space' to close it
    #     ok_btn.focus_set()

    #     # center the popup dynamically relative to the parent window
    #     msg_box.update_idletasks()

    #     # calculate screen position coordinates
    #     p_width = parent.winfo_width()
    #     p_height = parent.winfo_height()
    #     p_x = parent.winfo_x()
    #     p_y = parent.winfo_y()

    #     m_width = msg_box.winfo_reqwidth()
    #     m_height = msg_box.winfo_reqheight()

    #     # mathematical positioning to center over the application layout
    #     x = p_x + (p_width // 2) - (m_width // 2)
    #     y = p_y + (p_height // 2) - (m_height // 2)

    #     msg_box.geometry(f"{m_width}x{m_height}+{x}+{y}")

###############################################################################
# main
###############################################################################

def main():
    # def initialize_dpi_awareness():
    #     """ Forces the OS to scale Tkinter AND native dialogs properly """
    #     import sys
    #     # --- WINDOWS ---
    #     if sys.platform.startswith("win"):
    #         try:
    #             import ctypes
    #             # PROCESS_PER_MONITOR_DPI_AWARE = 2
    #             # This ensures native dialogs (file dialogs) scale to the monitor they appear on
    #             ctypes.windll.shcore.SetProcessDpiAwareness(2)
    #         except Exception:
    #             try:
    #                 # Fallback for older Windows versions
    #                 ctypes.windll.user32.SetProcessDPIAware()
    #             except Exception:
    #                 pass
    #     # --- LINUX / MAC ---
    #     # macOS handles this natively. For Linux, Tkinter provides a built-in scaling method.

    DESC = """description: interactive seismic data viewer"""
    PROG = "seisview"

    parser = argparse.ArgumentParser(prog=PROG, description=DESC, add_help=True)
    parser.add_argument("-v", "--verbose",
                        action="count",
                        default=0,
                        help="output additional information (repeat for debug mode)")
    parser.add_argument("--version",
                        action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s(%(name)s,%(funcName)s): %(message)s')
    elif args.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

    # initialize_dpi_awareness()

    root = tk.Tk()
    app = DataViewer(root)
    root.mainloop()

# in case somebody calls "python -m seisview.dataviewer" directly.
if __name__ == "__main__":
    main()
