"""
2019-05     Martin Yeo
A python demonstration of Wireworld Cellular Automation (https://en.wikipedia.org/wiki/Wireworld)
"""

import numpy as np
import tkinter as tk
from tkinter import filedialog
from copy import deepcopy
import yaml
from yaml import scanner
from yaml import parser
import os.path

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


class TimeTicker:
    def __init__(self):
        self.ticks = 0

    def reset(self):
        self.ticks = 0
        if 'gui' in globals():
            gui.update_label()

    def advance(self):
        self.ticks += 1
        if 'gui' in globals():
            gui.update_label()


class WireCell(tk.Button):
    # WireCell is a tkinter button that represents the corresponding cell in array_states.
    # It is generated, along with the state array, by the load_array function.
    # Accepts positional coordinates and an initial state as arguments, as well as the standard master.
    def __init__(self, row_input, column_input, state=0, master=None):
        super().__init__(master)
        self.master = master

        # Won't want to overwrite the position occupied by the time label.
        # base_column = master.time_label.grid_info()["column"] + 1
        base_column = 1

        self.row, self.column = row_input, column_input
        self.grid(row=self.row, column=self.column + base_column)
        self.state_change(state)

    def state_change(self, state):
        self.state = state

        # Represent the Wireworld states using the accepted colours.
        target_colour = color_lookup[self.state]
        self.configure(
            background=target_colour,
            activebackground=target_colour
        )


class GUI(tk.Frame):
    # GUI is created once within the module, then worked with globally by all functions.
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()

        self.create_label()
        self.create_buttons()

    def create_label(self):
        # Label to hold the current time step.
        self.time_label_text = tk.StringVar()
        self.time_label = tk.Label(master=self, textvariable=self.time_label_text)
        self.time_label.grid(row=0, column=0)

        self.update_label()

    def update_label(self):
        # Get the latest time step and apply it to the time label's variable
        self.time_label_text.set("Step: " + str(time_ticker.ticks))

    def create_buttons(self):
        self.advance_button = tk.Button(
            master=self,
            text="Next",
            command=lambda: advance_time()
        )

        self.save_button = tk.Button(
            master=self,
            text="Save",
            command=lambda: save_file()
        )

        self.load_button = tk.Button(
            master=self,
            text="Load",
            command=lambda: load_file()
        )

        self.advance_button.grid(row=1, column=0)
        self.save_button.grid(row=3, column=0)
        self.load_button.grid(row=4, column=0)


def set_directory(is_save_mode=True):
    initial_directory = os.getcwd()
    try:
        if os.path.exists(tk_root.filename):
            initial_directory = os.path.split(tk_root.filename)[0]
    except AttributeError:
        pass

    config_dict = {
        "initialdir": initial_directory,
        "filetypes": (("yaml files", "*.yaml"), ("all files", "*.*"))
    }

    if is_save_mode:
        tk_root.filename = filedialog.asksaveasfilename(**config_dict)
    else:
        tk_root.filename = filedialog.askopenfilename(**config_dict)


def save_file():
    set_directory(is_save_mode=True)
    if tk_root.filename:
        save_yaml = yaml.dump(array_states.tolist())
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

        save_path = tk_root.filename
        if save_path[-5:] != ".yaml":
            save_path += '.yaml'

        try:
            f = open(save_path, "w+")
        except OSError:
            print("Error accessing path, please try a different path")

        if "f" in locals():
            f.write(save_yaml)
            f.close()

        # if os.path.isfile(path):
        #     check_overwrite = input("File already exists, overwrite? (y/n)")
        # if check_overwrite == 'y':
        #     try:
        #         f = open(path, "w+")
        #     except:
        #         print("Error accessing path, please try a different path")


def load_file():
    set_directory(is_save_mode=False)
    if tk_root.filename:
        load_path = tk_root.filename

        try:
            f = open(load_path, "r")
        except OSError:
            print("Error accessing path, please try a different path")

        if "f" in locals():
            file_contents = f.read()
            f.close()

        array_input = format_yaml(file_contents)

        if array_input is not None:
            load_array(array_input)


def format_yaml(yaml_input):

    yaml_load = None

    try:
        yaml_load = yaml.load(yaml_input)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as exception_:
        print("Invalid YAML format in config file, please try a different path \nError message: \n\n" +
              str(exception_))

    return yaml_load


def array_format_check(array_input):
    # A basic check to make sure the input array has properties that can be worked with
    format_ok = False
    try:
        format_ok = (np.array(array_input).ndim == 2)
    finally:
        if not format_ok:
            raise Exception("Input array format error. Must be 2 dimensional array")


def load_array(array_input):
    array_format_check(array_input)

    # Several functions will need to work with the list of buttons and with the array of states.
    global array_states

    time_ticker.reset()

    array_states = np.array(deepcopy(array_input))
    # Iterate over the rows then the columns of the input array,
    # creating a new button in the appropriate GUI grid position.
    for rx, r in enumerate(array_input):
        for cx, c in enumerate(r):
            state = c
            if state not in valid_states:
                state = 0
            new_cell = WireCell(master=gui, state=state, row_input=rx, column_input=cx)


def advance_time():
    # All cells calculate their next state when time advances.
    cycle_states()
    time_ticker.advance()
    print_states()


def cycle_states():
    # Check the cell's own state and its surroundings to provide the next state in line with Wireworld rules.

    global array_states

    # Store an array of all future states before setting any of them.
    array_states_future = deepcopy(array_states)
    for rx, r in enumerate(array_states):
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
                head_check = array_states[slice_limits[0]:slice_limits[1], slice_limits[2]:slice_limits[3]]
                head_check = np.where(head_check == 1, 1, 0)
                head_check = sum(sum(head_check))

                if head_check in (1, 2):
                    state_future = 1

            # Avoid any processing for empty cells.
            if state_future is not None:
                array_states_future[rx][cx] = state_future

                # Represent the Wireworld states using the accepted colours.
                target_button = gui.grid_slaves(rx, cx + 1)[0]
                target_button.state_change(state_future)

    # Finally update the main array of states.
    array_states = deepcopy(array_states_future)


def print_states():
    # Print a readable format of the state array in the terminal. Format empty cells as hyphens.
    array_print = deepcopy(array_states)
    array_print = np.where(array_print == 0, '-', array_print)

    print("\n-- STEP " + str(time_ticker.ticks) + " --")
    print('\n'.join( [''.join( ['{:3}'.format(c) for c in r] ) for r in array_print] ))


def demo():
    load_array(default_array)
    print_states()
    gui.mainloop()


if __name__ == '__main__':
    # Initiate the core architecture.
    time_ticker = TimeTicker()
    tk_root = tk.Tk()
    gui = GUI(master=tk_root)

    try:
        demo()
    finally:
        # Close down the GUI no matter what.
        try:
            tk_root.destroy()
        except tk.TclError:
            pass
