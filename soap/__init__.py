import re
import datetime
import pprint
from colander import iso8601

falsey = ['', {}, []]


class Invalid(Exception):
    pos = None
    positional = False

    def __init__(self, msg, node):
        self.msg = msg
        self.node = node
        self.children = []

    def __str__(self):
        return pprint.pformat(self.asdict())

    __repr__ = __str__

    def add(self, exc, pos=None):
        if pos is not None:
            self.positional = True
            exc.pos = pos
        self.children.append(exc)

    def _keyname(self):
        if self.pos:
            return str(self.pos)
        return self.node.name

    def asdict(self):
        if self.children:
            returned = {}
            for child in self.children:
                key = child._keyname()
                returned[key] = child.asdict()
            return returned

        # so we always return a list
        if type(self.msg) is list:
            return self.msg
        return [self.msg]


#
# Types
#

class Int(object):
    def deserialize(self, value, payload, node, model):
        try:
            return int(value)
        except Exception:
            raise Invalid('SchemaNode is not an integer.', node)


class String(object):
    def deserialize(self, value, payload, node, model):
        try:
            return str(value)
        except Exception:
            raise Invalid('SchemaNode is not an string.', node)


class DateTime(object):
    def __init__(self, default_tzinfo=None):
        if default_tzinfo is None:
            default_tzinfo = iso8601.Utc()
        self.default_tzinfo = default_tzinfo

    def deserialize(self, value, payload, node, model):
        try:
            result = iso8601.parse_date(value, default_timezone=self.default_tzinfo)
        except (iso8601.ParseError, TypeError):
            try:
                year, month, day = map(int, value.split('-', 2))
                result = datetime.datetime(year, month, day,
                                           tzinfo=self.default_tzinfo)
            except Exception:
                raise Invalid('SchemaNode is not a datetime', node)
        return result


class Boolean(object):
    def deserialize(self, value, payload, node, model):
        try:
            result = str(value)
        except:
            raise Invalid('Boolean SchemaNode is not a string', node)
        result = result.lower()

        if result in ('false', '0'):
            return False

        return True


class Mapping(object):
    def deserialize(self, value, payload, node, model):
        validated = self.validate(value, payload, node, model)

        exc = None
        deserialized = {}
        for child in node.children:
            try:
                value = validated.get(child.name, None)
                if not value is None:
                    deserialized[child.name] = child.deserialize(value, payload=payload, model=model)
                elif not child.missing is None:
                    deserialized[child.name] = child.missing
                else:
                    raise Invalid('The field named \'%s\' is missing.' % child.name, child)
            except Invalid as e:
                if exc is None:
                    exc = Invalid('Mapping Errors', node)
                exc.add(e)

        if exc is not None:
            raise exc

        return deserialized

    def validate(self, value, payload, node, model):
        try:
            return dict(value)
        except Exception:
            raise Invalid('SchemaNode is not a mapping type.', node)


class Sequence(object):
    def deserialize(self, value, payload, node, model):
        validated = self.validate(value, payload, node, model)
        child = node.children[0]

        exc = None
        deserialized = []
        for num, value in enumerate(validated):
            try:
                deserialized.append(child.deserialize(value, payload=payload, model=model))
            except Invalid as e:
                if exc is None:
                    exc = Invalid('Sequence Errors', node)
                exc.add(e, num)

        if exc is not None:
            raise exc

        return deserialized

    def validate(self, value, payload, node, model):
        try:
            return list(value)
        except Exception:
            raise Invalid('SchemaNode is not an interable type.', node)


class Relationship(object):
    name = ''

    def __init__(self, name, uselist=True):
        self.name = name
        self.uselist = uselist

    def deserialize(self, value, payload, node, model):
        inst = model._models[self.name]
        inst = inst if isinstance(inst, SchemaModel) else inst(name=node.name,
                                                               missing=node.missing)

        if self.uselist:
            schema_model = SchemaNode(Sequence(),
                                      inst,
                                      name=node.name,
                                      missing=node.missing)
        else:
            schema_model = inst

        return schema_model.deserialize(value, payload=payload, model=model)


#
# Validators
#

