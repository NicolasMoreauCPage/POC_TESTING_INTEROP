msg='PID|1||123456^^^HOSP||DOE^JOHN||19800101|||||^^^^^||^^^^^INVALIDTYPE'
parts=msg.split('|')
print(f'Total fields: {len(parts)}')
for i, p in enumerate(parts):
    print(f'  [{i}]: {p!r}')
print()
print(f'PID-11 (index 11): [{parts[11] if len(parts)>11 else ""}]')
print(f'PID-13 (index 13): [{parts[13] if len(parts)>13 else ""}]')
print(f'PID-14 (index 14): [{parts[14] if len(parts)>14 else ""}]')
