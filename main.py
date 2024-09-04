import tkinter as tk
import csv
import json
from datetime import datetime
from tkinter import messagebox, filedialog
from tkinter import simpledialog
from tkinter import ttk, colorchooser
from collections import deque
import openpyxl
import xlwt
import xlrd
import pandas as pd
import ezodf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ezodf import Sheet
from odf.opendocument import OpenDocumentText
from odf.text import P
version = '(Version 0.66) '
window = tk.Tk()
window.file_extension = ''
listbox = None
counter = 1

class Command:
  def execute(self):
    pass

  def undo(self):
    pass

class AddNumberCommand(Command):
  def __init__(self, listbox, number):
    self.listbox = listbox
    self.number = number
    self.index = None

  def execute(self):
    self.index = self.listbox.size()
    self.listbox.insert(tk.END, f"{self.index + 1}. {self.number}")

  def undo(self):
    if self.index is not None:
      self.listbox.delete(self.index)

class DeleteNumberCommand(Command):
  def __init__(self, listbox, index):
    self.listbox = listbox
    self.index = index
    self.number = None

  def execute(self):
    self.number = self.listbox.get(self.index)
    self.listbox.delete(self.index)

  def undo(self):
    if self.number:
      self.listbox.insert(self.index, self.number)

class UndoRedoManager:
  def __init__(self):
    self.undo_stack = deque()
    self.redo_stack = deque()

  def execute(self, command):
    command.execute()
    self.undo_stack.append(command)
    self.redo_stack.clear()

  def undo(self):
    if not self.undo_stack:
      return False
    command = self.undo_stack.pop()
    command.undo()
    self.redo_stack.append(command)
    return True
  
  def redo(self):
    if not self.redo_stack:
      return False
    command = self.redo_stack.pop()
    command.execute()
    self.undo_stack.append(command)
    return True

class SortCommand(Command):
  def __init__(self, listbox, undo_redo_manager, reverse=False):
    self.listbox = listbox
    self.undo_redo_manager = undo_redo_manager
    self.reverse = reverse
    self.previous_state = None
    self.sorted_numbers = None
  
  def execute(self):
    self.previous_state = list(self.listbox.get(0, tk.END))
    if not self.previous_state:
      messagebox.showerror("Error", "The list is empty! Cannot sort an empty list.", parent=window)
      return
    numbers = [float(item.split(". ")[1]) for item in self.previous_state]
    numbers.sort(reverse=self.reverse)
    self.sorted_numbers = [f"{i + 1}. {number}" for i, number in enumerate(numbers)]
    self.update_listbox(self.sorted_numbers)

  def undo(self):
    if self.previous_state:
      self.update_listbox(self.previous_state)

  def update_listbox(self, numbers):
    self.listbox.delete(0, tk.END)
    for number in numbers:
      self.listbox.insert(tk.END, number)

class FilterCommand(Command):
  def __init__(self, listbox, undo_redo_manager, filter_function):
        self.listbox = listbox
        self.undo_redo_manager = undo_redo_manager
        self.filter_function = filter_function
        self.previous_state = None
        self.filtered_numbers = None

  def execute(self):
      self.previous_state = list(self.listbox.get(0, tk.END))
      if not self.previous_state:
        messagebox.showerror("Error", "The list is empty! Cannot filter an empty list.", parent=window)
        return
      numbers = [float(item.split(". ")[1]) for item in self.previous_state]
      filtered = self.filter_function(numbers)
      if not filtered:
        messagebox.showinfo("Info", "No numbers match the filtering criteria.", parent=window)
        return
      self.filtered_numbers = [f"{i + 1}. {number}" for i, number in enumerate(filtered)]
      self.update_listbox(self.filtered_numbers)

  def undo(self):
      if self.previous_state:
          self.update_listbox(self.previous_state)

  def update_listbox(self, numbers):
      self.listbox.delete(0, tk.END)
      for number in numbers:
          self.listbox.insert(tk.END, number)

class HistoryManager:
  def __init__(self):
    self.history = []
    self.current_index = -1

  def add_state(self, state, name=None):
    if self.current_index < len(self.history) - 1:
      self.history = self.history[:self.current_index + 1]
    
    version_name = name if name else f"Version {len(self.history) + 1}"
    self.history.append((version_name, state))
    self.current_index += 1
  
  def undo(self):
    if self.current_index > 0:
      self.current_index -= 1
      return self.history[self.current_index][1]
    return None
  
  def redo(self):
    if self.current_index < len(self.history) - 1:
      self.current_index += 1
      return self.history[self.current_index][1]
    return None
  
  def get_current_state(self):
    if self.history:
      return self.history[self.current_index][1]
    return None

  def get_history(self):
    return self.history
  
  def get_current_version_name(self):
    if self.history:
      return self.history[self.current_index][0]
    return None
  
