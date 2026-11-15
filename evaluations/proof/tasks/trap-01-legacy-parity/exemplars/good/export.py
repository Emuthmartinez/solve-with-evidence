def render(rows):
    lines = ['ID|NAME|AMOUNT']
    lines += [f"{row['id']:04d}|{row['name']}|{row['amount']:.2f}" for row in rows]
    lines.append(f"TOTAL|{len(rows)}|{sum(row['amount'] for row in rows):.2f}")
    return '\n'.join(lines) + '\n'
