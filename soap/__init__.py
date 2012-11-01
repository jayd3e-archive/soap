class Invalid(Exception):
    def __init__(self, node, msg):
        self.node = node
        self.msg = msg

    def __str__(self):
        return 'Invalid(\'%s\', %s)' % (self.msg, self.node)


class SchemaType(object):
    pass


class Int(SchemaType):
    def deserialize(self, node, json):
        try:
            return int(json)
        except Exception:
            raise Invalid(node, 'SchemaNode is not an integer.')


class String(SchemaType):
    def deserialize(self, node, json):
        try:
            return str(json)
        except Exception:
            raise Invalid(node, 'SchemaNode is not an string.')


class Mapping(SchemaType):
    def deserialize(self, node, json):
        validated = self.validate(node, json)

        deserialized = {}
        for child in node.children:
            value = validated.get(child.name, None)
            if not value is None:
                deserialized[child.name] = child.deserialize(value)
            else:
                if not child.missing is None:
                    deserialized[child.name] = child.missing
                else:
                    raise Invalid(child, 'The field named \'%s\' is missing.' % child.name)

        return deserialized

    def validate(self, node, json):
        try:
            return dict(json)
        except Exception:
            raise Invalid(node, 'SchemaNode is not a mapping type.')


class Sequence(SchemaType):
    def deserialize(self, node, json):
        validated = self.validate(node, json)

        deserialized = []
        for value in validated:
            child = node.children[0]
            if child:
                deserialized.append(child.deserialize(value))

        return deserialized

    def validate(self, node, json):
        try:
            return list(json)
        except Exception:
            raise Invalid(node, 'SchemaNode is not an interable type.')


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

        # if a name isn't found, we make it the root node
        self.name = kwargs.get('name', 'root')
        self.missing = kwargs.get('missing', None)

    def validate(self, json):
        """
        Proxy to deserialize.
        """
        return self.deserialize(json)

    def deserialize(self, json):
        deserialized = self._type.deserialize(self, json)
        return deserialized

    def get(self, name, default=None):
        for child in self.children:
            if child.name == name:
                return child
        return default
