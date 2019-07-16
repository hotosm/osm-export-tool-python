from pyparsing import Word, delimitedList, Optional, \
    Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, Keyword 

class InvalidSQL(Exception):
    pass


ident          = Word( alphas, alphanums + "_:" )
columnName =   (ident | quotedString())("columnName")

whereExpression = Forward()
and_ = Keyword("and", caseless=True)('and')
or_ = Keyword("or", caseless=True)('or')
in_ = Keyword("in", caseless=True)("in")
isnotnull = Keyword("is not null",caseless=True)('notnull')
binop = oneOf("= != < > >= <=", caseless=True)('binop')
intNum = Word( nums )

columnRval = (intNum | quotedString.setParseAction(lambda x:x[0][1:-1]))('rval*')
whereCondition = Group(
    ( columnName + isnotnull ) |
    ( columnName + binop + columnRval ) |
    ( columnName + in_ + "(" + delimitedList( columnRval ) + ")" ) |
    ( "(" + whereExpression + ")" )
    )('condition')
whereExpression << Group(whereCondition + ZeroOrMore( ( and_ | or_ ) + whereExpression ) )('expression')

class SQLValidator(object):
    """ Parses a subset of SQL to define feature selections.
        This validates the SQL to make sure the user can't do anything dangerous."""

    def __init__(self,s):
        self._s = s
        self._errors = []
        self._parse_result = None

    @property
    def valid(self):
        try:
            self._parse_result = whereExpression.parseString(self._s,parseAll=True)
        except InvalidSQL as e:
            self._errors.append(str(e))
            return False
        except ParseException as e:
            self._errors.append("SQL could not be parsed.")
            return False
        return True

    @property
    def errors(self):
        return self._errors

    @property
    def column_names(self):
        # takes a dictionary, returns a list
        def column_names_in_dict(d):
            result = []
            for key, value in d.items():
                if 'columnName'  == key:
                    result = result + [value]
                if isinstance(value,dict):
                    result = result + column_names_in_dict(value)
            return result
        return column_names_in_dict(self._parse_result.asDict())

def strip_quotes(token):
    if token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    if token[0] == "'" and token[-1] == "'":
        token = token[1:-1]
    return token.replace(' ','\\ ')


# is either an Expression or a Condition
def _match(d,tags):
    if 'or' in d:
        return _match(d['condition'],tags) or _match(d['expression'],tags)
    if 'and' in d:
        return _match(d['condition'],tags) and _match(d['expression'],tags)
    if 'binop' in d:
        if d['binop'] == '=':
            return d['columnName'] in tags and tags[d['columnName']] == d['rval'][0]
        if d['binop'] == '!=':
            return d['columnName'] not in tags or tags[d['columnName']] != d['rval'][0]
    if 'condition' in d:
        return _match(d['condition'],tags)
    if 'expression' in d:
        return _match(d['expression'],tags)
    if 'notnull' in d:
        return d['columnName'] in tags
    if 'in' in d:
        return d['columnName'] in tags and tags[d['columnName']] in d['rval']
    print(d)
    raise Exception

class Matcher:
    def __init__(self,s):
        self._parse_result = whereExpression.parseString(s,parseAll=True).asDict()
        # TODO convert parse_result into an optimized form with string interning

    def matches(self,tags):
        return _match(self._parse_result,tags)
