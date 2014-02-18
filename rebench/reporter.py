# Copyright (c) 2009-2014 Stefan Marr
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import with_statement
from __future__ import print_function
from datetime import datetime
import time
import logging
from .statistics import StatisticProperties
from .persistence import DataPointPersistence
import json
import urllib2
import urllib
import re
import locale


class Reporter(object):

    def __init__(self):
        pass

    def run_failed(self, run_id, cmdline, return_code, output):
        raise NotImplementedError('Subclass responsibility')
    
    def run_completed(self, run_id, statistics, cmdline):
        raise NotImplementedError('Subclass responsibility')
    
    def job_completed(self, run_ids):
        raise NotImplementedError('Subclass responsibility')
    
    def set_total_number_of_runs(self, num_runs):
        raise NotImplementedError('Subclass responsibility')
    
    def start_run(self, run_id):
        raise NotImplementedError('Subclass responsibility')
    

class Reporters(Reporter):
    """Distributes the information to all registered reporters."""
    
    def __init__(self, reporters):
        super(Reporters, self).__init__()
        if type(reporters) is list:
            self._reporters = reporters
        else:
            self._reporters = [reporters]

    def run_failed(self, run_id, cmdline, return_code, output):
        for reporter in self._reporters:
            reporter.run_failed(run_id, cmdline, return_code, output)
            
    def run_completed(self, run_id, statistics, cmdline):
        for reporter in self._reporters:
            reporter.run_completed(run_id, statistics, cmdline)
    
    def job_completed(self, run_ids):
        for reporter in self._reporters:
            reporter.job_completed(run_ids)
    
    def set_total_number_of_runs(self, num_runs):
        for reporter in self._reporters:
            reporter.set_total_number_of_runs(num_runs)
    
    def start_run(self, run_id):
        for reporter in self._reporters:
            reporter.start_run(run_id)


class TextReporter(Reporter):
    
    def __init__(self, configurator):
        super(TextReporter, self).__init__()
        self._configurator = configurator
    
    def _configuration_details(self, run_id, statistics = None):
        result = ["\t".join(run_id.as_str_list()), " = "]
        self._output_stats(result, run_id, statistics)
        return result
    
    def _output_stats(self, output_list, run_id, statistics):
        if not statistics:
            return
        
        for field, value in statistics.__dict__.iteritems():
            if not field.startswith('_'):
                output_list.append("%s: %s " % (field, value))

    @staticmethod
    def _path_to_string(path):
        out = [path[0].as_simple_string()]
        for item in path[1:]:
            if item:
                out.append(str(item))
        return " ".join(out) + " "
    
    def _generate_all_output(self, run_id, path):
        data = run_id.get_data_points()

        if type(data) is dict:
            for key, val in data.iteritems():
                for result in self._generate_all_output(run_id, val, path + (key,)):
                    yield result
        else:
            stats = StatisticProperties(data, 
                                        self._configurator.reporting['confidence_level'])
                
            out = [self._path_to_string(path)]
            self._output_stats(out, run_id, stats)
            result = "".join(out)
            yield result


class CliReporter(TextReporter):
    """ Reports to standard out using the logging framework """
    
    def __init__(self, configurator):
        TextReporter.__init__(self, configurator)
        self._num_runs       = None
        self._runs_completed = 0
        self._startTime      = None
        self._runs_remaining = 0
        
        # TODO: re-add support, think, we need that based on the proper config, i.e., the run id
#         self._min_runtime = configurator.statistics.min_runtime

    def run_failed(self, run_id, cmdline, return_code, output):
        # Additional information in debug mode
        result = "[%s] Run failed: %s\n" % (
            datetime.now(),
            " ".join(self._configuration_details(run_id)))
        logging.debug(result)
        
        # Standard error output
        if return_code == -9:
            log_msg = "Run timed out. return_code: %s"
        else:
            log_msg = "Run failed return_code: %s"
        
        print(log_msg % return_code)
        
        print("Cmd: %s\n" % cmdline)
        
        if run_id.bench_cfg.suite.has_max_runtime():
            logging.debug("max_runtime: %s" % run_id.bench_cfg.suite.max_runtime)
        logging.debug("cwd: %s" % run_id.bench_cfg.suite.location)
        
        if len(output.strip()) > 0:
            print("Output:\n%s\n" % output)    

    def run_completed(self, run_id, statistics, cmdline):
        result = "[%s] Run completed: %s\n" % (
            datetime.now(),
            " ".join(self._configuration_details(run_id, statistics)))
        
        logging.debug(result)
        
        self._runs_completed += 1
        self._runs_remaining -= 1

        # TODO: re-add warning for min_runtime
