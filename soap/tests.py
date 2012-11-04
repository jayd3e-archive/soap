from soap import (
    Relationship,
    String,
    Int,
    SchemaNode,
    SchemaModel
)


class A(SchemaModel):
    a = SchemaNode(String())
    b = SchemaNode(Relationship('B'), missing=[])


class B(SchemaModel):
    c = SchemaNode(Int())
    d = SchemaNode(Int())
    a = SchemaNode(Relationship('A', uselist=False))


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
