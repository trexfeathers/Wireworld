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

        self.blank_image = tk.PhotoImage()

        self.wipe_wireworld()

    def __setattr__(self, name, value):
        # keep_playing signals wireworld to continuously advance time steps,
        # whenever the value changes, the gui is put into 'playback mode' or 'pause mode' using toggle_play_button.
        self.__dict__[name] = value
        if name == "keep_playing" and tk_widget_exists(self, "gui_controls"):
            self.gui_controls.toggle_play_button(set_to_play=not value)
        elif name == "generations" and tk_widget_exists(self, "gui_controls"):
            self.gui_controls.update_time_label(value)
        else:
            pass

    ####################################################################################################################
    # WireWorldInstance classes

    class GuiControls(tk.Frame):
        # The container for tkinter widgets controlling the wireworld instance.
        def __init__(self, master, wireworld_parent):
            super().__init__(master)
            self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

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

            self.edit_button = tk.Button(**button_standards)

            self.save_button.grid(column=0, row=1)
            self.load_button.grid(column=0, row=2)
            self.default_button.grid(column=0, row=3)

            self.time_label.grid(column=1, row=0)
            self.advance_button.grid(column=1, row=1)
            self.play_button.grid(column=1, row=2)
            self.reset_button.grid(column=1, row=3)

            self.spacer = tk.Label(master=self, text=" ")
            self.spacer.grid(column=0, row=4)

            self.edit_button.grid(column=0, row=5)

            # Set various widgets to their default states before any wireworld grid has been loaded.
            self.update_time_label(0)
            self.toggle_play_button(set_to_play=True)
            self.toggle_edit_button(edit_shown=False)
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
                self.reset_button,
                self.edit_button
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
            # Also everything in the gui grid if it exists yet:
            if tk_widget_exists(self.wireworld_parent, "gui_edit"):
                toggle_tk_widget(
                    is_enable_mode=set_to_play,
                    toggle_tuple=tuple(self.wireworld_parent.gui_edit.matrix.winfo_children())
                )

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

        def toggle_edit_button(self, edit_shown: bool):
            if edit_shown:
                kwargs = {
                    "text": "Hide Edit Box",
                    "command": lambda: (self.wireworld_parent.toggle_edit_box(edit_visible=not edit_shown))
                }
            else:
                kwargs = {
                    "text": "Show Edit Box",
                    "command": lambda: (self.wireworld_parent.toggle_edit_box(edit_visible=not edit_shown))
                }

            self.edit_button.configure(**kwargs)

    class GuiEdit(tk.Frame):
        # The container for tkinter widgets displaying the wireworld instance.
        def __init__(self, master, wireworld_parent):
            super().__init__(master)
            self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

            top_frame = tk.Frame(master=self)
            top_frame.pack(side=tk.TOP)

            self.matrix = self.GuiEditMatrix(master=self,wireworld_parent=self.wireworld_parent)
            self.matrix.pack(side=tk.TOP)

            for control_type in ("add", "del", "nav"):
                direction_control = self.GuiEditControls(
                    master=top_frame,
                    wireworld_parent=self.wireworld_parent,
                    control_type=control_type
                )
                direction_control.pack(side=tk.LEFT)

            self.pack()

        class GuiEditControls(tk.Frame):
            def __init__(self, master, wireworld_parent, control_type):
                super().__init__(master)
                self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

                kwargs = {
                    "master": self,
                    "wireworld_parent": self.wireworld_parent,
                    "control_type": control_type
                }

                self.ButtonNESW(face="n", **kwargs).grid(row=0, column=2)
                self.ButtonNESW(face="e", **kwargs).grid(row=1, column=3)
                self.ButtonNESW(face="s", **kwargs).grid(row=2, column=2)
                self.ButtonNESW(face="w", **kwargs).grid(row=1, column=1)

                # spacers
                tk.Label(master=self, text=" ").grid(row=1, column=0)
                tk.Label(master=self, text=" ").grid(row=1, column=4)
                tk.Label(master=self, text=" ").grid(row=4, column=1)

                tk.Label(
                    master=self,
                    text=control_type,
                    font="Arial 8 bold"
                ).grid(row=1, column=2)

                self.pack()

            class ButtonNESW(tk.Button):
                def __init__(self, master, wireworld_parent, face, control_type):
                    super().__init__(master)
                    self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

                    if control_type == "add" or (control_type == "nav" and face in ("e", "s")):
                        ranks = 1
                    else:
                        ranks = -1

                    if control_type == "nav":
                        if face in ("n", "s"):
                            axis = 0
                        else:
                            axis = 1
                        command = lambda: self.wireworld_parent.move_edit_box(axis=axis, ranks=ranks)
                    elif control_type in ("add", "del"):
                        command = lambda: self.wireworld_parent.resize(face=face, ranks=ranks)
                    else:
                        command = None

                    button_size = 8
                    self.configure(
                        image=self.wireworld_parent.blank_image,
                        height=button_size,
                        width=button_size,
                        command=command
                    )

        class GuiEditMatrix(tk.Frame):
            def __init__(self, master, wireworld_parent):
                super().__init__(master)
                self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

                # self.top_left = [0, 0]
                # self.dimensions = [1, 1]

                self.reset_grid(self.wireworld_parent.edit_dimensions)

            class ButtonWireCell(tk.Button):
                def __init__(self, master, wireworld_parent, hidden=False):
                    super().__init__(master)
                    self.wireworld_parent = enforce_type_wireworld(wireworld_parent)

                    button_size = 15  # px
                    self.configure(
                        image=self.wireworld_parent.blank_image,  # stops tk using font sizing of buttons (not square)
                        command=lambda: self.edit_state(),
                        height=button_size,
                        width=button_size,
                    )

                    self.hidden = hidden
                    self.state = valid_states[0]

                def __setattr__(self, name, value):
                    # Included to make sure the colour is updated whenever state changes.
                    self.__dict__[name] = value
                    if name == "state":
                        # avoiding self.__dict__[name] = cleanse_state(value) for better performance
                        # Represent the Wireworld state using one of the accepted colours.
                        if len(color_lookup) > self.state:
                            target_colour = color_lookup[self.state]
                            self.configure(
                                background=target_colour,
                                activebackground=target_colour
                            )
                    elif name == "hidden":
                        if value:
                            self.state = valid_states[0]
                            kwargs = {
                                "relief": "flat",
                                "state": "disabled"
                            }
                        else:
                            kwargs = {
                                "relief": "raised",
                                "state": "normal"
                            }
                        self.configure(**kwargs)

                def edit_state(self):
                    # Called when the WireCellEdit button is clicked - this is how the state is edited.
                    # Cycles backwards through states since 3 will be the most common.
                    if self.state <= 0:
                        new_state = 3
                    else:
                        new_state = self.state - 1

                    row = self.grid_info()["row"] + self.wireworld_parent.edit_top_left[0]
                    column = self.grid_info()["column"] + self.wireworld_parent.edit_top_left[1]

                    array_changes = [(row, column, new_state)]
                    self.wireworld_parent.update_states(array_changes=array_changes)

            def reset_grid(self, dimensions):
                for i in self.grid_slaves():
                    i.destroy()

                for row in range(dimensions[0]):
                    for column in range(dimensions[1]):
                        self.ButtonWireCell(
                            master=self,
                            wireworld_parent=self.wireworld_parent,
                        ).grid(
                            row=row,
                            column=column
                        )

                self.refresh_grid()

            def refresh_grid(self):
                array_shape = np.shape(self.wireworld_parent.array_states)
                for target_cell in self.grid_slaves():
                    # target_cell = i[0]
                    hidden =\
                        target_cell.grid_info()["row"] >= array_shape[0] or\
                        target_cell.grid_info()["column"] >= array_shape[1]
                    target_cell.hidden = hidden

                row_offset = self.wireworld_parent.edit_top_left[0]
                column_offset = self.wireworld_parent.edit_top_left[1]
                row_count = self.wireworld_parent.edit_dimensions[0]
                column_count = self.wireworld_parent.edit_dimensions[1]
                array_refresh = self.wireworld_parent.array_states[
                                row_offset:row_offset + row_count,
                                column_offset:column_offset + column_count
                                ]

                for rx, r in enumerate(array_refresh):
                    for cx, c in enumerate(r):
                        state = c
                        target_button = self.grid_slaves(
                            row=rx,
                            column=cx
                        )[0]
                        target_button.state = state

            def update_states(self, array_changes):
                enforce_coords_array(array_changes)
                row_offset = self.wireworld_parent.edit_top_left[0]
                column_offset = self.wireworld_parent.edit_top_left[1]
                row_count = self.wireworld_parent.edit_dimensions[0]
                column_count = self.wireworld_parent.edit_dimensions[1]

                for row, column, state in array_changes:
                    if row_offset <= row < row_offset + row_count and \
                            column_offset <= column < column_offset + column_count:

                        target_button = self.grid_slaves(
                            row=row - row_offset,
                            column=column - column_offset
                        )[0]
                        target_button.state = state

    class GuiMap(tk.Canvas):
        def __init__(self, master, wireworld_parent):
            super().__init__(master)
            self.wireworld_parent = enforce_type_wireworld(wireworld_parent)
            self.color_lookup = ("#646464",) + color_lookup[1:]
            self.cell_size = 5
            self.reset_canvas()

            # self.pack(side="top", fill="both", expand="yes")
            self.pack()

        def reset_canvas(self):
            self.delete("all")
            array_shape = np.shape(self.wireworld_parent.array_states)
            self.array_cells = np.empty(array_shape, dtype=np.int32)    # can't copy array_states - not storing states
            self.configure(
                height=max(array_shape[0] * self.cell_size, 100),
                width=max(array_shape[1] * self.cell_size, 100)
            )

            for row in range(array_shape[0]):
                for column in range(array_shape[1]):
                    self.create_cell(row=row, column=column)

            self.highlight_edit_box(self.wireworld_parent.edit_top_left, self.wireworld_parent.edit_dimensions)

            self.bind("<Button-1>", self.click_event)

        def create_cell(self, row, column):
            c_lower = column * self.cell_size
            r_lower = row * self.cell_size
            c_upper = c_lower + self.cell_size
            r_upper = r_lower + self.cell_size
            self.array_cells[row][column] = self.create_rectangle(
                c_lower,
                r_lower,
                c_upper,
                r_upper,
                outline=self.color_lookup[0],
                fill=self.color_lookup[0]
            )

        def highlight_edit_box(self, top_left=(0, 0), dimensions=(1, 1), highlight_nothing=False):
            r_lower = top_left[0]
            c_lower = top_left[1]
            r_upper = r_lower + dimensions[0]
            c_upper = c_lower + dimensions[1]

            # array_edit = self.array_cells[r_lower:r_upper, c_lower:c_upper]

            for rx, r in enumerate(self.array_cells):
                for cx, c in enumerate(r):
                    target_rectangle = c
                    if r_lower <= rx < r_upper and c_lower <= cx < c_upper and not highlight_nothing:
                        target_colour = "#d9d9d9"
                    else:
                        target_colour = self.color_lookup[0]
                    self.itemconfigure(target_rectangle, outline=target_colour)

        def update_states(self, array_changes):
            enforce_coords_array(array_changes)
            for row, column, state in array_changes:
                target_colour = self.color_lookup[state]
                self.itemconfigure(self.array_cells[row][column], fill=target_colour)
            self.update()

        def click_event(self, event):
            x_scaled = event.x / self.cell_size
            y_scaled = event.y / self.cell_size
            x_centered = int(x_scaled - (self.wireworld_parent.edit_dimensions[0] / 2))
            y_centered = int(y_scaled - (self.wireworld_parent.edit_dimensions[1] / 2))
            self.wireworld_parent.new_edit_box((y_centered, x_centered))

    ####################################################################################################################
    # WireWorldInstance methods

    def execute(self):
        # The basic behaviour of a wireworld instance.
        try:
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

        self.array_states = np.array(deepcopy(array_input))
        self.array_states_original = deepcopy(self.array_states)

        self.create_map_window()
        self.update_states()

        # print_states(array_input=self.array_states, ticks=self.generations)

    def update_states(self, array_changes=None):
        if array_changes is None:
            array_changes = []
            for rx, r in enumerate(self.array_states):
                for cx, c in enumerate(r):
                    state = c
                    array_changes.append((rx, cx, state))

        enforce_coords_array(array_changes)

        for row, column, state in array_changes:
            self.array_states[row][column] = state

        if tk_widget_exists(self, "gui_map"):
            self.gui_map.update_states(array_changes)

        if tk_widget_exists(self, "gui_edit"):
            if tk_widget_exists(self.gui_edit, "matrix"):
                if self.gui_edit.matrix.winfo_exists():
                    self.gui_edit.matrix.update_states(array_changes)

    def create_map_window(self):
        if tk_widget_exists(self, "window_map"):
            self.window_map.destroy()
        self.window_map = tk.Toplevel(self.tk_root)
        self.window_map.title("Wireworld Map")
        # Set to re-disable relevant gui controls when the edit is closed.
        self.window_map.protocol("WM_DELETE_WINDOW", self.map_on_closing)

        if tk_widget_exists(self, "gui_map"):
            self.gui_map.destroy()
        self.gui_map = self.GuiMap(master=self.window_map, wireworld_parent=self)

        # Position the edit window underneath the control window.
        geometry_controls = parse_tk_geometry(self.tk_root.geometry())
        geometry_map = parse_tk_geometry(self.window_map.geometry())
        geometry_map[3] = geometry_controls[3] + 8
        geometry_map[2] = geometry_controls[2] + geometry_controls[0] + 20
        self.window_map.geometry("+%d+%d" % tuple(geometry_map[2:4]))

        # Enable relevant gui controls now the map has been created
        self.gui_controls.toggle_interaction_controls(is_enable_mode=True)

        self.toggle_edit_box(edit_visible=False)

    def map_on_closing(self):
        # Run when a grid window is closed.
        self.wipe_wireworld()
        self.toggle_edit_box(edit_visible=False)
        if tk_widget_exists(self, "gui_controls"):
            self.gui_controls.toggle_interaction_controls(is_enable_mode=False)
        if tk_widget_exists(self, "window_map"):
            self.window_map.destroy()
        if tk_widget_exists(self, "window_edit"):
            self.window_edit.destroy()

    def create_edit_window(self):
        # Create and position a new GUI window independent of the controls window.

        # Initiate or re-initiate the window that will contain the edit gui.
        # An existing window is destroyed not re-used since several 'reset' methods are held within map_on_closing.
        self.destroy_edit_window()
        self.window_edit = tk.Toplevel(self.tk_root)
        self.window_edit.title("Wireworld Edit")
        # Set to re-disable relevant gui controls when the edit is closed.
        self.window_edit.protocol("WM_DELETE_WINDOW", self.edit_on_closing)

        # Initiate or re-initiate the frame that will contain the edit gui.
        if tk_widget_exists(self, "gui_edit"):
            self.gui_edit.destroy()
        self.gui_edit = self.GuiEdit(master=self.window_edit, wireworld_parent=self)

        # Position the edit window underneath the control window.
        geometry_controls = parse_tk_geometry(self.tk_root.geometry())
        geometry_edit = parse_tk_geometry(self.window_edit.geometry())
        geometry_edit[3] = geometry_controls[3] + geometry_controls[1] + 50
        geometry_edit[2] = geometry_controls[2] + 10
        self.window_edit.geometry("+%d+%d" % tuple(geometry_edit[2:4]))

        self.new_edit_box((tuple(self.edit_top_left)))

        # Enable relevant gui controls now the edit has been created
        # self.toggle_edit_box(edit_visible=True)

    def edit_on_closing(self):
        self.toggle_edit_box(edit_visible=False)
        if tk_widget_exists(self, "gui_edit"):
            self.gui_edit.destroy()
        if tk_widget_exists(self, "window_edit"):
            self.window_edit.destroy()

    def destroy_edit_window(self):
        if tk_widget_exists(self, "window_edit"):
            self.window_edit.destroy()

    def advance_step(self):
        # Advance the wireworld instance to the next time step.

        array_changes = cycle_states(array_input=self.array_states)
        self.update_states(array_changes=array_changes)

        self.generations += 1
        # Terminal output of states.
        # print_states(array_input=self.array_states, ticks=self.generations)

    def continuous_play_start(self):
        # Advance wireworld to the next time step every 0.5 seconds.
        self.keep_playing = True
        time_base = time.time()

        while self.keep_playing:
            # The tk elements are updated continuously during playback.
            self.tk_root.update()
            if time.time() - time_base > 0.05:
                # Reset time_base for future comparisons.
                time_base = time.time()
                self.advance_step()

    def continuous_play_pause(self):
        # Halts the loop within continuous_play_start if it is running.
        self.keep_playing = False

    def wipe_wireworld(self):
        # New time ticker, new state array.
        # self.time_ticker = self.TimeTicker(wireworld_parent=self)
        self.generations = 0
        self.array_states = np.array([[0]])     # single empty cell
        if "edit_top_left" not in self.__dict__:
            self.edit_top_left = [0, 0]
        self.edit_dimensions = [10, 10]

    def limit_edit_box(self, axis: int, new_value: int):
        array_shape = np.shape(self.array_states)
        new_value = min(new_value, array_shape[axis] - self.edit_dimensions[axis])
        new_value = max(new_value, 0)
        return new_value

    def move_edit_box(self, axis: int, ranks: int):
        if type(axis) is int and type(ranks) is int:
            new_value = self.edit_top_left[axis] + ranks
            new_value = self.limit_edit_box(axis=axis, new_value=new_value)
            self.edit_top_left[axis] = new_value
        self.refresh_edit_box()

    def new_edit_box(self, top_left: tuple):
        if np.shape(top_left) == (2,):
            new_top_left = list(top_left)
            for ix, i in enumerate(new_top_left):
                new_top_left[ix] = self.limit_edit_box(axis=ix, new_value=i)

            self.edit_top_left = new_top_left
        self.refresh_edit_box()

    def refresh_edit_box(self):
        if tk_widget_exists(self, "gui_map"):
            self.gui_map.highlight_edit_box(self.edit_top_left, self.edit_dimensions)

        if tk_widget_exists(self, "gui_edit"):
            if tk_widget_exists(self.gui_edit, "matrix"):
                self.gui_edit.matrix.refresh_grid()

        # self.update_states()

    def toggle_edit_box(self, edit_visible: bool):
        if edit_visible:
            self.create_edit_window()
        else:
            self.destroy_edit_window()

        if tk_widget_exists(self, "gui_controls"):
            self.gui_controls.toggle_edit_button(edit_shown=edit_visible)
        if tk_widget_exists(self, "gui_map"):
            self.gui_map.highlight_edit_box(
                top_left=self.edit_top_left,
                dimensions=self.edit_dimensions,
                highlight_nothing=not edit_visible
            )

    def reset_to_original(self):
        # array_states_original is recorded from the initial array_states when parse_array is run.
        # This allows the user to return to the states of time step 0.
        if "array_states_original" in self.__dict__:
            self.parse_array(self.array_states_original)

    def resize(self, face: str, ranks=1):
        self.array_states, axis_shift, rank_shift = resize_array(array_input=self.array_states, face=face, ranks=ranks)
        array_shape = np.shape(self.array_states)
        if rank_shift != 0 and array_shape[axis_shift] > self.edit_dimensions[axis_shift]:
            # self.gui_edit.matrix.top_left_shift(axis_shift, rank_shift)
            self.move_edit_box(axis=axis_shift, ranks=rank_shift)
        self.gui_map.reset_canvas()
        # self.gui_edit.matrix.reset_grid()
        self.gui_edit.matrix.refresh_grid()
        self.update_states()


