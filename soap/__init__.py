class relationship(object):
    def __init__(self, classname):
        self._classname = classname
        self._obj = None

    def __get__(self, instance, cls):
        if self._obj is None:
            self._obj = cls._subs[self._classname]
        return self._obj


class SchemaBaseMeta(type):
    _subs = {}

    def __new__(metaclass, classname, bases, attrs):
        attrs['_subs'] = metaclass._subs
        new = super(SchemaBaseMeta, metaclass).__new__(metaclass, classname, bases, attrs)
        # do we have the Base or a subclass here?
        if any(isinstance(parent, SchemaBaseMeta) for parent in bases):
            metaclass._subs[classname] = new
        return new


class SchemaBase(object):
    __metaclass__ = SchemaBaseMeta
