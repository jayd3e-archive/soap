from soap import (
    SchemaModel,
    SchemaNode,
    String,
    Int,
    Mapping,
    Relationship
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


ChildSchema = SchemaModel('ChildSchema',
                          Mapping(),
                          SchemaNode(Int(), name='id'),
                          SchemaNode(String(), name='name'),
                          SchemaNode(Relationship('TestSchema', uselist=False), name='parent_node', missing={}))


TestSchema = SchemaModel('TestSchema',
                         Mapping(),
                         SchemaNode(Int(), name='id'),
                         SchemaNode(String(), name='name'),
                         SchemaNode(Relationship('ChildSchema', uselist=False), name='sub_node', missing={}),
                         SchemaNode(Relationship('ChildSchema'), name='sub_seq_nodes', missing=[]))


payload = TestSchema.validate(json)
print payload

# {
#     'id': 0,
#     'name': 'blah',
#     'sub_seq_nodes': [{
#         'parent_node': {
#             'sub_seq_nodes': [],
#             'sub_node': {},
#             'id': 0,
#             'name': 'blah'
#         },
#         'id': 0,
#         'name': 'sub_seq_blah_0'
#     },
#     {
#         'parent_node': {},
#         'id': 1,
#         'name': 'sub_seq_blah_1'
#     }],
#     'sub_node': {
#         'parent_node': {},
#         'id': 0,
#         'name': 'sub_blah'
#     }
# }
