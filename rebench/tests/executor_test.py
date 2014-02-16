import unittest
import subprocess

from rebench.Executor       import Executor
from rebench.persistence import DataPointPersistence
from rebench.Configurator   import Configurator
from rebench.Reporter       import Reporters
from rebench.model.benchmark_config import BenchmarkConfig
from rebench.model.run_id   import RunId
from rebench.model.measurement import Measurement
from rebench          import ReBench
import tempfile
import os
import sys

class ExecutorTest(unittest.TestCase):
    
    def setUp(self):
        BenchmarkConfig.reset()
        RunId.reset()
        self._path = os.path.dirname(os.path.realpath(__file__))
        self._tmpFile = tempfile.mkstemp()[1] # just use the file name
        os.chdir(self._path + '/../')
        
        self._sys_exit = sys.exit  # make sure that we restore sys.exit   
    
    def tearDown(self):
        os.remove(self._tmpFile)
        sys.exit = self._sys_exit
        
        
    def test_setup_and_run_benchmark(self):

        # before executing the benchmark, we override stuff in subprocess for testing
        subprocess.Popen =  Popen_override
        options = ReBench().shell_options().parse_args([])[0]
        
        cnf  = Configurator(self._path + '/test.conf', options, 'Test')
        data = DataPointPersistence(self._tmpFile)
        
        ex = Executor(cnf.get_runs(), cnf.use_nice, data, Reporters([]))
        ex.execute()
        
### should test more details
#        (mean, sdev, (interval, interval_percentage), 
#                (interval_t, interval_percentage_t)) = ex.result['test-vm']['test-bench']
#        
#        self.assertEqual(31, len(ex.benchmark_data['test-vm']['test-bench']))
#        self.assertAlmostEqual(45870.4193548, mean)
#        self.assertAlmostEqual(2.93778711485, sdev)
#        
#        (i_low, i_high) = interval
#        self.assertAlmostEqual(45869.385195243565, i_low)
#        self.assertAlmostEqual(45871.453514433859, i_high)
#        self.assertAlmostEqual(0.00450904792104, interval_percentage)

    def test_broken_command_format(self):
        def test_exit(val):
            self.assertEquals(-1, val, "got the correct error code")
            raise RuntimeError("TEST-PASSED")
        sys.exit = test_exit
        
        options = ReBench().shell_options().parse_args([])[0]
        cnf = Configurator(self._path + '/test.conf', options, 'TestBrokenCommandFormat')
        data = DataPointPersistence(self._tmpFile)
        ex = Executor(cnf.get_runs(), cnf.use_nice, data, Reporters([]))

        with self.assertRaisesRegexp(RuntimeError, "TEST-PASSED"):
            ex.execute()
    
    def test_broken_command_format_with_TypeError(self):
        def test_exit(val):
            self.assertEquals(-1, val, "got the correct error code")
            raise RuntimeError("TEST-PASSED")
        sys.exit = test_exit
        
        options = ReBench().shell_options().parse_args([])[0]
        cnf = Configurator(self._path + '/test.conf', options, 'TestBrokenCommandFormat2')
        data = DataPointPersistence(self._tmpFile)
        ex = Executor(cnf.get_runs(), cnf.use_nice, data, Reporters([]))
        
        with self.assertRaisesRegexp(RuntimeError, "TEST-PASSED"):
            ex.execute()
    
    def test_basic_execution(self):
        cnf = Configurator(self._path + '/small.conf', None)
        runs = cnf.get_runs()
        self.assertEquals(8, len(runs))

        data = DataPointPersistence(self._tmpFile)
        ex = Executor(cnf.get_runs(), cnf.use_nice, data, Reporters([]))
        ex.execute()

        for run in runs:
            data_points = run.get_data_points()
            self.assertEquals(10, len(data_points))
            for data_point in data_points:
                measurements = data_point.get_measurements()
                self.assertEquals(4, len(measurements))
                self.assertIsInstance(measurements[0], Measurement)
                self.assertTrue(measurements[3].is_total())
                self.assertEquals(data_point.get_total_value(), measurements[3].value)
        

def Popen_override(cmdline, stdout, shell):
    class Popen:
        returncode = 0
        def communicate(self):
            return (None, None)
    
    return Popen()

def test_suite():
    return unittest.makeSuite(ExecutorTest)

if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')