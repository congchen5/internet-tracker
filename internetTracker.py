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
#   - debug: whether to run in debug mode or not. SpeedTest will be mocked.
#   - offset: minute offset from the hour of when to perform the speed test.
#   - times: number of times per hour to perform a speed test.
# }
#
# The offset and times define the intervals of when to perform speed tests.
# Thus, the polling can begin before the offset time.
#
# Example: offset: 30, times: 4. This defines the polling at once every 15 min,
# on the hour, 15, 30, and 45. If the local time was 35, the polling would begin
# at 45 instead of 30.
#
# Note: We assume that the interval between each speed test does not take less
# than the time it takes to perform a speed test itself.
# (HOUR_IN_SEC / times) > speedTest time

class PollingSpeedTest:
  """A class that allows you to poll speedTests and export the result to csv"""
  speedTestOutputRegex = (
    'Ping:\s([\d\.]+)\s\w+\nDownload:\s([\d\.]+)\s[\w\/]+\nUpload:\s([\d\.]+)')
  HOUR_IN_SEC = 3600

  def __init__(self, debug, offset, times):
    self.debug = debug
    self.offset = offset
    self.interval = self.HOUR_IN_SEC / times
    self.times = times

    # Whether polling is active or not
    self.active = False

  def Start(self):
    self.active = True

    startMinute = self._DetermineStartMinute()
    if self.debug:
      print('Determined Start Minute: ' + str(startMinute))

    self._WaitTillStart(startMinute)
    self._Poll()

  def Stop(self):
    self.active = False

  # Takes the offset and interval to determine what the start minute is.
  def _DetermineStartMinute(self):
    intervals = []
    intervalMinute = self.offset
    for count in range(self.times):
      intervals.append(intervalMinute % 60)
      intervalMinute += self.interval / 60  # convert interval to minutes

    intervals.sort()
    currentMinute = time.localtime().tm_min

    for interval in intervals:
      if currentMinute < interval:
        return interval

    # Should never happen
    return -1

  def _WaitTillStart(self, startMinute):
    currentMinute = time.localtime().tm_min

    # If more than 2 minutes away, sleep until then.
    if (startMinute - currentMinute) > 2:
      if self.debug:
        print('Will sleep for ' + str(startMinute - currentMinute - 2) +
              ' until startMinute ' + str(startMinute))
      time.sleep((startMinute - currentMinute - 2) * 60)
      self._WaitTillStart(startMinute)

    if currentMinute == startMinute:
      if self.debug:
        print('Start time hit at time: ' + CurrentTime())
      return
    else:
      time.sleep(30)
      self._WaitTillStart(startMinute)

  def _Poll(self):
    startTime = time.time()

    print('SpeedTest started at: ' + CurrentTime())
    speedTestResult = self._RunSpeedTest()

    # Only parse and export data if the speedTest did not fail.
    if (speedTestResult != -1):
      runOutput = self._ParseSpeedTestOutput(speedTestResult)

      # Append to the csv file if parsing was successful.
      if runOutput != -1:
        with open('speedData.csv', 'a', 0) as csvfile:
          csvWriter = csv.writer(csvfile, delimiter=' ')
          csvWriter.writerow([time.time(), CurrentTime(), runOutput[0],
              runOutput[1], runOutput[2]])
    else:
      print('Skipping SpeedTest due to failed test.')

    # If polling is active, all Poll again after waiting interval amount of time
    if self.active:
      # Account for the amount of time spent performing the speed test.
      speedTestTime = time.time() - startTime
      time.sleep(self.interval - speedTestTime)
      self._Poll()
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
  pprint(data)

  debug = False
  offset = 0  # defaults to on the hour
  times = 1  # defaults to 1 speed test per hour

  if 'debug' in data:
    debug = data['debug']

  if 'offset' in data:
    offset = int(data['offset'])
  if offset < 0 or offset > 60:
    raise Exception('Please supply a offset value between [0, 60).')

  if 'times' in data:
    times = data['times']

  return [debug, offset, times]

def CurrentTime():
  return str(datetime.now(timezone('US/Pacific')))

def main():
  # First, read in the settings.config
  configs = ReadSettingsConfig()

  pollingSpeedTest = PollingSpeedTest(configs[0], configs[1], configs[2])
  pollingSpeedTest.Start()

if __name__ == '__main__':
  # execute only if run as a script
  main()
