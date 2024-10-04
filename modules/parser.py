##################################################
#    ____                ________  ________      #
#   / __ \___  ___ ___  / ___/ _ \/ __/ __/      #
#  / /_/ / _ \/ -_) _ \/ (_ / ___/\ \_\ \        #
#  \____/ .__/\__/_//_/\___/_/  /___/___/        #
#      /_/           by NotSoOld, 2017 (c)       #
#                                                #
#         route|process|gather stats             #
#                                                #
# parser.py - processes every token line of      #
# a program, creating variables and executing    #
# blocks and functions. Parses expressions.      #
#                                                #
##################################################



import sys
import os
from . import structs
from . import lexer
from . import interpreter
from . import errors
from . import builtins
import copy
import inspect

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from . import config

pos = 0
tokline = []
lineindex = 0
assgs = [
         'eq', 
         'add', 
         'subt', 
         'inc', 
         'dec', 
         'multeq', 
         'diveq', 
         'remaineq', 
         'pwreq'
        ]
fac_params = [
              'curplaces',
              'maxplaces',
              'enters_f',
              'isAvail'
             ]
queue_params = [
                'curxacts',
                'enters_q'
               ]
chain_params = [
                'length'
               ]
xact_params = [
               'group',
               'index'
              ]
hist_params = [
               'enters_h',
               'average'
              ]

defined_var_names = []  
arrays_info = {}     # name: [lbound, rbound]
matrices_info = {}   # name: [[horl, horr], [vertl, vertr]]

             
def tocodelines(program):
    parsed = [['padding', [0, 0, 0]]]
    i = 0
    li = 1
    while i < len(program):
        token = program[i]
        if token[0] in 'lbrace'+'rbrace'+'lexec'+'rexec':
            parsed.append([token, [li, 0, 0]])
            i += 1
            li += 1
            continue

        line = []
        while True:
            token = program[i]
            line.append(token)
            i += 1
            if token[0] == 'eocl' or token == ['block', 'else'] or \
               (token == ['rparen', ''] and program[i] == ['lbrace', ''] and \
                ['block', 'inject'] not in line and 
                ['typedef', 'function'] not in line):
                line.append([li, 0, 0])
                parsed.append(line)
                li += 1
                break
            if i >= len(program):
                errors.print_error(2, '')
    return parsed

def convertBlocks(lines):
    num = 0
    nesting = []
    skip = True
    for i in range(len(lines)):
        if lines[i][0][0] == 'lexec':
            skip = False
        if lines[i][0][0] == 'rexec':
            skip = True
        if skip:
            continue
        if lines[i][0][0] == 'lbrace':
            if ['block', 'if'] in lines[i-1]:
                nesting.append('if')
            elif ['block', 'else_if'] in lines[i-1]:
                nesting.append('else_if')
            elif ['block', 'else'] in lines[i-1]:
                nesting.append('else')
            elif ['block', 'while'] in lines[i-1]:
                nesting.append('while')
            elif ['block', 'loop_times'] in lines[i-1]:
                nesting.append('loop_times')
        elif lines[i][0][0] == 'rbrace':
            nesting.pop()
        elif ['block', 'iter_next'] in lines[i]:
            nest = copy.copy(nesting)
            for j in reversed(list(range(0, i))):
                if lines[j][0][0] == 'lbrace':
                    n = nest.pop()
                    if n == 'while' or n == 'loop_times':
                        l = []
                        if lines[i][1][0] == 'marksep':
                            l = lines[i][0:2]
                        if lines[j-1][1][0] == 'marksep':
                            lines[i] = l + [['transport', ''], ['gt', ''],
                                            lines[j-1][0], ['eocl', ''],
                                            lines[i][-1]]
                        else:
                            lines[j-1] = [['word', '&while'+str(num)],
                                          ['marksep', '']] + lines[j-1]
                            lines.append([['typedef', 'mark'],
                                          ['word', '&while'+str(num)],
                                          ['eocl', ''],
                                          [len(lines), 0, 0]])
                            lines[i] = l + [['transport', ''], ['gt', ''],
                                            ['word', '&while'+str(num)],
                                            ['eocl', ''], lines[i][-1]]
                            num += 1
                        break
                        
                elif lines[j][0][0] == 'rbrace':
                    nest.append('smth')
        
        elif ['block', 'iter_stop'] in lines[i]:
            nest = copy.copy(nesting)
            for j in reversed(list(range(0, i))):
                if lines[j][0][0] == 'lbrace':
                    n = nest.pop()
                    if n == 'while' or n == 'loop_times':
                        break
                            
                elif lines[j][0][0] == 'rbrace':
                    nest.append('smth')
            depth = 0
            for k in range(j, len(lines)):
                if lines[k][0][0] == 'lbrace':
                    depth += 1
                elif lines[k][0][0] == 'rbrace':
                    depth -= 1
                if depth == 0:
                    break
            lines.append([['typedef', 'mark'],
                          ['word', '&while'+str(num)],
                          ['eocl', ''],
                          [len(lines), 0, 0]])
            l = []
            if lines[i][1][0] == 'marksep':
                l = lines[i][0:2]
            lines[i] = l + [['transport', ''], ['gt', ''],
                            ['word', '&while'+str(num)],
                            ['eocl', ''], lines[i][-1]]
            newln = [['word', '&while'+str(num)], ['marksep', ''],
                     ['block', 'move'], ['lparen', ''], ['rparen', ''],
                     ['eocl', ''], [k+1, 0, 0]]
            lines = lines[0:k+1] + [newln] + lines[k+1:]
            for j in range(k+2, len(lines)):
                lines[j][-1][0] += 1
        
    return lines

