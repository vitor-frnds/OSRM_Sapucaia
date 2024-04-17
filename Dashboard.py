#---------------------Bibliotecas Utilizadas---------------------

import streamlit as st
from streamlit_folium import folium_static
import folium as fl
from folium import plugins
import pandas as pd
import requests
import plotly as pl
import json

st.set_page_config(layout = 'wide',
                   page_title = 'OSRM - Sapucaia',
                   page_icon = "ppgmc-logo.png")

st.title('OSRM - Sapucaia 🚛🗑️')

st.sidebar.title('Filtros')
rotas = ["Sapucaia", "Anta", "Aparecida", "Aterro-Garagem"]
rotas_selecionadas = st.sidebar.multiselect("Escolha as rotas:", rotas)

todos_km = st.sidebar.checkbox("Todos os consumos de combustível", value = True)
if todos_km:
  km = ''
else:
  km = st.sidebar.slider("Consumo", 3.0, 4.0, None, 0.5)

#----------------------------Funções-----------------------------

# Função para gerar os mapas:
def gerarMapas(data):

  # Criando os mapas com a Folium
  map = fl.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=14)

  # Adicionando os marcadores ao mapa
  for index, row in data.iterrows():
    fl.Marker([row['latitude'], row['longitude']], popup=row['logradouro']).add_to(map)

  # Conectando as coordenadas
  fl.PolyLine(data[['latitude', 'longitude']].values, color='blue').add_to(map)

  return map

# Gerando o link do OSRM:
# Link de exemplo: https://map.project-osrm.org/?z=17&center=-21.994312%2C-42.910903&loc=-21.994048%2C-42.915773&loc=-21.993740%2C-42.908510&hl=en&alt=0&srv=0
def gerarOSRM(data):

  # URL inicial:
  OSRM_url = 'https://map.project-osrm.org/'

  # URL Zoom:
  zoom_url = '?z=15&'

  # Definindo o centro do mapa:
  center = (data.shape[0])//2
  center_url = f'center={data.at[center, "latitude"]}%2C{data.at[center, "longitude"]}&'

  # Definindo o URL com as coordenadas:
  coord_url = ''
  for index, row in data.iterrows():
        lat, lon = row['latitude'], row['longitude']
        coord_url += (f'loc={lat}%2C{lon}&')

  # URL final:
  final_url = 'hl=en&alt=0&srv=0'

  # Montando o link:
  link = ''
  link = f'{OSRM_url}{zoom_url}{center_url}{coord_url}{final_url}'
  return link

# Função para calcular o centro do dataframe:
def calcularCentro(data):
  return (data['latitude'].mean(), data['longitude'].mean())

# Função para gerar o link do JSON:
def gerarJSON(data):

  # Exemplo de URL: {url_base}13.388860,52.517037;13.397634,52.529407;13.428555,52.523219?overview=false

  url_base   = 'http://router.project-osrm.org/route/v1/driving/'
  url_coords = ''
  url_final  = '?geometries=geojson&overview=full'


  # Definindo o URL com as coordenadas:
  for index, row in data.iterrows():
        lat, lon = row['latitude'], row['longitude']
        url_coords += (f'{lon},{lat};')

  # Removendo o último ponto e vírgula
  url_coords = url_coords.rstrip(';')

  url = f'{url_base}{url_coords}{url_final}'

  return url

# Função para validar se foi possível gerar corretamente o JSON
def validarJSON(data):

  url = gerarJSON(data)

  # Fazendo a solicitação HTTP
  resposta = requests.get(url)

  # Verificando se a solicitação teve sucesso
  if resposta.status_code == 200:
    dados_rota = resposta.json()
  else:
    print(f"Falha na solicitação com código de status: {resposta.status_code}")
    return

  return dados_rota

# Função para colher o campo referente à distância e à duração total da rota:
def lerJSON(data):

  dados_rota = validarJSON(data)

  # Verificando se os dados da rota foram obtidos corretamente
  if dados_rota is not None:
    # Acessando a distância do último segmento da rota
    distancia = dados_rota['routes'][0]['distance']
    duracao   = dados_rota['routes'][0]['duration']

    return distancia, duracao
    
