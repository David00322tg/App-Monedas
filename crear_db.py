import sqlite3

conn = sqlite3.connect('monedas.db')
c = conn.cursor()

# Crear la tabla con los campos correctos
c.execute('''
CREATE TABLE IF NOT EXISTS monedas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    valor REAL NOT NULL,
    tipo TEXT NOT NULL,
    pais TEXT NOT NULL,
    anio INTEGER NOT NULL,
    rareza TEXT,
    historia TEXT,
    imagen TEXT
)
''')

conn.commit()
conn.close()

print("✅ Base de datos creada correctamente: monedas.db")
