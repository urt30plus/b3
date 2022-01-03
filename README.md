# Overview

This is a fork of the Big Brother Bot (B3) that was updated to work with 
Python 3 and only supports the Urban Terror 4.3 Game.

https://github.com/BigBrotherBot/big-brother-bot

# Requirements

* Python 3.9+

# Running

Use the following command to start the bot

```bash
python3 -m b3 -c ~/.b3/b3.ini
```

# Configuration

Copy the `b3/conf/b3.distribution.ini` file and customize it as needed. The 
recommended location for the file is `~/.b3/b3.ini`. By default, the bot will
look for the configuration file in the `~/.b3` directory, in the directory
where `B3` is located or in the `b3/conf` directory.

You can use the `-c` flag to specify the exact path to the configuration file.
