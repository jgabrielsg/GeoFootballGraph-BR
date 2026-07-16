import requests
from geopy.distance import geodesic

def get_osrm_route(lon_orig, lat_orig, lon_dest, lat_dest):
    """
    Consulta a API pública do OSRM para rota rodoviária.
    ATENÇÃO: O OSRM espera o formato 'lon,lat;lon,lat'
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lon_orig},{lat_orig};{lon_dest},{lat_dest}?overview=false"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('code') == 'Ok':
            distancia_km = data['routes'][0]['distance'] / 1000.0
            tempo_horas = data['routes'][0]['duration'] / 3600.0
            return distancia_km, tempo_horas
        else:
            print("Erro no roteamento:", data.get('message'))
            return None, None
    except Exception as e:
        print("Erro de conexão OSRM:", e)
        return None, None

def main():
    print("="*60)
    print("SIMULADOR DE CUSTO LOGÍSTICO: RODOVIÁRIO vs MULTIMODAL")
    print("="*60)

    # 1. COORDENADAS DOS CLUBES (Peguei valores aproximados)
    # Manaus (AM)
    clube_A = {"nome": "Manaus FC", "lat": -3.1190, "lon": -60.0217}
    # Capão da Canoa (RS)
    clube_B = {"nome": "Capão da Canoa FC", "lat": -29.7455, "lon": -50.0151}

    # 2. COORDENADAS DOS AEROPORTOS MAIS PRÓXIMOS (No futuro, o código achará isso sozinho)
    aero_A = {"nome": "Aeroporto Eduardo Gomes (MAO)", "lat": -3.0366, "lon": -60.0515}
    aero_B = {"nome": "Aeroporto Salgado Filho (POA)", "lat": -29.9935, "lon": -51.1711}

    print(f"Rota: {clube_A['nome']} (AM) -> {clube_B['nome']} (RS)\n")

    # =========================================================
    # CENÁRIO 1: APENAS RODOVIÁRIO (O "Ônibus do Sofrimento")
    # =========================================================
    print("--- CENÁRIO 1: VIAGEM 100% RODOVIÁRIA ---")
    dist_rod, tempo_rod = get_osrm_route(clube_A['lon'], clube_A['lat'], clube_B['lon'], clube_B['lat'])
    
    if dist_rod:
        print(f"Distância em estradas: {dist_rod:.2f} km")
        print(f"Tempo de viagem ininterrupto: {tempo_rod:.2f} horas (aprox. {tempo_rod/24:.1f} dias direto)")

    # =========================================================
    # CENÁRIO 2: MULTIMODAL (Ônibus -> Avião -> Ônibus)
    # =========================================================
    print("\n--- CENÁRIO 2: VIAGEM MULTIMODAL (VIA AÉREA) ---")
    
    # Trecho 1: Clube A até seu Aeroporto
    dist_t1, tempo_t1 = get_osrm_route(clube_A['lon'], clube_A['lat'], aero_A['lon'], aero_A['lat'])
    print(f"Trecho 1 (Ônibus até MAO): {dist_t1:.2f} km | {tempo_t1:.2f} horas")

    # Trecho 2: Voo MAO -> POA
    # Usamos a distância geodésica e adicionamos 15% para simular conexões e órbitas
    distancia_voo = geodesic((aero_A['lat'], aero_A['lon']), (aero_B['lat'], aero_B['lon'])).kilometers * 1.15
    tempo_voo = distancia_voo / 800.0 # Velocidade média do avião em cruzeiro (km/h)
    tempo_aeroporto = 4.0 # Horas de antecedência, check-in, embarque e desembarque
    print(f"Trecho 2 (Voo MAO-POA): {distancia_voo:.2f} km | {tempo_voo + tempo_aeroporto:.2f} horas (com check-in)")

    # Trecho 3: Aeroporto B até Clube B (Descer em POA e ir de ônibus para o litoral)
    dist_t3, tempo_t3 = get_osrm_route(aero_B['lon'], aero_B['lat'], clube_B['lon'], clube_B['lat'])
    print(f"Trecho 3 (Ônibus POA até Capão): {dist_t3:.2f} km | {tempo_t3:.2f} horas")

    # Totais Multimodal
    dist_total_multi = dist_t1 + distancia_voo + dist_t3
    tempo_total_multi = tempo_t1 + (tempo_voo + tempo_aeroporto) + tempo_t3

    print("-" * 40)
    print(f"DISTÂNCIA TOTAL MULTIMODAL: {dist_total_multi:.2f} km")
    print(f"TEMPO TOTAL MULTIMODAL: {tempo_total_multi:.2f} horas")
    
    print("\n" + "="*60)
    print("CONCLUSÃO LOGÍSTICA:")
    print(f"Fazer essa viagem de ônibus exige rodar absurdos {dist_rod:.0f} km. De avião, você viaja um")
    print(f"equivalente a {dist_total_multi:.0f} km, mas reduz o tempo de {tempo_rod:.0f} horas para apenas {tempo_total_multi:.0f} horas!")
    print("="*60)

if __name__ == "__main__":
    main()