"""
2019-05     Martin Yeo
A python demonstration of Wireworld Cellular Automation (https://en.wikipedia.org/wiki/Wireworld)
"""

import numpy as np
import os
import tkinter as tk
import yaml

from copy import deepcopy
from os import path
from tkinter import filedialog
from yaml import parser
from yaml import scanner

default_array = [
    [0, 0, 0, 3, 0, 0, 0],
    [0, 3, 0, 3, 0, 3, 0],
    [3, 0, 3, 0, 3, 0, 3],
    [1, 0, 0, 3, 0, 0, 1],
    [2, 0, 3, 3, 3, 0, 2],
    [0, 3, 0, 3, 0, 3, 0],
    [0, 0, 0, 3, 0, 0, 0],
]

valid_states = (0, 1, 2, 3)
color_lookup = (None, "#0000ff", "#ff0000", "#ffff00")


class WireWorldInstance:
    def __init__(self):
        self.tk_root = tk.Tk()
        self.gui = self.GUI(master=self.tk_root, wireworld=self)
        self.time_ticker = self.TimeTicker(wireworld=self)



    class TimeTicker:
        # Simple class containing the 'ticks' property.
        # When ticks changes value, the gui label is updated to reflect this.
        def __init__(self, wireworld):
            enforce_type_wireworld(wireworld)
            self.gui = wireworld.gui
            self.ticks = 0

        def __setattr__(self, name, value):
            self.__dict__[name] = value
            if name == "ticks":
                self.gui.update_time_label(self.ticks)

    class GUI(tk.Frame):
        # GUI is created once within the module, then worked with globally by all functions.
        def __init__(self, master, wireworld):
            enforce_type_wireworld(wireworld)
            super().__init__(master)
            self.master = master
            self.pack()

            # tk.StringVar() allows time_label_text to be updated at later points
            self.time_label_text = tk.StringVar()
            self.time_label = tk.Label(
                master=self,
                textvariable=self.time_label_text
            )

            self.advance_button = tk.Button(
                master=self,
                text="Next",
                command=lambda: wireworld.advance_time()
            )

            self.save_button = tk.Button(
                master=self,
                text="Save",
                command=lambda: wireworld.save_load_states(is_save_mode=True)
            )

            self.load_button = tk.Button(
                master=self,
                text="Load",
                command=lambda: wireworld.save_load_states(is_save_mode=False)
            )

            self.time_label.grid(row=0, column=0)
            self.advance_button.grid(row=1, column=0)
            self.save_button.grid(row=3, column=0)
            self.load_button.grid(row=4, column=0)

            self.update_time_label(0)

        def update_time_label(self, ticks):
            # Change the time label variable to an input integer
            self.time_label_text.set("{:05d}".format(ticks))

    class WireCell(tk.Button):
        # WireCell is a tkinter button that represents the corresponding cell in array_states.
        # It is generated, along with the state array, by the load_array function.
        # Accepts positional coordinates and an initial state as arguments, as well as the standard master.
        def __init__(self, master, row_input, column_input, state=0):
            super().__init__(master)
            self.master = master

            # Won't want to overwrite the position occupied by the time label.
            # base_column = master.time_label.grid_info()["column"] + 1
            base_column = 1

            self.row, self.column = row_input, column_input
            self.grid(row=self.row, column=self.column + base_column)

            self.state = state
            self.state_change(self.state)

        def state_change(self, state):
            self.state = state

            # Represent the Wireworld states using the accepted colours.
            target_colour = color_lookup[self.state]
            self.configure(
                background=target_colour,
                activebackground=target_colour
            )

    def execute(self):
        try:
            self.load_array(default_array)
            print_states(self.array_states, self.time_ticker.ticks)
            self.gui.mainloop()
        finally:
            # Close down the GUI no matter what.
            try:
                self.tk_root.destroy()
            except tk.TclError:
                pass

    def save_load_states(self, is_save_mode=True):
        # Used during both save and load functions to get the target path from the user via a file dialog.

        # Try to use a previously set path as the dialog's starting point. If not possible use the working directory.
        initial_directory = os.getcwd()
        try:
            if os.path.exists(self.tk_root.filename):
                initial_directory = os.path.split(self.tk_root.filename)[0]
        except (AttributeError, TypeError):
            pass

        # Config for save or load is the same so use kwargs.
        config_dict = {
            "initialdir": initial_directory,
            "filetypes": (("yaml files", "*.yaml"), ("all files", "*.*"))
        }

        if is_save_mode:
            self.tk_root.filename = filedialog.asksaveasfilename(**config_dict)
        else:
            self.tk_root.filename = filedialog.askopenfilename(**config_dict)

        if self.tk_root.filename:   # only run if populated
            if is_save_mode:
                save_file(self.tk_root.filename, self.array_states)
            else:
                array_load = load_file(self.tk_root.filename)
                self.load_array(array_load)

    def load_array(self, array_input):
        array = cleanse_array(array_input)

        self.time_ticker.ticks = 0

        self.array_states = np.array(deepcopy(array))
        # Iterate over the rows then the columns of the input array,
        # creating a new button in the appropriate GUI grid position.
        for rx, r in enumerate(array):
            for cx, c in enumerate(r):
                state = c
                self.WireCell(master=self.gui, state=state, row_input=rx, column_input=cx)

    def advance_time(self):
        self.array_states, changed_coords = cycle_states(self.array_states)

        for rx, cx in changed_coords:
            # Represent the Wireworld states using the accepted colours.
            target_button = self.gui.grid_slaves(rx, cx + 1)[0]
            target_button.state_change(self.array_states[rx][cx])

        self.time_ticker.ticks += 1
        print_states(self.array_states, self.time_ticker.ticks)


