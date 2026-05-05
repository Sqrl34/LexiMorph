from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from leximorph.lexer import Token


class LexiMorphParseError(ValueError):
    def __init__(self, message: str, *, token: Token):
        super().__init__(f"{message} (line {token.line}, col {token.col})")
        self.token = token


@dataclass(frozen=True, slots=True)
class Node:
    line: int
    col: int


# --- Statements ---


@dataclass(frozen=True, slots=True)
class Module(Node):
    stmts: list[Stmt]


class Stmt(Node):
    pass


@dataclass(frozen=True, slots=True)
class Assign(Stmt):
    target: str
    value: Expr


@dataclass(frozen=True, slots=True)
class ExprStmt(Stmt):
    value: Expr


@dataclass(frozen=True, slots=True)
class If(Stmt):
    test: Expr
    body: list[Stmt]
    elifs: list[tuple[Expr, list[Stmt]]]
    orelse: list[Stmt]


@dataclass(frozen=True, slots=True)
class While(Stmt):
    test: Expr
    body: list[Stmt]


@dataclass(frozen=True, slots=True)
class For(Stmt):
    target: str
    iterable: Expr
    body: list[Stmt]


@dataclass(frozen=True, slots=True)
class FunctionDef(Stmt):
    name: str
    params: list[str]
    body: list[Stmt]


@dataclass(frozen=True, slots=True)
class Return(Stmt):
    value: Expr | None


@dataclass(frozen=True, slots=True)
class Pass(Stmt):
    pass


@dataclass(frozen=True, slots=True)
class Break(Stmt):
    pass


@dataclass(frozen=True, slots=True)
class Continue(Stmt):
    pass


# --- Expressions ---


class Expr(Node):
    pass


@dataclass(frozen=True, slots=True)
class Name(Expr):
    id: str


@dataclass(frozen=True, slots=True)
class Constant(Expr):
    value: object


@dataclass(frozen=True, slots=True)
class ListLit(Expr):
    elts: list[Expr]


@dataclass(frozen=True, slots=True)
class Subscript(Expr):
    value: Expr
    index: Expr


@dataclass(frozen=True, slots=True)
class Call(Expr):
    func: Expr
    args: list[Expr]


@dataclass(frozen=True, slots=True)
class UnaryOp(Expr):
    op: str
    operand: Expr