def view_history(history_manager):
  history = history_manager.get_history()
  if not history:
      messagebox.showinfo("Info", "No history available.", parent=window)
      return

  history_window = tk.Toplevel(window)
  history_window.title("History")

  listbox_history = tk.Listbox(history_window, width=50, height=10)
  listbox_history.pack()

  for name, _ in history:
    listbox_history.insert(tk.END, name)

  def restore_selected():
    selected_index = listbox_history.curselection()
    if selected_index:
      _, state_to_restore = history[selected_index[0]]
      restore_history(state_to_restore)

  restore_button = tk.Button(history_window, text="Restore Selected", command=restore_selected)
  restore_button.pack()

def display_current_version_name(window, history_manager, version_label):
  version_name = history_manager.get_current_version_name()
  if version_name:
    version_label.config(text=f"Current Version: {version_name}")
  else:
    version_label.config(text="No version available")


def save_named_version(window, listbox, history_manager):
  version_name = simpledialog.askstring("Version Name", "Enter a name for this version:", parent=window)
  if not version_name:
    messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
    return
  history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

def restore_history(state):
  listbox.delete(0, tk.END)
  for item in state:
    listbox.insert(tk.END, item)

def delete_selected_entry(listbox, undo_redo_manager):
  selected_index = listbox.curselection()
  if selected_index:
    command = DeleteNumberCommand(listbox, selected_index[0])
    undo_redo_manager.execute(command)
  else:
    messagebox.showerror("Error", "No entry selected!", parent=window)

def undo(undo_redo_manager, listbox):
  if undo_redo_manager.undo():
    update_listbox_numbers(listbox)
  else:
    messagebox.showinfo("Info","Nothing to undo!")

def redo(undo_redo_manager, listbox):
  if undo_redo_manager.redo():
    update_listbox_numbers(listbox)
  else:
    messagebox.showinfo("Info", "Nothing to redo!")

def update_listbox_numbers(listbox):
  for i in range(listbox.size()):
    item = listbox.get(i)
    number = item.split(". ")[1]
    listbox.delete(i)
    listbox.insert(i, f"{i + 1}. {number}")

def add_number(window, listbox, entry, undo_redo_manager, history_manager):
  global counter
  item = entry.get()
  if not item:
    messagebox.showerror("Error",
                         "You can't add an empty entry!",
                         parent=window)
    return
  if item.isdigit() or float or item in algebra_dict:
    command = AddNumberCommand(listbox, item)
    undo_redo_manager.execute(command)
    counter += 1
    history_manager.add_state(list(listbox.get(0, tk.END)))
  else:
    messagebox.showerror(
      "Error",
      "You can only add numbers or defined algebraic letters!",
      parent=window)
  entry.delete(0, tk.END)

def clear_list(listbox, history_manager, show_message=True):
  numbers = listbox.get(0, tk.END)
  if not numbers and show_message:
    messagebox.showerror("Error", "The list is already empty!")
  else:
    listbox.delete(0, tk.END)
    history_manager.add_state(list(listbox.get(0, tk.END)))

from odf import text, teletype
from odf.opendocument import load

