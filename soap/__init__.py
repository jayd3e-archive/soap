import re
import datetime
import pprint
from colander import iso8601

falsey = ['', {}, []]


class Invalid(Exception):
    """
    An exception raised by data types and validators. Requires a mandatory
    msg and node argument.  The msg is used for conveying what part of the application
    actually threw the exception and also why the exception was thrown.  The node
    is used to store off which particular node was being deserialized when the errors
    was thrown. The node should be an instance of a :class:`soap.SchemaNode`.


    Like the SchemaNodes themselves, the Invalid exception is heirarchical.  This means
    you can add child exceptions to it.  As the exceptions bubble up, they form a
    mapping of exceptions that is identical to the value being parsed.
    """
    pos = None

    def __init__(self, msg, node):
        self.msg = msg
        self.node = node
        self.children = []

    def __str__(self):
        """  Return a formatted representation of the exception """
        return pprint.pformat(self.asdict())

    __repr__ = __str__

    def add(self, exc, pos=None):
        """ Method for adding a child exception.  If a :class:`soap.Sequence` is being
            parsed and errors are being reported, specify a str for the optional
            'pos' argument. The 'pos' argument, which is an abbreviation of 'position',
            represents the index of the :class:`soap.Sequence` element where errors
            occured. """
        if pos is not None:
            exc.pos = pos
        self.children.append(exc)

    def _keyname(self):
        """ Returns the node name of the exception, or the 'pos' argument if it's
            set.  """
        if self.pos is not None:
            return str(self.pos)
        return self.node.name

    def asdict(self):
        """ Returns a representation of the exception in dict() form.  This is commonly
            used in the view of the application during error reporting.  The structure
            of this dict, strictly mimics that of the value that is being deserialized. """
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

class null(object):
    """ Represents a null value in soap-related operations. """
    def __nonzero__(self):
        return False

    def __repr__(self):
        return '<soap.null>'


class Int(object):
    """ Represents a Integer datatype in a schema.  Anything that can be cast as a
        python int() will be deserialized properly. Like all other datatypes, an instance
        of this class can be passed into a :class:`soap.SchemaNode` to create a SchemaNode
        of type :class:`soap.Int`. """

    def deserialize(self, value, mapping, node, model):
        try:
            return int(value)
        except Exception:
            raise Invalid('SchemaNode is not an integer.', node)


class String(object):
    """ Represents a String datatype in a schema.  Anything that can be cast as a
        python str() will be deserialized properly. Like all other datatypes, an instance
        of this class can be passed into a :class:`soap.SchemaNode` to create a SchemaNode
        of type :class:`soap.String` """

    def deserialize(self, value, mapping, node, model):
        try:
            return str(value)
        except Exception:
            raise Invalid('SchemaNode is not an string.', node)


class DateTime(object):
    """ Represents a DateTime datatype in a schema.  This is an identical implementation
        to colander's DateTime object.  iso8601 is actually a module in colander itself.
        Like all other datatypes, an instance of this class can be passed into a
        :class:`soap.SchemaNode` to create a SchemaNode of type :class:`soap.DateTime` """

    def __init__(self, default_tzinfo=None):
        if default_tzinfo is None:
            default_tzinfo = iso8601.Utc()
        self.default_tzinfo = default_tzinfo

    def deserialize(self, value, mapping, node, model):
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
    """ Represents a Boolean datatype in a schema.  This is evaluated as True, unless
        the value is equal to 'false' or '0'.  Like all other datatypes, an instance of
        this class can be passed into a :class:`soap.SchemaNode` to create a SchemaNode
        of type :class:`soap.Boolean` """

    def deserialize(self, value, mapping, node, model):
        try:
            result = str(value)
        except:
            raise Invalid('Boolean SchemaNode is not a string', node)
        result = result.lower()

        if result in ('false', '0'):
            return False

        return True


class Mapping(object):
    """ Represents a Mapping datatype, or a set of key/value pairs in other words.  This datatype
        is commonly known as dict() in Python or as an object in Javascript.  This datatype
        takes in a value, and loops through each key/value pair, deserializing each value and
        assigning the result to the respective key.

        This datatype is also unique in the fact that exceptions that are thrown at lower levels
        of deserialization, are packaged into a parent exception.  This allows us to represent
        exceptions in an identical structure as the value being deserialized. """

    def deserialize(self, value, mapping, node, model):
        validated = self.validate(value, mapping, node, model)

        exc = None
        deserialized = {}
        for child in node.children:
            try:
                value = validated.get(child.name, None)
                if not value is None:
                    deserialized[child.name] = child.deserialize(value, mapping=mapping, model=model)
                elif not child.missing is null:
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

    def validate(self, value, mapping, node, model):
        """ Ensures that the value being deserialized is actually a dict() variable.  Will fail if
            the value past in cannot be cast as a Python dict() """

        try:
            return dict(value)
        except Exception:
            raise Invalid('SchemaNode is not a mapping type.', node)