@dataclass(frozen=True, slots=True)
class BinOp(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass(frozen=True, slots=True)
class BoolOp(Expr):
    op: str  # 'and' / 'or'
    values: list[Expr]


@dataclass(frozen=True, slots=True)
class Compare(Expr):
    left: Expr
    ops: list[str]
    comparators: list[Expr]


def parse_tokens(tokens: Sequence[Token]) -> Module:
    return Parser(list(tokens)).parse_module()


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def cur(self) -> Token:
        if self.i >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.i]

    def at(self, kind: str, value: object | None = None) -> bool:
        t = self.cur()
        if t.kind != kind:
            return False
        if value is not None and t.value != value:
            return False
        return True

    def accept(self, kind: str, value: object | None = None) -> Token | None:
        if self.at(kind, value):
            t = self.cur()
            self.i += 1
            return t
        return None

    def expect(self, kind: str, value: object | None = None) -> Token:
        t = self.accept(kind, value)
        if t is None:
            got = self.cur()
            if value is None:
                raise LexiMorphParseError(f"Expected {kind}, got {got.kind}({got.value!r})", token=got)
            raise LexiMorphParseError(
                f"Expected {kind}({value!r}), got {got.kind}({got.value!r})",
                token=got,
            )
        return t

    def skip_newlines(self) -> None:
        while self.accept("NEWLINE") is not None:
            pass

    # --- module / statements ---

    def parse_module(self) -> Module:
        self.skip_newlines()
        start = self.cur()
        stmts: list[Stmt] = []
        while not self.at("EOF"):
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        self.expect("EOF")
        return Module(line=start.line, col=start.col, stmts=stmts)

    def parse_stmt(self) -> Stmt:
        t = self.cur()
        if self.at("KEYWORD", "if"):
            return self.parse_if()
        if self.at("KEYWORD", "while"):
            return self.parse_while()
        if self.at("KEYWORD", "for"):
            return self.parse_for()
        if self.at("KEYWORD", "def"):
            return self.parse_def()
        if self.at("KEYWORD", "return"):
            return self.parse_return()
        if self.at("KEYWORD", "pass"):
            self.i += 1
            self.expect("NEWLINE")
            return Pass(line=t.line, col=t.col)
        if self.at("KEYWORD", "break"):
            self.i += 1
            self.expect("NEWLINE")
            return Break(line=t.line, col=t.col)
        if self.at("KEYWORD", "continue"):
            self.i += 1
            self.expect("NEWLINE")
            return Continue(line=t.line, col=t.col)

        # assignment vs expression statement
        if self.at("NAME"):
            if self.i + 1 < len(self.tokens) and self.tokens[self.i + 1].kind == "OP" and self.tokens[self.i + 1].value == "=":
                name_tok = self.expect("NAME")
                self.expect("OP", "=")
                value = self.parse_expr()
                self.expect("NEWLINE")
                return Assign(line=name_tok.line, col=name_tok.col, target=str(name_tok.value), value=value)

        expr = self.parse_expr()
        self.expect("NEWLINE")
        return ExprStmt(line=expr.line, col=expr.col, value=expr)

    def parse_suite(self) -> list[Stmt]:
        self.expect("NEWLINE")
        self.expect("INDENT")
        stmts: list[Stmt] = []
        self.skip_newlines()
        while not self.at("DEDENT"):
            if self.at("EOF"):
                raise LexiMorphParseError("Unterminated block (expected DEDENT)", token=self.cur())
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        self.expect("DEDENT")
        return stmts

    def parse_if(self) -> If:
        if_tok = self.expect("KEYWORD", "if")
        test = self.parse_expr()
        self.expect("OP", ":")
        body = self.parse_suite()

        elifs: list[tuple[Expr, list[Stmt]]] = []
        while self.accept("KEYWORD", "elif") is not None:
            etest = self.parse_expr()
            self.expect("OP", ":")
            ebody = self.parse_suite()
            elifs.append((etest, ebody))

        orelse: list[Stmt] = []
        if self.accept("KEYWORD", "else") is not None:
            self.expect("OP", ":")
            orelse = self.parse_suite()

        return If(
            line=if_tok.line,
            col=if_tok.col,
            test=test,
            body=body,
            elifs=elifs,
            orelse=orelse,
        )

    def parse_while(self) -> While:
        w_tok = self.expect("KEYWORD", "while")
        test = self.parse_expr()
        self.expect("OP", ":")
        body = self.parse_suite()
        return While(line=w_tok.line, col=w_tok.col, test=test, body=body)

    def parse_for(self) -> For:
        f_tok = self.expect("KEYWORD", "for")
        target_tok = self.expect("NAME")
        self.expect("KEYWORD", "in")
        iterable = self.parse_expr()
        self.expect("OP", ":")
        body = self.parse_suite()
        return For(
            line=f_tok.line,
            col=f_tok.col,
            target=str(target_tok.value),
            iterable=iterable,
            body=body,
        )

    def parse_def(self) -> FunctionDef:
        d_tok = self.expect("KEYWORD", "def")
        name_tok = self.expect("NAME")
        self.expect("OP", "(")
        params: list[str] = []
        if not self.at("OP", ")"):
            p0 = self.expect("NAME")
            params.append(str(p0.value))
            while self.accept("OP", ",") is not None:
                p = self.expect("NAME")
                params.append(str(p.value))
        self.expect("OP", ")")
        self.expect("OP", ":")
        body = self.parse_suite()
        return FunctionDef(
            line=d_tok.line,
            col=d_tok.col,
            name=str(name_tok.value),
            params=params,
            body=body,
        )

    def parse_return(self) -> Return:
        r_tok = self.expect("KEYWORD", "return")
        if self.at("NEWLINE"):
            self.expect("NEWLINE")
            return Return(line=r_tok.line, col=r_tok.col, value=None)
        value = self.parse_expr()
        self.expect("NEWLINE")
        return Return(line=r_tok.line, col=r_tok.col, value=value)

    # --- expressions ---

    def parse_expr(self) -> Expr:
        return self.parse_or()

    def parse_or(self) -> Expr:
        left = self.parse_and()
        if self.accept("KEYWORD", "or") is None:
            return left
        values = [left, self.parse_and()]
        while self.accept("KEYWORD", "or") is not None:
            values.append(self.parse_and())
        return BoolOp(line=left.line, col=left.col, op="or", values=values)

    def parse_and(self) -> Expr:
        left = self.parse_not()
        if self.accept("KEYWORD", "and") is None:
            return left
        values = [left, self.parse_not()]
        while self.accept("KEYWORD", "and") is not None:
            values.append(self.parse_not())
        return BoolOp(line=left.line, col=left.col, op="and", values=values)

    def parse_not(self) -> Expr:
        if self.at("KEYWORD", "not"):
            t = self.expect("KEYWORD", "not")
            operand = self.parse_not()
            return UnaryOp(line=t.line, col=t.col, op="not", operand=operand)
        return self.parse_compare()

    def parse_compare(self) -> Expr:
        left = self.parse_arith()
        ops: list[str] = []
        comps: list[Expr] = []
        while self.at("OP") and self.cur().value in ("<", "<=", ">", ">=", "==", "!="):
            op_tok = self.expect("OP")
            ops.append(str(op_tok.value))
            comps.append(self.parse_arith())
        if not ops:
            return left
        return Compare(line=left.line, col=left.col, left=left, ops=ops, comparators=comps)

    def parse_arith(self) -> Expr:
        left = self.parse_term()
        while self.at("OP") and self.cur().value in ("+", "-"):
            op_tok = self.expect("OP")
            right = self.parse_term()
            left = BinOp(line=left.line, col=left.col, left=left, op=str(op_tok.value), right=right)
        return left

    def parse_term(self) -> Expr:
        left = self.parse_power()
        while self.at("OP") and self.cur().value in ("*", "/", "//", "%"):
            op_tok = self.expect("OP")
            right = self.parse_power()
            left = BinOp(line=left.line, col=left.col, left=left, op=str(op_tok.value), right=right)
        return left

    def parse_power(self) -> Expr:
        left = self.parse_unary()
        if self.at("OP", "**"):
            op_tok = self.expect("OP", "**")
            right = self.parse_power()  # right-associative
            return BinOp(line=left.line, col=left.col, left=left, op=str(op_tok.value), right=right)
        return left

    def parse_unary(self) -> Expr:
        if self.at("OP", "-"):
            t = self.expect("OP", "-")
            operand = self.parse_unary()
            return UnaryOp(line=t.line, col=t.col, op="-", operand=operand)
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        t = self.cur()

        if self.at("NUMBER"):
            tok = self.expect("NUMBER")
            expr: Expr = Constant(line=tok.line, col=tok.col, value=tok.value)
            return self.parse_postfix(expr)

        if self.at("STRING"):
            tok = self.expect("STRING")
            expr = Constant(line=tok.line, col=tok.col, value=str(tok.value))
            return self.parse_postfix(expr)

        if self.at("KEYWORD") and self.cur().value in ("True", "False", "None"):
            tok = self.expect("KEYWORD")
            val = True if tok.value == "True" else False if tok.value == "False" else None
            expr = Constant(line=tok.line, col=tok.col, value=val)
            return self.parse_postfix(expr)

        if self.at("NAME"):
            tok = self.expect("NAME")
            expr = Name(line=tok.line, col=tok.col, id=str(tok.value))
            return self.parse_postfix(expr)

        if self.at("OP", "("):
            self.expect("OP", "(")
            expr = self.parse_expr()
            self.expect("OP", ")")
            return self.parse_postfix(expr)

        if self.at("OP", "["):
            lbr = self.expect("OP", "[")
            elts: list[Expr] = []
            if not self.at("OP", "]"):
                elts.append(self.parse_expr())
                while self.accept("OP", ",") is not None:
                    if self.at("OP", "]"):
                        break
                    elts.append(self.parse_expr())
            self.expect("OP", "]")
            expr = ListLit(line=lbr.line, col=lbr.col, elts=elts)
            return self.parse_postfix(expr)

        raise LexiMorphParseError(f"Unexpected token {t.kind}({t.value!r}) in expression", token=t)

    def parse_postfix(self, expr: Expr) -> Expr:
        while True:
            if self.at("OP", "("):
                lpar = self.expect("OP", "(")
                args: list[Expr] = []
                if not self.at("OP", ")"):
                    args.append(self.parse_expr())
                    while self.accept("OP", ",") is not None:
                        if self.at("OP", ")"):
                            break
                        args.append(self.parse_expr())
                self.expect("OP", ")")
                expr = Call(line=expr.line, col=expr.col, func=expr, args=args)
                continue

            if self.at("OP", "["):
                lb = self.expect("OP", "[")
                idx = self.parse_expr()
                self.expect("OP", "]")
                expr = Subscript(line=expr.line, col=expr.col, value=expr, index=idx)
                continue

            break
        return expr

