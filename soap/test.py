from soap import (
    SchemaBase,
    relationship
)


class A(SchemaBase):
    b = relationship('B')


class B(SchemaBase):
    a = A


print A.b