class Sequence(object):
    """ Reperesents a Sequence datatype.  This datatype is commonly known as a list() in Python, or
        an Array() in javascript.  This datatype takes in a Python list(), and loops through each
        element within it, and deserializes each child element, retaining the order of elements.

        This datatype is unique in the fact that exceptions that are thrown at lower levels of
        deserialization, are packaged into a parent exception.  This allows us to represent
        exceptions in an identical structure as the value being deserialized.  We also retain
        the index count in the sequence, so exceptions are logged specific to an index in the
        sequence. """

    def deserialize(self, value, mapping, node, model):
        validated = self.validate(value, mapping, node, model)
        child = node.children[0]

        exc = None
        deserialized = []
        for num, value in enumerate(validated):
            try:
                deserialized.append(child.deserialize(value, mapping=value, model=model))
            except Invalid as e:
                if exc is None:
                    exc = Invalid('Sequence Errors', node)
                exc.add(e, num)

        if exc is not None:
            raise exc

        return deserialized

    def validate(self, value, mapping, node, model):
        """ Ensures that we receive a list element during deserialization. """

        try:
            return list(value)
        except Exception:
            raise Invalid('SchemaNode is not an interable type.', node)


class Relationship(object):
    """  A datatype that represents a Relationship between two :class:`soap.SchemaModel`s.  This is
         used during the case where you want to have one :class:`soap.SchemaModel`s include a single instance
         or a list of instances of another :class:`soap.SchemaModel`s.  In order to have a :class:`SchemaNode`
         represent a list of instances of a :class:`soap.SchemaModel` called TestSchema, you would have
         a :class:`soap.SchemaNode` like so, attached to another one of your :class:`soap.SchemaModel`s:

         ... code-block:: python

             test_schema = SchemaNode(Relationship('TestSchema'))
    """
    name = ''

    def __init__(self, name, uselist=True):
        self.name = name
        self.uselist = uselist

    def deserialize(self, value, mapping, node, model):
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

        return schema_model.deserialize(value, mapping=value, model=model)


#
# Validators
#

class Length(object):
    def __init__(self, _min=None, _max=None):
        self.min = _min
        self.max = _max

    def __call__(self, value, mapping, node, model):
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

    def __call__(self, value, mapping, node, model):
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

    def __call__(self, value, mapping, node, model):
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
    """ The main object used to represent each element in a schema.  That element
        could be a Mapping, Sequence, String, Integer, it doesn't matter.  """

    name = ''
    _type = None
    children = None
    missing = null
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
        return self.missing is null

    def deserialize(self, value, mapping=None, node=None, model=None):
        """ Method for deserialization of a specific value of type ``_type``.  This method
            optionally excepts a ``mapping``, a ``node``, and a ``model``.

            The ``mapping`` is the original value passed into the :class:`soap.SchemaModel`.
            We keep track of the mapping so our validators can potentially see other values
            in the schema, to determine if a single :class:`SchemaNode` is correct, as sometimes
            values depend on one another.

            The ``node`` is the current node being deserialized, and is an instance of
            :class:`soap.SchemaNode`.  A node should almost never get passed into this function,
            as we want it to get defaulted to ``self``.  On rare occassions involving Relationships,
            we want to have a node pass through.  So in this case, we will pass a predetermined
            node that we want this :class:`soap.SchemaNode` to pretend to be.

            The ``model`` is the :class:`soap.SchemaModel` currently being processed.  We hold
            onto this, so that aribitrary attributes that were attached to it, can be used in
            the validators.  For example, in a number of cases, we need a database object to
            get passed into our validators.  We would pass our db session object into the
            constructor of a SchemaModel object, like so:

            .. code-block: python

               schema = TestSchema(db=db)

            Then within a validator, we can grab it off of the model object like so:

            .. code-block: python

               def validator(value, mapping, node, model):
                   db = model.db
        """

        node = node if node else self
        model = model if model else self
        mapping = mapping if mapping else value

        deserialized = self._type.deserialize(value, mapping, node, model)

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
                    validator(deserialized, mapping, node, model)
                except Invalid as e:
                    excs.append(e)
        elif self.validator:
            try:
                self.validator(deserialized, mapping, node, model)
            except Invalid as e:
                excs.append(e)

        # If we have any validation exceptions, then raise them as a single exception
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
    """ A superclass of :class:`SchemaNode` that is used to represent the top
        node in a schema.  This abstraction is necessary, so we know which SchemaNodes
        to store as 'models,' and which to simply treat as regular model 'fields' """

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
