import matplotlib
matplotlib.use('Agg')
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
import matplotlib.pyplot as plt
from pywaffle import Waffle
import io
import os
import base64
import csv
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ruta del disco persistente
# db_dir='/var/data'
db_dir=os.path.join(os.getcwd(),'data')

os.makedirs(db_dir,exist_ok=True)
db_path=os.path.join(db_dir,'apartamentos.db')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Apartamento(db.Model):
   id = db.Column(db.Integer, primary_key=True)
   number = db.Column(db.String(20), unique=True, nullable=False)
   coeficient = db.Column(db.Float, nullable=False)
   user = db.Column(db.String(50), nullable=False)
   date_registered = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
   id = db.Column(db.Integer, primary_key=True)
   username = db.Column(db.String(50), unique=True, nullable=False)
   password = db.Column(db.String(50), nullable=False)

# Crear base de datos
with app.app_context():
   db.create_all()

# Cargar datos desde Excel
df_apartamentos = pd.read_excel('COEFICIENTES DE CO_PROPIEDAD.xlsx', engine='openpyxl')
df_apartamentos['Apartamentos'] = df_apartamentos['Apartamentos'].astype(str)
apartamentos_permitidos = df_apartamentos.set_index('Apartamentos')['Coeficiente'].to_dict()

# Contraseña para reiniciar
RESET_PASSWORD = 'propiedad.horizontal'

# Usuarios permitidos (ejemplo simple, en producción usa una base de datos segura)
usuarios = {'admin': 'Admin.1', 'user1': 'User.1', 'user2': 'User.2', 'user.3': 'User.4', 
            'user4': 'User.4', 'user5': 'User.5','user6': 'User.6','user7': 'User.7',
            'user8': 'User.8','user9': 'User.9', 'user10': 'User.10'}

@app.route('/')
def index():
   if 'username' in session:
       return redirect(url_for('dashboard'))
   return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
   username = request.form['username']
   password = request.form['password']
   if username in usuarios and usuarios[username] == password:
       session['username'] = username
       return redirect(url_for('dashboard'))
   return 'Credenciales incorrectas', 403

@app.route('/logout')
def logout():
   session.pop('username', None)
   return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
   if 'username' in session:
       return render_template('dashboard.html')
   return redirect(url_for('index'))

@app.route('/registrar', methods=['POST'])
def registrar_ticket():
   if 'username' not in session:
       return jsonify({'status': 'error', 'message': 'No autenticado.'})
   apartamento = request.form['apartamento'].strip()
   usuario = session['username']
   if apartamento in apartamentos_permitidos:
       existing_apartamento = Apartamento.query.filter_by(number=apartamento).first()
       coeficiente=apartamentos_permitidos[apartamento]
       if not existing_apartamento:
           new_apartamento = Apartamento(number=apartamento, coeficient=apartamentos_permitidos[apartamento], user=usuario)
           db.session.add(new_apartamento)
           db.session.commit()
           return jsonify({'status': 'success', 'message': f'Apartamento <b>{apartamento}</b> registrado correctamente con el coefieciente: <b>{coeficiente}</b>'})
       else:
           return jsonify({'status': 'error', 'message': f'Apartamento {apartamento} ya <b>ha sido registrado anteriormente</b>.'})
   else:
       return jsonify({'status': 'error', 'message': f'Apartamento {apartamento} <b>NO válido</b>.'})

@app.route('/tickets')
def mostrar_tickets():
   if 'username' not in session:
       return redirect(url_for('index'))
   registrados = Apartamento.query.all()
   registrados_list = [{'number': t.number, 'coeficient': t.coeficient, 'user': t.user, 'date_registered': t.date_registered} for t in registrados]
   no_registrados = set(apartamentos_permitidos.keys()) - {t['number'] for t in registrados_list}
   # total_coeficiente = sum([t['category'] for t in registrados_list])
   return render_template('tickets.html', registrados=registrados_list, no_registrados=list(no_registrados))

