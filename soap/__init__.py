import re
import datetime
from colander import iso8601

falsey = ['', {}, []]


class Invalid(Exception):
    def __init__(self, msg, node, model):
        self.msg = msg
        self.node = node
        self.model = model

    def __str__(self):
        return 'Invalid(\'%s\', %s, %s)' % (self.msg, self.model, self.node)


#
# Types
#

class Int(object):
    def deserialize(self, json, node, model):
        try:
            return int(json)
        except Exception:
            raise Invalid('SchemaNode is not an integer.', node, model)


class String(object):
    def deserialize(self, json, node, model):
        try:
            return str(json)
        except Exception:
            raise Invalid('SchemaNode is not an string.', node, model)


class DateTime(object):
    def __init__(self, default_tzinfo=None):
        if default_tzinfo is None:
            default_tzinfo = iso8601.Utc()
        self.default_tzinfo = default_tzinfo

    def deserialize(self, json, node, model):
        try:
            result = iso8601.parse_date(json, default_timezone=self.default_tzinfo)
        except (iso8601.ParseError, TypeError):
            try:
                year, month, day = map(int, json.split('-', 2))
                result = datetime.datetime(year, month, day,
                                           tzinfo=self.default_tzinfo)
            except Exception:
                raise Invalid('SchemaNode is not a datetime', node, model)
        return result


class Boolean(object):
    def deserialize(self, json, node, model):
        try:
            result = str(json)
        except:
            raise Invalid('Boolean SchemaNode is not a string', node, model)
        result = result.lower()

        if result in ('false', '0'):
            return False

        return True


class Mapping(object):
    def deserialize(self, json, node, model):
        validated = self.validate(json, node, model)

        deserialized = {}
        for child in node.children:
            value = validated.get(child.name, None)
            if not value is None:
                deserialized[child.name] = child.deserialize(value, model=model)
            elif not child.missing is None:
                deserialized[child.name] = child.missing
            else:
                raise Invalid('The field named \'%s\' is missing.' % child.name, child, model)

        return deserialized

    def validate(self, json, node, model):
        try:
            return dict(json)
        except Exception:
            raise Invalid('SchemaNode is not a mapping type.', node, model)


class Sequence(object):
    def deserialize(self, json, node, model):
        validated = self.validate(json, node, model)

        deserialized = []
        for value in validated:
            child = node.children[0]
            if child:
                deserialized.append(child.deserialize(value, model=model))

        return deserialized

    def validate(self, json, node, model):
        try:
            return list(json)
        except Exception:
            raise Invalid('SchemaNode is not an interable type.', node, model)


class Relationship(object):
    model_name = ''

    def __init__(self, model_name, uselist=True):
        self.model_name = model_name
        self.uselist = uselist

    def deserialize(self, json, node, model):
        inst = model._models[self.model_name]
        inst = inst if isinstance(inst, SchemaModel) else inst(name=node.name,
                                                               missing=node.missing)

        if self.uselist:
            schema_model = SchemaNode(Sequence(),
                                      inst,
                                      name=node.name,
                                      missing=node.missing)
        else:
            schema_model = inst

        return schema_model.deserialize(json, model=model)


#
# Validators
#

class Length(object):
    def __init__(self, _min=None, _max=None):
        self.min = _min
        self.max = _max

    def __call__(self, value, node, model):
        if self.min is not None:
            if len(value) < self.min:
                raise Invalid('Shorter than minimum length %s' % self.min, node, model)

        if self.max is not None:
            if len(value) > self.max:
                raise Invalid('Longer than maximum length %s' % self.max, node, model)


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

    def __call__(self, value, node, model):
        if self.match_object.match(value) is None:
            raise Invalid(self.msg, node, model)


class Email(Regex):
    def __init__(self):
        msg = 'Invalid email address'
        super(Email, self).__init__('(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', msg=msg)


class Range(object):
    def __init__(self, _min=None, _max=None):
        self.min = _min
        self.max = _max

    def __call__(self, value, node, model):
        if self.min is not None:
            if value < self.min:
                raise Invalid('Less than minimum value of %s' % self.min, node, model)

        if self.max is not None:
            if value > self.max:
                raise Invalid('Greater than maximum value of %s' % self.max, node, model)


#
# Core
#

class SchemaNode(object):
    _type = None
    children = None
    name = ''
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

    def deserialize(self, json, node=None, model=None):
        node = node if node else self
        model = model if model else self

        deserialized = self._type.deserialize(json, node, model)

        # preparers logic

        if json in falsey and node.required:
            raise Invalid('%s is required.' % node.name, node, model)

        if self.preparer and type(self.preparer) is list:
            for preparer in self.preparer:
                deserialized = preparer(deserialized)
        elif self.preparer:
            deserialized = self.preparer(deserialized)

        if self.validator and type(self.validator) is list:
            for validator in self.validator:
                validator(json, node, model)
        elif self.validator:
            self.validator(json, node, model)

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

    def __init__(cls, model_name, bases, clsattrs):
        if any(isinstance(parent, SchemaModelMeta) for parent in bases):
            cls.children = []
            cls.model_name = model_name
            cls._models[model_name] = cls
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

            model_name = args[0]
            self._models[model_name] = self
            self.model_name = model_name

            self._type = args[1]
            self.children = list(args[2:])

        self.__dict__.update(kwargs)

    def validate(self, json):
        return self.deserialize(json)
