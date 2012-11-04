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


#
# Core
#

class SchemaNode(object):
    _type = None
    children = None
    name = ''
    missing = None
    validator = None

    def __init__(self, *args, **kwargs):
        self.children = []

        if args:
            self._type = args[0]
            self.children = list(args[1:])

        self.name = kwargs.get('name', '')
        self.missing = kwargs.get('missing', None)
        self.validator = kwargs.get('validator', None)

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


class SchemaModelMeta(type):
    _models = {}

    def __init__(cls, model_name, bases, clsattrs):
        if any(isinstance(parent, SchemaModelMeta) for parent in bases):
            cls.model_name = model_name
            cls._models[model_name] = cls
            cls._type = Mapping()
            cls.children = []

            for key, value in clsattrs.items():
                if isinstance(value, SchemaNode):
                    delattr(cls, key)

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