def parseDefinition(line):
    global pos
    global tokline
    pos = 0
    tokline = line
    name = ''
    newobj = None
    deftype = line[0][1]
    global lineindex
    lineindex = line[-1][0]
    
    typ = []
    if deftype == 'hist':
        nexttok()
        consume('less')
        while True:
            if peek(0)[0] == 'gt':
                break
            typ.append(peek(0))
            nexttok()
    elif deftype == 'graph':
        nexttok()
        consume('less')
        typ1 = []
        while True:
            if peek(0)[0] == 'comma':
                break
            typ1.append(peek(0))
            nexttok()
        typ.append(typ1)
        consume('comma')
        typ1 = []
        while True:
            if peek(0)[0] == 'gt':
                break
            typ1.append(peek(0))
            nexttok()
        typ.append(typ1)
    
    tok = nexttok()
    if not tok or tok[0] != 'word':
       errors.print_error(3, lineindex, tok)
    name = tok[1]
    
    nexttok()
    indexes = []
    if matchtok('lbracket'):
        if name in arrays_info:
            errors.print_error(61, lineindex, [name])
        indexes.append(parseExpression())
        consume('rbracket')
        arrays_info[name] = [0, indexes[0] - 1]
    elif matchtok('lmatrix'):
        if name in matrices_info:
            errors.print_error(61, lineindex, [name])
        indexes.append(parseExpression())
        consume('comma')
        indexes.append(parseExpression())
        consume('rmatrix')
        matrices_info[name] = [[0, indexes[0] - 1], [0, indexes[1] - 1]]
    if indexes and deftype in ['mark', 'function']:
        errors.print_error(62, lineindex, [deftype])
    
    tok = peek(0)
    if deftype == 'int':
        if name in defined_var_names:
            errors.print_error(61, lineindex, [name])
        if not indexes:
            defined_var_names.append(name)
        if tok[0] == 'eocl':
            newobj = structs.IntVar(name, 0)
        elif tok[0] == 'eq':
            nexttok()
            newobj = structs.IntVar(name, parseExpression())
        else:
            errors.print_error(12, lineindex, ['=', peek(0)])
        
    elif deftype == 'float':
        if name in defined_var_names:
            errors.print_error(61, lineindex, [name])
        if not indexes:
            defined_var_names.append(name)
        if tok[0] == 'eocl':
            newobj = structs.FloatVar(name, 0)
        elif tok[0] == 'eq':
            nexttok()
            newobj = structs.FloatVar(name, parseExpression())
        else:
            errors.print_error(12, lineindex, ['=', peek(0)])
            
    elif deftype == 'bool':
        if name in defined_var_names:
            errors.print_error(61, lineindex, [name])
        if not indexes:
            defined_var_names.append(name)
        if tok[0] == 'eocl':
            newobj = structs.BoolVar(name, 0)
        elif tok[0] == 'eq':
            nexttok()
            newobj = structs.BoolVar(name, parseExpression())
        else:
            errors.print_error(12, lineindex, ['=', peek(0)])
            
    elif deftype == 'fac':
        deftype = 'facilitie'
        if tok[0] == 'eocl':
            newobj = structs.Facility(name, 1, True)
            # Note: let the interpreter create a queue for facility.
        elif matchtok('lbrace'):
            isQueued = True
            places = 1
            while True:
                if matchtok('rbrace'):
                    break
                if matchtok('comma'):
                    continue
                if matchtok('word', 'places'):
                    consume('eq')
                    tok = peek(0)
                    try:
                        places = int(tok[1])
                    except ValueError:
                        errors.print_error(5, lineindex, 
                               ['int', 'places', tok])
                    nexttok()
                    continue
                if matchtok('word', 'isQueued'):
                    consume('eq')
                    tok = peek(0)
                    if tok[1] == 'true':
                        isQueued = True
                    elif tok[1] == 'false':
                        isQueued = False
                    else:
                        errors.print_error(5, lineindex, 
                               ['bool', 'isQueued', tok[1]])
                    nexttok()
                    continue
                errors.print_error(4, lineindex, [peek(0)])
            newobj = structs.Facility(name, places, isQueued)
        else:
            errors.print_error(12, lineindex, ['{', peek(0)])
        
    elif deftype == 'queue':
        newobj = structs.Queue(name)
    
    elif deftype == 'chain':
        newobj = structs.Chain(name)
        
    elif deftype == 'mark':
        newobj = structs.Mark(name, -1)
        for line in interpreter.toklines:
            if line[0] == ['word', name] and line[1][0] == 'marksep':
                if newobj.block != -1:
                    i = line[-1][0]
                    errors.print_error(13, i, [name])
                newobj.block = line[-1][0]
        if newobj.block == -1:
            errors.print_warning(3, '', [name])
            
    elif deftype == 'str':
        if name in defined_var_names:
            errors.print_error(61, lineindex, [name])
        if not indexes:
            defined_var_names.append(name)
        if tok[0] == 'eocl':
            newobj = structs.StrVar(name, '')
        elif tok[0] == 'eq':
            nexttok()
            newobj = structs.StrVar(name, parseExpression())
        else:
            errors.print_error(12, lineindex, ['=', peek(0)])
    
    elif deftype == 'function':
        consume('lparen')
        args = []
        while True:
            if matchtok('rparen'):
                break
            if matchtok('comma'):
                continue
            if peek(0)[0] != 'word':
                errors.print_error(21, lineindex, ['word', peek(0)], 'F')
            args.append(peek(0)[1])
            nexttok()
        consume('lbrace')
        choices = []
        choice = []
        toks = []
        depth = 0
        while True:
            if peek(0)[0] == 'lparen':
                depth += 1
            if peek(0)[0] == 'rparen':
                depth -= 1
            if matchtok('rbrace'):
                choice.append(toks)
                if len(choice) != 2:
                    errors.print_error(54, lineindex, [len(choices), 2])
                choices.append(choice)
                break
            if matchtok('transport_prob'):
                choice.append(toks)
                toks = []
                if len(choice) != 2:
                    errors.print_error(54, lineindex, [len(choices), 2])
                choices.append(choice)
                choice = []
                continue
            if matchtok('comma'):
                if depth == 0:
                    choice.append(toks)
                    toks = []
                    if len(choice) != 1:
                        errors.print_error(54, lineindex, [len(choices), 1])
                    continue
                else:
                    pos -= 1
            toks.append(copy.deepcopy(peek(0)))
            nexttok()
        
        newobj = structs.ConditionalFunction(name, args, choices)
    
    elif deftype == 'graph':
        newobj =  structs.Graph2D(name, typ)
                
    else: # If deftype is hist
        if not matchtok('lbrace'):
            errors.print_error(51, lineindex)
        startval = None
        interval = None
        count = None
        while True:
            if matchtok('rbrace'):
                break
            if matchtok('comma'):
                continue
            if matchtok('word', 'start') or \
               matchtok('word', 'interval') or \
               matchtok('word', 'count'):
                consume('eq')
                tok = peek(0)
                valuename = peek(-2)[1]
                tempvalue = 0
                try:
                    tempvalue = float(tok[1])
                except ValueError:
                    errors.print_error(5, lineindex, 
                           ['int/float', valuename, tok])
                if valuename == 'start':
                    startval = tempvalue
                elif valuename == 'interval':
                    interval = tempvalue
                else:
                    count = tempvalue
                nexttok()
                continue
            errors.print_error(4, lineindex, [peek(0)])
        if startval != None and interval != None and count != None:
            newobj = structs.Histogram(name, typ, startval, interval, count)
        else:
            errors.print_error(52, lineindex)
    
    return (deftype, name, newobj, indexes)

