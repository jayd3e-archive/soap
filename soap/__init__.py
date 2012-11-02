class Invalid(Exception):
    def __init__(self, msg, node, model):
        self.msg = msg
        self.node = node
        self.model = model

    def __str__(self):
        return 'Invalid(\'%s\', %s, %s)' % (self.msg, self.model, self.node)


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
                deserialized[child.name] = child.deserialize(value, node, model)
            else:
                if not child.missing is None:
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
                deserialized.append(child.deserialize(value, node, model))

        return deserialized

    def validate(self, json, node, model):
        try:
            return list(json)
        except Exception:
            raise Invalid('SchemaNode is not an interable type.', node, model)


class Relationship(object):
    name = ''

    def __init__(self, model_name, uselist=True):
        self.model_name = model_name
        self.uselist = uselist

    def deserialize(self, json, node, model):
        inst = model._models[self.model_name]
        if self.uselist:
            schema_model = SchemaNode(Sequence(),
                                      inst,
                                      name=node.name)
        else:
            schema_model = inst
        return schema_model.deserialize(json, node, model)


class SchemaNode(object):
    _type = None
    children = None
    name = ''
    missing = None

    def __init__(self, *args, **kwargs):
        self.children = []

        if args:
            self._type = args[0]
            self.children = list(args[1:])

        self.name = kwargs['name']
        self.missing = kwargs.get('missing', None)

    def deserialize(self, json, node, model):
        deserialized = self._type.deserialize(json, self, model)
        return deserialized

    def get(self, name, default=None):
        for child in self.children:
            if child.name == name:
                return child
        return default


class SchemaModel(SchemaNode):
    _models = {}

    def __init__(self, name, *args, **kwargs):
        self.children = []

        if args:
            self._type = args[0]
            self.children = list(args[1:])

        self.name = name
        self._models[name] = self

    def validate(self, json):
        return self.deserialize(json)

    def deserialize(self, json, node=None, model=None):
        node = node if node else self
        model = self
        # ugly
        self.name = node.name if node else self.name

        deserialized = self._type.deserialize(json, self, model)
        return deserialized