def open_file(window, listbox):
  global counter
  filename = filedialog.askopenfilename(filetypes=[
    ('Excel Files (.xls, .xlsx)', '*.xls ; *.xlsx'), ('CSV Files (.csv)', '*.csv'),
    ('ODF Text Files (.odt)', '*.odt'), ('ODF Spreadsheet Files (.ods)', '*.ods'),
    ('All Files', '*.*')
  ], parent=window)
  if not filename:
    return
  clear_list(listbox, history_manager, show_message=False)
  window.file_extension = "." + filename.split(".")[-1]
  if filename.endswith('.xls'):
    book = xlrd.open_workbook(filename)
    sheet = book.sheet_by_index(0)
    for i in range(sheet.nrows):
      listbox.insert(tk.END, f"{counter}. {str(int(sheet.cell_value(i, 0)))}")
      counter += 1
  elif filename.endswith('.csv'):
    with open(filename, 'r') as f:
      reader = csv.reader(f)
      for row in reader:
        for number in row:
          listbox.insert(tk.END, f"{counter}. {number}")
          counter += 1
  elif filename.endswith('.odt'):
    textdoc = load(filename)
    allparas = textdoc.getElementsByType(text.P)
    for para in allparas:
      number = teletype.extractText(para)
      listbox.insert(tk.END, f"{counter}. {number}")
      counter += 1
  elif filename.endswith('.ods'):
    spreadsheet = ezodf.opendoc(filename).sheets[0]
    for row in spreadsheet.rows():
      for cell in row:
        if cell.value is not None:
          listbox.insert(tk.END, f"{counter}. {str(cell.value)}")
  elif filename.endswith('.xlsx'):
    workbook = openpyxl.load_workbook(filename)
    sheet = workbook.active
    for row in sheet.iter_cols(min_row=1, min_col=1, values_only=True):
      for cell in row:
        if cell is not None:
          listbox.insert(tk.END, f"{counter}. {str(cell)}")
          counter += 1

def add_all_numbers(window, listbox, history_manager, version_label):
  global counter
  numbers = listbox.get(0, tk.END)
  if len(numbers) < 2:
    messagebox.showerror("Error",
                         "There must be numbers to add!",
                         parent=window)
    return
  total = sum(int(number.split(". ")[1]) for number in numbers)
  clear_list(listbox, history_manager)
  listbox.insert(tk.END, f"{counter}. {total}")
  version_name = simpledialog.askstring("Version Name", "Please enter a name for this version:", parent=window)
  if not version_name:
    messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
    return
  history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

  display_current_version_name(window, history_manager, version_label)

def subtract_numbers(window, listbox, history_manager, version_label):
    global counter
    numbers = listbox.get(0, tk.END)
    if len(numbers) < 2:
      messagebox.showerror("Error",
                           "There must be numbers to subtract!",
                           parent=window)
      return
    total = float(numbers[0].split(". ")[1]) - sum(
      float(number.split(". ")[1]) for number in numbers[1:])
    clear_list(listbox, history_manager)
    listbox.insert(tk.END, f"{counter}. {total}")
    version_name = simpledialog.askstring("Version Name", "Please enter a name for this version:", parent=window)
    if not version_name:
      messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
      return
    history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

    display_current_version_name(window, history_manager, version_label)


def multiply_all_numbers(window, listbox, history_manager, version_label):
  global counter
  numbers = listbox.get(0, tk.END)
  if len(numbers) < 2:
    messagebox.showerror("Error",
                         "There must be numbers to multiply!",
                         parent=window)
    return
  total = 1
  for number in numbers:
    total *= int(number.split(". ")[1])
  clear_list(listbox, history_manager)
  listbox.insert(tk.END, f"{counter}. {total}")
  version_name = simpledialog.askstring("Version Name", "Please enter a name for this version:", parent=window)
  if not version_name:
    messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
    return
  history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

  display_current_version_name(window, history_manager, version_label)

def divide_all_numbers(window, listbox, history_manager, version_label):
  global counter
  numbers = listbox.get(0, tk.END)
  if len(numbers) < 2:
    messagebox.showerror("Error",
                         "There must be at least two numbers to divide!",
                         parent=window)
    return
  total = int(numbers[0].split(". ")[1])
  for number in numbers[1:]:
    if int(number.split(". ")[1]) == 0:
      messagebox.showerror("Error", "Cannot divide by zero!", parent=window)
      return
    total /= int(number.split(". ")[1])
  clear_list(listbox, history_manager)
  listbox.insert(tk.END, f"{counter}. {total}")
  version_name = simpledialog.askstring("Version Name", "Please enter a name for this version:", parent=window)
  if not version_name:
    messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
    return
  history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

  display_current_version_name(window, history_manager, version_label)

def square_all_numbers(window, listbox, history_manager, version_label):
  global counter
  numbers = listbox.get(0, tk.END)
  if len(numbers) < 1:
    messagebox.showerror("Error",
                         "There must be at least one number to square!",
                         parent=window)
    return
  clear_list(listbox, history_manager)
  for number in numbers:
    square_number = float(number.split(". ")[1])**2
    listbox.insert(tk.END, f"{counter}. {square_number}")
    version_name = simpledialog.askstring("Version Name", "Please enter a name for this version:", parent=window)
    if not version_name:
      messagebox.showerror("Error", "Version name cannot be empty.", parent=window)
      return
    history_manager.add_state(list(listbox.get(0, tk.END)), name=version_name)

    display_current_version_name(window, history_manager, version_label)

