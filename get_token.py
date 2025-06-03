import requests
import json
import urllib3

# Desabilitar o warning de certificado SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_token(username, password, veeam_url):
    data = {
        'grant_type': 'password',
        'username': username,
        'password': password
    }

    headers = {
        'x-api-version': '1.2-rev0',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        # Requisição para obter o token
        response = requests.post(veeam_url, data=data, headers=headers, verify=False, timeout=10) #adicionado timeout

        response.raise_for_status() # Verifica se a resposta foi bem sucedida
        return response.json().get('access_token')

    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro ao obter o token: {e}")

