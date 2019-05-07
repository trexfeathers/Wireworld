"""
2019-05     Martin Yeo
A python demonstration of Wireworld Cellular Automation (https://en.wikipedia.org/wiki/Wireworld)
"""

import numpy as np
import tkinter as tk
from tkinter import filedialog
from copy import deepcopy
import yaml
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


class WireCell(tk.Button):
    # WireCell is a tkinter button that handles the advancement of its Wireworld state and stores this in an array.
    # It is generated, along with the state array, by the load_array function.
    # Accepts positional coordinates and an initial state as arguments, as well as the standard master.
    def __init__(self, row_input, column_input, state=0, master=None):
        super().__init__(master)
        self.master = master

        # Won't want to overwrite the position occupied by the time label.
        base_column = master.time_label.grid_info()["column"] + 1

        self.row, self.column = row_input, column_input
        self.grid(row=self.row, column=self.column + base_column)
        self.state_change(state)

    def state_change(self, state):
        if state in valid_states:
            self.state = state
        else:
            self.state = 0

        # Store state in numpy array for easy calculations.
        array_states[self.row][self.column] = self.state

        # Represent the Wireworld states using the accepted colours.
        target_colour = color_lookup[self.state]
        self.configure(
            background=target_colour,
            activebackground=target_colour
        )

    def cycle_states(self):
        # Check the cell's own state and its surroundings to provide the next state in line with Wireworld rules.
        state_future = None

        if self.state in (1, 2):
            state_future = self.state + 1
        elif self.state == 3:
            # Conductors will change to heads if they have exactly 1 or 2 neighbouring heads.
            # Use numpy slicing to get the neighbours, then numpy where to filter them.
            slice_limits = [self.row - 1, self.row + 2, self.column - 1, self.column + 2]
            slice_limits = [max(x, 0) for x in slice_limits]    # change negatives to 0
            head_check = array_states[slice_limits[0]:slice_limits[1], slice_limits[2]:slice_limits[3]]
            head_check = np.where(head_check == 1, 1, 0)
            head_check = sum(sum(head_check))

            if head_check in (1, 2):
                state_future = 1

        # Avoid any processing for empty cells.
        if state_future is not None:
            self.state_change(state_future)


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
        global time_ticker
        self.time_label_text.set(str(time_ticker))

    def create_buttons(self):
        self.advance_button = tk.Button(
            master=self,
            text="Next",
            command=lambda: advance_time()
        )

        self.save_button = tk.Button(
            master=self,
            text="Save",
            command=lambda: self.save_file()
        )

        self.test_button = tk.Button(
            master=self,
            text="Test",
            command=lambda: test_function()
        )

        self.advance_button.grid(row=1, column=0)
        self.save_button.grid(row=3, column=0)
        self.test_button.grid(row=5, column=0)



    def save_file(self):
        self.set_directory(is_save_mode=True)
        save_yaml = yaml.dump(array_states)

        try:
            f = open(tk_root.filename, "w+")
        except OSError:
            print("Error accessing path, please try a different path")

        if 'f' in locals():
            f.write(save_yaml)
            f.close()

    def set_directory(self, is_save_mode=True):
        if os.path.exists(tk_root.filename):
            initial_directory = os.path.split(tk_root.filename)[0]
        else:
            initial_directory = "/"

        if is_save_mode:
            tk_root.filename = filedialog.asksaveasfilename(initialdir=initial_directory)
        else:
            tk_root.filename = filedialog.askopenfilename(initialdir=initial_directory)



def array_format_check(array_input):
    # A basic check to make sure the input array has properties that can be worked with
    format_ok = False
    try:
        format_ok = (np.array(array_input).ndim == 2)
    finally:
        if not format_ok:
            raise Exception('Input array format error. Must be 2 dimensional array')


def load_array(array_input):
    array_format_check(array_input)

    # Several functions will need to work with the list of buttons and with the array of states.
    global list_buttons
    global array_states

    list_buttons = []
    array_states = np.array(deepcopy(array_input))
    # Iterate over the rows then the columns of the input array,
    # creating a new button in the appropriate GUI grid position.
    for rx, r in enumerate(array_input):
        for cx, c in enumerate(r):
            new_cell = WireCell(master=gui, state=c, row_input=rx, column_input=cx)
            list_buttons.append(new_cell)


def advance_time():
    # All cells calculate their next state when time advances.
    for b in list_buttons:
        b.cycle_states()

    # Update the time ticker and the GUI label accordingly.
    global time_ticker
    time_ticker += 1
    gui.update_label()
    print_states()


def print_states():
    # Print a readable format of the state array in the terminal. Format empty cells as hyphens.
    array_print = deepcopy(array_states)
    array_print = np.where(array_print == 0, '-', array_print)

    print("\n-- STEP " + str(time_ticker) + " --")
    print('\n'.join( [''.join( ['{:3}'.format(c) for c in r] ) for r in array_print] ))


# def save_file(path):
#     save_yaml = yaml.dump(array_states)
#     if os.path.isfile(path):
#         check_overwrite = input("File already exists, overwrite? (y/n)")
#     if check_overwrite == 'y':
#         try:
#             f = open(path, "w+")
#         except:
#             print("Error accessing path, please try a different path")


def demo():
    # Displays the default array for a moment, advances time once, displays the result.
    load_array(default_array)
    gui.mainloop()

    # gui.update()
    # gui.after(2000)
    #
    # advance_time()
    # print("\n-- TIME ADVANCE --\n")
    #
    # print_states()
    # gui.update()
    # gui.after(2000)
    #
    # print("\n-- END --\n")


def test_function():
    gui.grid_slaves(3, 3)[0].configure(background="Green")


if __name__ == '__main__':
    # Initiate the core architecture.
    time_ticker = 0
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
