from soap import (
    relationship,
    String,
    Int,
    SchemaNode,
    MappingSchema
)


class A(MappingSchema):
    a = SchemaNode(String())
    b = relationship('B')


class B(MappingSchema):
    c = relationship('A')
    d = SchemaNode(Int())

a_deal = A()
output = a_deal.deserialize({'a': 'blah', 'b': [{'c': {'a': 'blah', 'b': []}, 'd': 1}, {'c': {'a': 'bleep', 'b': []}, 'd': 2}]})
print(output)
