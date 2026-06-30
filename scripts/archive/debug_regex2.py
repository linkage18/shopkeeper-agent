"""Debug regex extraction from saved response."""
import re
import json

# Read the saved response
with open('scripts/last_response.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print(f"Text length: {len(text)}")
print(f"First 200 chars: {text[:200]}")
print(f"Last 200 chars: {text[-200:]}")

# Try the regex on each line
for i, line in enumerate(text.split('\n')):
    line = line.strip()
    if '"sql"' in line:
        print(f"\nLine {i} contains 'sql' (len={len(line)})")
        # Show the context around "sql"
        idx = line.index('"sql"')
        print(f"Context around 'sql': ...{line[max(0,idx-10):idx+200]}...")
        
        match = re.search(r'"sql":"([^"]+)"', line)
        print(f"Regex match: {match}")
        if match:
            print(f"  Captured: {match.group(1)}")
        else:
            # Try different patterns
            for pat, name in [
                (r'"sql":"([^"]*)"', 'simple'),
                (r'"sql":"((?:[^"\\\\]|\\\\.)*)"', 'escaped'),
                (r'"sql":\s*"([^"]+)"', 'whitespace'),
            ]:
                m = re.search(pat, line)
                if m:
                    print(f"  Pattern '{name}' matched: {m.group(1)[:60]}")
                else:
                    print(f"  Pattern '{name}' did NOT match")
