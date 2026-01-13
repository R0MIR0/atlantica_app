# app.py — VERSÃO FINAL 100% CORRIGIDA E FUNCIONANDO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import requests, re, json
from flask import abort, jsonify, current_app
import json

def tem_permissao(nivel_necessario=None, funcao=None):
    """
    Verifica se o usuário tem permissão para acessar uma função.
    nivel_necessario: número do nível (ex: 1, 2, 10)
    funcao: string exata como no niveis_acesso (ex: "Clientes - Listar")
    """
    if current_user.nivel_acesso == 0:  # Admin sempre pode tudo
        return True

    if nivel_necessario is not None and current_user.nivel_acesso > nivel_necessario:
        return False

    if funcao:
        config = Configuracao.query.first()
        if not config or not config.permissoes:
            return False

        try:
            permissoes = json.loads(config.permissoes)
            permissoes_do_nivel = permissoes.get(str(current_user.nivel_acesso), [])
            return funcao in permissoes_do_nivel
        except:
            return False

    return False

from functools import wraps

def permissao_requerida(funcao=None):
    @wraps(funcao)
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not tem_permissao(funcao=funcao):
                flash('Você não tem permissão para acessar esta função.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ======================= MODELOS =======================
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo_usuario_id = db.Column(db.Integer, db.ForeignKey('tipo_usuario.id'))
    gerente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nivel_acesso = db.Column(db.Integer, default=10)
    status = db.Column(db.String(10), default='ATIVO')
    tipo = db.relationship('TipoUsuario', backref='usuarios')
    gerente = db.relationship('Usuario', remote_side=[id], uselist=False)
    def get_id(self): return str(self.id)

class TipoUsuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_usuario = db.Column(db.String(50), unique=True, nullable=False)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permissoes = db.Column(db.Text)

class Consulta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa = db.Column(db.String(100), nullable=False)
    razao_social = db.Column(db.String(150))
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    ie = db.Column(db.String(20))
    grupo = db.Column(db.String(100))
    cep = db.Column(db.String(9))
    logradouro = db.Column(db.String(100))
    numero = db.Column(db.String(10))
    complemento = db.Column(db.String(50))
    bairro = db.Column(db.String(50))
    cidade = db.Column(db.String(50))
    estado = db.Column(db.String(2))
    nome_contato = db.Column(db.String(100))
    telefone_contato = db.Column(db.String(20))
    email_contato = db.Column(db.String(100))
    nome_representante = db.Column(db.String(100))
    data_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    status_consulta = db.Column(db.String(20), default='PENDENTE')
    motivo_negativa = db.Column(db.Text)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa = db.Column(db.String(100), nullable=False)
    razao_social = db.Column(db.String(150))
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    ie = db.Column(db.String(20))
    grupo = db.Column(db.String(100))
    cep = db.Column(db.String(9))
    logradouro = db.Column(db.String(100))
    numero = db.Column(db.String(10))
    complemento = db.Column(db.String(50))
    bairro = db.Column(db.String(50))
    cidade = db.Column(db.String(50))
    estado = db.Column(db.String(2))
    nome_contato = db.Column(db.String(100))
    telefone_contato = db.Column(db.String(20))
    email_contato = db.Column(db.String(100))
    nome_representante = db.Column(db.String(100))
    status_cliente = db.Column(db.String(20), default='RESERVADO')
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
   

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False)
    representante = db.Column(db.String(100))
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    status = db.Column(db.String(20), default='ATIVO')
    fila_interesse = db.Column(db.Text)
    cliente = db.relationship('Cliente', backref='reservas')

@login_manager.user_loader
def load_user(id):
    return Usuario.query.get(int(id))

# ======================= IMPORTS DOS UTILS =======================
from utils.masks import mascarar_cnpj, mascarar_cep, mascarar_telefone, limpar_numero
from utils.helpers import calcular_fim_reserva, gerar_fila_string

# ======================= FUNÇÃO AUXILIAR =======================
def buscar_cep(cep):
    cep = limpar_numero(cep)
    if len(cep) != 8:
        return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
        data = r.json()
        return data if 'erro' not in data else None
    except:
        return None

# ======================= ROTAS =======================
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(email=request.form['email'].lower()).first()
        if user and check_password_hash(user.senha_hash, request.form['senha']) and user.status == 'ATIVO':
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login inválido ou usuário inativo', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    tipo = current_user.tipo.tipo_usuario.strip().lower()

    # Queries base
    query_clientes = Cliente.query
    query_consultas = Consulta.query
    query_reservas = Reserva.query.filter_by(status='ATIVA')

    # Aplica filtro se for representante ou gerente
    if tipo == 'representante':
        nome_rep = current_user.nome.strip().upper()

        query_clientes = query_clientes.filter(
            func.trim(func.upper(Cliente.nome_representante)) == nome_rep
        )
        query_consultas = query_consultas.filter(
            func.trim(func.upper(Consulta.nome_representante)) == nome_rep
        )
        # TENTA filtrar Reserva — se o campo não existir, ignora o filtro (não quebra)
        try:
            query_reservas = query_reservas.filter(
                func.trim(func.upper(Reserva.nome_representante)) == nome_rep
            )
        except AttributeError:
            try:
                query_reservas = query_reservas.filter(
                    func.trim(func.upper(Reserva.representante)) == nome_rep
                )
            except AttributeError:
                pass  # não tem campo de representante na Reserva → mostra todas (ou zero, veja abaixo)

    elif tipo == 'gerente':
        representantes_do_gerente = Usuario.query.filter(
            Usuario.gerente_id == current_user.id,
            Usuario.tipo.has(TipoUsuario.tipo_usuario.ilike('%representante%'))
        ).with_entities(Usuario.nome).all()

        nomes_representantes = [rep.nome.strip().upper() for rep in representantes_do_gerente]

        if nomes_representantes:
            query_clientes = query_clientes.filter(
                func.trim(func.upper(Cliente.nome_representante)).in_(nomes_representantes)
            )
            query_consultas = query_consultas.filter(
                func.trim(func.upper(Consulta.nome_representante)).in_(nomes_representantes)
            )
            try:
                query_reservas = query_reservas.filter(
                    func.trim(func.upper(Reserva.nome_representante)).in_(nomes_representantes)
                )
            except AttributeError:
                try:
                    query_reservas = query_reservas.filter(
                        func.trim(func.upper(Reserva.representante)).in_(nomes_representantes)
                    )
                except AttributeError:
                    pass
        else:
            query_clientes = query_clientes.filter(Cliente.id == 0)
            query_consultas = query_consultas.filter(Consulta.id == 0)
            query_reservas = query_reservas.filter(Reserva.id == 0)

    # Executa as contagens
    total_clientes = query_clientes.count()
    total_consultas_pendentes = query_consultas.filter_by(status_consulta='PENDENTE').count()
    total_reservas_ativas = query_reservas.count()

    return render_template('dashboard.html',
        total_clientes=total_clientes,
        total_consultas=total_consultas_pendentes,
        total_reservas_ativas=total_reservas_ativas,
        now=datetime.now()
    )

