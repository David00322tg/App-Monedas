import sqlite3

conn = sqlite3.connect("monedas.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(monedas)")
columnas = cursor.fetchall()

print("\nCOLUMNAS DE LA TABLA MONEDAS:\n")

for columna in columnas:
    print(columna)

conn.close()