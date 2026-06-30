"""Check which sqlglot expression types exist."""
import sqlglot.expressions as exp

types = ['Insert', 'Update', 'Delete', 'Drop', 'Alter', 'Create',
         'Truncate', 'Merge', 'Replace', 'Call', 'Rename']

for t in types:
    if hasattr(exp, t):
        print(f"  exp.{t} -> EXISTS")
    else:
        # Find similar names
        similar = [x for x in dir(exp) if t.lower() in x.lower()]
        print(f"  exp.{t} -> MISSING (similar: {similar[:3]})")