# ======================= USUÁRIOS =======================
from sqlalchemy import or_   # ainda pode manter se usar em outro lugar

@app.route('/usuarios')
@login_required
@permissao_requerida("Usuários - Listar")
def usuarios():
    query = Usuario.query.order_by(Usuario.nome)

    tipo = current_user.tipo.tipo_usuario.strip().lower()

    # 1. REPRESENTANTE → NÃO vê ninguém na lista de usuários
    if tipo == 'representante':
        query = query.filter(Usuario.id == 0)  # ou query.filter(False)

    # 2. GERENTE → vê ele mesmo + seus representantes diretos
    elif tipo == 'gerente':
        query = query.filter(
            #(Usuario.id == current_user.id)# |
            (
                (Usuario.gerente_id == current_user.id) &
                Usuario.tipo.has(TipoUsuario.tipo_usuario.ilike('%representante%'))
            )
        )

    # 3. ADMINISTRADOR → vê todos (sem filtro)

    usuarios = query.all()

    tipos = TipoUsuario.query.order_by(TipoUsuario.tipo_usuario).all()
    
    gerentes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario.ilike('%gerente%'))\
        .order_by(Usuario.nome).all()

    return render_template(
        'usuarios/index.html',
        usuarios=usuarios,
        tipos=tipos,
        gerentes=gerentes
    )


@app.route('/usuarios/form', methods=['GET', 'POST'])
@app.route('/usuarios/form/<int:id>', methods=['GET', 'POST'])
@login_required
@permissao_requerida("Usuários - Criar")
def usuario_form(id=None):
    # Para edição, verifica permissão separada
    if id:
        if not tem_permissao(funcao="Usuários - Editar"):
            flash('Você não tem permissão para editar usuários.', 'danger')
            return redirect(url_for('usuarios'))
    
    usuario = Usuario.query.get_or_404(id) if id else None
    tipos = TipoUsuario.query.all()
    gerentes = Usuario.query.filter(Usuario.tipo.has(tipo_usuario='GERENTE')).all() if TipoUsuario.query.filter_by(tipo_usuario='GERENTE').first() else []

    if request.method == 'POST':
        dados = request.form
        
        if not usuario:
            if Usuario.query.filter_by(email=dados['email'].lower()).first():
                flash('E-mail já existe', 'danger')
                return redirect(request.url)
            usuario = Usuario()
            if not dados.get('senha'):
                flash('Senha obrigatória para novo usuário', 'danger')
                return redirect(request.url)
            usuario.senha_hash = generate_password_hash(dados['senha'])

        usuario.nome = dados['nome'].upper()
        usuario.email = dados['email'].lower()
        usuario.telefone = mascarar_telefone(dados.get('telefone', ''))
        usuario.tipo_usuario_id = int(dados['tipo_usuario'])
        usuario.gerente_id = int(dados['gerente_id']) if dados.get('gerente_id') else None
        usuario.nivel_acesso = int(dados['nivel_acesso'])
        usuario.status = dados['status']
        
        if dados.get('senha'):
            usuario.senha_hash = generate_password_hash(dados['senha'])

        db.session.add(usuario)
        db.session.commit()
        flash('Usuário salvo com sucesso!', 'success')
        return redirect(url_for('usuarios'))

    return render_template('usuarios/form.html', 
                         usuario=usuario, 
                         tipos=tipos, 
                         gerentes=gerentes, 
                         niveis=range(0,11))


@app.route('/usuarios/ver/<int:id>')
@login_required
@permissao_requerida("Usuários - Listar")  # Ver = listar
def usuario_ver(id):
    usuario = Usuario.query.get_or_404(id)
    return render_template('usuarios/view.html', usuario=usuario)

@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Usuários - Excluir")
def usuario_excluir(id):
    u = Usuario.query.get_or_404(id)
    if u.email == 'admin@atlantica.com.br':
        return jsonify(success=False, message='Não é possível excluir o administrador principal!')
    
    db.session.delete(u)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return jsonify(success=True)


# ======================= TIPOS DE USUÁRIO =======================
@app.route('/tipos_usuario')
@login_required
@permissao_requerida("Usuários - Listar")  # Quem vê usuários, vê tipos
def tipos_usuario():
    tipos = TipoUsuario.query.order_by(TipoUsuario.tipo_usuario).all()
    return render_template('tipos_usuario/index.html', tipos=tipos)


