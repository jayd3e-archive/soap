import unittest
from datetime import datetime
from soap import (
    Relationship,
    String,
    Int,
    Boolean,
    DateTime,
    Mapping,
    Sequence,
    SchemaNode,
    SchemaModel,
    Invalid,
    iso8601
)

date_str = '2007-01-25T12:00:00Z'
date = datetime(2007, 1, 25, 12, 0, tzinfo=iso8601.Utc())


class TestFunctionalDeclarative(unittest.TestCase):
    def setUp(self):
        from soap import SchemaModelMeta
        from soap import SchemaModel
        SchemaModelMeta._models = {}
        SchemaModel._models = {}

    def test_scenario_no_relationships(self):
        class SchemaOne(SchemaModel):
            id = SchemaNode(Int())
            name = SchemaNode(String())
            booly = SchemaNode(Boolean())
            datey = SchemaNode(DateTime())

        class SchemaTwo(SchemaModel):
            id = SchemaNode(Int())
            name = SchemaNode(String())
            mapping = SchemaNode(Mapping(),
                                 SchemaNode(String(), name='sub_name'),
                                 SchemaNode(Int(), name='sub_id'))
            sequence = SchemaNode(Sequence(),
                                  SchemaNode(String(), name='seq'))

        json = {
            'id': '0',
            'name': 'schema_one',
            'booly': 'false',
            'datey': date_str,
            'del_key': 'this key needs to get deleted'
        }
        schema = SchemaOne()
        payload = schema.deserialize(json)
        self.assertEqual(payload, {
            'id': 0,
            'name': 'schema_one',
            'booly': False,
            'datey': date
        })

        json = {
            'id': '0',
            'name': 'schema_two',
            'mapping': {
                'sub_name': 'schema_two_sub_node',
                'sub_id': '0',
                'del_key': 'this key should be deleted'
            },
            'sequence': ['tag0', 'tag1', 2, 'tag3']
        }
        schema = SchemaTwo()
        payload = schema.deserialize(json)
        self.assertEqual(payload, {
            'id': 0,
            'name': 'schema_two',
            'mapping': {
                'sub_name': 'schema_two_sub_node',
                'sub_id': 0
            },
            'sequence': ['tag0', 'tag1', '2', 'tag3']
        })

    def test_scenario_relationships(self):
        class ChildSchema(SchemaModel):
            id = SchemaNode(Int())
            name = SchemaNode(String())
            parent_node = SchemaNode(Relationship('TestSchema', uselist=False), missing={})

        class TestSchema(SchemaModel):
            id = SchemaNode(Int())
            name = SchemaNode(String())
            booly = SchemaNode(Boolean())
            datey = SchemaNode(DateTime())
            sub_node = SchemaNode(Relationship('ChildSchema', uselist=False), missing={})
            sub_seq_nodes = SchemaNode(Relationship('ChildSchema'), missing=[])

        json = {
            'id': 0,
            'name': 'blah',
            'booly': 'true',
            'datey': date_str,
            'sub_node': {
                'id': 0,
                'name': 'sub_blah',
                'del_key': 'this key should get removed'
            },
            'sub_seq_nodes': [{
                'id': '0',
                'name': 'sub_seq_blah_0',
                'parent_node': {
                    'id': 0,
                    'name': 'blah',
                    'booly': 'false',
                    'datey': date_str
                },
                'del_key': 'this key should be removed'
            },
            {
                'id': 1,
                'name': 'sub_seq_blah_1'
            }]
        }

        schema = TestSchema()
        payload = schema.deserialize(json)
        self.assertEqual(payload, {
            'id': 0,
            'name': 'blah',
            'booly': True,
            'datey': date,
            'sub_node': {
                'id': 0,
                'name': 'sub_blah',
                'parent_node': {}
            },
            'sub_seq_nodes': [{
                'id': 0,
                'name': 'sub_seq_blah_0',
                'parent_node': {
                    'id': 0,
                    'name': 'blah',
                    'booly': False,
                    'datey': date,
                    'sub_seq_nodes': [],
                    'sub_node': {}
                }
            }, {
                'parent_node': {},
                'id': 1,
                'name': 'sub_seq_blah_1'
            }]
        })

    def test_scenario_relationships_and_validators(self):
        def test_validator0(value, payload, node, model):
            if not value.startswith('b'):
                raise Invalid('This is an error.', node)

        def test_validator1(value, payload, node, model):
            if value != 'blah':
                raise Invalid('This is an error too.', node)

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

        schema = TestSchema()
        try:
            payload = schema.deserialize(json)
        except Invalid as e:
            self.assertEqual(e.asdict(), {
                'sub_seq_nodes': {
                    '1': {
                        'name': ['This is an error.']
                    },
                    '0': {
                        'name': ['This is an error.'],
                        'parent_node': {
                            'name': ['This is an error.', 'This is an error too.']
                        }
                    }
                },
                'sub_node': {
                    'name': ['This is an error.']
                }
            })

        json = {
            'id': 0,
            'name': 'blah',
            'sub_node': {
                'id': 0,
                'name': 'blah',
                'del_key': 'this key should get removed'
            },
            'sub_seq_nodes': [{
                'id': 0,
                'name': 'blah',
                'parent_node': {
                    'id': 0,
                    'name': 'blah'
                },
                'del_key': 'this key should be removed'
            },
            {
                'id': 1,
                'name': 'blah'
            }]
        }

        schema = TestSchema()
        payload = schema.deserialize(json)
        self.assertEqual(payload, {
            'id': 0,
            'name': 'blah',
            'sub_seq_nodes': [{
                'id': 0,
                'name': 'blah',
                'parent_node': {
                    'id': 0,
                    'sub_seq_nodes': [],
                    'name': 'blah',
                    'sub_node': {}
                }
            }, {
                'id': 1,
                'name': 'blah',
                'parent_node': {}
            }],
            'sub_node': {
                'id': 0,
                'name': 'blah',
                'parent_node': {}
            }
        })


class TestFunctionalImperative(unittest.TestCase):

    def test_scenario_relationships(self):
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

        SchemaModel('ChildSchema',
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
        self.assertEqual(payload, {
            'id': 0,
            'name': 'blah',
            'sub_seq_nodes': [{
                'parent_node': {
                    'sub_seq_nodes': [],
                    'sub_node': {},
                    'id': 0,
                    'name': 'blah'
                },
                'id': 0,
                'name': 'sub_seq_blah_0'
            },
            {
                'parent_node': {},
                'id': 1,
                'name': 'sub_seq_blah_1'
            }],
            'sub_node': {
                'parent_node': {},
                'id': 0,
                'name': 'sub_blah'
            }
        })
