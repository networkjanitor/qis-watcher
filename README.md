# QIS Watcher

Used for parsing grades from https://qis.fh-stralsund.de/


## TODO:
 * Implement detection method for detecting changes to the transcript of records (TOC), currently only parses grades
    and dumps them to stdout
 * Implement mail notification for said changes

## Why this is currently a piece of crap and ugly (but working!) code:
 * almost no documentation
 * uses a combination of obscure string operations and htmlparser to extract information
 * no structure whatsoever
 * I only tested it for my own account