def parseBlock(line, not_first_loop=False):
    global tokline
    global pos
    tokline = line
    pos = 0
    name = ''
    args = []
    global lineindex
    lineindex = line[-1][0]
    
    if ['rexec', ''] in tokline:
        errors.print_error(14, lineindex)
    if peek(0)[0] == 'word' and peek(1)[0] == 'marksep':
        if peek(0)[1] in interpreter.marks:
            consume('word')
            consume('marksep')
        else:
            errors.print_error(15, lineindex, [peek(0)[1]])

    tok = peek(0)
    if tok[0] == 'word':
        return parseAssignment()
    
    elif tok[0] == 'rbrace':
        depth = 0
        for i in reversed(list(range(0, interpreter.xact.curblk+2))):
            if interpreter.toklines[i][0][0] == 'rbrace':
                depth += 1
            elif interpreter.toklines[i][0][0] == 'lbrace':
                depth -= 1
            if depth == 0:
                break
        if depth != 0:
            errors.print_error(38, '', ['}', xact.curblk+1])
        i -= 1
        if ['block', 'while'] in interpreter.toklines[i]:
            interpreter.xact.curblk = i - 1
            interpreter.xact.cond = 'canmove'
            return parseBlock(interpreter.toklines[i])
        elif ['block', 'loop_times'] in interpreter.toklines[i]:
            interpreter.xact.curblk = i - 1
            interpreter.xact.cond = 'canmove'
            return parseBlock(interpreter.toklines[i], True)
        else:
            return ('move', '')
    
    elif tok[0] == 'block':
        if tok[1] == 'inject':
            name = 'move'
        elif tok[1] == 'loop_times':
            nexttok()
            consume('lparen')
            if not_first_loop:
                newln = []
                oldpos = pos
                while True:
                    t = peek(0)
                    if t[0] == 'comma':
                        break
                    newln.append(t)
                    if nexttok() == '':
                        errors.print_error(45, lineindex)
                oldline = line
                tokline = newln + [['inc', ''], ['eocl', '']]
                pos = 0
                parseAssignment()
                tokline = oldline
                pos = oldpos
            l = parseExpression()
            consume('comma')
            r = parseExpression()
            if l >= r:
                return ('while_block', [False])
            return ('while_block', [True])
        else:
            name = tok[1]
            if tok[1] == 'if' or tok[1] == 'else_if' or \
               tok[1] == 'else' or \
               tok[1] == 'while' or tok[1] == 'copy':
                name += '_block'
            nexttok()
            if tok[1] == 'else':
                return(name, [])
            consume('lparen')
            while True:
                if matchtok('rparen'):
                    break   
                if name == 'fac_irrupt' and len(args) == 4 or \
                   name == 'chain_pick' and len(args) == 1 or \
                   name == 'chain_find' and len(args) == 1:
                    toks = []
                    depth = 0
                    while True:
                        if peek(0)[0] == 'rparen':
                            depth -= 1
                        elif peek(0)[0] == 'lparen':
                            depth += 1
                        if depth == -1:
                            consume('rparen')
                            break
                        if peek(0)[0] == 'comma' and depth == 0:
                            consume('comma')
                            break
                        toks.append(peek(0))
                        nexttok()
                    args.append(toks)
                    continue
                
                args.append(parseExpression())
                if peek(0)[0] == 'comma':
                    consume('comma')
                    continue
                elif peek(0)[0] == 'rparen':
                    consume('rparen')
                    break
                else:
                    errors.print_error(16, lineindex, [peek(0)])
        return (name, args)
    
    elif tok[0] == 'transport':
        nexttok()
        if matchtok('gt'):
            name = 'transport'
        elif matchtok('transport_prob'):
            name = 'transport_prob'
        elif matchtok('transport_if'):
            name = 'transport_if'
        else:
            errors.print_error(34, lineindex, [peek(1)])
        block = parseExpression()
        if not matchtok('comma'):
            if name != 'transport':
                errors.print_error(35, lineindex)
            return (name, [block])
        prob = parseExpression()
        if matchtok('comma'):
            additblock = parseExpression()
            return (name, [block, prob, additblock])
        else:
            return (name, [block, prob])
    
    else:
        errors.print_error(21, lineindex, ['executive block, '\
               'transport operator or assignment lvalue', tok], 'E')

