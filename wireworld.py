"""
2019-05     Martin Yeo
A python demonstration of Wireworld Cellular Automation (https://en.wikipedia.org/wiki/Wireworld)
"""

import numpy as np
import os
import time
import tkinter as tk
import yaml

from copy import deepcopy
from tkinter import filedialog
from yaml import parser
from yaml import scanner

array_default = [
    [0, 0, 0, 3, 0, 0, 0],
    [0, 3, 0, 3, 0, 3, 0],
    [3, 0, 3, 0, 3, 0, 3],
    [1, 0, 0, 3, 0, 0, 1],
    [2, 0, 3, 3, 3, 0, 2],
    [0, 3, 0, 3, 0, 3, 0],
    [0, 0, 0, 3, 0, 0, 0],
]

valid_states = (0, 1, 2, 3)
color_lookup = ("#d9d9d9", "#0000ff", "#ff0000", "#ffff00")


class WireWorldInstance:
    # A class containing any classes and non-independent methods needed to run a wireworld instance.

    def __init__(self):
        self.keep_playing = False

        # Initialise the basic architecture.
        self.tk_root = tk.Tk()
        self.gui_controls = self.GuiControls(master=self.tk_root, wireworld_parent=self)
        self.tk_root.title("Wireworld Controls")

        self.wipe_wireworld()

    def __setattr__(self, name, value):
        # keep_playing signals wireworld to continuously advance time steps,
        # whenever the value changes, the gui is put into 'playback mode' or 'pause mode' using toggle_play_button.
        self.__dict__[name] = value
        if name == "keep_playing" and "gui_controls" in self.__dict__:
            self.gui_controls.toggle_play_button(not value)

    ####################################################################################################################
    # WireWorldInstance classes

    class TimeTicker:
        # Simple class containing the 'ticks' property.
        # When ticks changes value, the gui label is updated to reflect this.
        def __init__(self, wireworld_parent):
            # Need to ensure a wireworld parent has been provided (necessary since class could be called independently).
            enforce_type_wireworld(wireworld_parent)
            if "gui_controls" in wireworld_parent.__dict__:
                self.gui_controls = wireworld_parent.gui_controls
            self.ticks = 0

        def __setattr__(self, name, value):
            self.__dict__[name] = value
            if name == "ticks" and "gui_controls" in self.__dict__:
                self.gui_controls.update_time_label(self.ticks)

    class GuiControls(tk.Frame):
        # The container for tkinter widgets controlling the wireworld instance.
        def __init__(self, master, wireworld_parent):
            # Need to ensure a wireworld parent has been provided (necessary since class could be called independently).
            enforce_type_wireworld(wireworld_parent)
            self.wireworld_parent = wireworld_parent
            super().__init__(master)
            self.master = master

            # Used as kwargs when initiating every widget.
            button_standards = {
                "master": self,
                "width": 15
            }

            # tk.StringVar() allows time_label_text to be updated at later points
            self.time_label_text = tk.StringVar()
            self.time_label = tk.Label(
                textvariable=self.time_label_text,
                **button_standards
            )

            self.advance_button = tk.Button(
                text="Next Time Step",
                command=lambda: self.wireworld_parent.advance_step(),
                **button_standards
            )

            self.save_button = tk.Button(
                text="Save States",
                command=lambda: self.wireworld_parent.save_load_states(is_save_mode=True),
                **button_standards
            )

            self.load_button = tk.Button(
                text="Load States",
                command=lambda: self.wireworld_parent.save_load_states(is_save_mode=False),
                **button_standards
            )

            self.default_button = tk.Button(
                text="Default States",
                command=lambda: self.wireworld_parent.parse_array(array_default),
                **button_standards
            )

            self.play_button = tk.Button(**button_standards)

            self.reset_button = tk.Button(
                text="Reset to Step 0",
                command=lambda: self.wireworld_parent.reset_to_original(),
                **button_standards
            )

            # self.spacer = tk.Label(master=self, text=" ")
            # self.spacer.grid(row=2, column=0, sticky="we")

            self.save_button.grid(column=0, row=1)
            self.load_button.grid(column=0, row=2)
            self.default_button.grid(column=0, row=3)

            self.time_label.grid(column=1, row=0)
            self.advance_button.grid(column=1, row=1)
            self.play_button.grid(column=1, row=2)
            self.reset_button.grid(column=1, row=3)

            # Set various widgets to their default states before any wireworld grid has been loaded.
            self.update_time_label(0)
            self.toggle_play_button(set_to_play=True)
            self.toggle_interaction_controls(is_enable_mode=False)

            self.pack()

        def update_time_label(self, ticks: int):
            # Change the time label variable to an integer provided.
            self.time_label_text.set("{:05d}".format(ticks))

        def toggle_interaction_controls(self, is_enable_mode: bool):
            # Enable/disable any widgets that relate to an existing wireworld - only enable when one exists.
            # This method is used during initial setup, whenever an array is parsed, and whenever the grid is closed.
            toggleable = (
                self.time_label,
                self.advance_button,
                self.save_button,
                self.play_button,
                self.reset_button
            )

            toggle_tk_widget(is_enable_mode=is_enable_mode, toggle_tuple=toggleable)

        def toggle_play_button(self, set_to_play: bool):
            # During playback, the only possible action is to pause the playback.
            # When paused, all other actions are re-enabled.

            # Enable/disable all widgets other than the play/pause button and the time step indicator.
            control_list = self.winfo_children()
            for i in [self.play_button, self.time_label]:
                control_list.remove(i)

            toggle_tk_widget(is_enable_mode=set_to_play, toggle_tuple=tuple(control_list))

            # Change the text and function of the play/pause button depending on the current playback state.
            if set_to_play:
                text_var = "Play Time Steps"
                command_var = lambda: (self.wireworld_parent.continuous_play_start())
            else:
                text_var = "Pause Playback"
                command_var = lambda: (self.wireworld_parent.continuous_play_pause())

            self.play_button.configure(
                text=text_var,
                command=command_var
            )

    class GuiGrid(tk.Frame):
        # The container for tkinter widgets displaying the wireworld instance.
        def __init__(self, master):
            super().__init__(master)
            self.master = master
            self.pack()

    class WireCell(tk.Button):
        # WireCell is a tkinter button that represents the corresponding cell in array_states.
        # It is generated, along with the state array, by the parse_array function.
        # Accepts positional coordinates and an initial state as arguments, as well as the standard master.
        def __init__(self, master, wireworld_parent, row_input, column_input, state=0):
            # Need to ensure a wireworld parent has been provided (necessary since class could be called independently).
            enforce_type_wireworld(wireworld_parent)
            self.wireworld_parent = wireworld_parent

            super().__init__(master)
            self.master = master

            self.row, self.column = row_input, column_input
            self.grid(row=self.row, column=self.column)
            self.configure(command=lambda: self.edit_state())

            self.state = state

        def __setattr__(self, name, value):
            # Included to make sure the colour is updated whenever state changes.
            self.__dict__[name] = value
            if name == "state":
                # state is limited to one of the correct values.
                if self.state not in valid_states:
                    self.state = valid_states[0]

                # Represent the Wireworld state using one of the accepted colours.
                if len(color_lookup) > self.state:
                    target_colour = color_lookup[self.state]
                    self.configure(
                        background=target_colour,
                        activebackground=target_colour
                    )

        def edit_state(self):
            if self.state <= 0:
                self.state = 3
            else:
                self.state -= 1

            self.wireworld_parent.array_states[self.row][self.column] = self.state

    ####################################################################################################################
    # WireWorldInstance methods

    def execute(self):
        # The basic behaviour of a wireworld instance.
        try:
            # self.parse_array(array_default)
            # print_states(self.array_states, self.time_ticker.ticks)
            self.tk_root.mainloop()
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

        # Populate filename
        if is_save_mode:
            self.tk_root.filename = filedialog.asksaveasfilename(**config_dict)
        else:
            self.tk_root.filename = filedialog.askopenfilename(**config_dict)

        # Run specific save or load behaviour ONLY if filename is populated.
        if self.tk_root.filename:
            if is_save_mode:
                save_file(self.tk_root.filename, self.array_states)
            else:
                content = load_file(self.tk_root.filename)
                self.parse_array(content)

    def parse_array(self, array_input):
        # Take an input array and process it as a wireworld time step - specifically step 0.

        array_input = cleanse_array(array_input)

        self.wipe_wireworld()
        self.create_grid_window()

        self.array_states = np.array(deepcopy(array_input))
        self.array_states_original = deepcopy(self.array_states)
        # Iterate over the rows then the columns of the input array,
        # creating a new button in the appropriate GUI grid position.
        for rx, r in enumerate(array_input):
            for cx, c in enumerate(r):
                state = c
                self.WireCell(
                    master=self.gui_grid,
                    wireworld_parent=self,
                    state=state,
                    row_input=rx,
                    column_input=cx
                )

        print_states(array_input=self.array_states, ticks=self.time_ticker.ticks)

    def create_grid_window(self):
        # Create and position a new GUI window independent of the controls window.

        def parse_tk_geometry(geometry_input: str):
            # Convert tk's specific geometry string into a 4 item list
            geometry_list = geometry_input.split("+")
            geometry_dimensions = geometry_list[0].split("x")
            geometry_position = geometry_list[1:3]
            geometry_parsed = geometry_dimensions + geometry_position
            geometry_parsed = [int(i) for i in geometry_parsed]
            return geometry_parsed

        # Initiate or re-initiate the window that will contain the wireworld grid.
        if "window_grid" in self.__dict__:
            self.window_grid.destroy()
        self.window_grid = tk.Toplevel(self.tk_root)
        self.window_grid.title("Wireworld Grid")

        # Initiate or re-initiate the frame that will contain the wireworld grid.
        if "gui_grid" in self.__dict__:
            self.gui_grid.destroy()
        self.gui_grid = self.GuiGrid(master=self.window_grid)

        # Position the grid window to the right of the control window.
        geometry_controls = parse_tk_geometry(self.tk_root.geometry())
        geometry_grid = parse_tk_geometry(self.window_grid.geometry())
        geometry_grid[3] = geometry_controls[3]
        geometry_grid[2] = geometry_controls[2] + geometry_controls[0] + 20
        self.window_grid.geometry("+%d+%d" % tuple(geometry_grid[2:4]))

        # Enable relevant gui controls now the grid has been created
        self.gui_controls.toggle_interaction_controls(is_enable_mode=True)

        # Set to re-disable relevant gui controls when the grid is closed
        self.window_grid.protocol("WM_DELETE_WINDOW", self.grid_on_closing)

    def advance_step(self):
        # Advance the wireworld instance to the next time step.

        self.array_states, changed_coords = cycle_states(self.array_states)

        for rx, cx in changed_coords:
            # changed_coords provides a list, which is used to identify each button that needs updating.
            target_button = self.gui_grid.grid_slaves(rx, cx)[0]
            target_button.state = self.array_states[rx][cx]

        self.time_ticker.ticks += 1
        # Terminal output of states.
        print_states(array_input=self.array_states, ticks=self.time_ticker.ticks)

    def continuous_play_start(self):
        # Advance wireworld to the next time step every 0.5 seconds.
        self.keep_playing = True
        time_base = time.time()

        while self.keep_playing:
            # The tk elements are updated continuously during playback.
            self.tk_root.update()
            if time.time() - time_base > 0.5:
                # Reset time_base for future comparisons.
                time_base = time.time()
                self.advance_step()

    def continuous_play_pause(self):
        # Halts the loop within continuous_play_start if it is running.
        self.keep_playing = False

    def grid_on_closing(self):
        # Run when a grid window is closed.
        self.wipe_wireworld()
        if "gui_controls" in self.__dict__:
            self.gui_controls.toggle_interaction_controls(is_enable_mode=False)
        if "window_grid" in self.__dict__:
            self.window_grid.destroy()

    def wipe_wireworld(self):
        # New time ticker, new state array.
        self.time_ticker = self.TimeTicker(wireworld_parent=self)
        self.array_states = np.array([[0]])     # single empty cell

    def reset_to_original(self):
        # array_states_original is recorded from the initial array_states when parse_array is run.
        # This allows the user to return to the states of time step 0.
        if "array_states_original" in self.__dict__:
            self.parse_array(self.array_states_original)