########################################################################################################################
# independent functions


def enforce_type_wireworld(input_class: WireWorldInstance):
    # Used by several classes to make sure they have been provided with a reference to a parent WireWorldInstance
    # (since they could be called independently).
    if not isinstance(input_class, WireWorldInstance):
        raise Exception("class type check failed = must be type WireWorldInstance")
    else:
        return input_class


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


def cleanse_state(state):
    # Ensure state is one that is part of wireworld.
    if state not in valid_states:
        state = valid_states[0]

    return state


def check_2d_array(array_input):
    # A basic check to make sure the input array has properties that can be worked with.
    format_ok = False
    try:
        format_ok = (np.array(array_input).ndim == 2)
    finally:
        return format_ok


def enforce_coords_array(array_input):
    # format_ok = False
    try:
        np.ndim(array_input) == 2 and np.shape(array_input)[1] == 3
    except:
        raise Exception("Invalid array dimensions. Expected 2d array where second dimension has 3 elements")


def cleanse_array(array_input):
    # Force the array's compliance with assumptions throughout this module.
    if not check_2d_array(array_input):
        raise Exception("Input array format error. Must be 2 dimensional array")

    for rx, r in enumerate(array_input):
        for cx, c in enumerate(r):
            c = cleanse_state(c)

    return array_input


