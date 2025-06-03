import psycopg2
import requests
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import dateutil.tz
import urllib3
from get_token import get_token
from abrir_chamado import abrir_chamado
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pg_conn = {
    'dbname': 'veeam_db',
    'user': 'Seu_usuario_DB',
    'password': 'Seu_senha_DB',
    'host': 'localhost',
    'port': 5432
}

veeam_url_api = 'URL_seu_Veeam/api/v1/'
veeam_url_token = 'URL_seu_Veeam/api/oauth2/token'
username = 'Seu_Usuario'
password = 'sua_senha'

def get_sessions(token):
    headers = {'Authorization': f'Bearer {token}', 'x-api-version': '1.2-rev0'}
    resp = requests.get(f"{veeam_url_api}sessions", headers=headers, verify=False)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    agora = datetime.now(dateutil.tz.UTC)
    cutoff = agora - timedelta(days=2)
    return [s for s in data if dateparser.isoparse(s["creationTime"]).replace(tzinfo=dateutil.tz.UTC) >= cutoff]

def get_latest_session_for_job(sessions, job_name):
    return next((s for s in sessions if s.get("name") == job_name and s.get("sessionType") in ("BackupJob", "FileBackupJob")), None)

def list_backups(token):
    headers = {'Authorization': f'Bearer {token}', 'x-api-version': '1.2-rev0'}
    resp = requests.get(f"{veeam_url_api}backups", headers=headers, verify=False)
    resp.raise_for_status()
    return resp.json().get("data", [])

def find_backup_id_for_job(backups, job_name):
    return next((b["id"] for b in backups if b.get("name") == job_name), None)

def list_backup_files(token, backup_id):
    headers = {'Authorization': f'Bearer {token}', 'x-api-version': '1.2-rev0'}
    resp = requests.get(f"{veeam_url_api}backups/{backup_id}/backupFiles", headers=headers, verify=False)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    data.sort(key=lambda x: dateparser.isoparse(x["creationTime"]), reverse=True)
    return data

def insert_backup_pg(conn, backup_data):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO backups (job_name, session_start, session_end, duration, status, message, backup_size_gb)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_name, session_start) DO NOTHING;
            """, backup_data)
        conn.commit()
        print(f"Inserido no PostgreSQL: {backup_data[0]}")
    except Exception as e:
        print(f"Erro ao inserir no PostgreSQL: {e}")

def main():
    file_backup_size = float(sys.argv[1]) if len(sys.argv) > 1 else None
    token = get_token(username, password, veeam_url_token)
    sessions = get_sessions(token)
    backups = list_backups(token)

    jobs = [
        "JOB_1",
        "JOB_2",
        "JOB_3",
        "JOB_4",
        "JOB_5"
    ]

    conn = psycopg2.connect(**pg_conn)
    descricao = []
    todos_com_sucesso = True

    for job in jobs:
        sess = get_latest_session_for_job(sessions, job)
        if not sess:
            continue

        status = sess["result"].get("result", "")
        message = sess["result"].get("message", "")
        inicio = dateparser.isoparse(sess["creationTime"])
        fim = dateparser.isoparse(sess["endTime"])
        duracao = fim - inicio

        backup_id = find_backup_id_for_job(backups, job)
        backup_size_gb = 0

        if job == "FileBackupJob" and file_backup_size:
            backup_size_gb = file_backup_size
        elif backup_id:
            files = list_backup_files(token, backup_id)
            if files:
                tam = sum(f.get("backupSize", 0) for f in files[:2]) if job == "BackupJob - CA - Archive VMs S3" else files[0].get("backupSize", 0)
                backup_size_gb = round(tam / (1024**3), 2)

        descricao.append(f"Nome: {job}\nData: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\nDuração: {duracao}\nTamanho: {backup_size_gb} GB\nStatus: {status}\n")

        if status.lower() != "success":
            todos_com_sucesso = False

        backup_data = (job, inicio, fim, duracao, status, message, backup_size_gb)
        insert_backup_pg(conn, backup_data)

    if todos_com_sucesso:
        abrir_chamado(
            project_id="Seu-Projeto-no-redmine",
            subject="[Veeam] Todos os backups foram concluídos com sucesso - [Teste de Abertura Automatizada Neto]",
            description="Lista de Jobs:\n\n" + "\n".join(descricao),
            priority_id=1
        )

    conn.close()

if __name__ == "__main__":
    main()