def parseAssignment(toks=[]):
    global pos
    global toklines
    if toks != []:
        pos = 0
        toklines = toks
    
    tok = copy.deepcopy(peek(0))
    tok1 = copy.deepcopy(peek(1))
    tok2 = peek(2)
    tok3 = peek(3)
    prim = ''
    sec = ''
    assg = ''
    key = ''
    res = ()
    
    if tok1[0] == 'dot' and tok2[0] == 'word':
        nexttok()
        nexttok()
        if tok[1] == 'xact':
            prim = 'xact'
            if tok2[1] not in list(interpreter.xact.params.keys()):
                errors.print_error(25, lineindex, 
                       [interpreter.xact.group, tok2[1]])
            sec = 'params'
            key = tok2[1]
        else:
            errors.print_error(26, lineindex, [tok[1]])
        assg = tok3[0]
        
        res = evaluateAssignment(prim, sec, assg, key)
        
    else:
        if tok[1] in arrays_info and tok1[0] == 'lbracket':
            nexttok()
            consume('lbracket')
            index = parseExpression()
            tok[1] = getArrayElementName(tok[1], index)
            tok1[0] = peek(1)[0]
        
        if tok[1] in matrices_info and tok1[0] == 'lmatrix':
            nexttok()
            consume('lmatrix')
            index1 = parseExpression()
            consume('comma')
            index2 = parseExpression()
            tok[1] = getMatrixElementName(tok[1], index1, index2)
            tok1[0] = peek(1)[0]
        
        if tok[1] in interpreter.ints:
            prim = 'ints'
        elif tok[1] in interpreter.floats:
            prim = 'floats'
        elif tok[1] in interpreter.strs:
            prim = 'strs'
        elif tok[1] in interpreter.bools:
            prim = 'bools'
        else:
            errors.print_error(27, lineindex, [tok[1]])
        key = tok[1]
        assg = tok1[0]
        
        res = evaluateAssignment(prim, '', assg, key)
        
    return res