def cycle_states(array_input: np.ndarray):
    # Check the cell's own state and its surroundings to provide the next state in line with Wireworld rules.

    array_input = cleanse_array(array_input)

    # Store an array of all future states before setting any of them.
    # array_future = deepcopy(array_input)
    array_changes = []
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
                # array_future[rx][cx] = state_future
                # Provide a minimal list of those coordinates that have changed, for use in updating gui cells.
                array_changes.append([rx, cx, state_future])

    return array_changes


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


def parse_tk_geometry(geometry_input: str):
    # Convert tk's specific geometry string into a 4 item list
    geometry_list = geometry_input.split("+")
    geometry_dimensions = geometry_list[0].split("x")
    geometry_position = geometry_list[1:3]
    geometry_parsed = geometry_dimensions + geometry_position
    geometry_parsed = [int(i) for i in geometry_parsed]
    return geometry_parsed


def resize_array(array_input, face: str, ranks=1):
    if not check_2d_array(array_input):
        raise Exception("Input array format error. Must be 2 dimensional array")

    try:
        abs_ranks = int(abs(ranks))
    except ValueError:
        raise Exception("Invalid ranks value. Must be integer")

    array_shape = np.shape(array_input)
    kwargs = {"arr": array_input}

    if face in ["n", "s"]:
        axis_shift = 0
        kwargs["axis"] = axis_shift
        kwargs["values"] = np.zeros((abs_ranks, array_shape[1]), dtype=np.int8)     # blank rows
    elif face in ["e", "w"]:
        axis_shift = 1
        kwargs["axis"] = axis_shift
        if face == "e":
            kwargs["values"] = np.zeros((array_shape[0], abs_ranks), dtype=np.int8)
            # blank rows that are converted to columns by np.append()
        else:
            kwargs["values"] = np.zeros((abs_ranks, array_shape[0]), dtype=np.int8)     # blank columns
    else:
        raise Exception("Invalid face value. Must be on of (n, e, s, w)")

    if ranks < 0:       # deletion mode
        del kwargs["values"]
        if face in ("n", "w"):
            kwargs["obj"] = np.s_[:abs_ranks]
        elif face in ("e", "s"):
            kwargs["obj"] = np.s_[-abs_ranks:]
        array_output = np.delete(**kwargs)

    elif ranks > 0:     # addition mode
        if face in ("n", "w"):
            kwargs["obj"] = 0
            array_output = np.insert(**kwargs)
        elif face in ("e", "s"):
            array_output = np.append(**kwargs)

    else:
        raise Exception("Invalid ranks value. Must be more or less than 0")

    rank_shift = ranks if face in ("n", "w") else 0

    if "array_output" in locals():
        return array_output, axis_shift, rank_shift
    else:
        print("No array to return")


def tk_widget_exists(widget_parent, widget_name: str):
    exists = False
    try:
        widget = widget_parent.__dict__[widget_name]
        exists = widget.winfo_exists()
    except (KeyError, NameError):
        pass

    return bool(exists)

########################################################################################################################


if __name__ == "__main__":
    W1 = WireWorldInstance()
    W1.execute()