def enforce_type_wireworld(input_class):
    if not isinstance(input_class, WireWorldInstance):
    # if type(input_class) is not "WireWorldInstance":
        raise Exception("class type check failed = must be type WireWorldInstance")


def save_file(input_path, input_array):
    # Save the contents of array_states to a YAML file using the path selected by the user.

    if not check_2d_array(input_array):
        print("Not saving array. Must be 2 dimensional array")
        return

    save_yaml = yaml.dump(input_array.tolist())
    # Include a comment section at the top of the file to instruct any direct editing of the file.
    save_yaml = "\n".join((
        "# this file should be YAML format containing a rectangular array of states (0-3) for use in Wireworld",
        "# there should be no other YAML content"
        "# e.g.",
        "# - [0, 1, 2]",
        "# - [1, 0, 1]",
        "# - [3, 3, 3]",
        "",
        save_yaml
    ))

    # Add the .yaml suffix if not present.
    if input_path[-5:] != ".yaml":
        input_path += '.yaml'

    # Attempt to access the path provided.
    try:
        f = open(input_path, "w+")
    except OSError:
        print("Error accessing path, please try a different path")

    if "f" in locals():
        f.write(save_yaml)
        f.close()


def load_file(input_path):
    # Load contents of a YAML file using the path selected by the user.

    # Attempt to access the path provided.
    try:
        f = open(input_path, "r")
    except OSError:
        print("Error accessing path, please try a different path")

    if "f" in locals():
        file_contents = f.read()
        f.close()

    # Attempt to interpret file contents as YAML content.
    if "file_contents" in locals():
        output_array = format_yaml(file_contents)
        return output_array
    else:
        print("Nothing to load")
        return None


def format_yaml(input_string):
    # Attempt to an input variable as YAML content.
    yaml_load = None

    try:
        yaml_load = yaml.load(input_string)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as exception:
        print("Invalid YAML format in config file, please try a different path \nError message: \n\n" +
              str(exception))

    return yaml_load


def check_2d_array(input_array):
    # A basic check to make sure the input array has properties that can be worked with.
    format_ok = False
    try:
        format_ok = (np.array(input_array).ndim == 2)
    finally:
        return format_ok


def cleanse_array(array):
    if not check_2d_array(array):
        raise Exception("Input array format error. Must be 2 dimensional array")

    for rx, r in enumerate(array):
        for cx, c in enumerate(r):
            state = c
            if state not in valid_states:
                array[rx][cx] = 0

    return array


def cycle_states(array):
    # Check the cell's own state and its surroundings to provide the next state in line with Wireworld rules.

    array = cleanse_array(array)

    # Store an array of all future states before setting any of them.
    array_future = deepcopy(array)
    changed_coords = []
    for rx, r in enumerate(array):
        for cx, c in enumerate(r):
            state = c
            state_future = None

            if state in (1, 2):
                state_future = c + 1
            elif state == 3:
                # Conductors will change to heads if they have exactly 1 or 2 neighbouring heads.
                # Use numpy slicing to get the neighbours, then numpy where to filter them.
                slice_limits = [rx - 1, rx + 2, cx - 1, cx + 2]
                slice_limits = [max(x, 0) for x in slice_limits]  # change negatives to 0
                head_check = array[slice_limits[0]:slice_limits[1], slice_limits[2]:slice_limits[3]]
                head_check = np.where(head_check == 1, 1, 0)
                head_check = sum(sum(head_check))

                if head_check in (1, 2):
                    state_future = 1

            # Avoid any processing for empty cells.
            if state_future is not None:
                array_future[rx][cx] = state_future
                changed_coords.append([rx, cx])

    return array_future, changed_coords


def print_states(array_input, ticks):
    # Print a readable format of the state array in the terminal. Format empty cells as hyphens.
    # array_print = deepcopy(array_states)
    if type(array_input) is np.ndarray:
        array_input = np.where(array_input == 0, '-', array_input)
        print("\n-- STEP " + str(ticks) + " --")
        print('\n'.join( [''.join( ['{:3}'.format(c) for c in r] ) for r in array_input] ))


if __name__ == '__main__':
    W1 = WireWorldInstance()
    W1.execute()
