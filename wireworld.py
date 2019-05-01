import numpy as np
import pprint
import tkinter as tk
from copy import deepcopy

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
    def __init__(self, row, column, state=0, master=None):
        super().__init__(master)
        self.master = master

        self.row = row
        self.column = column
        self.state_change(state)

    def __repr__(self):
        return str(self.state) if self.state > 0 else '_'

    def __str__(self):
        return str(self.state) if self.state > 0 else '_'

    def state_change(self, state):
        if state in valid_states:
            self.state = state
        else:
            self.state = 0

        array_states[self.row][self.column] = self.state

        target_colour = color_lookup[self.state]
        self.configure(
            background=target_colour,
            activebackground=target_colour
        )

    def cycle_states(self):
        state_future = None

        if self.state in (1, 2):
            state_future = self.state + 1
        elif self.state == 3:
            slice_limits = [self.row - 1, self.row + 2, self.column - 1, self.column + 2]
            slice_limits = [max(x, 0) for x in slice_limits]
            head_check = array_states[slice_limits[0]:slice_limits[1], slice_limits[2]:slice_limits[3]]
            head_check = np.where(head_check == 1, 1, 0)
            head_check = sum(sum(head_check))

            if head_check > 0:
                state_future = 1

        if state_future is not None:
            self.state_change(state_future)


class GUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()


def array_format_check(array_input):
    format_ok = False
    try:
        format_ok = (np.array(array_input).ndim == 2)
    finally:
        if not format_ok:
            raise Exception('Input array format error. Must be 2 dimensional array')


def load_array(array_input):
    array_format_check(array_input)

    root = tk.Tk()
    gui = GUI(master=root)

    array_buttons = deepcopy(array_input)
    global array_states
    array_states = np.array(deepcopy(array_input))
    for rx, r in enumerate(array_input):
        for cx, c in enumerate(r):
            new_cell = WireCell(master=gui, state=c, row=rx, column=cx)
            new_cell.grid(row=rx, column=cx)
            array_buttons[rx][cx] = new_cell

    return array_buttons, array_states, gui


def advance_time():
    for r in array_buttons:
        for c in r:
            c.cycle_states()


if __name__ == '__main__':
    array_buttons, array_states, gui_1 = load_array(default_array)

    pprint.pprint(array_states)

    advance_time()
    print("\n-- TIME ADVANCE --\n")

    array_buttons, array_states, gui_2 = load_array(default_array)

    pprint.pprint(array_states)

    gui_1.mainloop()
    gui_2.mainloop()