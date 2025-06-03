
import requests
import json

# 🔐 Configurações do Redmine
REDMINE_URL = "URL_seu_Remine/issues.json"
API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Substitua pela sua chave real

HEADERS = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": API_KEY
}

def abrir_chamado(project_id, subject, description, priority_id=5):
    payload = {
        "issue": {
            "project_id": project_id,
            "subject": subject,
            "description": description,
            "priority_id": priority_id,            
            "custom_fields": [
                {
                    "id": 00,
                    "value": "Seu Ambiente"
                }
            ]
        }
    }

