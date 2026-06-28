from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import sqlite3
import os
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'clave_secreta'

UPLOAD_FOLDER = 'static/imagenes'
UPLOAD_FOLDER_CATALOGO = 'static/catalogo'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'monedas.db'

AUTHORIZED_USERS = {
    'admin': {'password': '3654', 'role': 'admin'},
    'invitado': {'password': '1234', 'role': 'viewer'}
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_CATALOGO, exist_ok=True)

# ----------------------
# Helpers
# ----------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------
# Rutas de Autenticación
# ----------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user_data = AUTHORIZED_USERS.get(user)
        if user_data and user_data['password'] == password:
            session['user'] = user
            session['role'] = user_data['role']
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos", "error")
    elif 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/billetes')
def billetes():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('billetes.html')

# ----------------------
# Rutas de monedas
# ----------------------

@app.route('/inicio')
def index():

    if 'user' not in session:
        return redirect(url_for('login'))

    filter_tipo = request.args.get('filter_tipo', '').strip()
    filter_anio = request.args.get('filter_anio', '').strip()
    filter_pais = request.args.get('filter_pais', '').strip()
    filter_valor = request.args.get('filter_valor', '').strip()

    conn = get_db_connection()

    # 🔹 Consulta principal
    query = "SELECT * FROM monedas WHERE 1=1"
    params = []

    if filter_tipo:
        query += " AND tipo=?"
        params.append(filter_tipo)

    if filter_anio:
        query += " AND anio=?"
        params.append(filter_anio)

    if filter_pais:
        query += " AND pais=?"
        params.append(filter_pais)

    if filter_valor:
        query += " AND valor LIKE ?"
        params.append(f"%{filter_valor}%")

    query += " ORDER BY anio ASC"

    monedas = conn.execute(query, params).fetchall()

    # 🔥 TODAS tus monedas (las que tienes)
    mis_monedas = conn.execute("""
        SELECT valor, tipo, pais, anio, rareza, imagen, imagen_detras
        FROM monedas
    """).fetchall()

    # ✔ usar set (más rápido y sin errores de dict)
    mis_set = set(
        (m["valor"], m["tipo"], m["pais"], m["anio"], m["rareza"])
        for m in mis_monedas
    )

    lista_final = []

    for moneda in monedas:
        moneda = dict(moneda)

        clave = (
            moneda["valor"],
            moneda["tipo"],
            moneda["pais"],
            moneda["anio"],
            moneda["rareza"]
        )

        if clave in mis_set:
            moneda["tengo"] = True

            # opcional: coger imágenes si existen
            mia = next(
                (m for m in mis_monedas if
                 m["valor"] == moneda["valor"] and
                 m["tipo"] == moneda["tipo"] and
                 m["pais"] == moneda["pais"] and
                 m["anio"] == moneda["anio"] and
                 m["rareza"] == moneda["rareza"]),
                None
            )

            if mia:
                moneda["imagen"] = mia["imagen"]
                moneda["imagen_detras"] = mia["imagen_detras"]

        else:
            moneda["tengo"] = False

        lista_final.append(moneda)

    from collections import defaultdict

    agrupadas = defaultdict(list)
    for m in lista_final:
        agrupadas[m["pais"]].append(m)

    total = len(monedas)
    conseguidas = sum(1 for m in lista_final if m["tengo"])

    tipos_moneda = conn.execute("SELECT DISTINCT tipo FROM monedas").fetchall()
    paises_moneda = conn.execute("SELECT DISTINCT pais FROM monedas").fetchall()
    anios_moneda = conn.execute("SELECT DISTINCT anio FROM monedas").fetchall()
    valores_moneda = conn.execute("SELECT DISTINCT valor FROM monedas").fetchall()

    conn.close()

    return render_template(
        "index.html",
        monedas=lista_final,
        total=total,
        conseguidas=conseguidas,
        filter_tipo=filter_tipo,
        filter_anio=filter_anio,
        filter_pais=filter_pais,
        filter_valor=filter_valor,
        tipos_moneda=[r["tipo"] for r in tipos_moneda],
        paises_moneda=[r["pais"] for r in paises_moneda],
        anios_moneda=[r["anio"] for r in anios_moneda],
        valores_moneda=[r["valor"] for r in valores_moneda]
    )