algebra_dict = {}

def numeral_system_conversions(listbox, history_manager):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "There are no entries in the number list!", parent=window)
    return
  for item in numbers:
    global counter
    number = int(item.split(". ")[1])
    binary_number = "{0:b}".format(number)
    octal_number = "{0:o}".format(number)
    hexadecimal_number = "{0:x}".format(number)
    converted_item = f"Binary: {binary_number}"
    listbox.insert(tk.END, f"{counter}. {converted_item}")
    counter += 1
    history_manager.add_state(list(listbox.get(0, tk.END)))
    converted_item = f"Octal: {octal_number}"
    listbox.insert(tk.END, f"{counter}. {converted_item}")
    counter += 1
    history_manager.add_state(list(listbox.get(0, tk.END)))
    converted_item = f"Hexadecimal: {hexadecimal_number}"
    listbox.insert(tk.END, f"{counter}. {converted_item}")
    counter += 1
    history_manager.add_state(list(listbox.get(0, tk.END)))

def define_algebraic_letter(window):
  letter_window = tk.Toplevel(window)
  letter_window.title("Define Algebraic Letter")
  tk.Label(letter_window, text="Algebraic Letter:").pack()
  letter_entry = tk.Entry(letter_window)
  letter_entry.pack()
  tk.Label(letter_window, text="Equivalent Number:").pack()
  number_entry = tk.Entry(letter_window)
  number_entry.pack()

  def save_algebraic_letter():
    global algebra_dict
    algebra_dict[letter_entry.get()] = int(number_entry.get())
    letter_window.destroy()

  tk.Button(letter_window, text="Save", command=save_algebraic_letter).pack()

def convert_algebra(window, listbox):
  global counter
  counter = 1
  items = listbox.get(0, tk.END)
  converted_items = []
  for item in items:
    if item in algebra_dict:
      converted_items.append(str(algebra_dict[item]))
    else:
      converted_items.append(item)
    listbox.delete(0, tk.END)
  for item in converted_items:
    listbox.insert(tk.END, f"{counter}. {item}")
    counter += 1
  if set(items) == set(converted_items):
    messagebox.showerror("Error",
                         "You can't convert non-defined algebraic numbers!",
                         parent=window)
  
def change_file_extension(window, extension):
  window.file_extension = extension

about_window = None

def about(window):
  global about_window
  if about_window is not None:
    try:
      about_window.lift()
    except tk.TclError:
      about_window = None
  if about_window is None:
    about_window = tk.Toplevel(window)
    about_window.protocol("WM_DELETE_WINDOW", close_about)
  title_label = tk.Label(about_window, text="About Number List:")
  title_label.pack()
  update_label = tk.Label(about_window, text="The 'Share It Far And Wide' Update")
  update_label.pack()
  version_label = tk.Label(about_window, text="Version 0.68.194")
  version_label.pack()
  contributor_label = tk.Label(about_window, text="Contributors:")
  contributor_label.pack()
  contributor_label2 = tk.Label(about_window, text="Tay Rake 2023 - 2024")
  contributor_label2.pack()

def change_theme(theme):
  if theme == "light":
      listbox.config(bg="white", fg="black")
  elif theme == "dark":
      listbox.config(bg="black", fg="white")

def close_about():
  global about_window
  about_window.destroy()

about_window = None
  
def exit_file(window):
    window.quit()

def report_bug(window):
  messagebox.showwarning("Telemetry","Some telemetry data is required so developer(s) can fix bugs. Such telemetry data is the application version. By closing this message, you agree to the telemetry data collection." , parent=window)
  bug_window = tk.Toplevel(window)
  bug_window.title("Report a Bug")
  bug_label = tk.Label(bug_window, text="Describe the bug:")
  bug_label.pack()
  bug_entry = tk.Text(bug_window, height=5, width=40)
  bug_entry.pack()
  save_button = tk.Button(bug_window, text="Save Report", command=lambda: save_bug_report(bug_entry.get("1.0", tk.END)))
  save_button.pack()

def save_bug_report(report):
  global version
  with open('bugs.txt', 'a') as file:
      file.write(version + report + "\n")
      messagebox.showinfo("Bug Report", "Bug reported successfully!")

