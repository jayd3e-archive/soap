from soap import (
    SchemaNode,
    String,
    Int,
    Mapping,
    Sequence
)


json = {
    'id': 0,
    'name': 'blah',
    'sub_node': {
        'id': 0,
        'sub_name': 'sub_blah',
        'del_key': 'this key should get removed'
    },
    'sub_seq_nodes': [{
        'id': 0,
        'name': 'sub_seq_blah_0',
        'del_key': 'this key should be removed'
    },
    {
        'id': 1,
        'name': 'sub_seq_blah_1'
    }]
}


ChildSchema = SchemaNode(Mapping(),
                         SchemaNode(Int(), name='id'),
                         SchemaNode(String(), name='name'))


TestSchema = SchemaNode(Mapping(),
                        SchemaNode(Int(), name='id'),
                        SchemaNode(String(), name='name'),
                        SchemaNode(Mapping(),
                                   SchemaNode(Int(), name='id'),
                                   SchemaNode(String(), name='sub_name'),
                                   name='sub_node'),
                        SchemaNode(Sequence(),
                                   ChildSchema,
                                   name='sub_seq_nodes'))


payload = TestSchema.validate(json)
print(payload)