# Função para gerar um novo mapa com base nas coordenadas do OSRM:
def mapaJSON(data, zoom = 14):

  # Validando a requisição
  dados_mapa = validarJSON(data)

  # Extraindo as coordenadas
  coords = dados_mapa['routes'][0]['geometry']['coordinates']

  # Invertendo as coordenadas para (lat, lon)
  coords = [(lat, lon) for lon, lat in coords]

  # Centro do mapa
  centro = calcularCentro(data)

  # Criando o Mapa
  map = fl.Map(location = centro, zoom_start= zoom)

  # Conectando as coordenadas
  fl.PolyLine(coords, color = "blue", weight=2.5, opacity=1).add_to(map)

  return map

# Função para salvar o JSON link em um arquivo .json:
# (nesta função transforma o URL obtido pelo OSRM em um arquivo .json)
def salvarJSON(data):

  url = gerarJSON(data)

  # Fazendo a requisição
  resposta = requests.get(url)

  # Verificando se a solicitação teve sucesso
  if resposta.status_code == 200:
      dados_rota = resposta.json()

      # Salva os dados em um arquivo.json
      with open(f'rota_{data.name}.json', 'w') as f:
        json.dump(dados_rota, f)

  else:
    print(f"Falha na solicitação com código de status: {resposta.status_code}")
    return
  
# Gerar arquivo do VROOM:
def arquivoVROOM(data):

  # Listas para os veículos e os trabalhos
  veiculos  = [] # (Inicialmente só implementarei um veículo, por hora esta lista é inútil)
  trabalhos = []

  coord_ini = [data.longitude[0], data.latitude[0]] # Posição da Garagem
  coord_fim = [data.longitude.iloc[-1], data.latitude.iloc[-1]] # Posição do Aterro Sanitário

  # Adicionar um único veículo
  veiculo = {
      "id"   : 1,
      "start": coord_ini,
      "end"  : coord_fim,
      "steps": [
          {"type": "start"}
      ]
  }

  # Adicionando os passos
  for j in range(len(data.latitude) - 1):
    veiculo["steps"].append({"type": "job", "id": j+1})
  veiculo["steps"].append({"type": "end"})

  # Adicionando o veiculo à lista de veículos
  veiculos.append(veiculo)


  # Adicionando os "jobs" para cada coordenada
  for i in range(len(data.latitude) - 1):

    coord = [data.longitude[i], data.latitude[i]]

    trabalho = {
        "id"         : i+1,
        "description": data.logradouro[i],
        "location"   : coord
    }
    trabalhos.append(trabalho)


  # Criar o objeto do VROOM
  vroom = {
      "vehicles": veiculos,
      "jobs"    : trabalhos
  }

  # Salvar os dados em um arquivo
  with open(f'VROOM_{data.name}.json', 'w') as f:
    json.dump(vroom, f, indent = 2)

# Gerar DataFrame a partir do JSON:
def completeData(data):
  dados_rota = validarJSON(data)

  coordinates_list = dados_rota['routes'][0]['geometry']['coordinates']

  return pd.DataFrame(coordinates_list, columns=["latitude", "longitude"])

# Converter o tempo
def converter_tempo(seg):
  # Convertendo segundos em minutos e segundos
  minutos, segundos = divmod(seg, 60)

  # Convertendo minutos em horas e minutos
  horas, minutos = divmod(minutos, 60)

  if horas > 0:
    return f"{int(horas)} hora{'s' if horas > 1 else ''} e {int(minutos)} minuto{'s' if minutos > 1 else ''}"
  elif minutos > 0:
    return f"{int(minutos)} minuto{'s' if minutos > 1 else ''} e {int(segundos)} segundo{'s' if segundos > 1 else ''}"
  else:
    return f"{int(segundos)} segundo{'s' if segundos > 1 else ''}"
  
#---------------------------DataFrame----------------------------

## --- Leitura dos Dados:

# URL das planilhas:
sheet_url1 = "https://docs.google.com/spreadsheets/d/1HeFq3PTkunMfmencOt5grV3ADZ9sBJM-boqpGpbuymM/export?format=csv"
sheet_url2 = "https://docs.google.com/spreadsheets/d/1Q3JsL_9LOPb9_QKsKcvoVGrwR4MBWYBBCNplrxE957o/export?format=csv"
sheet_url3 = "https://docs.google.com/spreadsheets/d/1C64cDoJcD9r5sGzUMJAMyH8ILSPwzS5hTKwtGABtdkk/export?format=csv"

