import sqlite3

conn = sqlite3.connect("monedas.db")
conn.row_factory = sqlite3.Row

print("CATALOGO:", conn.execute("SELECT COUNT(*) FROM catalogo").fetchone()[0])
print("MONEDAS:", conn.execute("SELECT COUNT(*) FROM monedas").fetchone()[0])
for fila in conn.execute("SELECT * FROM monedas"):
    print(dict(fila))