########################################################################################################################
# independent functions


def enforce_type_wireworld(input_class: WireWorldInstance):
    # Used by several classes to make sure they have been provided with a reference to a parent WireWorldInstance.
    if not isinstance(input_class, WireWorldInstance):
        raise Exception("class type check failed = must be type WireWorldInstance")


def save_file(path_input: str, array_input):
    # Save the contents of array_states to a YAML file using the path selected by the user.

    # Only necessary if function is called outside a WireWorldInstance class
    if not check_2d_array(array_input):
        print("Not saving array. Must be 2 dimensional array")
        return

    yaml_save = yaml.dump(array_input.tolist())
    # Include a comment section at the top of the file to instruct any direct editing of the file.
    yaml_save = "\n".join((
        "# this file should be YAML format containing a rectangular array of states (0-3) for use in Wireworld",
        "# there should be no other YAML content",
        "# e.g.",
        "# - [0, 1, 2]",
        "# - [1, 0, 1]",
        "# - [3, 3, 3]",
        "",
        yaml_save
    ))

    # Add the .yaml suffix if not present.
    if path_input[-5:] != ".yaml":
        path_input += ".yaml"

    # Attempt to access the path provided.
    try:
        f = open(path_input, "w+")
    except OSError:
        print("Error accessing path, please try a different path")

    if "f" in locals():
        f.write(yaml_save)
        f.close()


