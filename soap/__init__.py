import itertools
from colander import (
    Mapping,
    Tuple,
    _SchemaMeta,
    _SchemaNode,
    String,
    Int,
    Sequence,
    Mapping,
    SchemaNode,
    _marker
)


class relationship(SchemaNode):
    _counter = itertools.count()
    name = ''
    raw_title = _marker
    title = ''

    def __init__(self,
                 classname,
                 backref=None,
                 one_to_many=True,
                 many_to_one=False,
                 one_to_one=False,
                 uselist=False):
        self._list = True if one_to_many else False
        self._classname = classname
        self._backref = backref
        self._there = None

    def map(self, here):
        if self._there is None:
            self._there = here._subs[self._classname]

        if self._list:
            self.typ = Sequence()
        else:
            self.typ = Mapping()

        here.add(self._there(name='child', stop_exec=True))

        if self._backref:
            self._there.add(here.__class__(name=self._backref, stop_exec=True))


class SchemaBaseMeta(_SchemaMeta):
    _subs = {}

    def __new__(metaclass, classname, bases, attrs):
        attrs['_subs'] = metaclass._subs
        new = super(_SchemaMeta, metaclass).__new__(metaclass, classname, bases, attrs)

        # We want to only add subclasses of SchemaBase to the list of Schemas un '_subs',
        # so since SchemaBase(class) is an instance of SchemaBaseMeta(metaclass), we check
        # if any of our current parents(found in 'bases' arg) are instances of SchemaBaseMeta
        if any(isinstance(parent, SchemaBaseMeta) for parent in bases):
            metaclass._subs[classname] = new
        return new

    def __init__(metaclass, classname, bases, attrs):
        nodes = []

        for name, value in attrs.items():
            if isinstance(value, _SchemaNode) or isinstance(value, relationship):
                delattr(metaclass, name)
                if not value.name:
                    value.name = name
                if value.raw_title is _marker:
                    value.title = name.replace('_', ' ').title()
                nodes.append((value._order, value))

        nodes.sort()
        metaclass.__class_schema_nodes__ = [n[1] for n in nodes]

        # Combine all attrs from this class and its _SchemaNode superclasses.
        metaclass.__all_schema_nodes__ = []
        for c in reversed(metaclass.__mro__):
            csn = getattr(c, '__class_schema_nodes__', [])
            metaclass.__all_schema_nodes__.extend(csn)


def mapper(schema):
    for name, schema in Schema._subs.items():
        for node in schema.__all_schema_nodes__:
            if isinstance(node, relationship):
                node.map(schema)


def initialize_schema(self, *args, **kwargs):
    super(SchemaNode, self).__init__(*args, **kwargs)

    if not kwargs.get('stop_exec', False):
        mapper(self)


class Schema(SchemaNode):
    schema_type = Mapping
    __metaclass__ = SchemaBaseMeta
    __init__ = initialize_schema


MappingSchema = Schema


class TupleSchema(SchemaNode):
    schema_type = Tuple
    __metaclass__ = SchemaBaseMeta
    __init__ = initialize_schema


class MappingSchema(SchemaNode):
    schema_type = Mapping
    __metaclass__ = SchemaBaseMeta
    __init__ = initialize_schema
