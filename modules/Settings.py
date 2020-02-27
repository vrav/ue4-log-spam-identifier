import os, json

config_filename = "settings.json"

default_settings = {
    "startup_granularity": 1.0,
    "log_file_history": [""],
    "filter_history": ["Error", "Warning", "Error OR Warning"],
    "tooltips": "yes"
}

class JsonLoadable(object):
    def from_json(self, json):
        for setting in json:
            setattr(self, setting, json[setting])
    
    def to_json(self):
        j = {}
        for setting in default_settings:
            j[setting] = getattr(self, setting)
        return json.dumps(j, indent=True)

class Settings(JsonLoadable):
    def __init__(self, base_dir):
        self.fpath = os.path.join(base_dir, config_filename)

        for setting in default_settings:
            setattr(self, setting, default_settings[setting])

        self.loadFile()
        
    def loadFile(self):
        if os.path.isfile(self.fpath):
            with open(self.fpath, 'r') as f:
                try:
                    file_settings = json.loads(f.read())
                except:
                    file_settings = None
            if file_settings:
                self.from_json(file_settings)
        else:
            self.saveFile()

    def saveFile(self):
        with open(self.fpath, 'w') as f:
            f.write(self.to_json())
