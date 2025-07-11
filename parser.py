from typing import Any, NamedTuple
from lark import Lark, Transformer, v_args

grammar = r"""
    start: entity

    ?entity: STRING        -> string
           | SIGNED_NUMBER -> number
           | object
           | enum

    object : "{" [object_item ("," object_item)*] "}"
    ?object_item: entity                    -> unnamed_field
                | CNAME ":" entity          -> named_field

    enum   : CNAME entity?     -> enum_with_data

    %import common.CNAME
    %import common.ESCAPED_STRING -> STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


class EnumInstance(NamedTuple):
    name: str
    data: None | Any


class ObjectInstance(NamedTuple):
    unnamed: tuple
    named: dict


@v_args(inline=True)
class EntityTransformer(Transformer):
    def string(self, s):
        return s[1:-1]  # remove quotes

    def number(self, n):
        return float(n) if "." in n else int(n)

    def unnamed_field(self, val):
        return (None, val)

    def named_field(self, key, val):
        return (str(key), val)

    def object(self, *items):
        unnamed = []
        named = {}
        for k, v in items:
            if k is None:
                unnamed.append(v)
            else:
                named[k] = v
        return ObjectInstance(unnamed=tuple(unnamed), named=named)

    def enum_with_data(self, name, data=None):
        return EnumInstance(name=str(name), data=data)


parser = Lark(grammar, parser="lalr", transformer=EntityTransformer())

# Example usage
example = """
{
  redis: {
    host: "localhost",
    port: 6379
  },

  cameras: {
    {
      sn: "GFX712",
      focus: manual 100
    },
    {
      sn: "GFX114",
      focus: manual 100
    }
  },

  fps: 30
}
"""

result = parser.parse(example)
print(result)