def evaluateAssignment(prim, sec, assg, key):
    global assgs
    global lineindex
    #prim = xact, ints[], floats[], strs[]
    #sec = '', params[]
    #key = dict key if prim==ints,floats,strs and sec=='' - .value
       #or dict key if prim==xact and sec==params - []directly
    if config.log_assignments:  
        print(prim, sec, assg, key)
    
    if assg in assgs:
        attr = getattr(interpreter, prim)
        if sec != '': # xact.params[key]
            attr = getattr(attr, sec)
            if assg == 'inc':
                if type(attr[key]) is str or type(attr[key]) is bool:
                    errors.print_error(7, lineindex, ['inc'])
                attr[key] += 1
            elif assg == 'dec':
                if type(attr[key]) is str or type(attr[key]) is bool:
                    errors.print_error(7, lineindex, ['dec'])
                attr[key] -= 1
            else:
                nexttok()
                nexttok()
                result = parseExpression()
                result = checkAssignmentTypes(attr[key], result, assg)
                if assg == 'eq':         attr[key] = result
                elif assg == 'add':      attr[key] += result
                elif assg == 'subt':     attr[key] -= result
                elif assg == 'multeq':   attr[key] *= result
                elif assg == 'diveq':    attr[key] /= result
                elif assg == 'pwreq':    attr[key] = attr[key] ** result
                elif assg == 'remaineq': attr[key] %= result
                
        else: # ints[key].value, etc.
            if key == 'injected' or key == 'rejected' or key == 'curticks':
                errors.print_error(46, lineindex, [key])
            if assg == 'inc':
                if type(attr[key].value) is str or type(attr[key].value) is bool:
                    errors.print_error(7, lineindex, ['inc'])
                attr[key].value += 1
            elif assg == 'dec':
                if type(attr[key].value) is str or type(attr[key].value) is bool:
                    errors.print_error(7, lineindex, ['dec'])
                attr[key].value -= 1
            else:
                nexttok()
                nexttok()
                result = parseExpression()
                result = checkAssignmentTypes(attr[key].value, result, assg)
                if assg == 'eq':         attr[key].value = result
                elif assg == 'add':      attr[key].value += result
                elif assg == 'subt':     attr[key].value -= result
                elif assg == 'multeq':   attr[key].value *= result
                elif assg == 'diveq':    attr[key].value /= result
                elif assg == 'pwreq':
                    attr[key].value = attr[key].value ** result
                elif assg == 'remaineq': attr[key].value %= result
        
        if prim == 'xact' and sec == 'params' and key == 'priority':
            return ('review_cec', [])   
        return ('move', [])
    else:
        errors.print_error(21, lineindex, 
               ['assignment operator or "."', assg], 'C')

def checkAssignmentTypes(l, r, asg):
    if type(l) is int:
        if type(r) is int:
            return r
        if type(r) is float:
            return int(r)
        errors.print_error(33, lineindex, [asg, type(l), type(r)])
    if type(l) is float:
        if type(r) is int or type(r) is float:
            return r
        errors.print_error(33, lineindex, [asg, type(l), type(r)])
    if type(l) is str:
        if type(r) is not str:
            errors.print_error(33, lineindex, [asg, type(l), type(r)])
        if asg != 'eq' and asg != 'add':
            errors.print_error(33, lineindex, [asg, type(l), type(r)])
        return r
    if type(l) is bool:
        if type(r) is not bool:
            errors.print_error(33, lineindex, [asg, type(l), type(r)])
        return r
        
