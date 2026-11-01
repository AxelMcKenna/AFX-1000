"""KiCad S-expression reading and writing."""

import json
import re


class Atom(str):
    pass


def read_sexpr(text):
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text))

    def read(token):
        if token == "(":
            result = []
            for token in tokens:
                if token == ")":
                    return result
                result.append(read(token))
            raise ValueError("Unclosed expression")
        return json.loads(token) if token.startswith('"') else Atom(token)

    result = read(next(tokens))
    assert next(tokens, None) is None
    return result


def sexpr(value):
    if isinstance(value, list):
        return "(" + " ".join(sexpr(v) for v in value) + ")"
    if isinstance(value, Atom):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    return f"{value:.6f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def children(node, tag):
    return [v for v in node if isinstance(v, list) and v and v[0] == tag]


def first(node, tag):
    return children(node, tag)[0]


def a(value):
    return Atom(str(value))
