# Copyright (c) 2009-2011 Stefan Marr <http://www.stefan-marr.de/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

class Profile:
    """Profile is the base class for determining the dynamic execution
       characteristics of a specific benchmark.
    """
    
    def __init__(self, vm, benchmark):
        self.benchmark = benchmark
        self.vm = vm
        self.opcode_usage = {}
        self.memory_usage = {}
        self.library_usage = {}
    
    def get_vm_and_benchmark(self):
        return self.vm, self.benchmark
    
    def get_memory_usage(self):
        return self.memory_usage
    
    def get_library_usage(self):
        return self.library_usage
    
    def get_opcode_usage(self):
        return self.opcode_usage

    def process_profile_data(self, trace_filename):
        pass
    
    def normalize(self, profile):
        self.add_missing_keys(self.memory_usage,  profile.memory_usage.keys())
        self.add_missing_keys(self.library_usage, profile.library_usage.keys())
        self.add_missing_keys(self.opcode_usage,  profile.opcode_usage.keys())
    
    def add_missing_keys(self, dict, keys):
        for key in keys:
            if not dict.has_key(key):
                dict[key] = None
    
class LuaProfile(Profile):
    """LuaProfile is actually a reader for the profiling data
       generated by CSOM as well as Lua.
       It parses the given file and structures its data.
    """
    
    def process_data_lines(self, lines):
        currentDataDict = None
        orderedKeys = None
        orderedValues = None
        for line in lines:
            if line.find("Bytecode:\t") == 0:
                currentDataDict = self.opcode_usage
                line = line.replace("Bytecode:\t", "")
                orderedKeys = line.split("\t")
            elif line.find("Library:\t") == 0:
                currentDataDict = self.library_usage
                line = line.replace("Library:\t", "")
                orderedKeys = line.split("\t")
            elif line.find("ObjectSize:\t") == 0:
                currentDataDict = self.memory_usage
                line = line.replace("ObjectSize:\t", "")
                orderedKeys = line.split("\t")
            elif currentDataDict is not None and line.find("Count:\t") == 0:
                line = line.replace("Count:\t", "")
                orderedValues = line.split("\t")
                for i in range(len(orderedKeys)):
                    currentDataDict[orderedKeys[i]] = orderedValues[i]
            else:
                currentDataDict = None
    
    def process_profile_data(self, trace_filename):
        f = file(trace_filename, 'r')
        self.process_data_lines(f.readlines())
        
        
                
             