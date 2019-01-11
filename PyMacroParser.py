# -*- coding: utf-8 -*
import string
class PyMacroParser(object):
    _special = {'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v', '\\': '\\', '\'': '\'',
                '\"': '\"', '0': '\0'}
    _dumpSpecial = {'\a': 'a', '\b': 'b', '\f': 'f', '\n': 'n', '\r': 'r', '\t': 't', '\v': 'v', '\\': '\\', '\'': '\'',
                    '\"': '\"', '\0': '0'}
    _16number = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'a': 10, 'b': 11,
                 'c': 12, 'd': 13, 'e': 14, 'f': 15, 'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15}

    def __init__(self):
        self.lines = []  # codes read from c++ file
        self.parsedLines = []
        self.preDefinedMacro = {}  # pre-defined macro dictionary
        self.macroDict = {}  # macro transfer dictionary
        self.currentLine = 0  # currently handling line number
        self.totalLine = 0
        self.hasPreComment = False  # for indicating whether has /* before
        self.stateStack = []  # for dealing with statements

    def load(self, f):
        self.lines = []
        try:
            with open(f, 'r') as file:
                for line in file.readlines():
                    line = line.strip()
                    if line:
                        self.lines.append(line)
                file.close()
        except IOError:
            raise IOError("cannot read file")
        self.totalLine = len(self.lines)
        self._preparse()

    def preDefine(self, s):
        self.preDefinedMacro.clear() #need to clear before another defination

        macros = s.split(';')
        for macro in macros:         #add predefined macro to current macro dictionary
            macro = macro.strip()
            if len(macro) > 0:
                self.preDefinedMacro[macro] = None
        self._preparse()

    def dumpDict(self):
        return self._copyDict()     #return deepcopy, not shadow copy

    def dump(self, f):
        try:
            with open(f, 'w') as file:
                content = []
                it = iter(self.macroDict)
                for key in it:
                    value = self.macroDict[key]
                    if type(value) is tuple:
                        content.append('#define ' + key + ' ' + self._dumpTuple(value) + '\n')
                    else:
                        content.append('#define ' + key + ' ' + self._dumpBasicType(value) + '\n')
                file.write(''.join(content))
                file.close()
        except IOError:
            raise IOError("cannot write file")

    def _initMembers(self):
        self.macroDict.clear()
        self.parsedLines = []
        self.currentLine = 0
        self.hasPreComment = False
        self.stateStack = []

    def _preparse(self):
        self._initMembers()     #need to initialize everytime

        it = iter(self.preDefinedMacro)
        for key in it:
            self.macroDict[key] = self.preDefinedMacro[key]

        while self.currentLine < self.totalLine:
            sentence = self._getSentence()  #one sentence may exist in many lines
            self._parseSentence(sentence)

    def _getSentence(self):
        sentence = []
        end = False
        while self.currentLine < self.totalLine:
            if len(self.parsedLines) >= self.currentLine + 1:
                line = self.parsedLines[self.currentLine]
            else:
                line = self.lines[self.currentLine]
                line = self._parseComment(line)  # delete comments
                self.parsedLines.append(line.strip())
            if len(line.strip()) == 0:
                self.currentLine += 1
            else:
                if line.strip()[0] != '#': #every statement should start with '#'
                    self.currentLine += 1
                    sentence.append(line)
                else:
                    if end:
                        break
                    else:
                        sentence.append(line)
                        end = True
                        self.currentLine += 1
        print ''.join(sentence)
        return ''.join(sentence)

    def _parseSentence(self, sentence):
        invalid = string.whitespace
        macroState = []
        index = 1
        length = len(sentence)
        #get judgement sentence
        while index < length and sentence[index] in invalid:
            index += 1
        while index < length and sentence[index] not in invalid:
            macroState.append(sentence[index])
            index += 1
        macroState = ''.join(macroState)
        #get macroname
        while index < length and sentence[index] in invalid:
            index += 1
        macroName = []
        while index < length and sentence[index] not in invalid and sentence[index] != '\"':
            macroName.append(sentence[index])
            index += 1
        macroName = ''.join(macroName)
        #get macro value
        macroValue = []
        while index < length and sentence[index] in invalid:
            index += 1
        while index < length:
            macroValue.append(sentence[index])
            index += 1
        macroValue = ''.join(macroValue)

        #for statement, we have two situation, current and parent
        #current is used for else statement, if current and parent statement are both true, we can do the following operations
        if macroState == 'ifndef':
            currentState = True
            lastState = True
            macroName = self._macroNameCut(macroName)
            self._checkNameLegal(macroName)
            if macroName in self.macroDict:
                currentState = False
            if len(self.stateStack) > 0:
                if not self.stateStack[-1][1] or not self.stateStack[-1][2]:
                    lastState = False
            self.stateStack.append(['if', currentState, lastState])
        elif macroState == 'define':
            if len(macroName) > 0: #empty define may exist
                if len(self.stateStack) == 0 or self.stateStack[-1][1] and self.stateStack[-1][2]:
                    self._checkNameLegal(macroName)
                    if len(macroValue) > 0:
                        result = self._parseMacroValue(macroValue)
                        self.macroDict[macroName] = result
                    else:
                        self.macroDict[macroName] = None
        elif macroState == 'ifdef':
            currentState = True
            lastState = True
            macroName = self._macroNameCut(macroName)
            self._checkNameLegal(macroName)
            if macroName not in self.macroDict:
                currentState = False
            if len(self.stateStack) > 0:
                if not self.stateStack[-1][1] or not self.stateStack[-1][2]:
                    lastState = False
            self.stateStack.append(['if', currentState, lastState])
        elif macroState == 'else':
            content = self.stateStack[-1]
            if content[0] == 'if':
                self.stateStack.append(['else', not content[1], content[2]])
            else:
                raise NameError('many else!')
        elif macroState == 'endif':
            if len(self.stateStack) == 0:
                raise NameError('no if!')
            else:
                while self.stateStack[-1][0] != 'if':
                    self.stateStack.pop()
                self.stateStack.pop()
        elif macroState == 'undef':
            macroName = self._macroNameCut(macroName)
            self._checkNameLegal(macroName)
            if len(self.stateStack) == 0 or self.stateStack[-1][1] and self.stateStack[-1][2]:
                if macroName in self.macroDict:
                    del self.macroDict[macroName]
        else:
            raise NameError('Not valid statement!')

    def _checkNameLegal(self, macroName):
        if not macroName[0].isalpha() and macroName[0] != '_':
            raise NameError('Not valid macroname!')
        for i in range(1, len(macroName)):
            if not macroName[i].isalpha and not macroName[i].isdigit() and macroName[i] != '_':
                raise NameError('Not valid macroname!')

    def _macroNameCut(self, macroName):
        #for the case #ifdef a;123
        index = 1
        length = len(macroName)
        while index < length:
            if macroName[index] == ';':
                return macroName[0: index]
            index += 1
        return macroName

    def _combineString(self, macroValue):
        #need to combine string and know it is long string or common string
        isLong = False
        result = []
        result.append('\"')
        if macroValue[0] == 'L':
            index = 1
        else:
            index = 0
        length = len(macroValue)
        while index < length:
            start = self._findQuato(macroValue, index, '\"')
            if macroValue[start-1] == 'L':
                isLong = True
            if start == length:
                return macroValue
            end = self._findQuato(macroValue, start + 1, '\"')
            if end == length:
                raise NameError('Not valid string!')
            result.append(macroValue[start+1: end])
            index = end + 1
        result.append('\"')
        return ''.join(result), isLong

    def _findQuato(self, string, index, quato):
        #used for find the start and end of " to find a string
        hasTag = False #considering zhuanyi
        length = len(string)
        while index < length:
            if string[index] == '\\':
                hasTag = not hasTag
            else:
                if string[index] == quato and not hasTag:
                    return index
                hasTag = False
            index += 1
        return index


    def _parseComment(self, line):
        outStr = []
        i = 0
        length = len(line)
        while i < length:
            if self.hasPreComment:
                while i < length:
                    if i + 1 < len(line) and line[i: i+2] == '*/': #if has /* before, all these ignored until find '*/
                        self.hasPreComment = False
                        i += 2
                        outStr.append(' ')
                        break
                    i += 1
            else:
                #need to consider if these comment tags are in the string
                if line[i] == '\"':
                    next = self._findQuato(line, i + 1, '\"')
                    outStr.append(line[i: next+1])
                    i = next + 1
                elif line[i] == '\'':
                    next = self._findQuato(line, i + 1, '\'')
                    outStr.append(line[i: next+1])
                    i = next + 1
                elif i + 1 < length and line[i: i+2] == '/*':
                    self.hasPreComment = True
                    i = i + 2
                elif i + 1 < length and line[i: i+2] == '//':
                    break
                elif i + 1 < length and line[i: i+2] == '*/':
                    raise NameError('invalid commnet!')
                else:
                    outStr.append(line[i])
                    i += 1
        return ''.join(outStr)

    def _parseMacroValue(self, value):
        if value[0] == '{':
            return self._parseTuple(value)
        return self._parseBaseValue(value)

    def _parseBaseValue(self, value):
        if value[0] == '-' or value[0] == '+':
            countNegative = 0
            index = 0
            length = len(value)
            while index < length:
                if value[index] == '-':
                    countNegative += 1
                elif value[index] != '+' and value[index] != ' ':
                    break
                index += 1
            result = self._parseBaseValue(value[index:].strip())
            if type(result) != int and type(result) != float:
                raise NameError('not valid number')
            else:
                if countNegative % 2 == 1:
                    return -1 * result
                else:
                    return result
        if value[-1] == 'U' or value[-1] == 'u' or value[-1] == 'L' or value[-1] == 'l':
            return self._parseBaseValue(value[0: -1])
        if value[0: 2] == '0x' or value[0: 2] == '0X':
            return self._parse16Number(value[2:])
        if value[-1] == 'f' or value[-1] == 'F':
            return self._parseBaseValue(value[0: -1])
        if value[0] == '\'':
            return self._parseChar(value[1: -1])
        if value[0] == '0' and len(value) > 1 and value.isdigit():
            return self._parse8Number(value[1:])
        if value.isdigit():
            return self._parseInt(value)
        if value[0] == 'L' or value[0] == '\"':
            return self._parseStringSet(value)
        if value == 'true' or value == 'false':
            return self._parseBool(value)
        if 'e' in value or 'E' in value:
            return self._parseScientific(value)
        if '.' in value:
            count = 0
            for c in value:
                if c == '.':
                    count += 1
                    if count > 1:
                        raise NameError('not valid float number')
                elif not c.isdigit():
                    raise NameError('not valid float number')
            return self._parseFloat(value)
        raise NameError('Not valid type!')

    def _parseTuple(self, value):
        tupleStack = []
        part = []
        index = 0
        length = len(value)
        while index < length:
            c = value[index]
            if c == '\"':
                next = self._findQuato(value, index + 1, '\"')
                part.append(value[index: next+1])
                index = next + 1
            elif c == '\'':
                next = self._findQuato(value, index + 1, '\'')
                part.append(value[index: next+1])
                index = next + 1
            elif c == '{':
                tupleStack.append('\{')
                index += 1
            elif c == '}':
                result = ''.join(part).strip()
                if len(result) > 0:
                    tupleStack.append(self._parseBaseValue(result))
                    part = []
                list = []
                while tupleStack[-1] != '\{':
                    list.insert(0, tupleStack.pop())
                tupleStack.pop()
                tupleStack.append(tuple(list))
                index += 1
            elif c == ',':
                result = ''.join(part).strip()
                if len(result) > 0:
                    tupleStack.append(self._parseBaseValue(result))
                    part = []
                index += 1
            else:
                part.append(c)
                index += 1
        return tupleStack.pop()


    def _parseFloat(self, value):
        return float(value)

    def _parseInt(self, value):
        return int(value)

    def _parseChar(self, value):
        length = len(value)
        if length == 0 or length == 1 and value[0] == '\\':
            raise NameError('Not valid char!')
        if value[0] == '\\' and value[1] in self._special: #zhuanyi
            return ord(self._special[value[1]])
        if value[0] == '\\' and value[1] == 'x': #16 jinzhi
            return self._parse16Number(value[2:])
        if value[0] == '\\' and int(value[1]) in range(8): #8 jinzhi
            return self._parse8Number(value[1:])
        elif value[0] == '\\': #\p igonre \
            return ord(value[1])
        else:
            return ord(value[0])

    def _parse16Number(self, value):
        length = len(value)
        num = 0
        for i in range(length):
            if value[i] in self._16number:
                num += pow(16, length - i - 1) * self._16number[value[i]]
            else:
                raise NameError('Invalid 16 number!')
        return num

    def _parse8Number(self, value):
        length = len(value)
        num = 0
        for i in range(length):
            if int(value[i]) in range(0, 8):
                num += pow(8, length - i - 1) * int(value[i])
            else:
                raise NameError('Invalid 8 number!')
        return num

    def _parseLongString(self, value):
        value = self._parseString(value)
        return unicode(value)

    def _parseStringSet(self, value):
        value, isLong = self._combineString(value)
        if isLong:
            return self._parseLongString(value)
        else:
            return self._parseString(value)

    def _parseString(self, value):
        value = value[1: -1]
        i = 0
        result = []
        length = len(value)
        if length == 0:
            return ''
        while i < length:
            if value[i] == '\\':
                if i + 1 >= len(value):
                    raise NameError('Not valid zhuanyi!')
                elif value[i+1] in self._special:
                    result.append(self._special[value[i+1]])
                    i += 2
                elif value[i+1] == 'x':
                    i += 2
                    endIndex = i
                    maxIndex = i + 1
                    while endIndex < length and endIndex <= maxIndex:
                        if value[endIndex] in self._16number:
                            endIndex += 1
                        else:
                            break
                    if endIndex == i:
                        raise NameError('Not valid 16 number')
                    else:
                        result.append(chr(self._parse16Number(value[i: endIndex])))
                        i = endIndex
                else:
                    i += 1
                    endIndex = i
                    maxIndex = i + 2
                    while endIndex < length and endIndex <= maxIndex:
                        if value[endIndex].isdigit() and int(value[endIndex]) in range(8):
                            endIndex += 1
                        else:
                            break
                    if endIndex > i:
                        result.append(chr(self._parse8Number(value[i: endIndex])))
                        i = endIndex
                    else:
                        result.append(value[i])
                        i += 1
            else:
                result.append(value[i])
                i += 1
        return ''.join(result)

    def _parseBool(self, value):
        if value == 'true':
            return True
        else:
            return False

    def _parseScientific(self, value):
        return float(value)

    def _dumpTuple(self, value):
        result = []
        result.append('{')
        for item in value:
            if type(item) is tuple:
                result.append(self._dumpTuple(item))
            else:
                result.append(self._dumpBasicType(item))
            result.append(', ')
        if len(result) > 1:
            result = result[0: -1]
        result.append('}')
        return ''.join(result)

    def _dumpBasicType(self, value):
        if isinstance(value, unicode):
            return 'L"' + self._dumpString(value) + '"'
        elif isinstance(value, str):
            return '"' + self._dumpString(value) + '"'
        elif value == None:
            return ''
        elif type(value) == bool:
            if value:
                return 'true'
            else:
                return 'false'
        else:
            return str(value)

    def _dumpString(self, value):
        result = []
        for i in range(len(value)):
            if value[i] in self._dumpSpecial:
                result.append('\\' + self._dumpSpecial[value[i]])
            else:
                result.append(value[i])
        return ''.join(result)

    def _copyDict(self):
        copyDict = {}
        for key in self.macroDict:
            value = self.macroDict[key]
            if type(value) is tuple:
                copyDict[key] = self._copyTuple(value)
            else:
                copyDict[key] = self._copyBasic(value)
            copyDict[key] = value
        return copyDict

    def _copyTuple(self, object):
        list = []
        for element in object:
            if type(element) is tuple:
                return self._copyTuple(element)
            else:
                list.append(self._copyBasic(element))
        return tuple(list)

    def _copyBasic(self, value):
        if type(value) == str:
            return self._copyString(value)
        elif type(value) == unicode:
            return unicode(self._copyString(value))
        else:
            return value

    def _copyString(self, string):
        result = []
        for c in string:
            result.append(c)
        return ''.join(result)



if __name__ == '__main__':
    a1 = PyMacroParser()
    a2 = PyMacroParser()
    a1.load("/Users/Raina/Desktop/网易作业/Test/test09.cpp")
    filename = "/Users/Raina/Desktop/b.cpp"
    a1.dump(filename)
    a2.load(filename)
    a2.dumpDict()
    a1.preDefine("MC1;MC2")
    a1.dumpDict()
    a1.dump("/Users/Raina/Desktop/c.cpp")



