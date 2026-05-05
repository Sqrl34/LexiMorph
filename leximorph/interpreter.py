from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from leximorph.lexer import LexiMorphLexError, tokenize
from leximorph.parser import (
    Assign,
    BinOp,
    BoolOp,
    Break,
    Call,
    Compare,
    Constant,
    Continue,
    Expr,
    ExprStmt,
    For,
    FunctionDef,
    If,
    LexiMorphParseError,
    ListLit,
    Module,
    Name,
    Node,
    Pass,
    Return,
    Stmt,
    Subscript,
    UnaryOp,
    While,
    parse_tokens,
)


class LexiMorphRuntimeError(RuntimeError):
    def __init__(self, message: str, *, node: Node | None = None, line: int | None = None, col: int | None = None):
        if node is not None:
            line = node.line
            col = node.col
        self.line = int(line or 0)
        self.col = int(col or 0)
        loc = ""
        if self.line:
            loc = f" (line {self.line}, col {self.col or 1})"
        super().__init__(f"{message}{loc}")


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


@dataclass
class ReturnSignal(Exception):
    value: object


class Environment:
    def __init__(self, parent: Environment | None = None):
        self.parent = parent
        self.values: dict[str, object] = {}

    def get(self, name: str, *, node: Node) -> object:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name, node=node)
        raise LexiMorphRuntimeError(f"Name {name!r} is not defined", node=node)

    def set(self, name: str, value: object) -> None:
        self.values[name] = value