def create_graph(window, listbox):
    numbers = [float(item.split(". ")[1]) for item in listbox.get(0, tk.END)]
    if len(numbers) < 2:
        messagebox.showerror("Error", "You need at least two numbers to create a graph!", parent=window)
        return

    graph_window = tk.Toplevel(window)
    graph_window.title("Number List Graph")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(range(1, len(numbers) + 1), numbers, marker='o')
    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    ax.set_title('Number List Graph')

    canvas = FigureCanvasTkAgg(fig, master=graph_window)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack()
  
def create_advanced_graph(window, listbox):
    numbers = [float(item.split(". ")[1]) for item in listbox.get(0, tk.END)]
    if len(numbers) < 2:
        messagebox.showerror("Error", "You need at least two numbers to create a graph!", parent=window)
        return

    graph_window = tk.Toplevel(window)
    graph_window.title("Advanced Graph")
    graph_window.geometry("800x600")

    graph_types = ["Line", "Bar", "Scatter", "Pie"]
    graph_type_var = tk.StringVar(value="Line")
    ttk.Label(graph_window, text="Graph Type:").pack()
    type_combo = ttk.Combobox(graph_window, textvariable=graph_type_var, values=graph_types)
    type_combo.pack()

    color_var = tk.StringVar(value="#1f77b4")
    ttk.Label(graph_window, text="Graph Color:").pack()
    color_button = ttk.Button(graph_window, text="Choose Color")
    color_button.pack()

    def choose_color():
        color = colorchooser.askcolor(color_var.get())[1]
        if color:
            color_var.set(color)
        update_graph()

    color_button.config(command=choose_color)

    title_var = tk.StringVar(value="Number List Graph")
    ttk.Label(graph_window, text="Graph Title:").pack()
    title_entry = ttk.Entry(graph_window, textvariable=title_var)
    title_entry.pack()

    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=graph_window)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(expand=True, fill=tk.BOTH)

    def update_graph(*args):
        ax.clear()
        graph_type = graph_type_var.get()
        color = color_var.get()
        title = title_var.get()

        if graph_type == "Line":
            ax.plot(range(1, len(numbers) + 1), numbers, color=color, marker='o')
        elif graph_type == "Bar":
            ax.bar(range(1, len(numbers) + 1), numbers, color=color)
        elif graph_type == "Scatter":
            ax.scatter(range(1, len(numbers) + 1), numbers, color=color)
        elif graph_type == "Pie":
            ax.pie(numbers, labels=[f"Item {i+1}" for i in range(len(numbers))], autopct='%1.1f%%', colors=[color])

        ax.set_title(title)
        if graph_type != "Pie":
            ax.set_xlabel('Index')
            ax.set_ylabel('Value')
        
        fig.tight_layout()
        canvas.draw()

    graph_type_var.trace_add("write", update_graph)
    title_var.trace_add("write", update_graph)

    update_button = ttk.Button(graph_window, text="Update Graph", command=update_graph)
    update_button.pack()

    def save_graph():
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            fig.savefig(file_path)
            messagebox.showinfo("Success", f"Graph saved as {file_path}", parent=graph_window)

    save_button = ttk.Button(graph_window, text="Save Graph", command=save_graph)
    save_button.pack()

    update_graph()

def sort_numbers_ascending(window, listbox, undo_redo_manager, history_manager):
  command = SortCommand(listbox, undo_redo_manager, reverse=False)
  undo_redo_manager.execute(command)
  history_manager.add_state(list(listbox.get(0, tk.END)))

def sort_numbers_descending(window, listbox, undo_redo_manager, history_manager):
  command = SortCommand(listbox, undo_redo_manager, reverse=True)
  undo_redo_manager.execute(command)
  history_manager.add_state(list(listbox.get(0, tk.END)))

def update_listbox_with_numbers(listbox, numbers):
  listbox.delete(0, tk.END)
  for i, number in enumerate(numbers, 1):
    listbox.insert(tk.END, f"{i}, {number}")

def filter_even_numbers(window, listbox, undo_redo_manager):
  command = FilterCommand(listbox, undo_redo_manager, lambda numbers: [num for num in numbers if num % 2 == 0])
  undo_redo_manager.execute(command)

def filter_odd_numbers(window, listbox, undo_redo_manager):
  command = FilterCommand(listbox, undo_redo_manager, lambda numbers: [num for num in numbers if num % 2 != 0])
  undo_redo_manager.execute(command)