@app.route('/tipos_usuario/form', methods=['GET', 'POST'])
@login_required
@permissao_requerida("Usuários - Criar")  # Criar tipo = criar usuário
def tipos_usuario_form():
    if request.method == 'GET':
        return redirect(url_for('tipos_usuario'))

    nome = request.form['tipo_usuario'].strip().upper()
    id_form = request.form.get('id')

    if id_form:
        if not tem_permissao(funcao="Usuários - Editar"):
            return jsonify(success=False, message='Sem permissão para editar tipo de usuário!')
        t = TipoUsuario.query.get_or_404(int(id_form))
        if TipoUsuario.query.filter(TipoUsuario.tipo_usuario == nome, TipoUsuario.id != int(id_form)).first():
            return jsonify(success=False, message='Já existe um tipo com esse nome!')
        t.tipo_usuario = nome
    else:
        t = TipoUsuario(tipo_usuario=nome)
        if TipoUsuario.query.filter_by(tipo_usuario=nome).first():
            return jsonify(success=False, message='Já existe!')
        db.session.add(t)

    db.session.commit()
    return jsonify(success=True)


@app.route('/tipos_usuario/excluir/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Usuários - Excluir")
def tipo_usuario_excluir(id):
    t = TipoUsuario.query.get_or_404(id)
    if t.usuarios:
        return jsonify(success=False, message='Tipo em uso por usuários!')
    db.session.delete(t)
    db.session.commit()
    return jsonify(success=True)

# ======================= CONSULTAS SEM NIVEL DE ACESSO =======================
@app.route('/api/verificar_cnpj_disponivel/<cnpj>')
def verificar_cnpj_disponivel(cnpj):
    cnpj = ''.join(filter(str.isdigit, str(cnpj)))
    
    if len(cnpj) != 14:
        return jsonify(bloqueado=True, motivo="CNPJ deve ter 14 dígitos")

    cnpj_mask = mascarar_cnpj(cnpj)

    try:
        # 1. Tem reserva ATIVA?
        reserva_ativa = (
            db.session.query(Reserva)
            .join(Cliente)
            .filter(Cliente.cnpj == cnpj_mask)
            .filter(Reserva.status == 'ATIVA')           # ajuste conforme sua tabela
            # .filter(Reserva.ativo == True)
            # .filter(Reserva.data_cancelamento.is_(None))
            # .filter(Reserva.data_exclusao.is_(None))
            .first()
        )
        
        if reserva_ativa:
            return jsonify(bloqueado=True, motivo="Este CNPJ já possui reserva ativa")

        # 2. Tem consulta pendente?
        consulta_pendente = Consulta.query.filter_by(
            cnpj=cnpj_mask, 
            status_consulta='PENDENTE'
        ).first()
        
        if consulta_pendente:
            return jsonify(bloqueado=True, motivo="Já existe consulta PENDENTE para este CNPJ")

        # 3. Cliente existe?
        cliente = Cliente.query.filter_by(cnpj=cnpj_mask).first()
        if cliente:
            return jsonify(
                existe=True,
                cliente={
                    'empresa': cliente.empresa or '',
                    'razao_social': cliente.razao_social or '',
                    'cnpj': cliente.cnpj or '',
                    'ie': getattr(cliente, 'ie', '') or '',
                    'grupo': getattr(cliente, 'grupo', '') or '',
                    # ... demais campos
                }
            )

        return jsonify(existe=False)

    except Exception as e:
        return jsonify(error=str(e)), 500

    except Exception as e:
        # Isso vai te mostrar o erro real no console do Flask
        print("ERRO NA API CNPJ:", str(e))
        return jsonify(bloqueado=True, motivo="Erro interno. Tente novamente.")

@app.route('/api/cliente_por_cnpj/<cnpj>')
def cliente_por_cnpj(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        return jsonify(existe=False)

    cliente = Cliente.query.filter_by(cnpj=mascarar_cnpj(cnpj_limpo)).first()
    if cliente:
        return jsonify(existe=True, cliente={
            'empresa': cliente.empresa or '',
            'razao_social': cliente.razao_social or '',
            'cnpj': cliente.cnpj or '',
            'ie': cliente.ie or '',
            'grupo': cliente.grupo or '',
            'cep': cliente.cep or '',
            'logradouro': cliente.logradouro or '',
            'numero': cliente.numero or '',
            'complemento': cliente.complemento or '',
            'bairro': cliente.bairro or '',
            'cidade': cliente.cidade or '',
            'estado': cliente.estado or '',
            'nome_contato': cliente.nome_contato or '',
            'telefone_contato': cliente.telefone_contato or '',
            'email_contato': cliente.email_contato or ''
        })
    return jsonify(existe=False)

# LISTA DE CONSULTAS
from sqlalchemy import func

@app.route('/consultas')
@login_required
@permissao_requerida("Consultas - Listar")
def consultas():
    # Query base ordenada por data mais recente
    query = Consulta.query.order_by(Consulta.data_consulta.desc())

    tipo = current_user.tipo.tipo_usuario.strip().lower()

    # -------------------------------------------------
    # 1. REPRESENTANTE → vê apenas as consultas que ele criou
    # -------------------------------------------------
    if tipo == 'representante':
        query = query.filter(
            func.trim(func.upper(Consulta.nome_representante)) == current_user.nome.strip().upper()
        )

    # -------------------------------------------------
    # 2. GERENTE → vê as consultas de todos os representantes que estão sob ele
    # -------------------------------------------------
    elif tipo == 'gerente':
        # Representantes vinculados a este gerente
        reps_do_gerente = Usuario.query.filter(
            Usuario.gerente_id == current_user.id,
            Usuario.tipo.has(TipoUsuario.tipo_usuario.ilike('%representante%'))
        ).with_entities(Usuario.nome).all()

        nomes_reps = [rep.nome.strip().upper() for rep in reps_do_gerente]

        if nomes_reps:
            query = query.filter(
                func.trim(func.upper(Consulta.nome_representante)).in_(nomes_reps)
            )
        else:
            # Nenhum representante subordinado → não mostra nada
            query = query.filter(Consulta.id == 0)   # condição impossível

    # -------------------------------------------------
    # 3. ADMINISTRADOR / OUTROS → vê tudo (sem filtro)
    # -------------------------------------------------
    # Não faz nada → mantém a query original

    consultas = query.all()

    # Lista de representantes (útil para filtros na tela)
    representantes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario.ilike('%representante%'))\
        .order_by(Usuario.nome).all()

    return render_template(
        'consultas/index.html',
        consultas=consultas,
        representantes=representantes
    )


# FORMULÁRIO NOVA CONSULTA (GET)
@app.route('/consultas/form', methods=['GET'])
@login_required
def consulta_form():
    hoje = date.today().strftime('%d/%m/%Y')
    return render_template('consultas/form.html', hoje=hoje)

@app.route('/consultas/nova', methods=['POST'])
@login_required
@permissao_requerida("Consultas - Criar")
def consultas_nova():
    try:
        # === REPRESENTANTE ===
        if current_user.tipo.tipo_usuario.strip().lower() == 'representante':
            representante = current_user.nome.strip()
        else:
            representante = request.form.get('nome_representante', '').strip()

        if not representante:
            return jsonify({"success": False, "message": "Representante obrigatório"}), 400

        # === PEGA O CNPJ COM MÁSCARA DIRETO DO FORMULÁRIO ===
        cnpj_com_mascara = request.form.get('cnpj', '').strip()

        # Remove tudo que não for número (garante que está limpo)
        cnpj_numeros = ''.join(filter(str.isdigit, cnpj_com_mascara))

        # Valida se tem 14 dígitos
        if len(cnpj_numeros) != 14:
            return jsonify({"success": False, "message": "CNPJ inválido"}), 400

        # === APLICA A MÁSCARA PARA SALVAR NO BANCO ===
        cnpj_formatado = f"{cnpj_numeros[:2]}.{cnpj_numeros[2:5]}.{cnpj_numeros[5:8]}/{cnpj_numeros[8:12]}-{cnpj_numeros[12:]}"
        # Resultado: 12.345.678/0001-99

        # === CRIA A CONSULTA ===
        consulta = Consulta(
            empresa=request.form.get('empresa', '').strip().upper(),
            razao_social=request.form.get('razao_social', '').strip().upper(),
            cnpj=cnpj_formatado,           # ← AQUI AGORA VAI COM MÁSCARA
            ie=request.form.get('ie', '').strip().upper(),
            grupo=request.form.get('grupo', '').strip().upper(),
            cep=request.form.get('cep', '').replace('-', ''),
            logradouro=request.form.get('logradouro', '').strip().upper(),
            numero=request.form.get('numero', '').strip(),
            complemento=request.form.get('complemento', '').strip().upper(),
            bairro=request.form.get('bairro', '').strip().upper(),
            cidade=request.form.get('cidade', '').strip().upper(),
            estado=request.form.get('estado', '').strip().upper(),
            nome_contato=request.form.get('nome_contato', '').strip().upper(),
            telefone_contato=request.form.get('telefone_contato', '').strip(),
            email_contato=request.form.get('email_contato', '').strip().lower(),
            nome_representante=representante,
            status_consulta='PENDENTE'
        )

        db.session.add(consulta)
        db.session.commit()

        return jsonify({"success": True, "message": "Consulta enviada com sucesso!"})

    except Exception as e:
        db.session.rollback()
        print("ERRO AO CRIAR CONSULTA:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Erro ao salvar consulta"}), 500



