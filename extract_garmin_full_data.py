import os
import time
import shutil
from datetime import datetime, timedelta
import pandas as pd
from garminconnect import Garmin
import garth

TOKEN_PATH = "./garmin_tokens"

def pedir_codigo_mfa():
    """Esta función se activa solo si Garmin pide el PIN de seguridad."""
    return input("\n[!] Garmin requiere verificación. Introduce el código de 6 dígitos: ")

def get_garmin_client():
    print("[+] Intentando conectar a Garmin Connect...")
    
    # 1. Intentar usar la sesión guardada
    if os.path.exists(TOKEN_PATH):
        try:
            garth.client.load(TOKEN_PATH)
            api = Garmin()
            # Hacemos una prueba rápida para asegurar que el token es válido de verdad
            api.get_full_name() 
            print("[+] ¡Sesión restaurada mediante tokens locales con éxito!")
            return api
        except Exception:
            print("[-] Los tokens guardados han caducado. Limpiando sesión antigua automáticamente...")
            # EL SCRIPT BORRA LA CARPETA ÉL SOLO
            shutil.rmtree(TOKEN_PATH, ignore_errors=True)

    # 2. Pedir credenciales si no había sesión o si la antigua acaba de borrarse
    email = input("\nIntroduce tu correo de Garmin: ")
    password = input("Introduce tu contraseña de Garmin: ")
    
    try:
        api = Garmin(email, password, prompt_mfa=pedir_codigo_mfa)
        api.login()
        
        os.makedirs(TOKEN_PATH, exist_ok=True)
        garth.client.dump(TOKEN_PATH)
        print("[+] ¡Inicio de sesión exitoso y tokens guardados!")
        return api
    except Exception as e:
        print(f"[-] Error crítico al iniciar sesión: {e}")
        exit()

# Inicializar cliente
api = get_garmin_client()

end_date = datetime.today().date()
start_date = end_date - timedelta(days=270)

print(f"\n[+] Extrayendo EL HISTÓRICO TOTAL desde {start_date} hasta {end_date}...")
print("[!] Nota: Se están descargando miles de registros. Tardará entre 4 y 7 minutos. Paciencia...\n")

# 1. BARRIDO MASIVO
print("[+] Descargando Peso y Composición Corporal...")
try:
    weight_data = api.get_body_composition(start_date.isoformat(), end_date.isoformat())
    if weight_data and 'dateWeightList' in weight_data:
        pd.DataFrame(weight_data['dateWeightList']).to_csv("garmin_peso.csv", index=False)
except Exception: pass

print("[+] Descargando Actividades Deportivas (Entrenamientos)...")
try:
    activities = api.get_activities_by_date(start_date.isoformat(), end_date.isoformat())
    if activities:
        pd.DataFrame(activities).to_csv("garmin_actividades.csv", index=False)
except Exception: pass

# 2. BARRIDO DIARIO (Iteración con pausa de seguridad)
sleep_records = []
stats_records = []
hrv_records = []
training_records = []
spo2_records = []
respiration_records = []

current_d = start_date
while current_d <= end_date:
    d_str = current_d.isoformat()
    print(f" -> Procesando métricas del día: {d_str}...", end='\r')
    
    try:
        stats = api.get_user_summary(d_str)
        if stats: stats_records.append(stats)
    except: pass

    try:
        s_data = api.get_sleep_data(d_str)
        if s_data and 'dailySleepDTO' in s_data: sleep_records.append(s_data['dailySleepDTO'])
    except: pass
    
    try:
        hrv = api.get_hrv_data(d_str)
        if hrv and 'hrvSummary' in hrv: hrv_records.append(hrv['hrvSummary'])
    except: pass

    try:
        training = api.get_training_status(d_str)
        if training: training_records.append(training)
    except: pass

    try:
        spo2 = api.get_spo2_data(d_str)
        if spo2: spo2_records.append(spo2)
    except: pass

    try:
        resp = api.get_respiration_data(d_str)
        if resp: respiration_records.append(resp)
    except: pass

    # Freno para Cloudflare
    time.sleep(0.5)
    current_d += timedelta(days=1)

print("\n\n[+] Guardando todos los archivos CSV...")

if stats_records: pd.DataFrame(stats_records).to_csv("garmin_resumen_diario.csv", index=False)
if sleep_records: pd.DataFrame(sleep_records).to_csv("garmin_sueno.csv", index=False)
if hrv_records: pd.DataFrame(hrv_records).to_csv("garmin_vfc.csv", index=False)
if training_records: pd.DataFrame(training_records).to_csv("garmin_training_vo2.csv", index=False)
if spo2_records: pd.DataFrame(spo2_records).to_csv("garmin_spo2.csv", index=False)
if respiration_records: pd.DataFrame(respiration_records).to_csv("garmin_respiracion.csv", index=False)

print("\n[+] ¡EXTRACCIÓN TOTAL COMPLETADA!")