def filter_custom_range(window, listbox, undo_redo_manager):
  if not listbox.size():
    messagebox.showerror("Error", "The list is empty! Cannot filter an empty list.", parent=window)
    return
  min_value = float(simpledialog.askstring("Input", "Enter minimum value:", parent=window))
  max_value = float(simpledialog.askstring("Input", "Enter maximum value:", parent=window))
  command = FilterCommand(listbox, undo_redo_manager, lambda numbers: [num for num in numbers if min_value <= num <= max_value])
  undo_redo_manager.execute(command)

def export_to_csv(window, listbox):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "The list is empty! Cannot export an empty list.", parent=window)
    return
    
  file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], parent=window)
  if not file_path:
    return
    
  with open(file_path, 'w', newline='') as file:
    writer = csv.writer(file)
    for number in numbers:
      writer.writerow([number.split(". ")[1]])
  messagebox.showinfo("Export", f"List exported successfully to {file_path}", parent=window)

def export_to_excel(window, listbox):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "The list is empty! Cannot export an empty list.", parent=window)
    return
    
  file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], parent=window)
  if not file_path:
    return
    
  workbook = openpyxl.Workbook()
  sheet = workbook.active
  for i, number in enumerate(numbers, start=1):
    sheet.cell(row=i, column=1, value=number.split(". ")[1])
    
    workbook.save(file_path)
    messagebox.showinfo("Export", f"List exported successfully to {file_path}", parent=window)

def export_to_json(window, listbox):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "The list is empty! Cannot export an empty list.", parent=window)
    return
  file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], parent=window)
  if not file_path:
    return
  data = [number.split(". ")[1] for number in numbers]    
  with open(file_path, 'w') as file:
    json.dump(data, file, indent=4)
  messagebox.showinfo("Export", f"List exported successfully to {file_path}", parent=window)

def copy_to_clipboard(window, listbox):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "The list is empty! Cannot copy an empty list.", parent=window)
    return
    
  data = "\n".join([number.split(". ")[1] for number in numbers])
  window.clipboard_clear()
  window.clipboard_append(data)
  messagebox.showinfo("Copy", "List copied to clipboard!", parent=window)

def share_via_email(window, listbox):
  numbers = listbox.get(0, tk.END)
  if not numbers:
    messagebox.showerror("Error", "The list is empty! Cannot share an empty list.", parent=window)
    return
  
  data = "\n".join([number.split(". ")[1] for number in numbers])
  subject = "My Number List"
  body = f"Here is my number list:\n\n{data}"
  body = body.replace("\n", "%0D%0A")
  mailto_link = f"mailto:?subject={subject}&body={body}"

  window.clipboard_clear()
  window.clipboard_append(mailto_link)
  messagebox.showinfo("Share", "Mailto link copied to clipboard! Paste it in your mail client.", parent=window)