def parseInjector(line):
    newinj = None
    global tokline
    global pos
    pos = 0
    tokline = line
    global lineindex
    lineindex = line[-1][0]
    
    if peek(0)[0] == 'word' and peek(1)[0] == 'marksep':
        if peek(0)[1] in interpreter.marks:
            consume('word')
            consume('marksep')
        else:
            errors.print_error(15, lineindex, [peek(0)[1]])
    
    consume('block', 'inject')
    consume('lparen')
    
    tok = peek(0)
    if tok[0] != 'string':
        errors.print_error(17, lineindex, [tok])
    group = tok[1]
    nexttok()
    consume('comma')
    args = []
    for i in range (0, 4):
        tok = peek(0)
        if tok[0] != 'number':
            errors.print_error(18, lineindex, [tok])
        args.append(int(tok[1]))
        nexttok()
        if i != 3:
            consume('comma')
        else:
            consume('rparen')
            
    blk = line[-1][0]
    if not matchtok('lbrace'):
        newinj = structs.Injector(group, args[0], args[1], args[2], args[3], blk)
        return newinj
    params = {}
    while True:
        if matchtok('rbrace'):
            break
        if matchtok('comma'):
            continue
        tok1 = peek(0)
        nexttok()
        consume('eq')
        tok2 = peek(0)
        
        if tok1[0] != 'word':
            errors.print_error(21, lineindex, ['parameter name', tok1[0]], 'P')
        if tok1[1] in list(params.keys()):
                errors.print_warning(4, lineindex, [tok1[1]])
        
        if tok1[1] == 'priority':
            if tok2[0] != 'number':
                errors.print_error(19, lineindex, ['number', tok1[1], tok2])
            params[tok1[1]] = float(tok2[1])
        else:
            if tok2[0] == 'number':
                if '.' in tok1[1]:
                    params[tok1[1]] = float(tok2[1])
                else:
                    params[tok1[1]] = int(tok2[1])
            elif tok2[0] == 'string':
                params[tok1[1]] = tok2[1]
            elif tok2[0] == 'word':
                if tok2[1] == 'true':
                    params[tok1[1]] = True
                elif tok2[1] == 'false':
                    params[tok1[1]] = False
                else:
                    errors.print_error(21, lineindex, 
                              ['true/false word', tok2[1]], 'P')
            else:
                errors.print_error(21, lineindex, 
                              ['number/boolean/string', tok2], 'P')
        nexttok()
        
    newinj = structs.Injector(group, args[0], args[1], args[2], args[3], 
                              blk, params)
    return newinj
    
def parseExitCondition(line):
    global tokline
    global pos
    pos = 0
    tokline = line
    nexttok()
    consume('lparen')
    result = parseExpression()
    consume('rparen')
    if result == 0:
        return False
    return True

def parseExpression():
    result = parseLogicalOr()
    return result

def parseLogicalOr():
    result = parseLogicalAnd()
    while True:
        if matchtok('or'):
            rh = parseLogicalAnd()
            result = result or rh
            continue
        break
    return result

def parseLogicalAnd():
    result = parseCompEq()
    while True:
        if matchtok('and'):
            rh = parseCompEq()
            result = result and rh
            continue
        break
        
    return result
    
def parseCompEq():
    result = parseCondition()
    while True:
        if matchtok('compeq'):
            result = result == parseCondition()
            continue
        if matchtok('noteq'):
            result = result != parseCondition()
            continue
        break
    return result
    
def parseCondition():
    result = parseAdd()
    while True:
        if matchtok('gt'):
            result = result > parseAdd()
            continue
        if matchtok('less'):
            result = result < parseAdd()
            continue
        if matchtok('gteq'):
            result = result >= parseAdd()
            continue
        if matchtok('lesseq'):
            result = result <= parseAdd()
            continue
        break
    return result
    
def parseAdd():
    result = parseMult()
    
    while True:
        if matchtok('plus'):
            result1 = parseMult()
            if type(result1) is str and type(result) is not str or \
               type(result) is str and type(result1) is not str:
                errors.print_error(20, lineindex)
            result += result1
            continue
        if matchtok('minus'):
            result1 = parseMult()
            if type(result1) is str or type(result) is str:
                errors.print_error(8, lineindex, ['-'])
            result -= result1
            continue
        break
    
    return result
    
def parseMult():
    result = parseUnary()
    
    while True:
        if matchtok('mult'):
            result1 = parseUnary()
            if type(result1) is str or type(result) is str:
                errors.print_error(8, lineindex, ['*'])
            result *= result1
            continue
        if matchtok('div'):
            result1 = parseUnary()
            if type(result1) is str or type(result) is str:
                errors.print_error(8, lineindex, ['/'])
            result /= result1
            continue
        if matchtok('remain'):
            result1 = parseUnary()
            if type(result1) is str or type(result) is str:
                errors.print_error(8, lineindex, ['%'])
            result = result % result1
            continue
        if matchtok('pwr'):
            result1 = parseUnary()
            if type(result1) is str or type(result) is str:
                errors.print_error(8, lineindex, ['**'])
            result = result ** result1
            continue
        break
    
    return result
    
def parseUnary():
    if matchtok('not'):
        return (not parseDot())
    if matchtok('minus'):
        return -1 * parseDot()
    if matchtok('plus'):
        return parseDot()
    return parseDot()

def parseDot():
    lh = parseArray()
    if matchtok('dot'):
        return getAttrsForDotOperator(lh, parseArray())
    return lh
    