# APROVAR CONSULTA
@app.route('/consultas/aprovar/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Consultas - Aprovar")
def aprovar_consulta(id):
    consulta = Consulta.query.get_or_404(id)

    if consulta.status_consulta != 'PENDENTE':
        return jsonify(success=False, message="Esta consulta já foi processada!")

    try:
        cliente = Cliente.query.filter_by(cnpj=consulta.cnpj).first()

        if cliente:
            cliente.nome_representante = consulta.nome_representante
            cliente.status_cliente = 'RESERVADO'
            acao = "atualizado"
        else:
            cliente = Cliente(
                empresa=consulta.empresa,
                razao_social=consulta.razao_social or None,
                cnpj=consulta.cnpj,
                ie=consulta.ie or None,
                grupo=consulta.grupo or None,
                cep=consulta.cep,
                logradouro=consulta.logradouro,
                numero=consulta.numero,
                complemento=consulta.complemento,
                bairro=consulta.bairro,
                cidade=consulta.cidade,
                estado=consulta.estado,
                nome_contato=consulta.nome_contato,
                telefone_contato=consulta.telefone_contato,
                email_contato=consulta.email_contato,
                nome_representante=consulta.nome_representante,
                status_cliente='RESERVADO',
                data_cadastro=datetime.utcnow()
            )
            db.session.add(cliente)
            acao = "cadastrado"

        db.session.flush()

        # Reserva
        reserva = Reserva.query.filter_by(cliente_id=cliente.id).first()
        hoje = date.today()
        fim = hoje + timedelta(days=365)

        if reserva:
            reserva.representante = consulta.nome_representante
            reserva.data_inicio = hoje
            reserva.data_fim = fim
            reserva.status = 'ATIVA'
        else:
            nova_reserva = Reserva(
                cliente_id=cliente.id,
                empresa=cliente.empresa,
                cnpj=cliente.cnpj,
                representante=consulta.nome_representante,
                data_inicio=hoje,
                data_fim=fim,
                status='ATIVA'
            )
            db.session.add(nova_reserva)

        # Finaliza consulta
        consulta.status_consulta = 'APROVADO'
        consulta.data_aprovacao = hoje

        db.session.commit()

        return jsonify(
            success=True,
            message=f"Cliente {acao} e reserva criada!\n"
                    f"Validade até: {fim.strftime('%d/%m/%Y')}"
        )

    except Exception as e:
        db.session.rollback()
        print("ERRO AO APROVAR:", str(e))
        return jsonify(success=False, message="Erro ao aprovar consulta.")


# REJEITAR CONSULTA
@app.route('/consultas/rejeitar/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Consultas - Aprovar")  # Quem aprova, rejeita
def rejeitar_consulta(id):
    c = Consulta.query.get_or_404(id)
    if c.status_consulta != 'PENDENTE':
        return jsonify(success=False, message="Consulta já processada.")
    
    c.status_consulta = 'REJEITADO'
    c.motivo_negativa = request.json.get('motivo', 'Sem motivo informado')
    db.session.commit()
    return jsonify(success=True, message='Consulta rejeitada.')


# VER CONSULTA
@app.route('/consultas/ver/<int:id>')
@login_required
@permissao_requerida("Consultas - Listar")
def ver_consulta(id):
    consulta = Consulta.query.get_or_404(id)
    reserva = Reserva.query.join(Cliente).filter(Cliente.cnpj == consulta.cnpj).first()
    return render_template('consultas/view.html', consulta=consulta, reserva=reserva)


# ======================= CLIENTES =======================

from sqlalchemy import func, or_

@app.route('/clientes')
@login_required
@permissao_requerida("Clientes - Listar")
def clientes():
    # Query base
    query = Cliente.query.order_by(Cliente.empresa)

    tipo = current_user.tipo.tipo_usuario.strip().lower()

    # 1. REPRESENTANTE → vê só os clientes em que ele é o representante
    if tipo == 'representante':
        query = query.filter(
            func.trim(func.upper(Cliente.nome_representante)) == current_user.nome.strip().upper()
        )

    # 2. GERENTE → vê os clientes dos representantes que têm ele como gerente_id
    elif tipo == 'gerente':
        # Busca todos os representantes subordinados ao gerente logado
        representantes_do_gerente = Usuario.query.filter(
            Usuario.gerente_id == current_user.id,
            Usuario.tipo.has(TipoUsuario.tipo_usuario.ilike('%representante%'))
        ).with_entities(Usuario.nome).all()

        nomes_representantes = [rep.nome.strip().upper() for rep in representantes_do_gerente]

        if nomes_representantes:
            query = query.filter(
                func.trim(func.upper(Cliente.nome_representante)).in_(nomes_representantes)
            )
        else:
            # Nenhum representante vinculado → não mostra nenhum cliente
            query = query.filter(Cliente.id == 0)  # condição impossível

    # 3. ADMINISTRADOR ou qualquer outro tipo → vê tudo (sem filtro adicional)

    clientes = query.all()

    # Lista de representantes (geralmente usada no filtro da tela)
    representantes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario.ilike('%representante%'))\
        .order_by(Usuario.nome).all()

    return render_template(
        'clientes/index.html',
        clientes=clientes,
        representantes=representantes
    )

@app.route('/clientes/form', methods=['GET', 'POST'])
@app.route('/clientes/form/<int:id>', methods=['GET', 'POST'])
@login_required
@permissao_requerida("Clientes - Criar")
def cliente_form(id=None):
    # Se for edição → precisa de permissão de editar
    if id and not tem_permissao("Clientes - Editar"):
        flash("Você não tem permissão para editar clientes.", "danger")
        return redirect(url_for('clientes'))

    cliente = Cliente.query.get_or_404(id) if id else None
    representantes = Usuario.query.join(TipoUsuario).filter(TipoUsuario.tipo_usuario == 'REPRESENTANTE').all()

    if request.method == 'POST':
        try:
            cnpj_raw = limpar_numero(request.form['cnpj'])
            if len(cnpj_raw) != 14:
                flash("CNPJ deve ter 14 dígitos.", "danger")
                return redirect(request.url)

            cnpj_mask = mascarar_cnpj(cnpj_raw)

            # Verifica duplicidade de CNPJ (exceto no próprio cliente sendo editado)
            existente = Cliente.query.filter(Cliente.cnpj == cnpj_mask)
            if id:
                existente = existente.filter(Cliente.id != id)
            if existente.first():
                flash("Este CNPJ já está cadastrado.", "danger")
                return redirect(request.url)

            if not cliente:
                cliente = Cliente()
                db.session.add(cliente)

            # === DADOS DO CLIENTE ===
            cliente.empresa = request.form['empresa'].strip().upper()
            cliente.razao_social = request.form.get('razao_social', '').strip().upper() or None
            cliente.cnpj = cnpj_mask
            cliente.ie = request.form.get('ie', '').strip().upper() or None
            cliente.grupo = request.form.get('grupo', '').strip().upper() or None
            cliente.cep = request.form.get('cep', '').strip()
            cliente.logradouro = request.form.get('logradouro', '').strip().upper()
            cliente.numero = request.form.get('numero', '').strip()
            cliente.complemento = request.form.get('complemento', '').strip().upper() or None
            cliente.bairro = request.form.get('bairro', '').strip().upper()
            cliente.cidade = request.form.get('cidade', '').strip().upper()
            cliente.estado = request.form.get('estado', '').strip().upper()
            cliente.nome_contato = request.form.get('nome_contato', '').strip().upper() or None
            cliente.telefone_contato = request.form.get('telefone_contato', '').strip()
            cliente.email_contato = request.form.get('email_contato', '').strip().lower()
            cliente.nome_representante = request.form.get('nome_representante')
            cliente.status_cliente = request.form.get('status_cliente', 'ATIVO')

            db.session.flush()  # garante que cliente.id exista

            # === RESERVA AUTOMÁTICA (só cria se não existir ativa) ===
            reserva_ativa = Reserva.query.filter_by(cliente_id=cliente.id, status='ATIVA').first()
            if not reserva_ativa:
                nova_reserva = Reserva(
                    cliente_id=cliente.id,
                    empresa=cliente.empresa,
                    cnpj=cliente.cnpj,
                    representante=cliente.nome_representante or 'NÃO INFORMADO',
                    data_inicio=date.today(),
                    data_fim=date.today() + timedelta(days=365),
                    status='ATIVA'
                )
                db.session.add(nova_reserva)

            db.session.commit()
            flash(f"Cliente {'atualizado' if id else 'cadastrado'} com sucesso!", "success")
            return redirect(url_for('clientes'))

        except Exception as e:
            db.session.rollback()
            print("ERRO AO SALVAR CLIENTE:", str(e))
            flash("Erro ao salvar cliente. Verifique os dados.", "danger")
            return redirect(request.url)

    return render_template('clientes/form.html',
                         cliente=cliente,
                         representantes=representantes)


@app.route('/clientes/view/<int:id>')
@login_required
@permissao_requerida("Clientes - Listar")
def cliente_view(id):
    cliente = Cliente.query.get_or_404(id)
    reservas = Reserva.query.filter_by(cliente_id=cliente.id).order_by(Reserva.data_inicio.desc()).all()
    return render_template('clientes/view.html', cliente=cliente, reservas=reservas)

@app.route('/clientes/delete/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Clientes - Excluir")
def cliente_delete(id):
    cliente = Cliente.query.get_or_404(id)

    try:
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Cliente e reservas vinculadas excluídos com sucesso!"
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao excluir cliente {id}: {e}")
        return jsonify({
            "success": False,
            "message": "Erro interno do servidor. Tente novamente."
        }), 500


# ======================= RESERVAS - VERSÃO FINAL OFICIAL 100% PROTEGIDA =======================

from flask import render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
from datetime import date, timedelta
import time

# ------------------------------------------------------------------
# ATUALIZA STATUS AUTOMÁTICO: VENCIDA / ATIVA
# ------------------------------------------------------------------
def atualizar_status_reservas():
    hoje = date.today()
    reservas = Reserva.query.filter(Reserva.status != 'REMOVIDA').all()
    
    for r in reservas:
        if r.data_fim and r.data_fim < hoje:
            if r.status != 'VENCIDA':
                r.status = 'VENCIDA'
                cliente = Cliente.query.get(r.cliente_id)
                if cliente:
                    cliente.status_cliente = 'VENCIDA'
        elif r.status == 'VENCIDA' and r.data_fim and r.data_fim >= hoje:
            r.status = 'ATIVA'
            cliente = Cliente.query.get(r.cliente_id)
            if cliente:
                cliente.status_cliente = 'RESERVADO'
    
    db.session.commit()

# ------------------------------------------------------------------
# LISTAGEM PRINCIPAL
# ------------------------------------------------------------------
from sqlalchemy import func

@app.route('/reservas')
@login_required
@permissao_requerida("Reservas - Listar")
def reservas():
    cache_buster = int(time.time())
    atualizar_status_reservas()
    
    query = Reserva.query.order_by(
        Reserva.status.asc(),
        Reserva.data_inicio.desc()
    )

    

    tipo = current_user.tipo.tipo_usuario.strip().lower()

    # 1. REPRESENTANTE → vê só as próprias
    if tipo == 'representante':
        query = query.filter(
            func.trim(func.upper(Reserva.representante)) == current_user.nome.strip().upper()
        )

    # 2. GERENTE → vê as reservas dos representantes que têm ele como gerente_id
    elif tipo == 'gerente':
        # Busca todos os representantes que têm o ID do gerente logado
        representantes_do_gerente = Usuario.query.filter(
            Usuario.gerente_id == current_user.id,
            Usuario.tipo.has(TipoUsuario.tipo_usuario.ilike('%representante%'))
        ).all()

        nomes_representantes = [rep.nome.strip().upper() for rep in representantes_do_gerente]

        if nomes_representantes:
            query = query.filter(
                func.trim(func.upper(Reserva.representante)).in_(nomes_representantes)
            )
        else:
            # Se não tiver nenhum representante vinculado, não mostra nada
            query = query.filter(Reserva.id == 0)

    # 3. ADMINISTRADOR (ou qualquer outro) → vê tudo
    # Sem filtro

    reservas = query.all()

    representantes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario.ilike('%representante%'))\
        .order_by(Usuario.nome).all()

    return render_template(
        'reservas/index.html',
        reservas=reservas,
        representantes=representantes,
        cache_buster=cache_buster
    )

# ------------------------------------------------------------------
# API DE BUSCA
# ------------------------------------------------------------------
@app.route('/api/clientes_busca')
@login_required
@permissao_requerida("Reservas - Listar")
def api_clientes_busca():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    q_upper = q.upper()
    q_cnpj = ''.join(filter(str.isdigit, q))

    clientes = Cliente.query.filter(
        db.or_(
            Cliente.empresa.ilike(f'%{q_upper}%'),
            Cliente.cnpj.contains(q_cnpj)
        )
    ).limit(15).all()

    clientes_ids = [c.id for c in clientes]
    reservas_ativas = db.session.query(Reserva.cliente_id, Reserva.id)\
        .filter(Reserva.cliente_id.in_(clientes_ids), Reserva.status == 'ATIVA')\
        .all()

    reservas_map = {r.cliente_id: r.id for r in reservas_ativas}

    resultado = []
    for c in clientes:
        reserva_id = reservas_map.get(c.id)
        resultado.append({
            'id': c.id,
            'empresa': c.empresa,
            'cnpj': c.cnpj,
            'cidade': c.cidade or '',
            'estado': c.estado or '',
            'nome_representante': c.nome_representante or '',
            'tem_reserva_ativa': reserva_id is not None,
            'reserva_id': reserva_id
        })

    return jsonify(resultado)

# ------------------------------------------------------------------
# FORMULÁRIOS
# ------------------------------------------------------------------
@app.route('/reserva_form')
@login_required
@permissao_requerida("Reservas - Criar")
def reserva_form():
    representantes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario == 'REPRESENTANTE').all()
    return render_template('reservas/form.html', reserva=None, representantes=representantes)

