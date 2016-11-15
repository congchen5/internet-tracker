# internet-tracker
Program that will track your internet speed.

## Introduction

internet-tracker allows you to define at what interval you wish to test your internet speed. The program will run continuously so it's ideal to be run on a computer that's always on and connected to your internet. A Raspberry Pi would be a perfect example. The results of each speed test are written to a sqlite3 db file. There is a simple querying API for seeing the results from the db file.

Soon, the data will be uploaded to a Firebase project where you can visually see the data. This is still under development.

This project uses [sivel/speedtest-cli](https://github.com/sivel/speedtest-cli) to run an internet speed test. Please install this before running internet-tracker.

## Versions

internet-tracker works on Python 2.7.

## Installation

### pip

TODO

### Github

TODO

## Usage

Define a settings.config JSON file with your preferences.

```
{
  - debug: whether to run in debug mode or not. SpeedTest will be mocked if true.
  - offset: minute offset from the hour of when to perform the speed test.
  - times: number of times per hour to perform a speed test.
  - dbfile: the sqlite3 db file to use.
}
```

The offset and times define the intervals of when to perform speed tests.
Thus, the polling can begin before the offset time.

Example: offset: 30, times: 4. This defines the polling at once every 15 min,
on the hour, 15, 30, and 45. If the local time was 35, the polling would begin
at 45 instead of 30.

The settings.config would look like:
```
{
  "debug": false,
  "offset": 30,
  "times": 4,
  "dbfile": "example.db"
}
```

Note: We assume that the interval between each speed test does not take less
than the time it takes to perform a speed test itself.
(HOUR_IN_SEC / times) > speedTest time

The results of the speed test are stored in the `dbfile` with each row:

`{timestamp, date, ping, download speed, upload speed}`

## Currently Under Development

At the moment, the speed test results are simply stored in an sqlite3 database. I am currently working on having the data be saved to a [FCM](https://firebase.google.com/docs/cloud-messaging/) project so that the data can be visualized online.
