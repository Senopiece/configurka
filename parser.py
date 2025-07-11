import json
import sys
from typing import NamedTuple, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput

# TODO: rewrite manually with better error reports + neat integrated typing to enhance error reports even more

grammar = r"""
    start: implicit_record
         | implicit_list
         | enum

    implicit_record: pair ("," pair)*         -> record
    implicit_list: entity ("," entity)+       -> list

    ?entity: STRING        -> string
           | SIGNED_NUMBER -> number
           | list
           | record
           | enum

    list  : "[" [entity ("," entity)*] "]"
    record : "{" [pair ("," pair)*] "}"
    pair   : CNAME ":" entity

    enum   : CNAME entity?     -> enum_with_data

    %import common.CNAME
    %import common.ESCAPED_STRING -> STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


class ParsedEnum(NamedTuple):
    name: str
    data: Union[None, str]


@v_args(inline=True)
class EntityTransformer(Transformer):
    def start(self, value):
        return value

    def string(self, s):
        return s[1:-1]  # Remove quotes

    def number(self, n):
        try:
            return int(n)
        except ValueError:
            return float(n)

    def list(self, *items):
        return list(items)

    def record(self, *pairs):
        return dict(pairs)

    def pair(self, key, val):
        return (str(key), val)

    def enum_with_data(self, name, data=None):
        return ParsedEnum(name=str(name), data=data if data is None else str(data))


parser = Lark(grammar, parser="lalr", transformer=EntityTransformer())

# --- Example Usage ---


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, "r", encoding="utf-8") as f:
            input_data = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    try:
        result = parser.parse(input_data)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except UnexpectedInput as e:
        print("Parsing failed!")
        print(f"Line {e.line}, Column {e.column}:")
        print(e.get_context(input_data))
        print(f"Error type: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    main()
