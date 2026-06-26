import sqlite3

conn = sqlite3.connect("monedas.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(catalogo)")
columnas = cursor.fetchall()

print("\nCOLUMNAS DE LA TABLA CATALOGO:\n")

for columna in columnas:
    print(columna)

conn.close()