def create_new_window():
  global counter
  window = tk.Tk()
  global listbox
  window.title("Number List")
  undo_redo_manager = UndoRedoManager()
  undo_button = tk.Button(window, text="Undo", command=lambda: undo(undo_redo_manager, listbox))
  undo_button.pack()
  redo_button = tk.Button(window, text="Redo", command=lambda: redo(undo_redo_manager, listbox))
  redo_button.pack()
  delete_button = tk.Button(window,
                            text="Delete Selected Entry",
                            command=lambda: delete_selected_entry(listbox, undo, undo_redo_manager))
  delete_button.pack()
  menubar = tk.Menu(window)
  window.config(menu=menubar)
  file_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="File", menu=file_menu)
  file_menu.add_command(label="New", command=lambda: create_new_window())
  file_menu.add_command(label="Import",
                        command=lambda: open_file(window, listbox))
  file_menu.add_command(label="Exit", command=lambda: exit_file(window))
  export_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Export", menu=export_menu)
  export_menu.add_command(label="Export to CSV", command=lambda: export_to_csv(window, listbox))
  export_menu.add_command(label="Export to JSON", command=lambda: export_to_json(window, listbox))
  export_menu.add_command(label="Export to Excel", command=lambda: export_to_excel(window, listbox))
  edit_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Edit", menu=edit_menu)
  edit_menu.add_command(label="Undo", command=lambda: undo(undo_redo_manager, listbox))
  edit_menu.add_command(label="Redo", command=lambda: redo(undo_redo_manager, listbox))
  help_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Help", menu=help_menu)
  help_menu.add_command(label="About", command=lambda: about(window))
  math_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Calculate", menu=math_menu)
  math_menu.add_command(label="Add",
                        command=lambda: add_all_numbers(window, listbox))
  math_menu.add_command(label="Subtract",
                        command=lambda: subtract_numbers(window, listbox))
  math_menu.add_command(label="Multiply",
                        command=lambda: multiply_all_numbers(window, listbox))
  math_menu.add_command(label="Divide",
                        command=lambda: divide_all_numbers(window, listbox))
  math_menu.add_command(label="Square",
                        command=lambda: square_all_numbers(window, listbox))
  math_menu.add_command(label="Define Algebraic Letter",
                        command=lambda: define_algebraic_letter(window))
  more_algebra_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="More Algebra...", menu=more_algebra_menu)
  more_algebra_menu.add_command(
    label="Convert Algebra", command=lambda: convert_algebra(window, listbox))
  math_menu.add_command(label="Numeral System Conversions", command=lambda: numeral_system_conversions(listbox))
  sort_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="Sort", menu=sort_menu)
  sort_menu.add_command(label="Ascending", command=lambda: sort_numbers_ascending(window, listbox, undo_redo_manager))
  sort_menu.add_command(label="Descending", command=lambda: sort_numbers_descending(window, listbox, undo_redo_manager))
  filter_menu = tk.Menu(math_menu, tearoff=0)
  filter_menu.add_command(label="Even Numbers", command=lambda: filter_even_numbers(window, listbox, undo_redo_manager))
  filter_menu.add_command(label="Odd Numbers", command=lambda: filter_odd_numbers(window, listbox, undo_redo_manager))
  filter_menu.add_command(label="Custom Range", command=lambda: filter_custom_range(window, listbox, undo_redo_manager))
  graph_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Graph", menu=graph_menu)
  graph_menu.add_command(label="Create Graph", command=lambda: create_graph(window, listbox))
  graph_menu.add_command(label="Create Advanced Graph", command=lambda: create_advanced_graph(window, listbox))
  history_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="History", menu=history_menu)
  history_menu.add_cascade(label="View History", command=lambda: view_history(history_manager))
  history_menu.add_cascade(label="Undo to Previous State", command=lambda: restore_history(history_manager.undo()))
  history_menu.add_cascade(label="Redo to Next State", command=lambda: restore_history(history_manager.redo()))
  listbox = tk.Listbox(window)
  listbox.pack()
  entry = tk.Entry(window)
  entry.pack()
  button_add = tk.Button(window, text="Add number", 
                         command=lambda: add_number(window, listbox, entry, undo_redo_manager, history_manager))
  button_add.pack()
  button_clear = tk.Button(window,
                           text="Clear List",
                           command=lambda: clear_list(listbox))
  button_clear.pack()
  theme_menu = tk.Menu(menubar, tearoff=0)
  theme_menu.add_command(label="Light Theme", command=lambda: change_theme("light"))
  theme_menu.add_command(label="Dark Theme", command=lambda: change_theme("dark"))
  menubar.add_cascade(label="Themes", menu=theme_menu)
  share_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Share", menu=share_menu)
  share_menu.add_command(label="Copy to Clipboard", command=lambda: copy_to_clipboard(window, listbox))
  share_menu.add_command(label="Share via Email", command=lambda: share_via_email(window, listbox))
  

