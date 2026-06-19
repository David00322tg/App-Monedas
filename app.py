from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'clave_secreta'

UPLOAD_FOLDER = 'static/imagenes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'monedas.db'

AUTHORIZED_USERS = {
    'admin': {'password': '3654', 'role': 'admin'},
    'invitado': {'password': '1234', 'role': 'viewer'}
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

    query = 'SELECT * FROM monedas WHERE 1=1'
    params = []

    if filter_tipo:
        query += ' AND tipo = ?'
        params.append(filter_tipo)

    if filter_anio:
        query += ' AND anio = ?'
        params.append(filter_anio)

    if filter_pais:
        query += ' AND pais = ?'
        params.append(filter_pais)

    if filter_valor:
        query += ' AND valor LIKE ?'
        params.append('%' + filter_valor + '%')

    query += ' ORDER BY anio ASC'

    monedas = conn.execute(query, params).fetchall()

    ultima_moneda = conn.execute(
        'SELECT * FROM monedas ORDER BY id DESC LIMIT 1'
    ).fetchone()

    tipos_moneda = [
        row['tipo'] for row in conn.execute(
            'SELECT DISTINCT tipo FROM monedas'
        ).fetchall()
    ]

    paises_moneda = [
        row['pais'] for row in conn.execute(
            'SELECT DISTINCT pais FROM monedas'
        ).fetchall()
    ]

    anios_moneda = [
        row['anio'] for row in conn.execute(
            'SELECT DISTINCT anio FROM monedas'
        ).fetchall()
    ]

    valores_moneda = [
        row['valor'] for row in conn.execute(
            'SELECT DISTINCT valor FROM monedas'
        ).fetchall()
    ]

    conn.close()

    return render_template(
        'index.html',
        monedas=monedas,
        tipos_moneda=tipos_moneda,
        paises_moneda=paises_moneda,
        anios_moneda=anios_moneda,
        valores_moneda=valores_moneda,
        filter_tipo=filter_tipo,
        filter_anio=filter_anio,
        filter_pais=filter_pais,
        filter_valor=filter_valor,
        ultima_moneda=ultima_moneda
    )

@app.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
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

        # VALIDACIÓN
        if not valor or not tipo or not pais or not anio:
            flash("Por favor rellena todos los campos obligatorios", "error")
            conn.close()
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

        # EVITAR DUPLICADOS
        existente = conn.execute(
            'SELECT * FROM monedas WHERE valor=? AND tipo=? AND pais=? AND anio=?',
            (valor, tipo, pais, anio)
        ).fetchone()

        if existente:
            conn.close()
            flash("Esta moneda ya está registrada", "error")
            return render_template(
                'nuevo.html',
                tipos=tipos,
                paises=paises,
                anios=anios,
                valores=valores
            )

        # INSERTAR
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
        tipos=tipos,
        paises=paises,
        anios=anios,
        valores=valores
    )
@app.route('/editar/<int:moneda_id>', methods=['GET', 'POST'])
def editar_moneda(moneda_id):
    conn = get_db_connection()
    moneda = conn.execute('SELECT * FROM monedas WHERE id=?', (moneda_id,)).fetchone()
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


@app.route('/borrar/<int:moneda_id>', methods=['POST'])
def borrar_moneda(moneda_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM monedas WHERE id=?', (moneda_id,))
    conn.commit()
    conn.close()
    flash('Moneda eliminada correctamente', 'success')
    return redirect(url_for('index'))


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
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
