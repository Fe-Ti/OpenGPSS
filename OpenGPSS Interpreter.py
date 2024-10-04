##################################################
#    ____                ________  ________      #
#   / __ \___  ___ ___  / ___/ _ \/ __/ __/      #
#  / /_/ / _ \/ -_) _ \/ (_ / ___/\ \_\ \        #
#  \____/ .__/\__/_//_/\___/_/  /___/___/        #
#      /_/           by NotSoOld, 2017 (c)       #
#                                                #
#         route|process|gather stats             #
#                                                #
# OpenGPSS_Interpreter.py - starts all action!   #
#                                                #
##################################################


from modules import interpreter, errors, config

import os
import signal
from sys import argv

def handler(signum, frame):
    print("\nShutting down...")
    exit()
signal.signal(signal.SIGINT, handler)


config.load_config_file()
interpreter.print_logo()

if len(argv) < 2:
    sys_file = input('Enter name of file with system to simulate: ')
else: # If we specify input file in command line
    sys_file = argv[1]

# Making path to input file
filepath = (os.path.dirname(os.path.abspath(__file__)) +
            '/'+sys_file+(not(sys_file.endswith('.ogps')))*'.ogps')

if not os.path.isfile(filepath):
    errors.print_error(1, '', [filepath])

interpreter.start_interpreter(filepath)
