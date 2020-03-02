# ue4-log-spam-identifier
![alt text](https://i.imgur.com/FFB9ai4.png "screenshot")

This tool can be used to identify spam in UE4 game logs. The only thing tying it to UE4 is how it skips the timestamp, which has a format similar to `[2020.02.27-05.15.05:151][160]`. It splits the line by ']' and discards the first two elements.

Granularity can be reduced to combine results for similar lines. This is useful when the log is being spammed with errors about loading certain objects, but each line has a different object name.

The filter field has one special keyword, 'OR'. Whitespace operates as 'AND'. 'OR' takes precedence and splits the terms into groups that will be searched for in their entirety. To use 'OR' as a search term, escape it by typing '\OR'.

If you come to understand the tool and the tooltips bother you, set the tooltips value in settings.json (generated after first run) to any string other than "yes".
## Running from Source
This tool uses `PySimpleGUI`. Install this with your package manager or via pip within your python environment.

Basic route:
```
git clone https://github.com/vrav/ue4-log-spam-identifier.git
cd ue4-log-spam-identifier
python -m pip install PySimpleGUI
python ./main.py
```
However, you may wish to set up a virtual environment apart from your system installation of Python. Do as you see fit.
## Building with PyInstaller
I have found it's necessary to use the `--hidden-import` option when building with PyInstaller.

```python -m PyInstaller -wD --name "LogSpamIdentifier" --hidden-import PySimpleGUI .\main.py```

When building on Windows, pyinstaller.exe was giving me permissions complaints, so I had to install a portable version of Python and build with that. I'm guessing a virtual environment made with venv or conda would work as well.