@app.route('/reserva_form/<int:id>')
@login_required
@permissao_requerida("Reservas - Editar")
def reserva_form_editar(id):
    reserva = Reserva.query.get_or_404(id)
    representantes = Usuario.query.join(TipoUsuario)\
        .filter(TipoUsuario.tipo_usuario == 'REPRESENTANTE').all()
    return render_template('reservas/form.html', reserva=reserva, representantes=representantes)

# ------------------------------------------------------------------
# SALVAR RESERVA
# ------------------------------------------------------------------
@app.route('/reserva_salvar', methods=['POST'])
@app.route('/reserva_salvar/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Criar")
def reserva_salvar(id=None):
    if id and not tem_permissao("Reservas - Editar"):
        flash("Você não tem permissão para editar reservas.", "danger")
        return redirect(url_for('reservas'))

    cliente_id = request.form.get('cliente_id')
    representante = request.form.get('representante')
    data_inicio_str = request.form.get('data_inicio')
    fila_interesse = request.form.get('fila_interesse', '').strip()

    if not all([cliente_id, representante, data_inicio_str]):
        flash('Preencha todos os campos obrigatórios.', 'danger')
        return redirect(url_for('reservas'))

    try:
        cliente = Cliente.query.get_or_404(int(cliente_id))
        data_inicio = date.fromisoformat(data_inicio_str)
        data_fim = data_inicio + timedelta(days=183)
    except:
        flash('Dados inválidos.', 'danger')
        return redirect(url_for('reservas'))

    # EDIÇÃO DIRETA
    if id:
        reserva = Reserva.query.get_or_404(id)
        if reserva.cliente_id != cliente.id:
            flash('Erro de segurança.', 'danger')
            return redirect(url_for('reservas'))

        reserva.representante = representante
        reserva.data_inicio = data_inicio
        reserva.data_fim = data_fim
        reserva.fila_interesse = fila_interesse
        reserva.status = 'ATIVA'

        cliente.nome_representante = representante
        cliente.status_cliente = 'RESERVADO'
        cliente.data_reserva = data_inicio

        db.session.commit()
        flash('Reserva atualizada com sucesso!', 'success')
        return redirect(url_for('reservas'))

    # NOVA RESERVA → verifica se já tem
    reserva_existente = Reserva.query.filter_by(cliente_id=cliente.id).first()
    if reserva_existente:
        session['pendente_substituicao'] = {
            'cliente_id': cliente.id,
            'representante': representante,
            'data_inicio': data_inicio_str,
            'fila_interesse': fila_interesse,
            'reserva_id': reserva_existente.id
        }
        flash(f'O cliente <strong>{cliente.empresa}</strong> já possui reserva com '
              f'<strong>{reserva_existente.representante}</strong>. '
              f'Deseja realmente <strong>SUBSTITUIR</strong>?', 'warning')
        flash('CONFIRMAR_SUBSTITUICAO', 'info')
        return redirect(url_for('reservas'))

    # CRIA NOVA
    nova = Reserva(
        cliente_id=cliente.id,
        empresa=cliente.empresa,
        cnpj=cliente.cnpj,
        representante=representante,
        data_inicio=data_inicio,
        data_fim=data_fim,
        fila_interesse=fila_interesse,
        status='ATIVA'
    )
    db.session.add(nova)

    cliente.nome_representante = representante
    cliente.status_cliente = 'RESERVADO'
    cliente.data_reserva = data_inicio

    db.session.commit()
    flash(f'Reserva criada com sucesso para {cliente.empresa}!', 'success')
    return redirect(url_for('reservas'))

# ------------------------------------------------------------------
# CONFIRMAR SUBSTITUIÇÃO
# ------------------------------------------------------------------
@app.route('/reserva_substituir', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Criar")
def reserva_substituir():
    dados = session.pop('pendente_substituicao', None)
    if not dados:
        flash('Ação expirada.', 'danger')
        return redirect(url_for('reservas'))

    reserva = Reserva.query.get_or_404(dados['reserva_id'])
    data_inicio = date.fromisoformat(dados['data_inicio'])
    data_fim = data_inicio + timedelta(days=183)

    reserva.representante = dados['representante']
    reserva.data_inicio = data_inicio
    reserva.data_fim = data_fim
    reserva.fila_interesse = dados['fila_interesse']
    reserva.status = 'ATIVA'

    cliente = Cliente.query.get(reserva.cliente_id)
    cliente.nome_representante = dados['representante']
    cliente.status_cliente = 'RESERVADO'
    cliente.data_reserva = data_inicio

    db.session.commit()
    flash(f'Reserva substituída com sucesso! Agora {cliente.empresa} está com {dados["representante"]}.', 'success')
    return redirect(url_for('reservas'))

# ------------------------------------------------------------------
# RENOVAR / REMOVER
# ------------------------------------------------------------------
@app.route('/reservas/renovar/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Renovar")
def reserva_renovar(id):
    reserva = Reserva.query.get_or_404(id)
    cliente = Cliente.query.get(reserva.cliente_id)
    hoje = date.today()
    
    reserva.data_inicio = hoje
    reserva.data_fim = hoje + timedelta(days=183)
    reserva.status = 'ATIVA'
    
    if cliente:
        cliente.nome_representante = reserva.representante
        cliente.status_cliente = 'RESERVADO'
        cliente.data_reserva = hoje
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/reservas/renovar_massa', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Renovar")
def reserva_renovar_massa():
    data = request.get_json()
    ids = data.get('ids', []) if data else []

    if not ids:
        return jsonify({'success': False, 'message': 'Nenhum ID recebido'}), 400

    hoje = date.today()
    renovadas = 0

    for rid in ids:
        r = Reserva.query.get(rid)
        if not r:
            continue

        # === AQUI ESTÁ A MUDANÇA PRINCIPAL ===
        # Antes: só renovava se NÃO fosse REMOVIDA
        # Agora: renova SEMPRE, não importa o status atual

        r.data_inicio = hoje
        r.data_fim = hoje + timedelta(days=183)  # 6 meses ≈ 183 dias
        r.status = 'ATIVA'  # volta a estar ativa

        # Atualiza o cliente associado (se existir)
        if r.cliente_id:
            c = Cliente.query.get(r.cliente_id)
            if c:
                c.nome_representante = r.representante
                c.status_cliente = 'RESERVADO'
                c.data_reserva = hoje

        renovadas += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{renovadas} reserva(s) renovada(s) com sucesso!'
    })

@app.route('/reservas/remover/<int:id>', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Remover")
def reserva_remover(id):
    reserva = Reserva.query.get_or_404(id)
    cliente = Cliente.query.get(reserva.cliente_id)
    reserva.status = 'REMOVIDA'
    reserva.data_fim = None
    if cliente:
        cliente.nome_representante = None
        cliente.status_cliente = 'SEM RESERVA'
        cliente.data_reserva = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/reservas/remover_massa', methods=['POST'])
@login_required
@permissao_requerida("Reservas - Remover")
def reserva_remover_massa():
    ids = request.get_json().get('ids', [])
    for rid in ids:
        r = Reserva.query.get(rid)
        if r:
            c = Cliente.query.get(r.cliente_id)
            r.status = 'REMOVIDA'
            r.data_fim = None
            if c:
                c.nome_representante = None
                c.status_cliente = 'SEM RESERVA'
                c.data_reserva = None
    db.session.commit()
    return jsonify({'success': True})

# ------------------------------------------------------------------
# NO CACHE + HOJE()
# ------------------------------------------------------------------
@app.after_request
def add_no_cache(response):
    if request.path.startswith('/reservas'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response

@app.context_processor
def utility_processor():
    def hoje():
        return date.today()
    return dict(hoje=hoje)

# =============================================== ALTERAR SENHA — LIVRE PARA TODOS OS USUÁRIOS LOGADOS ==============
@app.route('/alterar_senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    """
    Qualquer usuário logado pode alterar a própria senha.
    Não precisa de permissão no sistema de níveis — é um direito básico.
    """
    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']

        # 1. Verifica senha atual
        if not check_password_hash(current_user.senha_hash, senha_atual):
            flash('Senha atual incorreta!', 'danger')
            return redirect(url_for('alterar_senha'))

        # 2. Confirmação
        if nova_senha != confirmar_senha:
            flash('As novas senhas não coincidem!', 'danger')
            return redirect(url_for('alterar_senha'))

        # 3. Tamanho mínimo
        if len(nova_senha) < 6:
            flash('A nova senha deve ter no mínimo 6 caracteres!', 'danger')
            return redirect(url_for('alterar_senha'))

        # 4. Tudo certo → altera
        current_user.senha_hash = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('alterar_senha.html')

#============== CRIA ADMIN AUTOMÁTICO ==============
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email='admin@atlantica.com.br').first():
        admin = Usuario(
            nome='ADMINISTRADOR',
            email='admin@atlantica.com.br',
            senha_hash=generate_password_hash('admin123'),
            nivel_acesso=0,
            status='ATIVO'
        )
        db.session.add(admin)
        db.session.commit()
        print("\nADMIN CRIADO!")
        print("Email: admin@atlantica.com.br")
        print("Senha: admin123\n")


#============== NÍVEIS DE ACESSO (SÓ ADMIN) ==============
@app.route('/niveis_acesso')
@login_required
def niveis_acesso():
    if current_user.nivel_acesso != 0:
        flash('Acesso negado! Apenas Administrador.', 'danger')
        return redirect(url_for('dashboard'))

    config = Configuracao.query.first()
    permissoes_salvas = json.loads(config.permissoes) if config and config.permissoes else {}

    funcoes_sistema = [
        "Dashboard",
        "Consultas - Listar",
        "Consultas - Criar",
        "Consultas - Aprovar",
        "Clientes - Listar",
        "Clientes - Criar",
        "Clientes - Editar",
        "Reservas - Listar",
        "Reservas - Criar",
        "Reservas - Editar",
        "Reservas - Renovar",
        "Reservas - Remover",
        "Usuários - Listar",
        "Usuários - Criar",
        "Usuários - Editar",
        "Usuários - Excluir",
        "Relatórios",
        "Configurações"
    ]

    return render_template(
        'admin/niveis_acesso.html',
        permissoes=permissoes_salvas,
        niveis=range(0, 11),
        funcoes=funcoes_sistema
    )

@app.route('/niveis_acesso/salvar', methods=['POST'])
@login_required
def niveis_acesso_salvar():
    if current_user.nivel_acesso != 0:
        return jsonify(success=False, message='Acesso negado.')

    dados = request.get_json()
    if not isinstance(dados, dict):
        return jsonify(success=False, message='Dados inválidos.')

    try:
        config = Configuracao.query.first()
        if not config:
            config = Configuracao()
            db.session.add(config)
        config.permissoes = json.dumps(dados, ensure_ascii=False)
        db.session.commit()
        return jsonify(success=True, message='Permissões salvas!')
    except Exception as e:
        db.session.rollback()
        print("ERRO SALVAR PERMISSÕES:", e)
        return jsonify(success=False, message='Erro interno.')


#============== INJEÇÃO ÚNICA E PERFEITA NO JINJA (APAGUE TODOS OS OUTROS!) ==============
@app.context_processor
def inject_everything():
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    def tem_permissao(funcao=None):
        if not current_user.is_authenticated:
            return False
        if current_user.nivel_acesso == 0:  # Admin vê tudo
            return True
        if not funcao:
            return False
        
        config = Configuracao.query.first()
        if not config or not config.permissoes:
            return False
        
        try:
            permissoes = json.loads(config.permissoes)
            return funcao in permissoes.get(str(current_user.nivel_acesso), [])
        except:
            return False

    def url_safe(endpoint, **vals):
        return url_for(endpoint, **vals) if endpoint in endpoints else '#'

    def endpoint_existe(nome):
        return nome in endpoints

    return dict(
        tem_permissao=tem_permissao,
                url_safe=url_safe,
                endpoint_existe=endpoint_existe)

#============== RODAR O APP ==============
if __name__ == '__main__':
    app.run(debug=True, port=5000)