@app.route('/nuevo_moneda', methods=['GET', 'POST'])
def nuevo_moneda():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash("No tienes permiso para añadir monedas", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()

    tipos = [row['tipo'] for row in conn.execute(
        'SELECT DISTINCT tipo FROM monedas ORDER BY tipo'
    ).fetchall()]

    paises = [row['pais'] for row in conn.execute(
        'SELECT DISTINCT pais FROM monedas ORDER BY pais'
    ).fetchall()]

    anios = [row['anio'] for row in conn.execute(
        'SELECT DISTINCT anio FROM monedas ORDER BY anio DESC'
    ).fetchall()]

    valores = [row['valor'] for row in conn.execute(
        'SELECT DISTINCT valor FROM monedas ORDER BY valor'
    ).fetchall()]

    if request.method == 'POST':

        valor = (
            request.form.get('valor_existente', '').strip()
            or request.form.get('valor_nuevo', '').strip()
        )

        tipo = request.form.get('tipo_existente', '').strip()
        if not tipo:
            tipo = request.form.get('tipo_nuevo', '').strip()

        pais = request.form.get('pais_existente', '').strip()
        if not pais:
            pais = request.form.get('pais_nuevo', '').strip()

        anio = request.form.get('anio', '').strip()
        if anio == 'otro':
            anio = request.form.get('anio_otro', '').strip()

        rareza = request.form.get('rareza', '').strip()
        historia = request.form.get('historia', '').strip()

        imagen = request.files.get('imagen')
        imagen_detras = request.files.get('imagen_detras')

        if not valor or not tipo or not pais or not anio:
            conn.close()
            flash("Por favor rellena todos los campos obligatorios", "error")
            return render_template(
                'nuevo.html',
                tipos=tipos,
                paises=paises,
                anios=anios,
                valores=valores
            )

        filename = None
        filename_detras = None

        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(UPLOAD_FOLDER, filename))

        if imagen_detras and allowed_file(imagen_detras.filename):
            filename_detras = secure_filename(imagen_detras.filename)
            imagen_detras.save(os.path.join(UPLOAD_FOLDER, filename_detras))

        conn.execute(
            '''
            INSERT INTO monedas
            (valor, tipo, pais, anio, rareza, historia, imagen, imagen_detras)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                valor,
                tipo,
                pais,
                anio,
                rareza,
                historia,
                filename,
                filename_detras
            )
        )

        conn.commit()
        conn.close()

        flash("Moneda añadida correctamente", "success")
        return redirect(url_for('index'))

    conn.close()

    return render_template(
        'nuevo.html',
        tipos_moneda=tipos,
        paises_moneda=paises,
        anios_moneda=anios,
        valores_moneda=valores
    )

@app.route('/nuevo_catalogo', methods=['GET', 'POST'])
def nuevo_catalogo():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash("No tienes permiso para añadir monedas", "error")
        return redirect(url_for('catalogo'))

    conn = get_db_connection()

    tipos = [row['tipo'] for row in conn.execute(
        'SELECT DISTINCT tipo FROM catalogo ORDER BY tipo'
    ).fetchall()]

    paises = [row['pais'] for row in conn.execute(
        'SELECT DISTINCT pais FROM catalogo ORDER BY pais'
    ).fetchall()]

    anios = [row['anio'] for row in conn.execute(
        'SELECT DISTINCT anio FROM catalogo ORDER BY anio DESC'
    ).fetchall()]

    valores = [row['valor'] for row in conn.execute(
        'SELECT DISTINCT valor FROM catalogo ORDER BY valor'
    ).fetchall()]

    if request.method == 'POST':

        valor = (
            request.form.get('valor_existente', '').strip()
            or request.form.get('valor_nuevo', '').strip()
        )

        tipo = request.form.get('tipo_existente', '').strip()
        if not tipo:
            tipo = request.form.get('tipo_nuevo', '').strip()

        pais = request.form.get('pais_existente', '').strip()
        if not pais:
            pais = request.form.get('pais_nuevo', '').strip()

        anio = request.form.get('anio', '').strip()
        if anio == 'otro':
            anio = request.form.get('anio_otro', '').strip()

        rareza = request.form.get('rareza', '').strip()
        historia = request.form.get('historia', '').strip()

        imagen = request.files.get('imagen')
        imagen_detras = request.files.get('imagen_detras')

        # VALIDACIÓN
        if not valor or not tipo or not pais or not anio:
            flash("Por favor rellena todos los campos obligatorios", "error")
            conn.close()
            return render_template(
                'nuevo_catalogo.html',
                tipos=tipos,
                paises=paises,
                anios=anios,
                valores=valores
            )

        filename = None
        filename_detras = None

        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(UPLOAD_FOLDER_CATALOGO, filename))

        if imagen_detras and allowed_file(imagen_detras.filename):
            filename_detras = secure_filename(imagen_detras.filename)
            imagen_detras.save(os.path.join(UPLOAD_FOLDER_CATALOGO, filename_detras))

        # INSERTAR
        conn.execute(
            '''
            INSERT INTO catalogo
            (valor, tipo, pais, anio, rareza, historia, imagen, imagen_detras)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                valor,
                tipo,
                pais,
                anio,
                rareza,
                historia,
                filename,
                filename_detras
            )
        )

        conn.commit()
        conn.close()

        flash("Moneda añadida correctamente", "success")
        return redirect(url_for('catalogo'))

    conn.close()

    return render_template(
        'nuevo_catalogo.html',
        tipos_moneda=tipos,
        paises_moneda=paises,
        anios_moneda=anios,
        valores_moneda=valores
    )
