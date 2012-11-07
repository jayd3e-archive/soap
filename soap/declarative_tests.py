from soap import (
    Relationship,
    String,
    Int,
    SchemaNode,
    SchemaModel,
    Invalid
)

json = {
    'id': 0,
    'name': 'blah',
    'sub_node': {
        'id': 0,
        'name': {},
        'del_key': 'this key should get removed'
    },
    'sub_seq_nodes': [{
        'id': 0,
        'name': 'eaaa',
        'parent_node': {
            'id': 0,
            'name': 'dlah'
        },
        'del_key': 'this key should be removed'
    },
    {
        'id': 1,
        'name': 'sub_seq_blah_1'
    }]
}


def test_validator0(value, node, model):
    if not value.startswith('b'):
        raise Invalid('This is an error.', node, model)


def test_validator1(value, node, model):
    if value != 'blah':
        raise Invalid('This is an error too.', node, model)


class ChildSchema(SchemaModel):
    id = SchemaNode(Int())
    name = SchemaNode(String(),
                      validator=test_validator0)
    parent_node = SchemaNode(Relationship('TestSchema', uselist=False), missing={})


class TestSchema(SchemaModel):
    id = SchemaNode(Int())
    name = SchemaNode(String(),
                      validator=[test_validator0, test_validator1])
    sub_node = SchemaNode(Relationship('ChildSchema', uselist=False), missing={})
    sub_seq_nodes = SchemaNode(Relationship('ChildSchema'), missing=[])


schema = TestSchema()
try:
    output = schema.deserialize(json)
    assert output == {
        'id': 0,
        'sub_seq_nodes': [{
            'parent_node': {
                'id': 0,
                'sub_seq_nodes': [],
                'name': 'blah',
                'sub_node': {}
            },
            'id': 0,
            'name': 'sub_seq_blah_0'
        }, {
            'parent_node': {},
            'id': 1,
            'name': 'sub_seq_blah_1'
        }],
        'name': 'blah',
        'sub_node': {
            'parent_node': {},
            'id': 0,
            'name': 'sub_blah'
        }
    }
except Invalid as e:
    print(e.asdict())
    # {'sub_seq_nodes': {'1': {'name': ['This is an error.']}, 'sub_seq_nodes': {'parent_node': {'name': ['This is an error.', 'This is an error too.']}, 'name': ['This is an error.']}}, 'sub_node': {'name': ['name is required.']}}
