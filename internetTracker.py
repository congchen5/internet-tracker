import sys
import re
import time
import csv
import subprocess
import json

from datetime import datetime
from pytz import timezone
from pprint import pprint

# This file expects a settings.config file which includes a JSON with all the
# appropriate configuration settings. The expected values are as follows:
#
# settings.config
#
# {
#   - interval: time in sec between every interval of speed test
#   - debug: whether to run in debug mode or not. SpeedTest will be mocked. TODO
#   - time: TODO
#   - offset: TODO
# }

class PollingSpeedTest:
  """A class that allows you to poll speedTests and export the result to csv"""
  speedTestOutputRegex = (
    'Ping:\s([\d\.]+)\s\w+\nDownload:\s([\d\.]+)\s[\w\/]+\nUpload:\s([\d\.]+)')

  def __init__(self, debug, interval):
    self.debug = debug
    self.interval = interval

    # Whether polling is active or not
    self.active = False

  def Start(self):
    self.active = True
    self.Poll()

  def Stop(self):
    self.active = False

  def Poll(self):
    pst = timezone('US/Pacific')
    print('SpeedTest started at: ' + str(datetime.now(pst)))
    speedTestResult = self._RunSpeedTest()

    # Only parse and export data if the speedTest did not fail.
    if (speedTestResult != -1):
      runOutput = self._ParseSpeedTestOutput(speedTestResult)

      # Append to the csv file if parsing was successful.
      if runOutput != -1:
        with open('speedData.csv', 'a', 0) as csvfile:
          csvWriter = csv.writer(csvfile, delimiter=' ')
          csvWriter.writerow([time.time(), str(datetime.now(pst)), runOutput[0],
              runOutput[1], runOutput[2]])
    else:
      print('Skipping SpeedTest due to failed test.')

    # If polling is active, all Poll again after waiting interval amount of time
    if self.active:
      time.sleep(self.interval)
      self.Poll()
    else:
      print('Polling stopped.')

  def _RunSpeedTest(self):
    try:
      if self.debug:
        return 'Ping: 11.11 ms\nDownload: 22.22 Mbit/s\nUpload: 33.3 Mbit/s'
      else:
        speedResult = subprocess.check_output(['speedtest-cli', '--simple'])
    except subprocess.CalledProcessError as e:
      print('Error in running the speed test.')
      print('Command \'{}\' return with error (code {}): {}'.format(
          e.cmd, e.returncode, e.output))
      return -1
    except:
      print('General Error in running the speed test.')
      return -1

    return speedResult;

  def _ParseSpeedTestOutput(self, output):
    try:
      matches = re.match(self.speedTestOutputRegex, output)

      print('Ping: ' + matches.group(1))
      print('Download: ' + matches.group(2))
      print('Upload: ' + matches.group(3))

      ping = matches.group(1)
      download = matches.group(2)
      upload = matches.group(3)
    except:
      print ('Unexpected Error while parsing the output from speed test.')
      print ('Regex matched group: {0}'.format(matches))
      print -1

    return [ping, download, upload];

def ReadSettingsConfig():
  with open('settings.config') as settings_file:
    data = json.load(settings_file)
  #pprint(data)

  debug = False
  interval = -1

  if 'interval' in data:
    interval = data['interval']

  # Make sure an interval time is supplied.
  if interval == -1:
    raise Exception('Please supply an interval time in settings.config.')

  if 'debug' in data:
    debug = data['debug']

  return [debug, interval]

def main():
  # First, read in the settings.config
  configs = ReadSettingsConfig()

  pollingSpeedTest = PollingSpeedTest(configs[0], configs[1])
  pollingSpeedTest.Start()

if __name__ == '__main__':
  # execute only if run as a script
  main()
