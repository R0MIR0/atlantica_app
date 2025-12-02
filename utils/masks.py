# utils/masks.py
import re

def mascarar_cnpj(cnpj):
    cnpj = re.sub(r'\D', '', str(cnpj))
    if len(cnpj) != 14: return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

def mascarar_cep(cep):
    cep = re.sub(r'\D', '', str(cep))
    if len(cep) != 8: return cep
    return f"{cep[:5]}-{cep[5:]}"

def mascarar_telefone(tel):
    tel = re.sub(r'\D', '', str(tel))
    if len(tel) == 11:
        return f"({tel[:2]}) {tel[2:7]}-{tel[7:]}"
    if len(tel) == 10:
        return f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"
    return tel

def limpar_numero(valor):
    return re.sub(r'\D', '', str(valor))