def getAttrsForDotOperator(lh, rh):
    val = None
    if config.log_dot_operator:
        print('Dot attrs:', lh, rh)
    if rh in fac_params and lh in interpreter.facilities:
        val = getattr(interpreter.facilities[lh], rh)
        
    elif rh in queue_params and lh in interpreter.queues:
        val = getattr(interpreter.queues[lh], rh)
        
    elif rh in chain_params and lh in interpreter.chains:
        val = getattr(interpreter.chains[lh], rh)
        
    elif rh in hist_params and lh in interpreter.hists:
        val = getattr(interpreter.hists[lh], rh)
    
    elif lh == 'xact':
        if rh not in xact_params: #parameters from 'params' dict
            if rh not in list(interpreter.xact.params.keys()):
                errors.print_error(25, lineindex, 
                       [interpreter.xact.group, rh])
            val = interpreter.xact.params[rh]
        else: #direct parameters
            val = getattr(interpreter.xact, rh)
    elif lh == 'chxact':
        if rh not in xact_params: #parameters from 'params' dict
            if rh not in list(interpreter.chxact.params.keys()):
                errors.print_error(25, lineindex, 
                       [interpreter.chxact.group, rh])
            val = interpreter.chxact.params[rh]         
        else: #direct parameters
            val = getattr(interpreter.xact, rh)
    
    elif rh == 'name':
        if lh in interpreter.ints:
            val = interpreter.ints[lh].name
        elif lh in interpreter.floats:
            val = interpreter.floats[lh].name
        elif lh in interpreter.strs:
            val = interpreter.strs[lh].name
        elif lh in interpreter.bools:
            val = interpreter.bools[lh].name
        else:
            errors.print_error(28, lineindex, [lh])
    else:
        errors.print_error(21, lineindex, 
               ["name of parameter of defined variable", lh+' '+rh], 'B')
    return val
    
def parseArray():
    arrayname = parsePrimary()
    if matchtok('lbracket'):
        arrname = getArrayElementName(arrayname, parseExpression())
        consume('rbracket')
        val = parsePrimaryWord(arrname)
        return val
    elif matchtok('lmatrix'):
        index1 = parseExpression()
        consume('comma')
        index2 = parseExpression()
        consume('rmatrix')
        mxname = getMatrixElementName(arrayname, index1, index2)
        val = parsePrimaryWord(mxname)
        return val
    return arrayname
    
def getArrayElementName(arrayname, index):
    lbound = arrays_info[arrayname][0]
    rbound = arrays_info[arrayname][1]
    if lbound <= index <= rbound:
        return arrayname + '&&' + str(index)
    errors.print_error(56, lineindex, [index, lbound, rbound])
    
def getMatrixElementName(matrixname, index1, index2):
    horlbound = matrices_info[matrixname][0][0]
    horrbound = matrices_info[matrixname][0][1]
    vertlbound = matrices_info[matrixname][1][0]
    vertrbound = matrices_info[matrixname][1][1]
    if vertlbound <= index1 <= vertrbound and \
       horlbound <= index2 <= horrbound:
        return arrayname + '&&(' + str(index1) + ',' + str(index2) + ')'
    errors.print_error(56, lineindex, [[index1, index2], 
                      [vertlbound, vertrbound], [horlbound, horrbound]])
    
def parsePrimary():
    if matchtok('lparen'):
        result = parseExpression()
        consume('rparen')
        return result
    tok = peek(0)
    val = 0
    
    if tok[0] == 'indirect':
        return parseIndirect()
        
    if tok[0] == 'number':
        if '.' in str(tok[1]):
            val = float(tok[1])
        else:
            val = int(tok[1])
            
    elif tok[0] == 'string':
        if tok[0].startswith('~'):
            return parseIndirectString()
        else:
            val = tok[1]
            
    elif tok[0] == 'word':
        val = parsePrimaryWord(tok[1])
    
    elif tok[0] == 'builtin':
        return parseBuiltin()
    
    nexttok()
    return val

def parsePrimaryWord(word):
    global pos
    if word == 'true':
        val = True
    elif word == 'false':
        val = False
    
    elif word in interpreter.functions:
        val = parseConditionalFunction(word)
        pos -= 1
    
    elif word in interpreter.attachables:
        val = parseAttachableFunction(word)
        pos -= 1
    
    elif word in interpreter.ints:
        val = interpreter.ints[word].value
    elif word in interpreter.floats:
        val = interpreter.floats[word].value
    elif word in interpreter.strs:
        val = interpreter.strs[word].value
    elif word in interpreter.bools:
        val = interpreter.bools[word].value
    elif word in interpreter.facilities:
        val = interpreter.facilities[word].name
    elif word in interpreter.queues:
        val = interpreter.queues[word].name
    elif word in interpreter.marks:
        val = interpreter.marks[word].name
    elif word in interpreter.chains:
        val = interpreter.chains[word].name
    elif word in interpreter.hists:
        val = interpreter.hists[word].name
    elif word in fac_params+queue_params+xact_params+ \
                   chain_params+hist_params+['xact', 'chxact']+ \
                   list(arrays_info.keys())+list(matrices_info.keys()):
        val = word
    elif type(list(interpreter.xact.params.keys())) is not None and \
         word in list(interpreter.xact.params.keys()):
        val = word
    else:
        errors.print_error(6, lineindex, [word])
    return val