def load_file(input_path: str):
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
        yaml_content = format_yaml(file_contents)
        return yaml_content
    else:
        print("Nothing to load")
        return None


def format_yaml(string_input: str):
    # Attempt to an input variable as YAML content.
    yaml_content = None

    try:
        yaml_content = yaml.load(string_input)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as exception:
        print("Invalid YAML format in config file, please try a different path \nError message: \n\n" +
              str(exception))

    return yaml_content


def check_2d_array(array_input):
    # A basic check to make sure the input array has properties that can be worked with.
    format_ok = False
    try:
        format_ok = (np.array(array_input).ndim == 2)
    finally:
        return format_ok


def cleanse_array(array_input):
    # Force the array's compliance with assumptions throughout this module.
    if not check_2d_array(array_input):
        raise Exception("Input array format error. Must be 2 dimensional array")

    for rx, r in enumerate(array_input):
        for cx, c in enumerate(r):
            state = c
            if state not in valid_states:
                array_input[rx][cx] = valid_states[0]

    return array_input


def cycle_states(array_input: np.ndarray):
    # Check the cell's own state and its surroundings to provide the next state in line with Wireworld rules.

    array_input = cleanse_array(array_input)

    # Store an array of all future states before setting any of them.
    array_future = deepcopy(array_input)
    changed_coords = []
    for rx, r in enumerate(array_input):
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
                head_check = array_input[slice_limits[0]:slice_limits[1], slice_limits[2]:slice_limits[3]]
                head_check = np.where(head_check == 1, 1, 0)
                head_check = sum(sum(head_check))

                if head_check in (1, 2):
                    state_future = 1

            if state_future is not None:    # avoid any processing for empty cells
                # Set the calculated future state.
                array_future[rx][cx] = state_future
                # Provide a minimal list of those coordinates that have changed, for use in updating gui cells.
                changed_coords.append([rx, cx])

    return array_future, changed_coords


def print_states(array_input: np.ndarray, ticks: int):
    # Print a readable format of the state array in the terminal. Format empty cells as hyphens.
    if type(array_input) is np.ndarray:
        array_input = np.where(array_input == 0, "-", array_input)
        print("\n-- STEP " + str(ticks) + " --")
        print("\n".join( [''.join( ["{:3}".format(c) for c in r] ) for r in array_input] ))


def toggle_tk_widget(is_enable_mode: bool, toggle_tuple: tuple):
    # Generic function to enable/disable any tkinter widget that is listed in the tuple.
    state_toggle = "normal" if is_enable_mode else "disable"
    for control in toggle_tuple:
        # try/except avoids issues if the user inputs other objects in the tuple.
        try:
            control.configure(state=state_toggle)
        except AttributeError:
            pass

########################################################################################################################


if __name__ == "__main__":
    W1 = WireWorldInstance()
    W1.execute()
