import os, threading

class StoppableThread:
    def __init__(self, thread, index):
        self.thread = thread
        self.index = index
        self.should_stop = False
    
    def stop(self):
        self.should_stop = True

class LogParser:
    def __init__(self, fname, fil, gran, msg_queue):
        self.fname = fname
        self.filter = fil
        self.granularity = gran
        self.msg_queue = msg_queue
        self.threads = []

        self.logsize = 0
        self.prev_logsize = 1e30000

        self.loglen = 0
        self.progress = 0.0 # 0.0-1.0, but change to 0-100 for progbar display

        self.last_line_parsed = 0
        self.tag_instances = {}
        self.found = {}
    
    def getProgress(self):
        return round(self.progress * 100)

    def getMatchCount(self):
        return len(self.found.keys())

    def stopAllThreads(self):
        for t in self.threads:
            t.should_stop = True
            t.thread.join()
        self.threads.clear()

    def changeFile(self, fname):
        self.stopAllThreads()
    
        self.fname = fname
        self.reset()

    def changeFilter(self, fil):
        self.stopAllThreads()
        
        self.filter = fil
        self.reset()

    def changeGranularity(self, gran):
        self.stopAllThreads()

        self.granularity = max(min(gran, 1.0), 0.0)
        self.reset()
    
    def generateOutputs(self):
        outputs = sorted(self.found.keys(), key=lambda k: self.found[k])
        outputs.reverse()

        return outputs
    
    def generateMessage(self):
        outputs = self.generateOutputs()
        msg = ""
        
        for out in outputs:
            tag = str(out)
            count = str(self.found[tag])
            msg += f'{count}\t{tag}\n'
        
        self.msg_queue.put(msg)

    def clear(self):
        self.found.clear()
        self.tag_instances.clear()

        self.generateMessage()

    def reset(self):
        self.last_line_parsed = 0
        self.found.clear()
        self.tag_instances.clear()
        self.msg_queue.put(f"Parsing entire file ({self.fname})...")

    def generateCSV(self):
        outputs = self.generateOutputs()
        csv = '"Count","Line ({0:.0f}% similarity)"\n'.format(self.granularity * 100)

        for tag in outputs:
            count = self.found[tag]
            line = tag.replace('"', '""')
            csv += f'{count},"{line}"\n'
        
        return csv
    
    def threadedParse(self):
        index = len(self.threads)
        thread = threading.Thread(target=self.parseLog, args=(index,))
        self.threads.append(StoppableThread(thread, index))
        thread.start()

    def parseLog(self, thread_index):
        # reset if log is smaller, due to restarting the game
        self.logsize = os.path.getsize(self.fname)
        if self.logsize != 0:
            if self.logsize < self.prev_logsize:
                self.reset()
            self.prev_logsize = self.logsize

        with open(self.fname, 'r') as f:
            lines = f.readlines()
            self.loglen = len(lines) - 1
            lines = lines[self.last_line_parsed:]

        for i, line in enumerate(lines):
            self.progress = i / self.loglen
            if self.filter.strip() == "":
                self.parseLine(line)
            else:
                match = False
                for and_sequence in self.filter.split(" OR "):
                    words = and_sequence.split()
                    all_true = True
                    for word in words:
                        if word.startswith("\\") and word == "\\OR":
                            word == "OR"
                        if word not in line:
                            all_true = False
                            break
                    if all_true:
                        match = True
                        break
                if match:
                    self.parseLine(line)
            if self.threads[thread_index].should_stop:
                return
        
        self.last_line_parsed += len(lines)
        self.generateMessage()

    def parseLine(self, line):
        if not line.strip():
            return
        
        # skip the timestamp
        if line.startswith('['):
            line = line.split(']', 2)[2]
        
        split = line.split()
        if len(split) == 0:
            return
        
        tag = split[0]
        line = ' '.join(split[1:])

        # keep track of lines we've seen with this tag,
        #  the times we've seen a line close to this line in particular,
        #  and if it's a similar line, acquire that line as the 'line' variable.
        if tag not in self.tag_instances:
            self.tag_instances[tag] = {line:1}
        else:
            found_similar_line = False
            try:
                for line_instance in self.tag_instances[tag].keys():
                    li_split = line_instance.split()
                    l_split = split[1:]
                    common = set(li_split).intersection(set(l_split))
                    if len(common) / max(len(l_split), 1) >= self.granularity:
                        self.tag_instances[tag][line_instance] += 1
                        line = line_instance
                        found_similar_line = True
                        break
            except:
                self.stopAllThreads()
                return
            if not found_similar_line:
                self.tag_instances[tag][line] = 1
        
        # add to 'found' dict, with incrementing counter for existing tags
        found_tag = ' '.join([tag, line])
        if found_tag not in self.found.keys():
            self.found[found_tag] = 1
        else:
            self.found[found_tag] += 1