@app.route('/catalogo')
def catalogo():

    filter_tipo = request.args.get('filter_tipo', '').strip()
    filter_anio = request.args.get('filter_anio', '').strip()
    filter_pais = request.args.get('filter_pais', '').strip()
    filter_valor = request.args.get('filter_valor', '').strip()
    filter_estado = request.args.get("filter_estado", "")
    filter_rareza = request.args.get("filter_rareza", "")

    conn = sqlite3.connect("monedas.db")
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM catalogo WHERE 1=1"
    params = []

    if filter_tipo:
        query += " AND tipo=?"
        params.append(filter_tipo)

    if filter_anio:
        query += " AND anio=?"
        params.append(filter_anio)

    if filter_pais:
        query += " AND pais=?"
        params.append(filter_pais)

    if filter_valor:
        query += " AND valor LIKE ?"
        params.append(f"%{filter_valor}%")

    query += " ORDER BY pais, valor, anio"

    catalogo = conn.execute(query, params).fetchall()

    mis_monedas = conn.execute("""
        SELECT valor, tipo, pais, anio, rareza, imagen, imagen_detras
        FROM monedas
    """).fetchall()

    # Diccionario para búsqueda rápida
    mis_dict = {
        (m["valor"], m["tipo"], m["pais"], m["anio"], m["rareza"]): m
        for m in mis_monedas
    }

    monedas = []

    for moneda in catalogo:

        clave = (
            moneda["valor"],
            moneda["tipo"],
            moneda["pais"],
            moneda["anio"],
            moneda["rareza"]
        )

        moneda = dict(moneda)

        if clave in mis_dict:
            mia = mis_dict[clave]
            moneda["imagen"] = mia["imagen"]
            moneda["imagen_detras"] = mia["imagen_detras"]
            moneda["tengo"] = True
        else:
            moneda["tengo"] = False

        monedas.append(moneda)

    # FILTRO ESTADO
    if filter_estado == "tengo":
        monedas = [m for m in monedas if m["tengo"]]
    elif filter_estado == "faltan":
        monedas = [m for m in monedas if not m["tengo"]]

    # FILTRO RAREZA
    if filter_rareza:
        monedas = [m for m in monedas if m["rareza"] == filter_rareza]

    from collections import defaultdict

    agrupadas = defaultdict(list)

    for m in monedas:
        agrupadas[m["pais"]].append(m)

    # Progreso por país
    progreso_paises = {}

    for pais, lista in agrupadas.items():

        total_pais = len(lista)
        tengo_pais = len([m for m in lista if m["tengo"]])

        porcentaje = 0

        if total_pais > 0:
            porcentaje = round((tengo_pais / total_pais) * 100)

        progreso_paises[pais] = {
            "total": total_pais,
            "tengo": tengo_pais,
            "porcentaje": porcentaje
        }

    total = len(catalogo)
    conseguidas = len([m for m in monedas if m["tengo"]])

    tipos_moneda = conn.execute(
        "SELECT DISTINCT tipo FROM catalogo"
    ).fetchall()

    paises_moneda = conn.execute(
        "SELECT DISTINCT pais FROM catalogo"
    ).fetchall()

    anios_moneda = conn.execute(
        "SELECT DISTINCT anio FROM catalogo"
    ).fetchall()

    valores_moneda = conn.execute(
        "SELECT DISTINCT valor FROM catalogo"
    ).fetchall()

    rarezas = conn.execute(
        "SELECT DISTINCT rareza FROM catalogo ORDER BY rareza"
    ).fetchall()

    conn.close()

    return render_template(
        "catalogo.html",
        agrupadas=agrupadas,
        total=total,
        progreso_paises=progreso_paises,
        conseguidas=conseguidas,
        filter_tipo=filter_tipo,
        filter_anio=filter_anio,
        filter_pais=filter_pais,
        filter_valor=filter_valor,
        filter_estado=filter_estado,
        filter_rareza=filter_rareza,
        rarezas=[r["rareza"] for r in rarezas],
        tipos_moneda=[r["tipo"] for r in tipos_moneda],
        paises_moneda=[r["pais"] for r in paises_moneda],
        anios_moneda=[r["anio"] for r in anios_moneda],
        valores_moneda=[r["valor"] for r in valores_moneda]
    )
