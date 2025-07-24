"""
Script inteligente para criar/gerenciar templates do Google Sheets.
Busca templates existentes e cria novos se necessário.
"""

import json
import os
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SERVICE_ACCOUNT_FILE = "C:\\Users\\florz\\dev\\workflow_app\\jobs_manager\\django-integrations-77c2e7c6fbfb.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    """Inicializa o serviço do Google Drive."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def find_or_create_templates_folder(service):
    """Busca ou cria a pasta 'Templates' no root do drive."""
    try:
        # Busca pasta Templates existente
        query = "name='Templates' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = (
            service.files()
            .list(q=query, fields="files(id, name, webViewLink)")
            .execute()
        )

        folders = results.get("files", [])

        if folders:
            folder = folders[0]
            print(f"📁 Pasta Templates encontrada: {folder['name']}")
            print(f"   ID: {folder['id']}")
            print(f"   Link: {folder.get('webViewLink', 'N/A')}")
            return folder

        # Cria pasta Templates se não existir
        print("📁 Criando pasta 'Templates'...")
        folder_metadata = {
            "name": "Templates",
            "mimeType": "application/vnd.google-apps.folder",
            "parents": ["root"],
        }

        folder = (
            service.files()
            .create(body=folder_metadata, fields="id, name, webViewLink")
            .execute()
        )

        print(f"✅ Pasta Templates criada: {folder['name']}")
        print(f"   ID: {folder['id']}")
        print(f"   Link: {folder.get('webViewLink', 'N/A')}")
        return folder

    except Exception as e:
        print(f"❌ Erro ao buscar/criar pasta Templates: {e}")
        return None


def search_existing_template(service, template_name):
    """Busca template existente por nome."""
    try:
        query = f"name contains '{template_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"

        results = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, webViewLink, createdTime, modifiedTime)",
            )
            .execute()
        )

        templates = results.get("files", [])

        if templates:
            print(f"📋 Templates encontrados com '{template_name}':")
            for template in templates:
                print(f"   Nome: {template['name']}")
                print(f"   ID: {template['id']}")
                print(f"   Link: {template.get('webViewLink', 'N/A')}")
                print(f"   Criado: {template.get('createdTime', 'N/A')}")
                print(f"   Modificado: {template.get('modifiedTime', 'N/A')}")
                print("-" * 50)

        return templates

    except Exception as e:
        print(f"❌ Erro ao buscar templates: {e}")
        return []


def create_template(service, folder_id, template_name, source_file_path):
    """Cria um novo template no Google Sheets."""
    try:
        print(f"📤 Uploading template '{template_name}'...")

        file_metadata = {
            "name": template_name,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id],
        }

        media = MediaFileUpload(
            source_file_path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=True,
        )

        file = (
            service.files()
            .create(
                body=file_metadata, media_body=media, fields="id, webViewLink, name"
            )
            .execute()
        )

        print(f"✅ Template criado com sucesso!")
        print(f"   Nome: {file.get('name')}")
        print(f"   ID: {file.get('id')}")
        print(f"   Link: {file.get('webViewLink')}")

        return file

    except Exception as e:
        print(f"❌ Erro ao criar template: {e}")
        return None


def save_template_info(template_data, templates_folder, existing_templates):
    """Salva informações dos templates em arquivo JSON."""
    try:
        template_info = {
            "timestamp": datetime.now().isoformat(),
            "templates_folder": {
                "id": templates_folder.get("id"),
                "name": templates_folder.get("name"),
                "link": templates_folder.get("webViewLink"),
            },
            "new_template": template_data,
            "existing_templates": existing_templates,
        }

        info_file = "template_info.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(template_info, f, indent=2, ensure_ascii=False)

        print(f"💾 Informações salvas em '{info_file}'")

    except Exception as e:
        print(f"❌ Erro ao salvar informações: {e}")


def main():
    """Função principal."""
    print("🚀 Gerenciador de Templates do Google Sheets")
    print("=" * 60)

    # Configurações
    template_name = "Quote Spreadsheet Template 2025 - Master"
    source_file = (
        "C:\\Users\\florz\\dev\\workflow_app\\jobs_manager\\quote_template.xlsx"
    )

    # Verifica se arquivo fonte existe
    if not os.path.exists(source_file):
        print(f"❌ Arquivo fonte não encontrado: {source_file}")
        return

    service = get_drive_service()

    # 1. Busca/cria pasta Templates
    templates_folder = find_or_create_templates_folder(service)
    if not templates_folder:
        return

    # 2. Busca templates existentes
    print("\n🔍 Buscando templates existentes...")
    existing_templates = search_existing_template(service, "Quote")

    # 3. Pergunta se deve criar novo template se já existem
    if existing_templates:
        response = input(
            f"\n❓ Foram encontrados {len(existing_templates)} templates existentes. Criar novo mesmo assim? (y/n): "
        )
        if response.lower() != "y":
            print("⏹️  Operação cancelada pelo usuário.")
            save_template_info(None, templates_folder, existing_templates)
            return

    # 4. Cria novo template
    print(f"\n📋 Criando novo template...")
    new_template = create_template(
        service, templates_folder["id"], template_name, source_file
    )

    if new_template:
        # 5. Salva informações
        save_template_info(new_template, templates_folder, existing_templates)

        print("\n" + "=" * 60)
        print("✅ RESUMO DA OPERAÇÃO")
        print(f"📁 Pasta Templates: {templates_folder['id']}")
        print(f"📋 Novo Template: {new_template['id']}")
        print(f"🔗 Link do Template: {new_template['webViewLink']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