# Leitura com o Pandas
sapucaia  = pd.read_csv(sheet_url1)
anta      = pd.read_csv(sheet_url2)
aparecida = pd.read_csv(sheet_url3)

# Dataframe para calcular a distância entre o aterro e a garagem sanitário:
garagem = pd.concat([sapucaia.iloc[[-1]], sapucaia.iloc[[0]]])

## --- Tratamento dos Dados:

# Renomeando as colunas
sapucaia.rename(columns  = {'Latitude': 'latitude', 'Longitude': 'longitude', 'Logradouro': 'logradouro'}, inplace = True)
anta.rename(columns      = {'Latitude': 'latitude', 'Longitude': 'longitude', 'Logradouro': 'logradouro'}, inplace = True)
aparecida.rename(columns = {'Latitude': 'latitude', 'Longitude': 'longitude', 'Logradouro': 'logradouro'}, inplace = True)
garagem.rename(columns   = {'Latitude': 'latitude', 'Longitude': 'longitude', 'Logradouro': 'logradouro'}, inplace = True)

# Removendo a Coluna 'Obs'
sapucaia  = sapucaia.drop('Obs', axis=1)
anta      = anta.drop('Obs', axis=1)
aparecida = aparecida.drop('Obs', axis=1)
garagem   = garagem.drop('Obs', axis=1)

# Excluindo linhas com NaN:
sapucaia  = sapucaia.dropna()
anta      = anta.dropna()
aparecida = aparecida.dropna()
garagem   = garagem.dropna()

# Reordenando os indíces para que fiquem sequenciais
sapucaia  = sapucaia.reset_index(drop=True)
anta      = anta.reset_index(drop=True)
aparecida = aparecida.reset_index(drop=True)
garagem   = garagem.reset_index(drop=True)

# Definindo a coluna Longitude para o tipo 'float64'
sapucaia['longitude']  = sapucaia['longitude'].astype(float)
anta['longitude']      = anta['longitude'].astype(float)
aparecida['longitude'] = aparecida['longitude'].astype(float)
garagem['longitude']   = garagem['longitude'].astype(float)

# Definindo os nomes dos Dataframes:
sapucaia.name  = "Sapucaia"
anta.name      = "Anta"
aparecida.name = "Aparecida"
garagem.name   = "Garagem"

#---------------------Leitura das Distâncias---------------------
garagem_distancia, garagem_duracao = lerJSON(garagem)

sapucaia_distancia, sapucaia_duracao = lerJSON(sapucaia)
sapucaia_distancia += garagem_distancia
sapucaia_duracao   += garagem_duracao

anta_distancia, anta_duracao = lerJSON(anta)
anta_distancia += garagem_distancia
anta_duracao   += garagem_duracao

aparecida_distancia, aparecida_duracao = lerJSON(aparecida)
aparecida_distancia += garagem_distancia
aparecida_duracao   += garagem_duracao

# Distancia do percurso total considerando a volta do Aterro para a Garagem:
dist_total = (sapucaia_distancia + aparecida_distancia + anta_distancia)

#-----------------------Cálculo dos Custos-----------------------
# Valor do Litro de Diesel S10 no Estado do Rio de Janeiro segundo a ANP:
combustivel = 6.02

# Variaveis Rota Originais variando os Consumos
dia_orig_3 = ((dist_total/1000)/3)*combustivel
sem_orig_3 = dia_orig_3 * 6
mes_orig_3 = sem_orig_3 * 4
ano_orig_3 = mes_orig_3 * 12

dia_orig_3_5 = ((dist_total/1000)/3.5)*combustivel
sem_orig_3_5 = dia_orig_3_5 * 6
mes_orig_3_5 = sem_orig_3_5 * 4
ano_orig_3_5 = mes_orig_3_5 * 12

dia_orig_4 = ((dist_total/1000)/4)*combustivel
sem_orig_4 = dia_orig_4 * 6
mes_orig_4 = sem_orig_4 * 4
ano_orig_4 = mes_orig_4 * 12

# Variaveis Rota 1 Caminhão variando os Consumos