#         if self._min_runtime:
#             if statistics.mean < self._min_runtime:
#                 print("WARNING: measured mean is smaller than min_runtime (%s) \t mean: %.1f [%.1f, %.1f]\trun id: %s"
#                       % (self._min_runtime,
#                          statistics.mean, statistics.confIntervalLow,
#                          statistics.confIntervalHigh, run_id.as_simple_string()))
#                 print("Cmd: %s" % cmdline)
#         
#         self._configurator.statistics.min_runtime

    def job_completed(self, run_ids):
        print("[%s] Job completed" % datetime.now())
        for line in self._generate_all_output(data_aggregator.getData(), ()):
            print(line)
    
    def set_total_number_of_runs(self, num_runs):
        self._num_runs = num_runs
        self._runs_remaining = num_runs
    
    def start_run(self, run_id):
        if self._runs_completed > 0:
            current = time.time()
            
            etl = ((current - self._startTime) / self._runs_completed *
                   self._runs_remaining)
            sec = etl % 60
            m   = (etl - sec) / 60 % 60
            h   = (etl - sec - m) / 60 / 60
            print(("Run %s \t runs left: %00d \t " +
                   "time left: %02d:%02d:%02d") % (run_id.bench_cfg.name,
                                                   self._runs_remaining,
                                                   round(h), round(m),
                                                   round(sec)))
        else:
            self._startTime = time.time()
            print("Run %s \t runs left: %d" % (run_id.bench_cfg.name,
                                               self._runs_remaining))
            
    def _output_stats(self, output_list, run_id, statistics):
        if not statistics:
            return
        
        if run_id.run_failed():
            output_list.append("run failed.")
        else:
            output_list.append("\t mean: %.1f [%.1f, %.1f]" % (statistics.mean,
                                                               statistics.conf_interval_low,
                                                               statistics.conf_interval_high))
    

class FileReporter(TextReporter):
    """ should be mainly a log file
        data is the responsibility of the data_aggregator
    """
    
    def __init__(self, filename, configurator):
        TextReporter.__init__(self, configurator)
        self._file = open(filename, 'a+')

    def run_failed(self, run_id, cmdline, return_code, output):
        result = "[%s] Run failed: %s\n" % (
            datetime.now(),
            " ".join(self._configuration_details(run_id)))
        self._file.writelines(result)
        
    def run_completed(self, run_id, statistics, cmdline):
        result = "[%s] Run completed: %s\n" % (
            datetime.now(),
            " ".join(self._configuration_details(run_id, statistics)))
        self._file.writelines(result)
    
    def job_completed(self, run_ids):
        self._file.write("[%s] Job completed\n" % datetime.now())
        for line in self._generate_all_output(data_aggregator.getData(), ()):
            self._file.write(line + "\n")
            
        self._file.close()
    
    def set_total_number_of_runs(self, num_runs):
        pass
    
    def start_run(self, run_id):
        pass

            
class CSVFileReporter(Reporter):
    """ Will generate a CSV file for processing in another program
        as for instance R, Excel, or Numbers """
    
    def __init__(self, configurator):
        self._file = open(configurator.reporting['csv_file'], 'a+')
        self._configurator = configurator
    
    def run_failed(self, run_id, cmdline, return_code, output):
        pass
    
    def run_completed(self, run_id, statistics, cmdline):
        pass
    
    def _prepareHeaderRow(self, data, data_aggregator, parameterMappings):
        # since the data might be irregular find the item with the most
        # parameters first
        longestTuple = max(data.keys(), key=lambda tpl: len(tpl))
        # and determine table width
        table_width = len(longestTuple)
        
        # now generate the header
        
        # get sorted parameter mapping first
        mapping = sorted(parameterMappings.items(), key=lambda entry:  entry[1])
        
        header_row = []
        for (title, _index) in mapping:
            header_row.append(title)
        
        # add empty columns to keep table aligned    
        while len(header_row) < table_width:
            header_row.append('')
        
        # now the statistic rows
        for title in StatisticProperties.tuple_mapping():
            header_row.append(title)
        
        return header_row, table_width
    
    def job_completed(self, run_ids):
        old_locale = locale.getlocale(locale.LC_ALL)
        if 'csv_locale' in self._configurator.reporting:
            locale.setlocale(locale.LC_ALL, self._configurator.reporting['csv_locale'])
        
        
        # get the data to be processed
        data = data_aggregator.getDataFlattend()
        parameterMappings = data_aggregator.data_mapping()
        num_common_parameters = len(parameterMappings)
        
        header_row, max_num_parameters = self._prepareHeaderRow(data, data_aggregator, parameterMappings)
        
        table = []
        
        # add the header row
        table.append(header_row)
        
        # add the actual results to the table
        for run, measures in data.iteritems():
            row = []
            row += run[0 : num_common_parameters]                 # add the common ones
            row += [''] * (max_num_parameters - len(run))         # add fill for unused parameters
            row += run[num_common_parameters : ]                  # add all remaining
            row += list(StatisticProperties(measures, 
                            self._configurator.reporting['confidence_level']).as_tuple()) # now add the actual result data
            table.append(row)
        
        for row in table:
            self._file.write(";".join([i if type(i) == str else locale.format("%f", i or 0.0) for i in row]) + "\n")
            
        self._file.close()
        locale.setlocale(locale.LC_ALL, old_locale)
    
    def set_total_number_of_runs(self, num_runs):
        pass
    
    def start_run(self, run_id):
        pass
        