class Length(object):
    def __init__(self, _min=None, _max=None):
        self.min = _min
        self.max = _max

    def __call__(self, value, payload, node, model):
        if self.min is not None:
            if len(value) < self.min:
                raise Invalid('Shorter than minimum length %s' % self.min, node)

        if self.max is not None:
            if len(value) > self.max:
                raise Invalid('Longer than maximum length %s' % self.max, node)


class Regex(object):
    def __init__(self, regex, msg=None):
        if isinstance(regex, basestring):
            self.match_object = re.compile(regex)
        else:
            self.match_object = regex
        if msg is None:
            self.msg = 'String does not match expected pattern'
        else:
            self.msg = msg

    def __call__(self, value, payload, node, model):
        if self.match_object.match(value) is None:
            raise Invalid(self.msg, node)


class Email(Regex):
    def __init__(self):
        msg = 'Invalid email address'
        super(Email, self).__init__('(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', msg=msg)


class Range(object):
    def __init__(self, _min=None, _max=None):
        self.min = _min
        self.max = _max

    def __call__(self, value, payload, node, model):
        if self.min is not None:
            if value < self.min:
                raise Invalid('Less than minimum value of %s' % self.min, node)

        if self.max is not None:
            if value > self.max:
                raise Invalid('Greater than maximum value of %s' % self.max, node)


#
# Core
#

class SchemaNode(object):
    name = ''
    _type = None
    children = None
    missing = None
    validator = None
    preparer = None

    def __init__(self, *args, **kwargs):
        self.children = []

        if args:
            self._type = args[0]
            self.children = list(args[1:])

        self.__dict__.update(kwargs)

    @property
    def required(self):
        return self.missing is None

    def deserialize(self, value, payload=None, node=None, model=None):
        node = node if node else self
        model = model if model else self
        payload = payload if payload else value

        deserialized = self._type.deserialize(value, payload, node, model)

        # Run all preparers
        if self.preparer and type(self.preparer) is list:
            for preparer in self.preparer:
                deserialized = preparer(deserialized)
        elif self.preparer:
            deserialized = self.preparer(deserialized)

        # Make sure the supplied value isn't a falsey value
        if deserialized in falsey and node.required:
            raise Invalid('%s is required.' % node.name, node)

        # Run all validators
        excs = []
        if self.validator and type(self.validator) is list:
            for validator in self.validator:
                try:
                    validator(deserialized, payload, node, model)
                except Invalid as e:
                    excs.append(e)
        elif self.validator:
            try:
                self.validator(deserialized, payload, node, model)
            except Invalid as e:
                excs.append(e)

        # If we have any validation exception, then raise them as a single exception
        if excs:
            exc = Invalid([e.msg for e in excs], node)
            for e in excs:
                exc.children.extend(e.children)
            raise exc

        return deserialized

    def get(self, name, default=None):
        for child in self.children:
            if child.name == name:
                return child
        return default

    def __repr__(self):
        return '<soap.SchemaNode named \'%s\'>' % self.name


class SchemaModelMeta(type):
    _models = {}

    def __init__(cls, name, bases, clsattrs):
        if any(isinstance(parent, SchemaModelMeta) for parent in bases):
            cls.children = []
            cls.name = name
            cls._models[name] = cls
            cls._type = Mapping()

            # get SchemaNodes from class
            for key, value in clsattrs.items():
                if isinstance(value, SchemaNode):
                    delattr(cls, key)

                    value.name = key if not value.name else value.name
                    cls.children.append(value)

            # get SchemaNodes from bases
            for _class in reversed(cls.__mro__[1:]):
                for key, value in _class.__dict__.items():
                    if isinstance(value, SchemaNode):
                        value.name = key if not value.name else value.name
                        cls.children.append(value)


class SchemaModel(SchemaNode):
    __metaclass__ = SchemaModelMeta
    _models = {}

    def __init__(self, *args, **kwargs):
        if args:
            self.children = []

            self.name = name = args[0]
            self._models[name] = self

            self._type = args[1]
            self.children = list(args[2:])

        self.__dict__.update(kwargs)

    def validate(self, value):
        return self.deserialize(value)