# Resultados com otimziação de 1 caminhão:
# Distância de Sapucaia:   21.0 km
# Distância de Aparecida:  52.4 km
# Distância de Anta:       34.9 km
# + Distância do Aterro-Garagem:  $garagem_distancia

dist_1caminhao = 21*1000 + 52.4*1000 + 34.9*1000 + 3*garagem_distancia

dia_1caminhao_3 = ((dist_1caminhao/1000)/3)*combustivel
sem_1caminhao_3 = dia_1caminhao_3 * 6
mes_1caminhao_3 = sem_1caminhao_3 * 4
ano_1caminhao_3 = mes_1caminhao_3 * 12

dia_1caminhao_3_5 = ((dist_1caminhao/1000)/3.5)*combustivel
sem_1caminhao_3_5 = dia_1caminhao_3_5 * 6
mes_1caminhao_3_5 = sem_1caminhao_3_5 * 4
ano_1caminhao_3_5 = mes_1caminhao_3_5 * 12

dia_1caminhao_4 = ((dist_1caminhao/1000)/4)*combustivel
sem_1caminhao_4 = dia_1caminhao_4 * 6
mes_1caminhao_4 = sem_1caminhao_4 * 4
ano_1caminhao_4 = mes_1caminhao_4 * 12

#----------------------Cálculo das Emissões----------------------
# Taxa para a conversão de litros para galões
tx_galao =  3.78541

# Quantidade de litros nas rotas Atuais:
litros_orig_3   = (ano_orig_3/combustivel)/tx_galao
litros_orig_3_5 = (ano_orig_3_5/combustivel)/tx_galao
litros_orig_4   = (ano_orig_4/combustivel)/tx_galao

# Quantidades de litros nas rotas otimizadas:
litros_1caminhao_3   = (ano_1caminhao_3/combustivel)/tx_galao
litros_1caminhao_3_5 = (ano_1caminhao_3_5/combustivel)/tx_galao
litros_1caminhao_4   = (ano_1caminhao_4/combustivel)/tx_galao

url = "https://www.carboninterface.com/api/v1/estimates"

headers = {
    'Authorization': 'Bearer 8ghXwBkzlc4xlnLQTcIEFA',
    'Content-Type': 'application/json'
}

data_orig_3 = {
      "name": "Otimização - 1 Caminhão - 3.5 km/l",
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_orig_3
}

data_orig_3_5 = {
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_orig_3_5
}

data_orig_4 = {
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_orig_4
}

data_1caminhao_3 = {
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_1caminhao_3
}

data_1caminhao_3_5 = {
      "name": "Otimização - 1 Caminhão - 3.5 km/l",
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_1caminhao_3_5
}

data_1caminhao_4 = {
      "type": "fuel_combustion",
      "fuel_source_type": "dfo",
      "fuel_source_unit": "gallon",
      "fuel_source_value": litros_1caminhao_4
}

# Requisições da Emissão da Rota Original

response_orig_3   = requests.post(url, headers=headers, json=data_orig_3)
response_orig_3_5 = requests.post(url, headers=headers, json=data_orig_3_5)
response_orig_4   = requests.post(url, headers=headers, json=data_orig_4)

# Requisições da Emissão da Rota Otimizada 1 Caminhão

response_1caminhao_3   = requests.post(url, headers=headers, json=data_1caminhao_3)
response_1caminhao_3_5 = requests.post(url, headers=headers, json=data_1caminhao_3_5)
response_1caminhao_4   = requests.post(url, headers=headers, json=data_1caminhao_4)

# Impressões das Emissões da Rota Original Variando o Consumo

carbon_data_orig_3   = response_orig_3.json()
carbon_data_orig_3_5 = response_orig_3_5.json()
carbon_data_orig_4   = response_orig_4.json()

# print(f"Emissão de Carbono da Rota Original - Consumo 3 km/L")
# print(json.dumps(carbon_data_orig_3, indent = 4))
# print("\n\n\n")

# print(f"Emissão de Carbono da Rota Original - Consumo 3.5 km/L")
# print(json.dumps(carbon_data_orig_3_5, indent = 4))
# print("\n\n\n")

# print(f"Emissão de Carbono da Rota Original - Consumo 4 km/L")
# print(json.dumps(carbon_data_orig_4, indent = 4))
# print("\n\n\n")


