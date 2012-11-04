from soap import (
    Relationship,
    String,
    Int,
    SchemaNode,
    SchemaModel
)

json = {
    'id': 0,
    'name': 'blah',
    'sub_node': {
        'id': 0,
        'name': 'sub_blah',
        'del_key': 'this key should get removed'
    },
    'sub_seq_nodes': [{
        'id': 0,
        'name': 'sub_seq_blah_0',
        'parent_node': {
            'id': 0,
            'name': 'blah'
        },
        'del_key': 'this key should be removed'
    },
    {
        'id': 1,
        'name': 'sub_seq_blah_1'
    }]
}


class ChildSchema(SchemaModel):
    id = SchemaNode(Int())
    name = SchemaNode(String())
    parent_node = SchemaNode(Relationship('TestSchema', uselist=False), missing={})


class TestSchema(SchemaModel):
    id = SchemaNode(Int())
    name = SchemaNode(String())
    sub_node = SchemaNode(Relationship('ChildSchema', uselist=False), missing={})
    sub_seq_nodes = SchemaNode(Relationship('ChildSchema'), missing=[])


schema = TestSchema()
output = schema.deserialize(json)
print(output)
