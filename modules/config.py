##################################################
#    ____                ________  ________      #
#   / __ \___  ___ ___  / ___/ _ \/ __/ __/      #
#  / /_/ / _ \/ -_) _ \/ (_ / ___/\ \_\ \        #
#  \____/ .__/\__/_//_/\___/_/  /___/___/        #
#      /_/           by NotSoOld, 2017 (c)       #
#                                                #
#         route|process|gather stats             #
#                                                #
# config.py - interpreter configuration          #
# management at runtime                          #
#                                                #
##################################################



from modules import lexer, errors
import os

DEFAULT_CONFNAME = "opengpss_config"
DEFAULT_CONFSUFFIX = ".cfg"

enable_nice_vt100_codes = True
results_to_file = False
log_to_file = False
print_program_in_tokens = True
log_tick_start = True
log_CEC_and_FEC = True
log_xact_trace = True
log_xact_blocking = True
log_facility_entering = True
log_FEC_entering = True
log_assignments = False
log_dot_operator = False
enable_antihalt = True
antihalt_threshold = 1000
tick_by_tick_simulation = False
block_by_block_simulation = False


def load_config_file(path=None):
    
    global enable_nice_vt100_codes
    global results_to_file
    global log_to_file
    global print_program_in_tokens
    global log_tick_start
    global log_CEC_and_FEC
    global log_xact_trace
    global log_xact_blocking
    global log_facility_entering
    global log_FEC_entering
    global log_assignments
    global log_dot_operator
    global enable_antihalt
    global antihalt_threshold
    global tick_by_tick_simulation
    global block_by_block_simulation
    
    conf = None
    try:
        if not path:
            # if path is None, then use default config path
            filepath = os.path.dirname(os.path.abspath(__file__))
            conf_file = filepath+'/'+DEFAULT_CONFNAME + DEFAULT_CONFSUFFIX
        else:
            # use path or append it with default conf name
            conf_file = path + \
                            (not(path.endswith(DEFAULT_CONFSUFFIX))) * \
                            ('/' + DEFAULT_CONFNAME + DEFAULT_CONFSUFFIX)
        conf = open(conf_file, 'r')
    except IOError:
        print('Cannot find config file "opengpss_config.cfg", ' \
              'default config file will be created...')
        write_config_file()
        return
    configtokens = lexer.analyze(conf.read())
    conf.close()
    
    i = 0
    while i < len(configtokens):
        name = configtokens[i][1]
        value = configtokens[i+2][1]
        value_type = configtokens[i+2][0]
        if name not in globals():
            errors.print_error(60, '', [name])
        if value_type == 'word':
            if value == 'True':
                globals()[name] = True
            else:
                globals()[name] = False
        elif value_type == 'number':
            globals()[name] = int(value)
        else:
            errors.print_error(63, '', [name])
        i += 3
    
def write_config_file():
    filepath = os.path.dirname(os.path.abspath(__file__))
    conf = open(filepath+'/opengpss_config.cfg', 'w')
    conf.write('enable_nice_vt100_codes = ' + str(enable_nice_vt100_codes))
    conf.write('\nresults_to_file = ' + str(results_to_file))
    conf.write('\nlog_to_file = ' + str(log_to_file))
    conf.write('\nprint_program_in_tokens = ' + str(print_program_in_tokens))
    conf.write('\nlog_tick_start = ' + str(log_tick_start))
    conf.write('\nlog_CEC_and_FEC = ' + str(log_CEC_and_FEC))
    conf.write('\nlog_xact_trace = ' + str(log_xact_trace))
    conf.write('\nlog_xact_blocking = ' + str(log_xact_blocking))
    conf.write('\nlog_facility_entering = ' + str(log_facility_entering))
    conf.write('\nlog_FEC_entering = ' + str(log_FEC_entering))
    conf.write('\nlog_assignments = ' + str(log_assignments))
    conf.write('\nlog_dot_operator = ' + str(log_dot_operator))
    conf.write('\nenable_antihalt = ' + str(enable_antihalt))
    conf.write('\nantihalt_threshold = ' + str(antihalt_threshold))
    conf.write('\ntick_by_tick_simulation = ' + str(tick_by_tick_simulation))
    conf.write('\nblock_by_block_simulation = ' + str(block_by_block_simulation))
    conf.write('\n')
    conf.close()
