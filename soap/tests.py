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
    c = SchemaNode(Int())
    d = SchemaNode(Int())
    a = relationship('A', uselist=False)


a_deal = A()
output = a_deal.deserialize({'a': 'blah',
                             'b': [{
                                'c': 1,
                                'd': 1,
                                'a': {
                                    'a': 'asdf'
                                }
                             },
                             {
                                'c': 1,
                                'd': 2,
                                'a': {
                                    'a': 'haha'
                                }
                             }]})
print(output)
