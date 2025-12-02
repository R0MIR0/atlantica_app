# utils/helpers.py
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def calcular_fim_reserva(inicio):
    if isinstance(inicio, str):
        inicio = datetime.strptime(inicio, '%Y-%m-%d').date()
    return inicio + relativedelta(months=6) - relativedelta(days=1)

def gerar_fila_string(lista):
    if not lista: return ''
    if isinstance(lista, str):
        return lista
    return ';'.join([x.strip() for x in lista if x.strip()])