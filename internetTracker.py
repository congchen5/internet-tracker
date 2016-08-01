import sys
import re
import subprocess

SPEED_TEST_OUTPUT_REGEX_PATTERN = 'Ping:\s([\d\.]+)\s\w+\nDownload:\s([\d\.]+)\s[\w\/]+\nUpload:\s([\d\.]+)'

def RunSpeedTest():
  try:
    runOutput = subprocess.check_output(["speedtest-cli", "--simple"])
    ParseSpeedTestOutput(runOutput)

  except:
    print("Error in running the speed test.");
    raise

def ParseSpeedTestOutput(output):
  matches = re.match(SPEED_TEST_OUTPUT_REGEX_PATTERN, output)
  try:
    print("Ping: " + matches.group(1))
    print("Download: " + matches.group(2))
    print("Upload: " + matches.group(3))
  except:
    print ('Unexpected Error while parsing the string output from speed test.')
    print ('Regex matched group: {0}'.format(matches))
    raise

def main():
  RunSpeedTest()

if __name__ == '__main__':
  main()