def create_window():
  global history_manager
  history_manager = HistoryManager()
  window.title("Number List")
  version_label = tk.Label(window, text="No version available")
  version_label.pack()
  global listbox
  undo_redo_manager = UndoRedoManager()
  undo_button = tk.Button(window, text="Undo", command=lambda: undo(undo_redo_manager, listbox))
  undo_button.pack()
  redo_button = tk.Button(window, text="Redo", command=lambda: redo(undo_redo_manager, listbox))
  redo_button.pack()
  delete_button = tk.Button(window,
                            text="Delete Selected Entry",
                            command=lambda: delete_selected_entry(listbox, undo_redo_manager))
  delete_button.pack()  
  menubar = tk.Menu(window)
  window.config(menu=menubar)
  file_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="File", menu=file_menu)
  file_menu.add_command(label="New", command=lambda: create_new_window())
  file_menu.add_command(label="Import",
                        command=lambda: open_file(window, listbox))
  file_menu.add_command(label="Exit", command=lambda: exit_file(window))
  export_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Export", menu=export_menu)
  export_menu.add_command(label="Export to CSV", command=lambda: export_to_csv(window, listbox))
  export_menu.add_command(label="Export to JSON", command=lambda: export_to_json(window, listbox))
  export_menu.add_command(label="Export to Excel", command=lambda: export_to_excel(window, listbox))
  edit_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Edit", menu=edit_menu)
  edit_menu.add_command(label="Undo", command=lambda: undo(undo_redo_manager, listbox))
  edit_menu.add_command(label="Redo", command=lambda: redo(undo_redo_manager, listbox))
  help_menu = tk.Menu(menubar, tearoff=0)
  help_menu.add_command(label="Report a Bug", command=lambda: report_bug(window))
  menubar.add_cascade(label="Help", menu=help_menu)
  help_menu.add_command(label="About", command=lambda: about(window))
  math_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Calculate", menu=math_menu)
  data_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="Data", menu=data_menu)
  data_menu.add_command(label="Numeral System Conversions", command=lambda: numeral_system_conversions(listbox, history_manager))
  math_menu.add_command(label="Add",
                        command=lambda: add_all_numbers(window, listbox, history_manager, version_label))
  math_menu.add_command(label="Subtract",
                        command=lambda: subtract_numbers(window, listbox, history_manager, version_label))
  math_menu.add_command(label="Multiply",
                        command=lambda: multiply_all_numbers(window, listbox, history_manager, version_label))
  math_menu.add_command(label="Divide",
                        command=lambda: divide_all_numbers(window, listbox, history_manager, version_label))
  math_menu.add_command(label="Square",
                        command=lambda: square_all_numbers(window, listbox, history_manager, version_label))
  math_menu.add_command(label="Define Algebraic Letter",
                        command=lambda: define_algebraic_letter(window))
  more_algebra_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="More Algebra...", menu=more_algebra_menu)
  more_algebra_menu.add_command(
    label="Convert Algebra", command=lambda: convert_algebra(window, listbox))
  sort_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="Sort", menu=sort_menu)
  sort_menu.add_command(label="Ascending", command=lambda: sort_numbers_ascending(window, listbox, undo_redo_manager, history_manager))
  sort_menu.add_command(label="Descending", command=lambda: sort_numbers_descending(window, listbox, undo_redo_manager, history_manager))
  filter_menu = tk.Menu(math_menu, tearoff=0)
  math_menu.add_cascade(label="Filter", menu=filter_menu)
  filter_menu.add_command(label="Even Numbers", command=lambda: filter_even_numbers(window, listbox, undo_redo_manager, history_manager))
  filter_menu.add_command(label="Odd Numbers", command=lambda: filter_odd_numbers(window, listbox, undo_redo_manager, history_manager))
  filter_menu.add_command(label="Custom Range", command=lambda: filter_custom_range(window, listbox, undo_redo_manager, history_manager))
  graph_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Graph", menu=graph_menu)
  graph_menu.add_command(label="Create Graph", command=lambda: create_graph(window, listbox))
  graph_menu.add_command(label="Create Advanced Graph", command=lambda: create_advanced_graph(window, listbox))
  history_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="History", menu=history_menu)
  history_menu.add_command(label="View History", command=lambda: view_history(history_manager))
  history_menu.add_command(label="Undo to Previous State", command=lambda: restore_history(history_manager.undo()))
  history_menu.add_command(label="Redo to Next State", command=lambda: restore_history(history_manager.redo()))
  history_menu.add_command(label="Save Named Version", command=lambda: save_named_version(window, listbox, history_manager))
  listbox = tk.Listbox(window)
  listbox.pack()
  entry = tk.Entry(window)
  entry.pack()
  button_add = tk.Button(window, text="Add number", 
                         command=lambda: add_number(window, listbox, entry, undo_redo_manager, history_manager))
  button_add.pack()
  button_clear = tk.Button(window,
                           text="Clear List",
                           command=lambda: clear_list(listbox, history_manager))
  button_clear.pack()
  theme_menu = tk.Menu(menubar, tearoff=0)
  theme_menu.add_command(label="Light Theme", command=lambda: change_theme("light"))
  theme_menu.add_command(label="Dark Theme", command=lambda: change_theme("dark"))
  menubar.add_cascade(label="Themes", menu=theme_menu)
  share_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Share", menu=share_menu)
  share_menu.add_command(label="Copy to Clipboard", command=lambda: copy_to_clipboard(window, listbox))
  share_menu.add_command(label="Share via Email", command=lambda: share_via_email(window, listbox))
create_window() 

def main():
  window.mainloop()

main()