@app.route('/editar_catalogo/<int:moneda_id>', methods=['GET', 'POST'])
def editar_catalogo(moneda_id):
    conn = get_db_connection()
    moneda = conn.execute(
        'SELECT * FROM catalogo WHERE id=?',
        (moneda_id,)
    ).fetchone()

    if not moneda:
        flash("Moneda no encontrada", "error")
        return redirect(url_for('catalogo'))

    if request.method == 'POST':
        valor = request.form['valor']
        tipo = request.form['tipo']
        pais = request.form['pais']
        anio = request.form['anio']
        rareza = request.form.get('rareza')
        historia = request.form.get('historia')

        conn.execute("""
            UPDATE catalogo
            SET valor=?, tipo=?, pais=?, anio=?, rareza=?, historia=?
            WHERE id=?
        """, (valor, tipo, pais, anio, rareza, historia, moneda_id))

        conn.commit()
        conn.close()

        flash("Catálogo actualizado con éxito", "success")
        return redirect(url_for('catalogo'))

    conn.close()
    return render_template('editar_catalogo.html', moneda=moneda)

@app.route('/editar_moneda/<int:moneda_id>', methods=['GET', 'POST'])
def editar_moneda(moneda_id):

    conn = get_db_connection()
    moneda = conn.execute(
        'SELECT * FROM monedas WHERE id=?',
        (moneda_id,)
    ).fetchone()

    if not moneda:
        flash("Moneda no encontrada", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        valor = request.form['valor']
        tipo = request.form['tipo']
        pais = request.form['pais']
        anio = request.form['anio']
        rareza = request.form.get('rareza')
        historia = request.form.get('historia')

        conn.execute("""
            UPDATE monedas
            SET valor=?, tipo=?, pais=?, anio=?, rareza=?, historia=?
            WHERE id=?
        """, (valor, tipo, pais, anio, rareza, historia, moneda_id))

        conn.commit()
        conn.close()

        flash("Moneda actualizada con éxito", "success")
        return redirect(url_for('index'))

    conn.close()
    return render_template('editar_moneda.html', moneda=moneda)


@app.route('/borrar_moneda/<int:moneda_id>', methods=['POST'])
def borrar_moneda(moneda_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM monedas WHERE id=?', (moneda_id,))
    conn.commit()
    conn.close()
    flash('Moneda eliminada correctamente', 'success')
    return redirect(url_for('index'))


@app.route('/borrar_catalogo/<int:moneda_id>', methods=['POST'])
def borrar_catalogo(moneda_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM catalogo WHERE id=?', (moneda_id,))
    conn.commit()
    conn.close()
    flash('Moneda del catálogo eliminada correctamente', 'success')
    return redirect(url_for('catalogo'))
# ----------------------
# Archivos PWA (Offline)
# ----------------------
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')


@app.route('/offline')
def offline():
    """Página offline cuando no hay conexión"""
    return render_template('offline.html')


# ----------------------
# Run
# ----------------------
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
