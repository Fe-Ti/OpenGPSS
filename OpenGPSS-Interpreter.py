##################################################
#    ____                ________  ________      #
#   / __ \___  ___ ___  / ___/ _ \/ __/ __/      #
#  / /_/ / _ \/ -_) _ \/ (_ / ___/\ \_\ \        #
#  \____/ .__/\__/_//_/\___/_/  /___/___/        #
#      /_/           by NotSoOld, 2017 (c)       #
#                                                #
#         route|process|gather stats             #
#                                                #
# OpenGPSS-Interpreter.py - starts all action!   #
#                                                #
# Python3 transition by Fe-Ti, 2024 (c)          #
##################################################


from modules import interpreter, errors, config

import os
import signal
import datetime
from sys import argv

HELP_MESSAGE = """
Possible options:
    -h, --help      - show this message and exit
    --quiet         - do NOT print results and logs into stdout
    --dry-run       - do NOT save resuts and logs (stdout is still used)
    --log PATH      - save logs into file at 'PATH' (by default not saved)
    --results PATH  - save results into file at 'PATH'
    --config PATH   - read config from 'PATH'

Note: '--dry-run' overrides '--log' and '--results' options.

OpenGPSS usage is (assuming 'python' is Python 3 interpreter):
python OpenGPSS-Interpreter.py [OPTIONS] [FILEPATH]
"""

def handler(signum, frame):
    print("\nShutting down...")
    exit()
signal.signal(signal.SIGINT, handler)

interpreter.print_logo()

now = datetime.datetime.now()
options = {
    "quiet"     : False,
    "dry-run"   : False,
    "logfile"   : None,
    "resfile"   : None
    }
sys_file = None
conf_path = None

argv = argv[1:]
i = 0
while i < len(argv):
    if argv[i] == "-h" or argv[i] == "--help":
        print(HELP_MESSAGE)
        exit()
    elif argv[i] == "--quiet":
        options["quiet"] = True
        i+=1
    elif argv[i] == "--dry-run":
        options["dry-run"] = True
        i+=1
    elif argv[i] == "--log":
        if i + 1 < len(argv):
            options["logfile"] = argv[i+1]
            i+=2
        else:
            print(HELP_MESSAGE)
            print("\nError: no log file path specified.")
    elif argv[i] == "--results":
        if i + 1 < len(argv):
            options["resfile"] = argv[i+1]
            i+=2
        else:
            print(HELP_MESSAGE)
            print("\nError: no results file path specified.")
    elif argv[i] == "--config":
        if i + 1 < len(argv):
            conf_path = argv[i+1]
            i+=2
        else:
            print(HELP_MESSAGE)
            print("\nError: no config file path specified.")
    else:
        if i + 1 == len(argv):
            sys_file = argv[i]
            i+=1
        else:
            print(f"\nError: unknown option '{argv[i]}'.")
            exit()
if not sys_file:
    sys_file = input('Enter name of file with system to simulate: ')

config.load_config_file(conf_path)

if options["dry-run"]:
    options["logfile"] = None
    options["resfile"] = None

# Making path to input file
filepath = os.path.dirname(os.path.abspath(__file__)) + \
            '/'+sys_file+(not(sys_file.endswith('.ogps')))*'.ogps'

if not os.path.isfile(filepath):
    errors.print_error(1, '', [filepath])

interpreter.start_interpreter(filepath, options)
