# -*- coding: utf-8 -*
class PyMacroParser(object):
    lines = []            # codes read from c++ file
    parsedLines = []
    preDefinedMacro = {}  # pre-defined macro dictionary
    macroDict = {}        # macro transfer dictionary
    currentLine = 0
    totalLine = 0
    hasPreComment = False
    stateStack = []
    _special = {'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v', '\\': '\\', '\'': '\'',
                '\"': '\"', '0': '\0'}

    def __init__(self):
        self.lines = []

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
            print "cannot read file"
        self.totalLine = len(self.lines)
        self._preparse()

    def preDefine(self, s):
        self.preDefinedMacro.clear()

        macros = s.split(';')
        for macro in macros:
            macro = macro.strip()
            if len(macro) > 0:
                self.preDefinedMacro[macro] = None
        self._preparse()

    def dumpDict(self):
        return self.macroDict.copy()

    def dump(self, f):
        try:
            with open(f, 'w') as file:
                for key, value in self.macroDict.items():
                    if type(value) is tuple:
                        file.write('#define ' + key + ' ' + self._dumpTuple(value) + '\n')
                    else:
                        file.write('#define ' + key + ' ' + self._dumpBasicType(value) + '\n')

                file.close()
        except IOError:
            print "cannot write file"

    def _initMembers(self):
        self.macroDict.clear()
        self.parsedLines = []
        self.currentLine = 0
        self.hasPreComment = False
        self.stateStack = []

    def _preparse(self):
        self._initMembers()

        for name, value in self.preDefinedMacro.items():
            self.macroDict[name] = value

        self.currentLine = 0
        while self.currentLine < self.totalLine:
            sentence = self._getSentence()
            self._parseSentence(sentence)

    def _getSentence(self):
        sentence = ''
        end = False
        while self.currentLine < self.totalLine:
            if len(self.parsedLines) >= self.currentLine + 1:
                line = self.parsedLines[self.currentLine]
            else:
                line = self.lines[self.currentLine]
                line = self._parseComment(line).strip()
                self.parsedLines.append(line)
            if len(line) == 0:
                self.currentLine += 1
            else:
                if line[0] != '#':
                    self.currentLine += 1
                    sentence += line + ' '
                else:
                    if end:
                        break
                    else:
                        sentence += line + ' '
                        end = True
                        self.currentLine += 1
        print sentence
        return sentence[0: -1]

    def _parseSentence(self, sentence):
        invalid = {' ', '\t', '\r', '\f'}
        macroState = ''
        index = 1
        while index < len(sentence) and sentence[index] in invalid:
            index += 1
        while index < len(sentence) and sentence[index] not in invalid:
            macroState += sentence[index]
            index += 1
        while index < len(sentence) and sentence[index] in invalid:
            index += 1
        macroName = ''
        while index < len(sentence) and sentence[index] not in invalid:
            macroName += sentence[index]
            index += 1
        macroValue = ''
        while index < len(sentence) and sentence[index] in invalid:
            index += 1
        while index < len(sentence):
            macroValue += sentence[index]
            index += 1
        if len(macroValue) > 0 and macroValue[0] == "\"":
            macroValue = self._combineString(macroValue)
        #print 'macroState: ' + macroState
        #print 'macroName: ' + macroName
        #print 'macroValue: ' + macroValue
        if macroState == 'ifndef':
            currentState = True
            lastState = True
            if macroName in self.macroDict:
                currentState = False
            if len(self.stateStack) > 0:
                if not self.stateStack[-1][1] or not self.stateStack[-1][2]:
                    lastState = False
            self.stateStack.append(['if', currentState, lastState])
        elif macroState == 'define':
            if len(macroName) > 0:
                if len(self.stateStack) == 0 or self.stateStack[-1][1] and self.stateStack[-1][2]:
                    if len(macroValue) > 0:
                        result = self._parseMacroValue(macroValue)
                        self.macroDict[macroName] = result
                    else:
                        self.macroDict[macroName] = None
        elif macroState == 'ifdef':
            currentState = True
            lastState = True
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
            if len(self.stateStack) == 0 or self.stateStack[-1][1] and self.stateStack[-1][2]:
                if macroName in self.macroDict:
                    del self.macroDict[macroName]

    def _combineString(self, macroValue):
        index = 0
        result = '\"'
        while index < len(macroValue):
            start = self._findQuato(macroValue, index)
            if start == len(macroValue):
                return macroValue
            end = self._findQuato(macroValue, start + 1)
            result += macroValue[start+1: end]
            index = end + 1
        result += '\"'
        return result

    def _findQuato(self, string, index):
        hasTag = False
        while index < len(string):
            if string[index] == '\\':
                hasTag = not hasTag
            else:
                hasTag = False
                if string[index] == '\"' and not hasTag:
                    return index
            index += 1
        return index


    def _parseComment(self, line):
        outStr = ''
        i = 0
        while i < len(line):
            if self.hasPreComment:
                while i < len(line):
                    if i + 1 < len(line) and line[i: i+2] == '*/':
                        self.hasPreComment = False
                        i += 2
                        break
                    i += 1
            else:
                hasTag = False
                if line[i] == '\\':
                    hasTag = not hasTag
                else:
                    hasTag = False
                if line[i] == '\"' and not hasTag:
                    outStr += line[i]
                    i += 1
                    while i < len(line):
                        if line[i] == '\\':
                            hasTag = not hasTag
                        else:
                            hasTag = False
                        outStr += line[i]
                        i += 1
                        if i < len(line) and line[i] == '\"' and not hasTag:
                            outStr += line[i]
                            i += 1
                            break
                elif i + 1 < len(line) and line[i: i+2] == '/*':
                    self.hasPreComment = True
                    i = i + 2
                elif i + 1 < len(line) and line[i: i+2] == '//':
                    break
                else:
                    outStr += line[i]
                    i += 1
        return outStr

    def _parseMacroValue(self, value):
        if value[0] == '{':
            return self._parseTuple(value)
        return self._parseBaseValue(value)

    def _parseBaseValue(self, value):
        if value[0] == '-' or value[0] == '+':
            result = self._parseBaseValue(value[1:].strip())
            if type(result) != int and type(result) != float:
                raise NameError('not valid number')
            else:
                if value[0] == '-':
                    return -1 * result
                else:
                    return result
        if value[-1] == 'f' or value[-1] == 'F':
            return self._parseFloat(value[0: -1])
        if value[0] == '\'':
            return self._parseChar(value)
        if value[0: 2] == '0x':
            return self._parse16Number(value[2:])
        if value[0] == '0':
            return self._parse8Number(value[1:])
        if value.isdigit():
            return self._parseInt(value)
        if value[-1] == 'L' or value[-1] == 'l':
            if '.' in value:
                return self._parseFloat(value[0: -1])
            else:
                return self._parseInt(value[0: -1])
        if value[0] == 'L':
            return self._parseLongString(value)
        if value[0] == '\"':
            return self._parseString(value)
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

    def _parseTuple(self, value):
        tupleStack = []
        part = ''
        hasQuato = False
        hasTag = False
        for c in value:
            if c == '\\':
                hasTag = not hasTag
            else:
                if c == '\"' and not hasTag:
                    hasQuato = not hasQuato
                hasTag = False
            if not hasQuato:
                if c == '{':
                    tupleStack.append('{')
                elif c == '}':
                    part = part.strip()
                    if len(part) > 0:
                        tupleStack.append(self._parseBaseValue(part))
                        part = ''
                    list = []
                    while tupleStack[-1] != '{':
                        list.insert(0, tupleStack.pop())
                    tupleStack.pop()
                    tupleStack.append(tuple(list))
                elif c == ',':
                    part = part.strip()
                    if len(part) > 0:
                        tupleStack.append(self._parseBaseValue(part.strip()))
                        part = ''
                else:
                    part += c
            else:
                part += c
        return tupleStack.pop()


    def _parseFloat(self, value):
        return float(value)

    def _parseInt(self, value):
        return int(value)

    def _parseChar(self, value):
        value = value[1:]
        if value[0] == '\\' and len(value) > 1 and value[1] in _special:
            return ord(_special[value[1]])
        if value[0] == '\\' and len(value) > 1 and value[1] == 'x':
            return self._parse16Number(value[2: -1])
        if value[0] == '\\' and len(value) > 1:
            return self._parse8Number(value[1: -1])
        else:
            return ord(value[0])

    def _parse16Number(self, value):
        _16number = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'a': 10, 'b': 11,
                     'c': 12, 'd': 13, 'e': 14, 'f': 15, 'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15}
        length = len(value)
        num = 0
        for i in range(length):
            if value[i] in _16number:
                num += pow(16, length - i - 1) * _16number[value[i]]
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
        value = value[2: -1]
        return unicode(value)

    def _parseString(self, value):
        value = value[1: -1]
        return value

    def _parseBool(self, value):
        if value == 'true':
            return True
        else:
            return False

    def _parseScientific(self, value):
        return float(value)

    def _dumpTuple(self, value):
        result = ''
        result += '{'
        for item in value:
            if type(item) is tuple:
                result += self._dumpTuple(item)
            else:
                result += self._dumpBasicType(item)
            result += ', '
        result = result[0: -2]
        result += '}'
        return result

    def _dumpBasicType(self, value):
        if isinstance(value, unicode):
            return 'L"' + value + '"'
        elif isinstance(value, str):
            return '"' + value + '"'
        elif value == None:
            return ''
        elif type(value) == bool:
            if value:
                return 'true'
            else:
                return 'false'
        else:
            return str(value)


f = "/Users/Raina/Desktop/a.cpp"
filename = "/Users/Raina/Desktop/b.cpp"
output = "/Users/Raina/Desktop/c.cpp"
a1 = PyMacroParser()
a2 = PyMacroParser()
a1.load(f)
a1.dump(filename)
a2.load(filename)
a2.dumpDict()
a1.preDefine("MC1;MC2")
a1.dumpDict()
a1.dump(output)


