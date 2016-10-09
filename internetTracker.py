import sys
import re
import time
import csv
import subprocess
import json
import sqlite3

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
#   - dbfile: the sqlite3 db file to use.
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
  POLL_TTL = 0

  def __init__(self, dbCursor, debug, offset, times):
    self.dbCursor = dbCursor
    self.debug = debug
    self.offset = offset
    self.times = times
    self.interval = self.HOUR_IN_SEC / self.times

    # Define the Poll TTL to be 1 day
    self.POLL_TTL = 24 * self.times

    # Whether polling is active or not
    self.active = False

  def Start(self):
    self.active = True

    startMinute = self._DetermineStartMinute()
    if self.debug:
      print('Determined Start Minute: ' + str(startMinute))

    self._WaitTillStart(startMinute)
    self._Poll(1)

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

    # If this point is reached, that means the currentMinute is within the
    # interval of the last value and the first value.
    return intervals[0]

  def _WaitTillStart(self, startMinute):
    currentMinute = time.localtime().tm_min

    # If more than 2 minutes away, sleep until then.
    if (startMinute - currentMinute) > 2:
      if self.debug:
        print('Will sleep for ' + str(startMinute - currentMinute - 2) +
              ' until 2 min before startMinute ' + str(startMinute))
      time.sleep((startMinute - currentMinute - 2) * 60)
      self._WaitTillStart(startMinute)

    if currentMinute == startMinute:
      if self.debug:
        print('Start time hit at time: ' + CurrentTime())
      return
    else:
      time.sleep(30)
      self._WaitTillStart(startMinute)

  def _Poll(self, count):
    startTime = time.time()

    print('SpeedTest started at: ' + CurrentTime())
    speedTestResult = self._RunSpeedTest()

    # Only parse and export data if the speedTest did not fail.
    if (speedTestResult != -1):
      runOutput = self._ParseSpeedTestOutput(speedTestResult)

      # Insert the data to the db if parsing was successful.
      if runOutput != -1:
        self.dbCursor.InsertSpeedTestData(self._FormFinalRowData(runOutput))

      # Append to the csv file if parsing was successful.
      #if runOutput != -1:
      #  with open('speedData.csv', 'a', 0) as csvfile:
      #    csvWriter = csv.writer(csvfile, delimiter=' ')
      #    csvWriter.writerow([time.time(), CurrentTime(), runOutput[0],
      #        runOutput[1], runOutput[2]])
    else:
      print('Skipping SpeedTest due to failed test.')

    # If polling is active, all Poll again after waiting interval amount of time
    if self.active:
      # Account for the amount of time spent performing the speed test.
      speedTestTime = time.time() - startTime
      time.sleep(self.interval - speedTestTime)

      # If the Poll TTL has been reached, start over to recalibrate intervals
      if count >= self.POLL_TTL:
        self.Start()
      else:
        count += 1
        self._Poll(count)
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

  def _FormFinalRowData(self, speedTestOutput):
    return (time.time(), CurrentTime(), speedTestOutput[0], speedTestOutput[1],
        speedTestOutput[2])


# TODO: Add set of API like functions that make interacting with db on command
# line easier. (e.g. Query by dates, length lookup, etc)
# May turn into an object where you can chain on things you want?
#   e.g. cursor.Query(...).withLength().withDownloadData()
class SpeedTestDataCursor:
  """A class that allows you to easily work with the SQLite3 DB"""
  TABLE_NAME = 'speed_test_data'
  SQL_GET_TABLE = "SELECT * FROM sqlite_master WHERE type='table' AND name=?;"
  SQL_CREATE_TABLE = (
      "CREATE TABLE %s (timestamp real, date text, ping real, download real, upload real);"
          % TABLE_NAME)
  SQL_DROP_TABLE = "DROP TABLE %s;" % TABLE_NAME
  SQL_INSERT_ROW = "INSERT INTO %s VALUES (?, ?, ?, ?, ?);" % TABLE_NAME
  SQL_SELECT_ALL = "SELECT * FROM %s;" % TABLE_NAME
  SQL_SELECT_RECENT = (
      "SELECT * FROM (SELECT * FROM %s ORDER BY timestamp DESC LIMIT 10) sub ORDER BY timestamp ASC"
      % TABLE_NAME)

  def __init__(self, dbName, debug):
    if dbName[-3:] != '.db':
      raise Exception('db name must end in .db')

    self.debug = debug
    self.conn = sqlite3.connect(dbName)
    self.c = self.conn.cursor()

    # Initialize the table. If it's not created, create it.
    self._MaybeCreateTable()

  # Allow executing arbitrary displaying queries for debugging purposes.
  # This method will not commit data manipulating queries.
  def Execute(self, query):
    for row in self.c.execute(query):
      print row

  def ImportCsv(self, csvfile):
    with open('speedData.csv', 'r', 0) as csvfile:
      reader = csv.reader(csvfile, delimiter=' ')
      for row in reader:
        self.InsertSpeedTestData(row)

  def PrintAll(self):
    print('=====%s=====' % self.TABLE_NAME)
    for row in self.c.execute(self.SQL_SELECT_ALL):
      print row
    print('-----%s-----' % ('-' * len(self.TABLE_NAME)))

  def PrintRecent(self):
    print('=====%s=====' % self.TABLE_NAME)
    for row in self.c.execute(self.SQL_SELECT_RECENT):
      print row
    print('-----%s-----' % ('-' * len(self.TABLE_NAME)))

  def DropTable(self):
    # TODO: Make more safe. Have some kind of confirmation.
    print('Dropped Table %s' % self.TABLE_NAME)
    self.c.execute(self.SQL_DROP_TABLE)
    self.conn.commit()

  def InsertSpeedTestData(self, data):
    self.c.execute(self.SQL_INSERT_ROW, data)
    self.conn.commit()
    if self.debug:
      print('Inserted data into table: ' + str(data))

  # Check if the speed_test_data table exists. If not, create it.
  def _MaybeCreateTable(self):
    self.c.execute(self.SQL_GET_TABLE, (self.TABLE_NAME,))
    if len(self.c.fetchall()) == 0:
      if self.debug:
        print('Create a new table: ' + str(self.TABLE_NAME))
      self.c.execute(self.SQL_CREATE_TABLE)
      self.conn.commit()
    else:
      if self.debug:
        print('No table to create. %s already exists.' % self.TABLE_NAME)


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

  if 'dbfile' in data:
    dbfile = data['dbfile']

  return [debug, offset, times, dbfile]

def CurrentTime():
  return str(datetime.now(timezone('US/Pacific')))

def main():
  # First, read in the settings.config
  configs = ReadSettingsConfig()
  debugFlag = configs[0]
  offset = configs[1]
  times = configs[2]
  dbfile = configs[3]

  # Create the db cursor for storing the data
  dbCursor = SpeedTestDataCursor(dbfile, debugFlag)

  pollingSpeedTest = PollingSpeedTest(dbCursor, debugFlag, offset, times)
  pollingSpeedTest.Start()

if __name__ == '__main__':
  # execute only if run as a script
  main()
