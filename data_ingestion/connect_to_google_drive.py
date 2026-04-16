"""
This is a job that checks Google Drive if some files were updates,
added, or deleted, and changes theirstatus in Google Sheets registry.
"""
import os
import pandas as pd
import gspread
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]
SERVICE_ACCOUNT_FILE = 'credentials.json'
FOLDER_ID = os.getenv("FOLDER_ID")
SHEET_ID = os.getenv("SHEET_ID")

def get_drive_service():
    """
    Connect to Google Drive API.
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_sheets_client():
    """
    Connect to Google Sheets API.
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def get_all_files_in_folder(service, folder_id, current_path=""):
    """
    This function recursively looks for all the files in drive.
    """
    all_files = []

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime, mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
 
    items = results.get('files', [])

    for item in items:
        item_path = f"{current_path}/{item['name']}".strip("/")
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            all_files.extend(get_all_files_in_folder(service, item['id'], item_path))
        else:
            item['full_path'] = item_path
            all_files.append(item)
       
    return all_files

def sync_files():
    """
    This is the main function that checks if some files in Google Drive were updated, added, or deleted.
    Next, it changes their status in Google Sheets.
    """
    service = get_drive_service()
    gc = get_sheets_client()
    sheet = gc.open_by_key(SHEET_ID).sheet1
    
    try:
        drive_files = get_all_files_in_folder(service, FOLDER_ID)
        drive_ids = {f['id']: f for f in drive_files}

        all_records = sheet.get_all_records()
        expected_cols = ['file_name', 'google_drive_id', 'last_modified_drive', 'status', 'vector_db_sync', 'access']

        if all_records:
            df = pd.DataFrame(all_records)
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None
        else:
            df = pd.DataFrame(columns=expected_cols)

        def check_deleted(row):
            if row['status'] == 'Deleted':
                return 'Deleted'
            if row['google_drive_id'] not in drive_ids:
                return 'Deleted'
            return row['status']

        if not df.empty:
            df['status'] = df.apply(check_deleted, axis=1)

        for f_id, f_data in drive_ids.items():
            mask = df['google_drive_id'] == f_id
            full_path = f_data.get('full_path', '')
            path_parts = full_path.split('/')
            access_type = path_parts[0]
  
            if not mask.any():
                new_row = {
                    'file_name': f_data['name'],
                    'google_drive_id': f_id,
                    'last_modified_drive': f_data['modifiedTime'],
                    'status': 'Pending',
                    'vector_db_sync': 'No',
                    'access': access_type
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)   

            else:
                current_idx = df.index[mask][0]
                old_date = str(df.at[current_idx, 'last_modified_drive'])
                new_date = str(f_data['modifiedTime'])
                
                if old_date != new_date:
                    print(f"Файл змінено: {f_data['name']} (Оновлюю дату)")
                    df.at[current_idx, 'last_modified_drive'] = new_date
                    df.at[current_idx, 'status'] = 'Pending'
                    df.at[current_idx, 'vector_db_sync'] = 'No'

        sheet.clear()
        data_to_save = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(data_to_save)  
        print("Sync with Google Drive was successfull")

    except Exception as e:
        print(f"ERROR: {e}")
