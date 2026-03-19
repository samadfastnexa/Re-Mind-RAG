import sqlite3

conn = sqlite3.connect('./data/users.db')
cursor = conn.cursor()
cursor.execute('SELECT username, email, role, is_active FROM users')
users = cursor.fetchall()
print(f'\nFound {len(users)} user(s) in database:\n')
for row in users:
    print(f'  Username: {row[0]}')
    print(f'  Email: {row[1]}')
    print(f'  Role: {row[2]}')
    print(f'  Active: {bool(row[3])}')
    print()
conn.close()
