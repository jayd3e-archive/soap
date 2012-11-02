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
                          SchemaNode(String(), name='name'))


TestSchema = SchemaModel('TestSchema',
                         Mapping(),
                         SchemaNode(Int(), name='id'),
                         SchemaNode(String(), name='name'),
                         SchemaNode(Relationship('ChildSchema', uselist=False), name='sub_node'),  # SchemaNode(Mapping(), name='subnode')
                         SchemaNode(Relationship('ChildSchema'), name='sub_seq_nodes'))


payload = TestSchema.validate(json)
print(payload)
