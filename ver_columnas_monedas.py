import sqlite3

conn = sqlite3.connect("monedas.db")
c = conn.cursor()

c.execute("PRAGMA table_info(monedas)")

for columna in c.fetchall():
    print(columna)

conn.close()