"""Debug ASC stripping issue."""
import sqlglot
from sqlglot import exp

sql = "SELECT title FROM albums ORDER BY title ASC"
tree = sqlglot.parse_one(sql, dialect="mysql")
print(f"Tree: {tree}")
print(f"Type: {type(tree).__name__}")

# Find Order expression
for node in tree.walk():
    if isinstance(node, exp.Order):
        print(f"\nOrder node: {node}")
        print(f"Order expressions: {node.expressions}")
        for expr in node.expressions:
            print(f"  - {type(expr).__name__}: {expr}, args: {expr.args}")
            if isinstance(expr, exp.Ordered):
                print(f"    desc={expr.args.get('desc')}, asc={expr.args.get('asc')}")
