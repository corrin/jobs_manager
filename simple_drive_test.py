#!/usr/bin/env python3
"""
Simple Google Drive API test - no Django required.
"""

import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

def test_drive_access():
    """Test Google Drive API access."""
    
    creds = os.getenv("GCP_CREDENTIALS")
    if not creds:
        print("❌ GCP_CREDENTIALS environment variable not set.")
        return False
    # Get credentials file path from environment
    key_file = os.getenv("GCP_CREDENTIALS")
    
    if not os.path.exists(key_file):
        print(f"❌ Credentials file not found: {key_file}")
        return False
    
    print(f"🔐 Loading credentials from: {key_file}")
    
    try:
        # Load credentials
        creds = service_account.Credentials.from_service_account_file(
            key_file, scopes=SCOPES
        )
        print("✅ Credentials loaded")
        print(f"   Service account email: {creds.service_account_email}")
        print(f"   Scopes: {list(creds.scopes)}")
        
        # Build Drive service
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Drive service created")
        
        # Test basic API access - list some files  
        print(f"\n🔍 Testing basic Drive API access...")
        try:
            results = drive_service.files().list(pageSize=20, fields="files(id, name, mimeType)").execute()
            files = results.get('files', [])
            print(f"✅ Can access Drive API - found {len(files)} files in root")
            
            jobs_manager_folder = None
            for f in files:
                print(f"   - {f['name']} ({f['id']}) - {f['mimeType']}")
                if f['name'] == 'Jobs Manager' and 'folder' in f['mimeType']:
                    jobs_manager_folder = f['id']
            
            if jobs_manager_folder:
                print(f"\n💡 Found existing 'Jobs Manager' folder: {jobs_manager_folder}")
                print(f"💡 Update CompanyDefaults to use: {jobs_manager_folder}")
        except Exception as e:
            print(f"❌ Basic Drive API failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   HTTP Status: {e.resp.status}")
                print(f"   HTTP Reason: {e.resp.reason}")
        
        # Test the original folder access
        folder_id = "1DNw8rOVNaqRuDB56yR3e4dSHxTmXGQJu"
        print(f"\n📁 Testing original folder: {folder_id}")
        
        try:
            folder = drive_service.files().get(fileId=folder_id).execute()
            print(f"✅ Original folder found: '{folder['name']}'")
            original_folder_works = True
        except Exception as e:
            print(f"❌ Original folder failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   HTTP Status: {e.resp.status}")
                print(f"   HTTP Reason: {e.resp.reason}")
                print(f"   Response content: {e.content.decode() if hasattr(e, 'content') else 'N/A'}")
            original_folder_works = False
        
        # Test the file you created
        file_id = "1ds1MwgIfRLtv1c_mbREE8H6xcRzz_yhAHHx3kKBehN0"
        print(f"\n📄 Testing your test file: {file_id}")
        
        try:
            file_info = drive_service.files().get(fileId=file_id).execute()
            print(f"✅ File found: '{file_info['name']}'")
            
            # Get parent folder from the file
            parents = file_info.get('parents', [])
            if parents:
                parent_id = parents[0]
                print(f"   Parent folder ID: {parent_id}")
                
                # Test parent folder
                try:
                    parent = drive_service.files().get(fileId=parent_id).execute()
                    print(f"✅ Parent folder: '{parent['name']}'")
                    
                    if not original_folder_works:
                        print(f"\n💡 Use this working folder ID: {parent_id}")
                    
                    # Try creating subfolder in working folder
                    print(f"\n🔨 Testing subfolder creation...")
                    test_folder = {
                        'name': 'Test Jobs Manager',
                        'parents': [parent_id],
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    
                    created = drive_service.files().create(body=test_folder).execute()
                    print(f"✅ Test folder created: {created['id']}")
                    
                    # Clean up
                    drive_service.files().delete(fileId=created['id']).execute()
                    print("🧹 Test folder deleted")
                    
                except Exception as e:
                    print(f"❌ Parent folder test failed: {e}")
                    print(f"   Error type: {type(e).__name__}")
                    if hasattr(e, 'resp'):
                        print(f"   HTTP Status: {e.resp.status}")
                        print(f"   HTTP Reason: {e.resp.reason}")
            else:
                print("   No parent folder found")
                
        except Exception as e:
            print(f"❌ File test failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   HTTP Status: {e.resp.status}")
                print(f"   HTTP Reason: {e.resp.reason}")
                print(f"   Response content: {e.content.decode() if hasattr(e, 'content') else 'N/A'}")
        
        print(f"\n🎉 SUCCESS: Google Drive API is working!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    test_drive_access()