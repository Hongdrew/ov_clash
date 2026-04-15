# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
from typing import Callable, Any


class FilterNode:
    """
    Node in a filter expression tree.

    Represents either a comparison (e.g., [Column] = 'value') or a logical operation (AND/OR) between sub-expressions.

    Attributes:
        column (str): The column name for comparison nodes.
        op (str): The comparison operator (e.g., '=', 'IN', 'LIKE').
        value (str): The value to compare against.
        left (FilterNode): Left child node (for logical operations).
        right (FilterNode): Right child node (for logical operations).
        logic (str): Logical operator ('AND' or 'OR') if this is a logical node.
    """
    def __init__(self, column=None, op=None, value=None, left=None, right=None, logic=None):
        self.column = column
        self.op = op
        self.value = value
        self.left = left
        self.right = right
        self.logic = logic  # 'AND' or 'OR'

    def __repr__(self):
        if self.logic:
            return f"({self.left} {self.logic} {self.right})"
        return f"({self.column} {self.op} {self.value})"

def parse_filter_expression(filter_expression: str, upper_cased: bool = True) -> FilterNode | None:
    """
    Parse a filter expression string and return a tree of FilterNode objects.

    Supports:
        - Column references: [ColumnName] (column names enclosed in square brackets)
        - String and numeric literals (strings must be enclosed in single quotes)
        - Operators: '=', '<', '>', '<=', '>=', '<>', '!=', 'IN', 'NOT IN', 'LIKE'
        - Logical operators: AND, OR
        - Parentheses for grouping
        - Comma-separated lists for IN/NOT IN

    Some notes:
        - LIKE: Checks if the right-hand string (pattern) is a substring of the left-hand value (column).
        - IN: Checks if the left-hand value (column) is present in the right-hand list. E.g., [State] IN ('A','B').
        - Can LIKE be used together with IN? No, LIKE is only supported as a binary operator, not as a list operator.
          You can't do [Name] IN LIKE ('foo', 'bar'). If you want to check if a value matches any of several LIKE
          patterns, you must chain with OR: ([Name] LIKE 'foo' OR [Name] LIKE 'bar').

    Each node in the returned tree is a FilterNode representing either a comparison or a logical operation.

    Args:
        filter_expression (str): The filter expression string, e.g. "[Name] = 'foo' AND ([Age] > 20 OR [Status] IN ('Active','Pending'))"
        upper_cased (bool): If True, upper-case column names and string literals for case-insensitive matching.

    Returns:
        FilterNode | None: The root FilterNode if parsing succeeds, or None if parsing fails.

    Raises:
        SyntaxError: If the filter expression is malformed.
    """
    # Constants for token types
    TOKEN_LPAREN = "LPAREN"
    TOKEN_RPAREN = "RPAREN"
    TOKEN_COLUMN = "COLUMN"
    TOKEN_STRING = "STRING"
    TOKEN_NUMBER = "NUMBER"
    TOKEN_COMMA = "COMMA"
    TOKEN_OP = "OP"
    TOKEN_AND = "AND"
    TOKEN_OR = "OR"
    TOKEN_IDENT = "IDENT"

    # Tokenizer
    def tokenize(s):
        i = 0
        n = len(s)
        tokens = []
        while i < n:
            c = s[i]
            if c.isspace():
                i += 1
                continue
            if c == '(':
                tokens.append((TOKEN_LPAREN, c))
                i += 1
                continue
            if c == ')':
                tokens.append((TOKEN_RPAREN, c))
                i += 1
                continue
            if c == '[':
                # Parse [ColumnName]
                j = i + 1
                while j < n and s[j] != ']':
                    j += 1
                if j >= n:
                    raise SyntaxError("Unclosed [ in column name")
                column_name = s[i+1:j]
                tokens.append((TOKEN_COLUMN, column_name.upper() if upper_cased else column_name))
                i = j + 1
                continue
            if c == "'":
                # Parse quoted string
                j = i + 1
                val = ''
                while j < n:
                    if s[j] == "'":
                        if j + 1 < n and s[j+1] == "'":
                            val += "'"
                            j += 2
                        else:
                            break
                    else:
                        val += s[j]
                        j += 1
                else:
                    raise SyntaxError("Unclosed string literal")
                tokens.append((TOKEN_STRING, val.upper() if upper_cased else val))
                i = j + 1
                continue
            # Support negative numbers
            if c == '-' and i + 1 < n and (s[i+1].isdigit() or (s[i+1] == '.' and i+2 < n and s[i+2].isdigit())):
                j = i + 1
                while j < n and (s[j].isdigit() or s[j] == '.'):
                    j += 1
                num_str = s[i:j]
                if '.' in num_str:
                    tokens.append((TOKEN_NUMBER, float(num_str)))
                else:
                    tokens.append((TOKEN_NUMBER, int(num_str)))
                i = j
                continue
            # Support floats starting with dot, e.g. .5 or -.5
            if c == '.' and i + 1 < n and s[i+1].isdigit():
                j = i + 1
                while j < n and s[j].isdigit():
                    j += 1
                num_str = s[i:j]
                tokens.append((TOKEN_NUMBER, float(num_str)))
                i = j
                continue
            if c.isdigit():
                # Parse number
                j = i
                while j < n and (s[j].isdigit() or s[j] == '.'):
                    j += 1
                num_str = s[i:j]
                if '.' in num_str:
                    tokens.append((TOKEN_NUMBER, float(num_str)))
                else:
                    tokens.append((TOKEN_NUMBER, int(num_str)))
                i = j
                continue
            if c == ',':
                tokens.append((TOKEN_COMMA, ','))
                i += 1
                continue
            # Parse operators and keywords
            # Multi-char ops first
            for op in ['NOT LIKE', 'NOT IN', '<=', '>=', '<>', '!=', '=', '<', '>', 'LIKE', 'IN']:
                if s[i:i+len(op)].upper() == op:
                    tokens.append((TOKEN_OP, op.upper()))
                    i += len(op)
                    break
            else:
                # Parse identifiers/keywords (AND, OR)
                if s[i].isalpha():
                    j = i
                    while j < n and (s[j].isalnum() or s[j] == '_'):
                        j += 1
                    word = s[i:j].upper()
                    if word == TOKEN_AND:
                        tokens.append((TOKEN_AND, word))
                    elif word == TOKEN_OR:
                        tokens.append((TOKEN_OR, word))
                    else:
                        tokens.append((TOKEN_IDENT, s[i:j]))
                    i = j
                    continue
                raise SyntaxError(f"Unexpected character at {i}: {c}")
        return tokens

    try:
        tokens = tokenize(filter_expression)
    except Exception as e:
        carb.log_error(str(e))
        return None

    # Parser
    def parse_expression(tokens):
        def expect(tok_type):
            if not tokens or tokens[0][0] != tok_type:
                raise SyntaxError(f"Expected {tok_type}")
            return tokens.pop(0)

        def parse_value_list(tokens):
            # Parse a parenthesized list of values (strings or numbers)
            expect(TOKEN_LPAREN)
            values = []
            while tokens and tokens[0][0] in (TOKEN_STRING, TOKEN_NUMBER, TOKEN_COLUMN):
                val = tokens.pop(0)[1]
                values.append(val)
                if tokens and tokens[0][0] == TOKEN_COMMA:
                    tokens.pop(0)
                else:
                    break
            expect(TOKEN_RPAREN)
            return values

        def parse_atom(tokens):
            if tokens and tokens[0][0] == TOKEN_LPAREN:
                tokens.pop(0)
                node = parse_or(tokens)
                expect(TOKEN_RPAREN)
                return node
            if tokens and tokens[0][0] == TOKEN_COLUMN:
                column = tokens.pop(0)[1]
                if not tokens or tokens[0][0] != TOKEN_OP:
                    raise SyntaxError("Expected operator after column")
                op = tokens.pop(0)[1]
                # Value: string, number, or (for IN) parenthesized list
                if op in ('IN', 'NOT IN'):
                    value = parse_value_list(tokens)
                else:
                    # Accept single value or parenthesized list for any op
                    if tokens and tokens[0][0] == TOKEN_LPAREN:
                        value = parse_value_list(tokens)
                    elif tokens and tokens[0][0] in (TOKEN_STRING, TOKEN_NUMBER, TOKEN_COLUMN):
                        value = '[' + tokens.pop(0)[1] + ']' if tokens[0][0] == TOKEN_COLUMN else tokens.pop(0)[1]
                    else:
                        raise SyntaxError("Expected value after operator")
                return FilterNode(column=column, op=op, value=value)
            raise SyntaxError("Expected '(' or [Column]")

        def parse_and(tokens):
            node = parse_atom(tokens)
            while tokens and tokens[0][0] == TOKEN_AND:
                tokens.pop(0)
                right = parse_atom(tokens)
                node = FilterNode(left=node, right=right, logic=TOKEN_AND)
            return node

        def parse_or(tokens):
            node = parse_and(tokens)
            while tokens and tokens[0][0] == TOKEN_OR:
                tokens.pop(0)
                right = parse_and(tokens)
                node = FilterNode(left=node, right=right, logic=TOKEN_OR)
            return node

        return parse_or(tokens)

    try:
        filter_tree = parse_expression(tokens)
        if tokens:
            raise SyntaxError("Unexpected tokens at end")
    except Exception as e:
        filter_tree = None
        carb.log_error(str(e))

    return filter_tree

