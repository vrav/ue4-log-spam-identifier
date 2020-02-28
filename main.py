import os, queue, time
import PySimpleGUI as sg

from modules.Settings import Settings
from modules.LogParser import LogParser

base_dir = os.path.dirname(os.path.realpath(__file__))
settings = Settings(base_dir)
msg_queue = queue.Queue()

sg.theme("LightGrey1")

msg = ""
live_update_last = time.time()
live_update_wait = 0.5 # seconds
gran_values = [i/10 for i in range(0, 11)]

tooltips = {
    "UPDATE": "Update the output to the file's current state.",
    "SAVE": "Save a comma-separated-values file for use in spreadsheets.",
    "CLEAR": "Clear output. Further updates will only show events that were written after clearing.",
    "FILTER": "Enter case-sensitive words to search for. Words on either side of the keyword OR will be parsed separately. To use OR as a search term, type \\OR.",
    "GRANULARITY": "Lower to reduce the amount of matches by combining similar lines.",
    "LIVE": "Continuously read the log file and update the output."
}

start_file = "" if not settings.log_file_history else settings.log_file_history[0]

layout = [
    [sg.Text("Log File:"), sg.InputCombo((settings.log_file_history), default_value=start_file, size=(5, 1), key="FILE"), sg.FileBrowse(key="BROWSE", size=(6, 1))],
    [sg.Frame(title="", layout=[], key="OUTPUT")],
    [sg.Button(button_text="Update", key="UPDATE"), \
        sg.FileSaveAs(button_text="Save CSV", key="SAVE", file_types=(("*.csv", "*.csv"), ("All files", "*.*")), enable_events=True), \
        sg.Button(button_text="Clear", key="CLEAR"), \
        sg.Text("Filter:"), sg.InputCombo((settings.filter_history), key="FILTER", default_value="Error"), \
        sg.Text("Granularity:"), sg.Spin(values=gran_values, initial_value=settings.startup_granularity, key="GRANULARITY")],
    [sg.Checkbox(text="Live Update", key="LIVE"), sg.Text("0 matches", size=(15, 1), key="MATCHES"), \
        sg.ProgressBar(100, orientation='h', size=(20, 16), key='PROGBAR')],
]

# create the window and read once so we can expand given widgets on window resize
window = sg.Window("Log Spam Identifier v0.1.0", layout, auto_size_buttons=True, resizable=True, size=(800, 600))
event, values = window.read(timeout=1)
window["OUTPUT"].expand(expand_x=True, expand_y=True)
window["FILTER"].expand(expand_x=True, expand_row=False)
window["FILE"].expand(expand_x=True, expand_row=False)
window["MATCHES"].expand(expand_x=True, expand_row=False)

# set tooltips
if settings.tooltips in (True, "yes", 1):
    for widget in tooltips.keys():
        window[widget].SetTooltip(tooltips[widget])

# custom widgets to fill the OUTPUT Frame widget
scrollbar_width = 12
vbar = sg.tk.Scrollbar(master=window["OUTPUT"].Widget, orient=sg.tk.VERTICAL, bd=1, width=scrollbar_width)
bot = sg.tk.Frame(master=window["OUTPUT"].Widget, bd=0, bg=sg.theme_input_background_color())
hbar = sg.tk.Scrollbar(master=bot, orient=sg.tk.HORIZONTAL, bd=1, width=scrollbar_width)
sq = sg.tk.Frame(master=bot, width=scrollbar_width+2, height=scrollbar_width+2, bg=sg.theme_input_background_color())

# pack order is sensitive. sq is the square in the bottom right between the scroll bars
sq.pack(side=sg.tk.RIGHT, fill=sg.tk.NONE)
hbar.pack(side=sg.tk.BOTTOM, fill=sg.tk.X)
bot.pack(side=sg.tk.BOTTOM, fill=sg.tk.X)
vbar.pack(side=sg.tk.RIGHT, fill=sg.tk.Y)

# output field
txt = sg.tk.Text(master=window["OUTPUT"].Widget, wrap="none", state=sg.tk.DISABLED, \
    foreground=sg.theme_input_text_color(), background=sg.theme_input_background_color(), \
    borderwidth=0, xscrollcommand=hbar.set, yscrollcommand=vbar.set, \
    highlightcolor=sg.theme_input_background_color())
txt.pack(side=sg.tk.TOP, fill=sg.tk.BOTH, expand=sg.tk.TRUE)

# enable copy-paste on disabled txt widget
txt.bind("<1>", lambda event: txt.focus_set())

hbar.config(command=txt.xview)
vbar.config(command=txt.yview)

def fileNotFoundMessage(fpath):
    msg_queue.put(f"File not found: \"{fpath}\"")

def isFloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def tryParse():
    global parser, live_update_last, msg, live_update_wait

    now = time.time()
    if (not parser.threads or not msg.startswith("Parsing")) and live_update_last + live_update_wait < now:
        parser.threadedParse()
        live_update_last = now

parser = LogParser(values["FILE"], values["FILTER"], values["GRANULARITY"], msg_queue )
if not os.path.isfile(values["FILE"]):
    fileNotFoundMessage(values["FILE"])
else:
    parser.threadedParse()

previous_values = values

while True:
    event, values = window.read(timeout=10)
    if event in (None, 'Quit'):
        break
    elif event == "CLEAR":
        if not msg.startswith("Parsing"):
            parser.clear()
    elif event == "UPDATE":
        parser.stopAllThreads()
        parser.threadedParse()

    if values["SAVE"]:
        print(f"Saving CSV to: {values['SAVE']}")

        with open(values["SAVE"], "w") as f:
            f.write(parser.generateCSV())

        # reset the string var so we only save once
        window["SAVE"].TKStringVar.set("")

    needs_update = False
    if values["FILE"] != previous_values["FILE"]:
        fname = values["FILE"]
        if os.path.isfile(fname):
            # if extant, remove from list so we can re-add at the top
            if fname in settings.log_file_history:
                settings.log_file_history.remove(fname)
            settings.log_file_history.insert(0, fname)
            settings.saveFile()
            window["FILE"].Widget.config(values=settings.log_file_history)
            
            parser.changeFile(fname)
            needs_update = True
        else:
            fileNotFoundMessage(values["FILE"])
    
    if values["FILTER"] != previous_values["FILTER"]:
        parser.changeFilter(values["FILTER"])
        needs_update = True
    
    if values["GRANULARITY"] != previous_values["GRANULARITY"]:
        gran = values["GRANULARITY"]
        if isFloat(gran):
            gran = min(max(float(gran), 0.0), 1.0)
            window["GRANULARITY"].update(gran)
            parser.changeGranularity(gran)
            needs_update = True
    
    if needs_update or values["LIVE"]:
        tryParse()
    
    if not msg_queue.empty():
        msg = msg_queue.get_nowait()

        # unlock txt widget and fill it, then lock again
        txt.config(state=sg.tk.NORMAL)
        txt.delete(1.0, sg.tk.END)
        txt.insert(sg.tk.END, msg)
        txt.config(state=sg.tk.DISABLED)

        matchstr = str(parser.getMatchCount()) + " matches"
        window["MATCHES"].update(matchstr)
    
    if msg.startswith("Parsing"):
        window["PROGBAR"].update_bar(parser.getProgress())
    else:
        window["PROGBAR"].update_bar(100)
    
    previous_values = values

window.close()