class CodespeedReporter(Reporter):
    """
    This report will report the recorded data on the completion of the job
    to the configured Codespeed instance.
    """
    
    def __init__(self, configurator):
        self._configurator = configurator
        self._incremental_report = self._configurator.options.report_incrementally
        
        # ensure that all necessary configurations have been set
        if self._configurator.options.commit_id is None:
            raise ValueError("--commit-id has to be set on the command line for codespeed reporting.")
        if self._configurator.options.environment is None:
            raise ValueError("--environment has to be set on the command line for codespeed reporting.")
        self._codespeed_cfg = self._configurator.reporting['codespeed']
        
        if "project" not in self._codespeed_cfg and self._configurator.options.project is None:
            raise ValueError("The config file needs to configure a 'project' in the reporting.codespeed section, or --project has to be given on the command line.")
        
        if "url" not in self._codespeed_cfg:
            raise ValueError("The config file needs to configure a URL to codespeed in the reporting.codespeed section")

        
        # contains the indexes into the data tuples for
        # the parameters
        self._indexMap = DataPointPersistence.data_mapping()
        
    def run_failed(self, run_id, cmdline, return_code, output):
        pass


    def run_completed(self, run_id, statistics, cmdline):
        if not self._incremental_report:
            return
        
        # if self._incremental_report is true we are going to talk to codespeed immediately
        results = [self._formatForCodespeed(run_id, statistics)]
        
        # now, send them of to codespeed
        self._sendToCodespeed(results)
    
    def _result_data_template(self):
        if self._configurator.options.project:
            project = self._configurator.options.project
        else:
            project = self._codespeed_cfg['project']
        
        # all None values have to be filled in
        return {
            'commitid':     self._configurator.options.commit_id,
            'project':      project,
            #'revision_date': '', # Optional. Default is taken
                                  # either from VCS integration or from current date
            'executable':   None,
            'benchmark':    None,
            'environment':  self._configurator.options.environment,
            'branch':       self._configurator.options.branch,
            'result_value': None,
            # 'result_date': datetime.today(), # Optional
            'std_dev':      None,
            'max':          None,
            'min':          None }

    def _beautifyBenchmarkName(self, name):
        """
        Currently just remove all bench, or benchmark strings.
        """
        replace = re.compile('bench(mark)?', re.IGNORECASE)
        return replace.sub('', name)

    def _formatForCodespeed(self, run_id, stats = None):
        run = run_id.as_tuple()
        result = self._result_data_template()
        
        if stats and not stats.failedRun:
            result['min']          = stats.min
            result['max']          = stats.max
            result['std_dev']      = stats.stdDev
            result['result_value'] = stats.mean
        else:
            result['result_value'] = -1
        
        if self._configurator.options.executable is None:
            result['executable']   = run[self._indexMap['vm']]
        else:
            result['executable']   = self._configurator.options.executable
        
        if 'codespeed_name' in run_id.bench_cfg.additional_config:
            name = run_id.bench_cfg.additional_config['codespeed_name']
        else:
            name = self._beautifyBenchmarkName(run[self._indexMap['bench']]) + " (%(cores)s cores, %(input_sizes)s %(extra_args)s)"

        name = name % {'cores' : run[self._indexMap['cores']]             or "",
                       'input_sizes' : run[self._indexMap['input_sizes']] or "",
                       'extra_args'  : run[self._indexMap['extra_args']]  or ""}
        
        result['benchmark'] = name
        
        return result

    def _prepareResult(self, run, measures):
        if measures:
            # get the statistics
            stats = StatisticProperties(measures, self._configurator.reporting['confidence_level'])
        else:
            stats = None
            
        return self._formatForCodespeed(run, stats)
    
    def _sendToCodespeed(self, results):
        payload = urllib.urlencode({'json' : json.dumps(results) })
        
        try:
            fh = urllib2.urlopen(self._codespeed_cfg['url'], payload)
            response = fh.read()
            fh.close()
            logging.info("Results were sent to codespeed, response was: " + response)
        except urllib2.HTTPError as error:
            logging.error(str(error) + " This is most likely caused by either " +
                   "a wrong URL in the config file, or an environment not " +
                   "configured in codespeed. URL: " +
                   self._codespeed_cfg['url'])
        

    def job_completed(self, run_ids):
        if self._incremental_report:
            # in this case all duties are already completed
            return
        
        # get the data to be processed
        data = data_aggregator.getDataFlattend()
        
        # create a list of results to be submitted
        results = []
        for run, measures in data.iteritems():
            results.append(self._prepareResult(run, measures))
        
        # now, send them of to codespeed
        self._sendToCodespeed(results)
    
    def set_total_number_of_runs(self, num_runs):
        pass
    
    def start_run(self, run_id):
        pass