class Function:
    def __init__(self, name: str, params: list[str], body: list[Stmt], defining_env: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.defining_env = defining_env

    def __call__(self, *args: object) -> object:
        call_env = Environment(parent=self.defining_env)
        if len(args) != len(self.params):
            raise TypeError(f"{self.name}() takes {len(self.params)} positional arguments but {len(args)} were given")
        for p, a in zip(self.params, args):
            call_env.set(p, a)
        try:
            for s in self.body:
                exec_stmt(s, call_env)
        except ReturnSignal as r:
            return r.value
        return None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<function {self.name}({', '.join(self.params)})>"


def _truthy(v: object) -> bool:
    return bool(v)


def _make_builtins(*, stdin, stdout) -> dict[str, object]:
    def b_print(*args: object) -> None:
        text = " ".join(str(a) for a in args)
        stdout.write(text + "\n")

    def b_input(prompt: object = "") -> str:
        if prompt:
            stdout.write(str(prompt))
            stdout.flush()
        line = stdin.readline()
        if line.endswith("\n"):
            line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
        return line

    def b_range(*args: object) -> range:
        try:
            return range(*[int(a) for a in args])
        except TypeError as e:
            raise TypeError("range() expects 1 to 3 integer args") from e

    def b_enumerate(it: Iterable[object]) -> Iterable[tuple[int, object]]:
        return enumerate(it)

    def b_list(x: object = ()) -> list[object]:
        return list(x)  # type: ignore[arg-type]

    allowed: dict[str, object] = {
        "print": b_print,
        "range": b_range,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "input": b_input,
        "enumerate": b_enumerate,
        "list": b_list,
    }
    return allowed


def exec_module(mod: Module, env: Environment) -> None:
    for s in mod.stmts:
        exec_stmt(s, env)


def exec_stmt(stmt: Stmt, env: Environment) -> None:
    try:
        if isinstance(stmt, Assign):
            env.set(stmt.target, eval_expr(stmt.value, env))
            return
        if isinstance(stmt, ExprStmt):
            eval_expr(stmt.value, env)
            return
        if isinstance(stmt, Pass):
            return
        if isinstance(stmt, Break):
            raise BreakSignal()
        if isinstance(stmt, Continue):
            raise ContinueSignal()
        if isinstance(stmt, Return):
            val = None if stmt.value is None else eval_expr(stmt.value, env)
            raise ReturnSignal(val)
        if isinstance(stmt, If):
            if _truthy(eval_expr(stmt.test, env)):
                for s in stmt.body:
                    exec_stmt(s, env)
                return
            for etest, ebody in stmt.elifs:
                if _truthy(eval_expr(etest, env)):
                    for s in ebody:
                        exec_stmt(s, env)
                    return
            for s in stmt.orelse:
                exec_stmt(s, env)
            return
        if isinstance(stmt, While):
            while _truthy(eval_expr(stmt.test, env)):
                try:
                    for s in stmt.body:
                        exec_stmt(s, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return
        if isinstance(stmt, For):
            it = eval_expr(stmt.iterable, env)
            try:
                iterator = iter(it)  # type: ignore[arg-type]
            except TypeError as e:
                raise LexiMorphRuntimeError("Object is not iterable", node=stmt) from e
            for v in iterator:
                env.set(stmt.target, v)
                try:
                    for s in stmt.body:
                        exec_stmt(s, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return
        if isinstance(stmt, FunctionDef):
            env.set(stmt.name, Function(stmt.name, stmt.params, stmt.body, env))
            return

        raise LexiMorphRuntimeError(f"Unsupported statement: {type(stmt).__name__}", node=stmt)
    except LexiMorphRuntimeError:
        raise
    except (BreakSignal, ContinueSignal, ReturnSignal):
        raise
    except Exception as e:
        raise LexiMorphRuntimeError(str(e), node=stmt) from e


def eval_expr(expr: Expr, env: Environment) -> object:
    try:
        if isinstance(expr, Constant):
            return expr.value
        if isinstance(expr, Name):
            return env.get(expr.id, node=expr)
        if isinstance(expr, ListLit):
            return [eval_expr(e, env) for e in expr.elts]
        if isinstance(expr, Subscript):
            v = eval_expr(expr.value, env)
            idx = eval_expr(expr.index, env)
            try:
                return v[idx]  # type: ignore[index]
            except Exception as e:
                raise LexiMorphRuntimeError("Invalid subscript operation", node=expr) from e
        if isinstance(expr, Call):
            fn = eval_expr(expr.func, env)
            args = [eval_expr(a, env) for a in expr.args]
            if isinstance(fn, Function):
                return fn(*args)
            if callable(fn):
                # Restrict to positional args only (no **kwargs support).
                return fn(*args)  # type: ignore[misc]
            raise LexiMorphRuntimeError("Object is not callable", node=expr)
        if isinstance(expr, UnaryOp):
            v = eval_expr(expr.operand, env)
            if expr.op == "-":
                return -v  # type: ignore[operator]
            if expr.op == "not":
                return not _truthy(v)
            raise LexiMorphRuntimeError(f"Unsupported unary operator {expr.op!r}", node=expr)
        if isinstance(expr, BinOp):
            l = eval_expr(expr.left, env)
            r = eval_expr(expr.right, env)
            op = expr.op
            if op == "+":
                return l + r  # type: ignore[operator]
            if op == "-":
                return l - r  # type: ignore[operator]
            if op == "*":
                return l * r  # type: ignore[operator]
            if op == "/":
                return l / r  # type: ignore[operator]
            if op == "//":
                return l // r  # type: ignore[operator]
            if op == "%":
                return l % r  # type: ignore[operator]
            if op == "**":
                return l**r  # type: ignore[operator]
            raise LexiMorphRuntimeError(f"Unsupported binary operator {op!r}", node=expr)
        if isinstance(expr, BoolOp):
            if expr.op == "and":
                for vexpr in expr.values:
                    v = eval_expr(vexpr, env)
                    if not _truthy(v):
                        return v
                return v  # type: ignore[possibly-undefined]
            if expr.op == "or":
                for vexpr in expr.values:
                    v = eval_expr(vexpr, env)
                    if _truthy(v):
                        return v
                return v  # type: ignore[possibly-undefined]
            raise LexiMorphRuntimeError(f"Unsupported boolean operator {expr.op!r}", node=expr)
        if isinstance(expr, Compare):
            left = eval_expr(expr.left, env)
            cur = left
            for op, comp_expr in zip(expr.ops, expr.comparators):
                right = eval_expr(comp_expr, env)
                ok: bool
                if op == "<":
                    ok = cur < right  # type: ignore[operator]
                elif op == "<=":
                    ok = cur <= right  # type: ignore[operator]
                elif op == ">":
                    ok = cur > right  # type: ignore[operator]
                elif op == ">=":
                    ok = cur >= right  # type: ignore[operator]
                elif op == "==":
                    ok = cur == right
                elif op == "!=":
                    ok = cur != right
                else:
                    raise LexiMorphRuntimeError(f"Unsupported comparison operator {op!r}", node=expr)
                if not ok:
                    return False
                cur = right
            return True

        raise LexiMorphRuntimeError(f"Unsupported expression: {type(expr).__name__}", node=expr)
    except LexiMorphRuntimeError:
        raise
    except Exception as e:
        raise LexiMorphRuntimeError(str(e), node=expr) from e


def run_program(source: str, mapping_doc: dict, *, stdin=None, stdout=None, stderr=None) -> int:
    """
    Public entry point: tokenize -> parse -> interpret.

    This intentionally does not use CPython `ast`, `exec`, or `subprocess`.
    """
    import sys as _sys

    stdin = _sys.stdin if stdin is None else stdin
    stdout = _sys.stdout if stdout is None else stdout
    stderr = _sys.stderr if stderr is None else stderr

    lexi_to_python = mapping_doc.get("lexi_to_python") or {}
    builtins_mapped = set(mapping_doc.get("builtins_mapped") or [])
    allowed_builtins = _make_builtins(stdin=stdin, stdout=stdout)

    # Provide only the supported builtin subset; anything else mapped in the JSON
    # should error cleanly at runtime if used.
    global_env = Environment()
    for name, obj in allowed_builtins.items():
        global_env.set(name, obj)

    # If mapping includes a builtin we don't implement and the source uses it,
    # it will fail with "not defined". Make it a bit clearer by pre-seeding
    # stubs for mapped-but-unsupported builtins.
    for b in sorted(builtins_mapped):
        if b not in allowed_builtins and b.isidentifier():
            def _stub(*_a: object, _b=b) -> object:  # type: ignore[no-redef]
                raise LexiMorphRuntimeError(
                    f"Builtin {_b!r} is not supported by the simple interpreter",
                    line=0,
                    col=0,
                )

            global_env.set(b, _stub)

    try:
        toks = tokenize(source, lexi_to_python)
        mod = parse_tokens(toks)
        exec_module(mod, global_env)
        return 0
    except (LexiMorphLexError, LexiMorphParseError) as e:
        stderr.write(f"{e}\n")
        return 1
    except LexiMorphRuntimeError as e:
        stderr.write(f"{e}\n")
        return 1