# Impressões das Emissões da Rota Otimizada com 1 Caminhão Variando o Consumo

carbon_data_1caminhao_3   = response_1caminhao_3.json()
carbon_data_1caminhao_3_5 = response_1caminhao_3_5.json()
carbon_data_1caminhao_4   = response_1caminhao_4.json()

# print(f"Emissão de Carbono da Rota Original - Consumo 3 km/L")
# print(json.dumps(carbon_data_1caminhao_3, indent = 4))
# print("\n\n\n")

# print(f"Emissão de Carbono da Rota Original - Consumo 3.5 km/L")
# print(json.dumps(carbon_data_1caminhao_3_5, indent = 4))
# print("\n\n\n")

# print(f"Emissão de Carbono da Rota Original - Consumo 4 km/L")
# print(json.dumps(carbon_data_1caminhao_4, indent = 4))
# print("\n\n\n")

#----------------------------------------------------------------


#-------------------Visualizacao no Streamlit--------------------

#Construção das abas
aba1, aba2, aba3 = st.tabs(['Rotas Atuais', 'Rotas Otimizadas', 'Comparações'])

with aba1:

  # # Criando um seletor para escolher entre as opções de rota
  # rotas = ["Sapucaia", "Anta", "Aparecida"]
  # rotas_selecionadas = st.multiselect("Escolha as rotas:", rotas)

  if not rotas_selecionadas:
    st.markdown(f"<h3>Por favor, selecione uma rota no filtro</h3>", unsafe_allow_html=True)
  else:
    for rota in rotas_selecionadas:
      col1, col2 = st.columns([1.5, 1])

      with col1:
        if rota == "Sapucaia":
          st.header("Sapucaia")
          folium_static(mapaJSON(sapucaia))
        elif rota == "Anta":
          st.header("Anta")
          folium_static(mapaJSON(anta, 15))
        elif rota == "Aparecida":
          st.header("Aparecida")
          folium_static(mapaJSON(aparecida, 15))
        elif rota == "Aterro-Garagem":
          st.header("Aterro-Garagem")
          folium_static(mapaJSON(garagem, 13))

      with col2:      
        st.write(" ")
        st.write(" ")
        st.write(" ")
        st.write(" ")
        if rota == "Sapucaia":
          st.markdown(f"<h4>Distância total percorrida:<br> {sapucaia_distancia/1000:.2f} km</h4>", unsafe_allow_html=True)
          st.markdown(f"<h4>Duração:<br> {converter_tempo(sapucaia_duracao)}</h4>", unsafe_allow_html=True)
        elif rota == "Anta":
          st.markdown(f"<h4>Distância total percorrida:<br> {anta_distancia/1000:.2f} km</h4>", unsafe_allow_html=True)
          st.markdown(f"<h4>Duração:<br> {converter_tempo(anta_duracao)}</h4>", unsafe_allow_html=True)
        elif rota == "Aparecida":
          st.markdown(f"<h4>Distância total percorrida:<br> {aparecida_distancia/1000:.2f} km</h4>", unsafe_allow_html=True)
          st.markdown(f"<h4>Duração:<br> {converter_tempo(aparecida_duracao)}</h4>", unsafe_allow_html=True)
        elif rota == "Aterro-Garagem":
          st.markdown(f"<h4>Distância total percorrida:<br> {garagem_distancia/1000:.2f} km</h4>", unsafe_allow_html=True)
          st.markdown(f"<h4>Duração:<br> {converter_tempo(garagem_duracao)}</h4>", unsafe_allow_html=True)
          st.markdown(f"<h4>Observação:<br> Estes valores já estão acrescidos nas demais rotas</h4>", unsafe_allow_html=True)
  

with aba2:

  print(2)

  # st.dataframe(sapucaia)

  st.dataframe(completeData(sapucaia))

  st.map(completeData(sapucaia))

  # st.map(sapucaia)

with aba3:
  
  col1, col2 = st.columns(2)
  
  with col1:

    st.header("Gráfico 1")
    # st.plotly_chart(fig1)

  with col2:
    # Adicione o segundo gráfico aqui
    st.header("Gráfico 2")
    # st.plotly_chart(fig2)

    # Adicione o terceiro gráfico que ocupa a linha inteira aqui
    st.header("Gráfico 3")
    # st.plotly_chart(fig3)