def parseConditionalFunction(functionName):
    func = interpreter.functions[functionName]
    argvalues = []
    nexttok()
    consume('lparen')
    while True:
        if matchtok('rparen'):
            break
        argvalues.append(parseExpression())
        if peek(0)[0] == 'comma':
            consume('comma')
            continue
        elif peek(0)[0] == 'rparen':
            consume('rparen')
            break
        else:
            errors.print_error(16, lineindex, [peek(0)], 'C')
    if len(argvalues) != len(func.args):
        errors.print_error(55, lineindex, [functionName, len(func.args),
                                           len(argvalues)])
    return func.call(argvalues)

def parseAttachableFunction(modulename):
    nexttok()
    consume('dot')
    functionname = peek(0)[1]
    func = None
    try:
        func = getattr(interpreter.attachables[modulename], functionname)
    except AttributeError:
        errors.print_error(58, lineindex, [modulename, functionname])
    nexttok()
    consume('lparen')
    args = []
    while True:
        if matchtok('rparen'):
            break
        args.append(parseExpression())
        if peek(0)[0] == 'comma':
            consume('comma')
            continue
        elif peek(0)[0] == 'rparen':
            consume('rparen')
            break
        else:
            errors.print_error(16, lineindex, [peek(0)], 'A')
    
    if len(inspect.getargspec(func).args) != len(args):
            errors.print_error(55, lineindex, [name, 
                                   len(inspect.getargspec(func).args), 
                                   len(args)])
    return func(*args)

def parseIndirect(val=''):
    global tokline
    global pos
    if val == '':
        consume('indirect')
        val = parseExpression()
    ln = lexer.analyze(str(val)+';\0')
    ln.pop()
    oldline = copy.deepcopy(tokline)
    oldpos = pos
    tokline = ln
    pos = 0
    val = parseExpression()
    tokline = copy.deepcopy(oldline)
    pos = oldpos
    return val
    
def parseIndirectString():
    global tokline
    global pos
    s = peek(0)[1][1:]
    return parseIndirect(s)

def parseBuiltin():
    name = peek(0)[1]
    fun = getattr(builtins, name)
    args = []
    nexttok()
    consume('lparen')
    if name == 'find_minmax':
        if peek(0)[1] != 'min' and peek(0)[1] != 'max':
            errors.print_error(21, lineindex, ['min/max', peek(0)[1]], 'D')
        args.append(peek(0)[1])
        nexttok()
        consume('comma')
    if name == 'find' or name == 'find_minmax':
        toks = []
        depth = 0
        while True:
            if peek(0)[0] == 'rparen':
                depth -= 1
            elif peek(0)[0] == 'lparen':
                depth += 1
            if depth == -1:
                consume('rparen')
                break
            toks.append(peek(0))
            nexttok()
        args.append(toks)
        
        if len(inspect.getargspec(fun).args) != len(args):
            errors.print_error(55, lineindex, [name, 
                                   len(inspect.getargspec(fun).args), 
                                   len(args)])
        return fun(*args)
        
    # For other builtins:   
    while True:
        if matchtok('rparen'):
            break
        args.append(parseExpression())
        if peek(0)[0] == 'comma':
            consume('comma')
            continue
        elif peek(0)[0] == 'rparen':
            consume('rparen')
            break
        else:
            errors.print_error(16, lineindex, [peek(0)], 'B')
    
    if name == 'round_to' and (len(args) != 1 or len(args) != 2):
        errors.print_error(55, lineindex, ['round_to', 
                                   '1 or 2', 
                                   len(args)])
    elif len(inspect.getargspec(fun).args) != len(args):
            errors.print_error(55, lineindex, [name, 
                                   len(inspect.getargspec(fun).args), 
                                   len(args)])
    return fun(*args)

def consume(toktype, toktext=''):
    global pos
    global lineindex
    if peek(0)[0] != toktype:
        if toktext != '':
            if peek(0)[1] != toktext:
                errors.print_error(21, lineindex, 
                       [[toktype, toktext], peek(0)], 'A')
        else:
            errors.print_error(21, lineindex, 
                       [toktype, peek(0)], 'A')
    pos += 1
    
def nexttok():
    global pos
    global tokline
    pos += 1
    if pos >= len(tokline):
        return []
    return tokline[pos]

def matchtok(toktype, toktext=''):
    global pos
    if not peek(0) or peek(0)[0] != toktype or peek(0)[1] != toktext:
        return False
    pos += 1
    return True
    
def peek(relpos):
    global pos
    global tokline
    index = pos + relpos
    if len(tokline) <= index:
        return []
    return tokline[index]
