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

def _match(d,tags):
    if len(d) == 0:
        return False
    op = d[0]
    if op == 'or':
        return _match(d[1],tags) or _match(d[2],tags)
    elif op == 'and':
        return _match(d[1],tags) and _match(d[2],tags)
    elif op == '=':
        return d[1] in tags and tags[d[1]] == d[2]
    elif op == 'notnull':
        return d[1] in tags
    elif op == 'in':
        return (d[1] in tags) and (tags[d[1]] in d[2])
    elif op == '!=':
        return d[1] not in tags or tags[d[1]] != d[2]
    elif op == '>':
        return d[1] in tags and str(tags[d[1]]) > str(d[2])
    elif op == '<':
        return d[1] in tags and str(tags[d[1]]) < str(d[2])
    elif op == '>=':
        return d[1] in tags and str(tags[d[1]]) >= str(d[2])
    elif op == '<=':
        return d[1] in tags and str(tags[d[1]]) <= str(d[2])
    raise Exception

class Matcher:
    def __init__(self,expr):
        self.expr = expr

    def matches(self,tags):
        return _match(self.expr,tags)

    # returns a new matcher
    def union(self,other_matcher):
        return Matcher(('or',self.expr,other_matcher.expr))

    @classmethod
    def any(cls,tag_name):
        return Matcher(('notnull',tag_name))

    @classmethod
    def null(cls):
        return Matcher(())

    @classmethod
    def from_sql(cls,sql):
        def prefixform(d):
            if 'or' in d:
                return ('or',prefixform(d['condition']),prefixform(d['expression']))
            elif 'and' in d:
                return ('and',prefixform(d['condition']),prefixform(d['expression']))
            elif 'condition' in d:
                return prefixform(d['condition'])
            elif 'expression' in d:
                return prefixform(d['expression'])
            elif 'binop' in d:
                return (d['binop'],d['columnName'],d['rval'][0])
            elif 'notnull' in d:
                return ('notnull',d['columnName'])
            elif 'in' in d:
                return ('in',d['columnName'],d['rval'])
        return cls(prefixform(whereExpression.parseString(sql,parseAll=True).asDict()))