def apply_filter(
    filter_tree: FilterNode | None,
    get_column_value_fn: Callable[[str], Any],
) -> bool:
    """
    Evaluate a filter expression tree (FilterNode) against a row.

    Args:
        filter_tree (FilterNode | None): Root node of the filter expression tree, or None for no filter.
        get_column_value_fn (Callable[[str], Any]): Function that takes a column name and returns the value for that column in the current row.

    Returns:
        bool: True if the row matches the filter, False otherwise. Always True if filter_tree is None.
    """
    if filter_tree is None:
        return True

    def on_comparison(column, op, value) -> bool:
        v = get_column_value_fn(column)
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            value = get_column_value_fn(value[1:-1])
        if op == "=":
            return v == value
        if op == "IN":
            return v in value
        if op == "NOT IN":
            return v not in value
        if op == ">":
            return v > value
        if op == "<":
            return v < value
        if op == ">=":
            return v >= value
        if op == "<=":
            return v <= value
        if op == "<>" or op == "!=":
            return v != value
        if op == "LIKE":
            return value in v if isinstance(v, str) else False
        if op == "NOT LIKE":
            return not (value in v if isinstance(v, str) else False)

        raise NotImplementedError(op)

    if filter_tree.logic:
        left_result = apply_filter(filter_tree.left, get_column_value_fn)
        right_result = apply_filter(filter_tree.right, get_column_value_fn)
        if filter_tree.logic == "AND":
            return left_result and right_result
        elif filter_tree.logic == "OR":
            return left_result or right_result
        else:
            raise ValueError(f"Unknown logic operator: {filter_tree.logic}")
    else:
        return on_comparison(filter_tree.column, filter_tree.op, filter_tree.value)