@app.route('/admin')
def admin():
   if 'username' not in session:
       return redirect(url_for('index'))
   stats_general = Apartamento.query.filter_by(coeficient='GENERAL').count()
   stats_cortesia = Apartamento.query.filter_by(coeficient='CORTESIA').count()
   stats_preferencial = Apartamento.query.filter_by(coeficient='PREFERENCIAL').count()
   stats_vip = Apartamento.query.filter_by(coeficient='VIP').count()
   return render_template('admin.html', stats_general=stats_general,stats_cortesia =stats_cortesia , stats_preferencial=stats_preferencial, stats_vip=stats_vip)

@app.route('/reset', methods=['GET', 'POST'])
def reset():
   if 'username' not in session:
       return redirect(url_for('index'))
   if request.method == 'POST':
       password = request.form['password']
       if password == RESET_PASSWORD:
           db.session.query(Apartamento).delete()
           db.session.commit()
           return redirect(url_for('admin'))
       else:
           return 'Contraseña incorrecta', 403
   return render_template('reset.html')

@app.route('/exportar')
def exportar():
   if 'username' not in session:
       return redirect(url_for('index'))
   si = io.StringIO()
   cw = csv.writer(si)
   cw.writerow(['Apartamento', 'Coeficiente', 'Usuario', 'Fecha'])
   apartamentos = Apartamento.query.all()
   for t in apartamentos:
       cw.writerow([t.number, t.coeficient, t.user, t.date_registered.strftime('%Y-%m-%d')])
   output = make_response(si.getvalue())
   output.headers["Content-Disposition"] = "attachment; filename=Apartamentos_registrados.csv"
   output.headers["Content-type"] = "text/csv"
   return output

@app.route('/graficos')
def graficos():
   if 'username' not in session:
       return redirect(url_for('index'))
   stats_general = Apartamento.query.filter_by(coeficient='GENERAL').count()
   stats_cortesia = Apartamento.query.filter_by(coeficient='CORTESIA').count()
   stats_preferencial = Apartamento.query.filter_by(coeficient='PREFERENCIAL').count()
   stats_vip = Apartamento.query.filter_by(coeficient='VIP').count()

   fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
   
   # Gráfico de barras
   fig, ax = plt.subplots()
   categorias = ['GENERAL', 'CORTESIA','PREFERENCIAL', 'VIP']
   valores = [stats_general, stats_cortesia, stats_preferencial, stats_vip]
   ax.bar(categorias, valores)
   ax.set_xlabel('Categoría')
   ax.set_ylabel('Número de Tickets Registrados')
   ax.set_title('')
   img = io.BytesIO()
   plt.savefig(img, format='png')
   img.seek(0)
   graph_url_barras = base64.b64encode(img.getvalue()).decode()
   plt.close()
   # Gráfico de Waffle
   fig = plt.figure(
       FigureClass=Waffle,
       rows=25,
    #    characters = '♥',
    #    icons='face-smile',
       values={'General': stats_general, 'Cortesía':stats_cortesia,'Preferencial': stats_preferencial, 'VIP': stats_vip},
       title={'label': '', 'loc': 'center'},
       labels=["{0} ({1})".format(k, v) for k, v in {'General': stats_general, 'Cortesía':stats_cortesia,'Preferencial': stats_preferencial, 'VIP': stats_vip}.items()],
       legend={'loc': 'upper left', 'bbox_to_anchor': (1, 1)}
    )
   img = io.BytesIO()
   plt.savefig(img, format='png')
   img.seek(0)
   graph_url_waffle = base64.b64encode(img.getvalue()).decode()
   plt.close()
   return render_template('graficos.html', graph_url_barras='data:image/png;base64,{}'.format(graph_url_barras), graph_url_waffle='data:image/png;base64,{}'.format(graph_url_waffle))

    
@app.route('/get_ticket_count')
def get_ticket_count():
   count = Apartamento.query.count()
   total_coeficiente=db.session.query(db.func.sum(Apartamento.coeficient)).scalar()
   total_coeficiente=f"{total_coeficiente:.3f}"
   return jsonify({'count': f'Apartamentos: {count} \n Coeficiente total: {total_coeficiente}' })

if __name__ == '__main__':
   app.run(debug=True)
