from dataclasses import dataclass
from typing import List, Tuple, Union
from lark import Lark, Transformer, Token, v_args

# TODO: try to parse with lalrl
# TODO: uint, int

grammar = r"""    
    start: record_items

    discriminator: CNAME (filler1 entity)?

    list_closure: "[" list_items "]"
    list_items: [filler list_content] filler ["," filler]
    list_content: entity list_element*
    list_element: filler "," filler entity

    record_closure: "{" record_items "}"
    record_items: [filler record_content] filler ["," filler]
    record_content: kv record_element*
    record_element: filler "," filler kv
    kv: CNAME filler ":" filler entity

    SPACING: /[ \t\r\n]+/
    ML_COMMENT: "/*" /(.|\n)*?/ "*/"
    SL_COMMENT: "//" /[^\n]*/
    filler: (SPACING | ML_COMMENT | SL_COMMENT)*
    filler1: (SPACING | ML_COMMENT | SL_COMMENT)+

    ?entity: ESCAPED_STRING
           | SIGNED_NUMBER
           | record_closure
           | list_closure
           | discriminator

    %import common.CNAME
    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
"""

# --- AST dataclasses ---


@dataclass
class Spacing:
    text: str

    def restore(self) -> str:
        return self.text


@dataclass
class Comment:
    text: str

    def restore(self) -> str:
        raise NotImplementedError("Use subclass restore method")


@dataclass
class SinglelineComment(Comment):
    def restore(self) -> str:
        return "//" + self.text


@dataclass
class MultilineComment(Comment):
    def restore(self) -> str:
        return "/*" + self.text + "*/"


@dataclass
class Filler:
    data: List[Union[Spacing, Comment]]

    def restore(self) -> str:
        return "".join(e.restore() for e in self.data)


@dataclass
class StringEntity:
    raw: str

    def restore(self) -> str:
        return '"' + self.raw + '"'


@dataclass
class NumberEntity:
    raw: str

    def restore(self) -> str:
        return self.raw


@dataclass
class DiscriminatorEntity:
    name: str
    data: Tuple[Filler, "Entity"] | None

    def restore(self) -> str:
        if self.data is None:
            return self.name
        else:
            filler, ent = self.data
            return self.name + filler.restore() + ent.restore()


@dataclass
class ListElement:
    precomma_filler: Filler
    postcomma_filler: Filler
    entity: "Entity"

    def restore(self) -> str:
        return (
            self.precomma_filler.restore()
            + ","
            + self.postcomma_filler.restore()
            + self.entity.restore()
        )


@dataclass
class ListContent:
    first_element: "Entity"
    rest_elements: List[ListElement]

    def restore(self) -> str:
        return self.first_element.restore() + "".join(
            e.restore() for e in self.rest_elements
        )


@dataclass
class ListItems:
    content: Tuple[Filler, ListContent] | None
    filler: Filler
    after_trailing: Filler | None

    def restore(self) -> str:
        return (
            (
                self.content[0].restore() + self.content[1].restore()
                if self.content
                else ""
            )
            + self.filler.restore()
            + ("," + self.after_trailing.restore() if self.after_trailing else "")
        )


@dataclass
class ListClosure:
    items: ListItems

    def restore(self) -> str:
        return "[" + self.items.restore() + "]"


@dataclass
class KVPair:
    key: str
    precolumn_filler: Filler
    postcolumn_filler: Filler
    data: "Entity"

    def restore(self) -> str:
        return (
            self.key
            + self.precolumn_filler.restore()
            + ":"
            + self.postcolumn_filler.restore()
            + self.data.restore()
        )


@dataclass
class RecordElement:
    precomma_filler: Filler
    postcomma_filler: Filler
    kv_pair: KVPair

    def restore(self) -> str:
        return (
            self.precomma_filler.restore()
            + ","
            + self.postcomma_filler.restore()
            + self.kv_pair.restore()
        )


@dataclass
class RecordContent:
    first_pair: KVPair
    rest_pairs: List[RecordElement]

    def restore(self) -> str:
        return self.first_pair.restore() + "".join(e.restore() for e in self.rest_pairs)


@dataclass
class RecordItems:
    content: Tuple[Filler, RecordContent] | None
    filler: Filler
    after_trailing: Filler | None

    def restore(self) -> str:
        return (
            (
                self.content[0].restore() + self.content[1].restore()
                if self.content
                else ""
            )
            + self.filler.restore()
            + ("," + self.after_trailing.restore() if self.after_trailing else "")
        )


@dataclass
class RecordClosure:
    items: RecordItems

    def restore(self) -> str:
        return "{" + self.items.restore() + "}"


Entity = Union[
    StringEntity,
    NumberEntity,
    DiscriminatorEntity,
    ListClosure,
    RecordClosure,
]

RootEntity = Union[
    StringEntity,
    NumberEntity,
    DiscriminatorEntity,
    ListClosure,
    RecordContent,
]


class ConfigurikTransformer(Transformer):
    @v_args(inline=True)
    def start(self, record_items):
        return record_items

    def discriminator(self, args):
        name = args[0]
        if len(args) == 1:
            return DiscriminatorEntity(name=name, data=None)
        else:
            return DiscriminatorEntity(name=name, data=(args[1], args[2]))

    def list_closure(self, args):
        return ListClosure(*args)

    def list_items(self, args):
        return ListItems(
            content=(args[0], args[1]) if args[1] is not None else None,
            filler=args[2],
            after_trailing=args[3],
        )

    def list_content(self, args):
        return ListContent(args[0], args[1:])

    def list_element(self, args):
        return ListElement(*args)

    def record_closure(self, args):
        return RecordClosure(*args)

    def record_items(self, args):
        return RecordItems(
            content=(args[0], args[1]) if args[1] is not None else None,
            filler=args[2],
            after_trailing=args[3],
        )

    def record_content(self, args):
        return RecordContent(args[0], args[1:])

    def record_element(self, args):
        return RecordElement(*args)

    def kv(self, args):
        return KVPair(*args)

    def SPACING(self, tok: Token):
        return Spacing(tok.value)

    def ML_COMMENT(self, tok: Token):
        return MultilineComment(tok.value[2:-2])

    def SL_COMMENT(self, tok: Token):
        return SinglelineComment(tok.value[2:])

    def filler(self, args):
        return Filler(args)

    def filler1(self, args):
        return Filler(args)

    def CNAME(self, tok: Token):
        return tok.value

    def ESCAPED_STRING(self, tok: Token):
        return StringEntity(tok.value[1:-1])

    def SIGNED_NUMBER(self, tok: Token):
        return NumberEntity(tok.value)


parser = Lark(grammar, parser="earley")

transformer = ConfigurikTransformer()


def parse_configurik(text: str):
    tree = parser.parse(text)
    return transformer.transform(tree)
