import sys
import re
import time
import csv
import subprocess

from datetime import datetime

SPEED_TEST_OUTPUT_REGEX_PATTERN = 'Ping:\s([\d\.]+)\s\w+\nDownload:\s([\d\.]+)\s[\w\/]+\nUpload:\s([\d\.]+)'
INTERVAL_TIME_SEC = 3600 # 1 hour

def RunSpeedTest():
  try:
    #return 'Ping: 12.34 ms\nDownload: 23.45 Mbit/s\nUpload: 10.1 Mbit/s'
    return subprocess.check_output(["speedtest-cli", "--simple"])
  except:
    print("Error in running the speed test.");
    raise

def ParseSpeedTestOutput(output):
  matches = re.match(SPEED_TEST_OUTPUT_REGEX_PATTERN, output)
  try:
    print("Ping: " + matches.group(1))
    print("Download: " + matches.group(2))
    print("Upload: " + matches.group(3))

    ping = matches.group(1)
    download = matches.group(2)
    upload = matches.group(3)
  except:
    print ('Unexpected Error while parsing the string output from speed test.')
    print ('Regex matched group: {0}'.format(matches))
    raise

  return [ping, download, upload];


# TODO: define a class that sets the interval and has a start and stop. Also
# make it account for the time it takes to run the test.
def ContinuousTesting():
  while True:
    print('SpeedTest started at: ' + str(datetime.now()))
    runOutput = ParseSpeedTestOutput(RunSpeedTest())

    # Append to the csv file.
    with open('speedData.csv', 'a', 0) as csvfile:
      csvWriter = csv.writer(csvfile, delimiter=' ')
      csvWriter.writerow([time.time(), str(datetime.now()), runOutput[0],
          runOutput[1], runOutput[2]])

    time.sleep(INTERVAL_TIME_SEC)

def main():
  ContinuousTesting()

if __name__ == '__main__':
  # execute only if run as a script
  main()
