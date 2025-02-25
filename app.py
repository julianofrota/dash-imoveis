import pandas as pd
import numpy as np
import json
import io
import zipfile
from datetime import datetime
import os

import plotly.express as px
from dash import Dash, dash_table, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

# Inicializa a aplicação com Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # Usado para deploy

# Injetar estilo customizado no head (para a classe .thumb-img)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .thumb-img {
                width: 50px;
                height: auto;
                transition: transform 0.2s;
                cursor: pointer;
                display: block;
                margin-left: auto;
                margin-right: auto;
            }
            .thumb-img:hover {
                transform: scale(1.5);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# --- 1. Pré-processamento dos Dados ---
# Abra o arquivo zip e leia o CSV
zip_path = 'imoveis-residencial.zip'
with zipfile.ZipFile(zip_path, 'r') as z:
    # Considerando que o zip contém apenas um arquivo CSV
    csv_filename = z.namelist()[0]
    df = pd.read_csv(z.open(csv_filename))

df.columns = df.columns.str.lower()
df['id'] = range(1, len(df) + 1)

if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'], unit='s', errors='coerce')
if 'price_value' in df.columns:
    df['price_value'] = pd.to_numeric(df['price_value'], errors='coerce')
if 'listid' in df.columns:
    df['listid'] = df['listid'].astype(str)

def parse_location(details):
    try:
        loc = json.loads(details)
        return {
            'municipality': loc.get('municipality', np.nan),
            'ddd': loc.get('ddd', np.nan),
            'neighbourhood': loc.get('neighbourhood', np.nan),
            'uf': loc.get('uf', np.nan)
        }
    except Exception:
        return {'municipality': np.nan, 'ddd': np.nan, 'neighbourhood': np.nan, 'uf': np.nan}

if 'locationdetails' in df.columns:
    df['locationdetails'] = df['locationdetails'].astype(str)
    location_parsed = df['locationdetails'].apply(parse_location)
    df['municipality'] = location_parsed.apply(lambda x: x['municipality'])
    df['ddd'] = location_parsed.apply(lambda x: x['ddd'])
    df['neighbourhood'] = location_parsed.apply(lambda x: x['neighbourhood'])
    df['uf'] = location_parsed.apply(lambda x: x['uf'])
else:
    df['municipality'] = "Desconhecido"
    df['ddd'] = "Desconhecido"
    df['neighbourhood'] = "Desconhecido"
    df['uf'] = "Desconhecido"

def parse_properties(prop_str):
    try:
        props = json.loads(prop_str)
        props_dict = {item.get("name"): item.get("value") for item in props}
        return {
            'category': props_dict.get('category', np.nan),
            'real_estate_type': props_dict.get('real_estate_type', np.nan),
            'rooms': props_dict.get('rooms', np.nan),
            'bathrooms': props_dict.get('bathrooms', np.nan),
            'garage_spaces': props_dict.get('garage_spaces', np.nan)
        }
    except Exception:
        return {'category': np.nan, 'real_estate_type': np.nan, 'rooms': np.nan,
                'bathrooms': np.nan, 'garage_spaces': np.nan}

if 'properties' in df.columns:
    df['properties'] = df['properties'].astype(str)
    props_parsed = df['properties'].apply(parse_properties)
    df['category'] = props_parsed.apply(lambda x: x['category'])
    df['real_estate_type'] = props_parsed.apply(lambda x: x['real_estate_type'])
    df['rooms'] = props_parsed.apply(lambda x: x['rooms'])
    df['bathrooms'] = props_parsed.apply(lambda x: x['bathrooms'])
    df['garage_spaces'] = props_parsed.apply(lambda x: x['garage_spaces'])
else:
    df['category'] = np.nan
    df['real_estate_type'] = np.nan
    df['rooms'] = np.nan
    df['bathrooms'] = np.nan
    df['garage_spaces'] = np.nan

df['rooms'] = pd.to_numeric(df['rooms'], errors='coerce').fillna(0)
df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce').fillna(0)
df['garage_spaces'] = pd.to_numeric(df['garage_spaces'], errors='coerce').fillna(0)

df['municipality'].fillna("Desconhecido", inplace=True)
df['ddd'].fillna("Desconhecido", inplace=True)
df['neighbourhood'].fillna("Desconhecido", inplace=True)
df['uf'].fillna("Desconhecido", inplace=True)
df['price_value'].fillna(0, inplace=True)

df = df[(df['price_value'] >= 100) & (df['price_value'] <= 10000)]

def create_thumbnail_html(url):
    if pd.isna(url) or url.strip() == "":
        return ""
    return f'<img src="{url}" class="thumb-img" />'

if 'thumbnail' in df.columns:
    df['thumbnail_link'] = df['thumbnail'].apply(create_thumbnail_html)
else:
    df['thumbnail_link'] = ""

# --- 2. Layout ---
columns_for_table = [
    {"name": "ID", "id": "id"},
    {"name": "listId", "id": "listid"},
    {"name": "Thumbnail", "id": "thumbnail_link", "type": "text", "presentation": "markdown"},
    {"name": "Subject", "id": "subject"},
    {"name": "Preço (R$)", "id": "price_value"},
    {"name": "Município", "id": "municipality"},
    {"name": "DDD", "id": "ddd"},
    {"name": "Bairro", "id": "neighbourhood"},
    {"name": "UF", "id": "uf"},
    {"name": "Categoria", "id": "category"},
    {"name": "Tipo", "id": "real_estate_type"},
    {"name": "Quartos", "id": "rooms"},
    {"name": "Banheiros", "id": "bathrooms"},
    {"name": "Vagas Garagem", "id": "garage_spaces"},
    {"name": "Data", "id": "date"}
]

# Aqui, para simplificar, usamos placeholders para filtros e resumos:
filtros_container = dbc.Container([
    dbc.Row([
        dbc.Col(html.Div("Filtros aqui..."), width=12)
    ])
], fluid=True)

resumos_container = dbc.Container([
    dbc.Row([
        dbc.Col(html.Div("Cards de resumo aqui..."), width=12)
    ])
], fluid=True)

imagem_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Visualizar Imagem")),
        dbc.ModalBody(html.Img(id="imagem-modal", src="", style={"width": "100%"})),
        dbc.ModalFooter(
            dbc.Button("Fechar", id="fechar-modal", className="ms-auto", n_clicks=0)
        ),
    ],
    id="modal-imagem",
    is_open=False,
    size="lg",
)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Dashboard OLX - Imóveis para Alugar no Amazonas",
                        className="text-center mb-4",
                        style={"font-family": "Arial", "font-weight": "bold", "color": "#2c3e50", "font-size": "3rem"}),
                width=12)
    ]),
    filtros_container,
    resumos_container,
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabela-dados',
                        columns=columns_for_table,
                        data=df.to_dict('records'),
                        style_table={'overflowY': 'scroll', 'maxHeight': '500px'},
                        filter_action="native",
                        sort_action="native",
                        style_cell={'textAlign': 'left', 'padding': '5px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        markdown_options={'html': True}
                    )
                ])
            ),
            width=12
        )
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Distribuição de Preços", className="card-title"),
                    dcc.Graph(id='grafico-precos')
                ])
            ),
            width=6
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Imóveis por Categoria", className="card-title"),
                    dcc.Graph(id='grafico-categorias')
                ])
            ),
            width=6
        )
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Preço por Bairro", className="card-title"),
                    dcc.Graph(id='grafico-preco-bairro')
                ])
            ),
            width=4
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Preço por Município", className="card-title"),
                    dcc.Graph(id='grafico-preco-municipio')
                ])
            ),
            width=4
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Preço por Categoria", className="card-title"),
                    dcc.Graph(id='grafico-preco-categoria')
                ])
            ),
            width=4
        )
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Análise Estatística", className="card-title"),
                    html.Div(id='analise-estatistica')
                ])
            ),
            width=12
        )
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(html.Button("Baixar Excel", id="botao-download", className="btn btn-primary"), width=2),
        dbc.Col(html.Button("Baixar CSV Debug", id="botao-download-csv", className="btn btn-secondary"), width=2)
    ]),
    dcc.Download(id="download-excel"),
    dcc.Download(id="download-csv"),
    imagem_modal
], fluid=True)

# --- 3. Callbacks ---
@app.callback(
    Output('tabela-dados', 'data'),
    Output('grafico-precos', 'figure'),
    Output('grafico-categorias', 'figure'),
    Output('analise-estatistica', 'children'),
    Output("total-imoveis", "children"),
    Output("preco-medio", "children"),
    Output("preco-mediano", "children"),
    Output("quartos-medios", "children"),
    Output('grafico-preco-bairro', 'figure'),
    Output('grafico-preco-municipio', 'figure'),
    Output('grafico-preco-categoria', 'figure'),
    Input('filtro-data', 'start_date'),
    Input('filtro-data', 'end_date'),
    Input('filtro-municipio', 'value'),
    Input('filtro-bairro', 'value'),
    Input('filtro-categoria', 'value'),
    Input('filtro-tipo', 'value'),
    Input('filtro-preco', 'value'),
    Input('filtro-quartos', 'value'),
    Input('filtro-banheiros', 'value'),
    Input('filtro-vagas', 'value'),
    Input('filtro-profissional', 'value'),
    Input('busca-input', 'value')
)
def atualizar_dashboard(start_date, end_date, municipios, bairros, categorias, tipos,
                        faixa_preco, faixa_quartos, faixa_banheiros, faixa_vagas,
                        profissional, busca):
    df_filtrado = df.copy()
    if start_date and end_date and df_filtrado['date'].notna().any():
        mask = (df_filtrado['date'] >= pd.to_datetime(start_date)) & (df_filtrado['date'] <= pd.to_datetime(end_date))
        df_filtrado = df_filtrado.loc[mask]
    if municipios:
        df_filtrado = df_filtrado[df_filtrado['municipality'].isin(municipios)]
    if bairros:
        df_filtrado = df_filtrado[df_filtrado['neighbourhood'].isin(bairros)]
    if categorias:
        df_filtrado = df_filtrado[df_filtrado['category'].isin(categorias)]
    if tipos:
        df_filtrado = df_filtrado[df_filtrado['real_estate_type'].isin(tipos)]
    if faixa_preco:
        df_filtrado = df_filtrado[
            (df_filtrado['price_value'] >= faixa_preco[0]) &
            (df_filtrado['price_value'] <= faixa_preco[1])
        ]
    if faixa_quartos:
        df_filtrado = df_filtrado[
            (df_filtrado['rooms'] >= faixa_quartos[0]) &
            (df_filtrado['rooms'] <= faixa_quartos[1])
        ]
    if faixa_banheiros:
        df_filtrado = df_filtrado[
            (df_filtrado['bathrooms'] >= faixa_banheiros[0]) &
            (df_filtrado['bathrooms'] <= faixa_banheiros[1])
        ]
    if faixa_vagas:
        df_filtrado = df_filtrado[
            (df_filtrado['garage_spaces'] >= faixa_vagas[0]) &
            (df_filtrado['garage_spaces'] <= faixa_vagas[1])
        ]
    if profissional is not None:
        df_filtrado = df_filtrado[df_filtrado['professionalad'] == profissional]
    if busca:
        cols_para_busca = [col for col in ['subject', 'title'] if col in df_filtrado.columns]
        if cols_para_busca:
            df_filtrado = df_filtrado[df_filtrado[cols_para_busca].apply(
                lambda row: row.astype(str).str.contains(busca, case=False).any(), axis=1)]
    
    dados_tabela = df_filtrado.to_dict('records')
    
    if len(df_filtrado) > 0:
        grafico_precos = px.histogram(df_filtrado, x="price_value",
                                      nbins=30,
                                      title="Distribuição dos Preços dos Imóveis",
                                      labels={"price_value": "Preço (R$)"},
                                      template="plotly_white")
    else:
        grafico_precos = px.histogram()
        grafico_precos.update_layout(title="Sem dados para exibir", xaxis_title="Preço (R$)")
    
    if len(df_filtrado) > 0:
        df_cat = df_filtrado.groupby('category', as_index=False).size()
        grafico_categorias = px.bar(df_cat, x="category", y="size",
                                    title="Contagem de Imóveis por Categoria",
                                    labels={"size": "Contagem", "category": "Categoria"},
                                    template="plotly_white")
    else:
        grafico_categorias = px.bar()
        grafico_categorias.update_layout(title="Sem dados para exibir")
    
    if len(df_filtrado) > 0:
        estatisticas_df = df_filtrado[['price_value', 'rooms', 'bathrooms', 'garage_spaces']].describe().round(2)
        estatisticas_df = estatisticas_df.rename(index={
            'count': 'Contagem',
            'mean': 'Média',
            'std': 'Desvio Padrão',
            'min': 'Mínimo',
            '25%': '1º Quartil',
            '50%': 'Mediana',
            '75%': '3º Quartil',
            'max': 'Máximo'
        })
        estatisticas_html = estatisticas_df.to_html(classes='table table-striped table-bordered', border=0)
        estatisticas_html = f"<div class='table-responsive'>{estatisticas_html}</div>"
    else:
        estatisticas_html = "Sem dados para exibir estatísticas."
    
    analise_estatistica_md = dcc.Markdown(estatisticas_html, dangerously_allow_html=True)
    
    total_imoveis = len(df_filtrado)
    preco_medio = np.round(df_filtrado['price_value'].mean(), 2) if total_imoveis > 0 else 0
    preco_mediano = np.round(df_filtrado['price_value'].median(), 2) if total_imoveis > 0 else 0
    quartos_medios = np.round(df_filtrado['rooms'].mean(), 2) if total_imoveis > 0 else 0
    
    if len(df_filtrado) > 0:
        grafico_preco_bairro = px.box(df_filtrado, x="neighbourhood", y="price_value",
                                      title="Preço por Bairro",
                                      labels={"neighbourhood": "Bairro", "price_value": "Preço (R$)"},
                                      template="plotly_white")
        grafico_preco_municipio = px.box(df_filtrado, x="municipality", y="price_value",
                                         title="Preço por Município",
                                         labels={"municipality": "Município", "price_value": "Preço (R$)"},
                                         template="plotly_white")
        grafico_preco_categoria = px.box(df_filtrado, x="category", y="price_value",
                                         title="Preço por Categoria",
                                         labels={"category": "Categoria", "price_value": "Preço (R$)"},
                                         template="plotly_white")
    else:
        grafico_preco_bairro = px.box()
        grafico_preco_bairro.update_layout(title="Sem dados para exibir")
        grafico_preco_municipio = px.box()
        grafico_preco_municipio.update_layout(title="Sem dados para exibir")
        grafico_preco_categoria = px.box()
        grafico_preco_categoria.update_layout(title="Sem dados para exibir")
    
    return (dados_tabela, grafico_precos, grafico_categorias, analise_estatistica_md,
            total_imoveis, preco_medio, preco_mediano, quartos_medios,
            grafico_preco_bairro, grafico_preco_municipio, grafico_preco_categoria)

@app.callback(
    Output("download-excel", "data"),
    Input("botao-download", "n_clicks"),
    State('tabela-dados', 'data'),
    prevent_initial_call=True,
)
def baixar_excel(n_clicks, dados_tabela):
    df_download = pd.DataFrame(dados_tabela)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_download.to_excel(writer, index=False, sheet_name="Dados Filtrados")
    buffer.seek(0)
    return dcc.send_bytes(buffer.getvalue(), filename="imoveis_filtrados.xlsx")

@app.callback(
    Output("download-csv", "data"),
    Input("botao-download-csv", "n_clicks"),
    State('tabela-dados', 'data'),
    prevent_initial_call=True,
)
def baixar_csv(n_clicks, dados_tabela):
    df_download = pd.DataFrame(dados_tabela)
    return dcc.send_data_frame(df_download.to_csv, filename="imoveis_filtrados_debug.csv", index=False)

@app.callback(
    Output("modal-imagem", "is_open"),
    Output("imagem-modal", "src"),
    Input("tabela-dados", "active_cell"),
    State("tabela-dados", "data"),
    Input("fechar-modal", "n_clicks"),
    State("modal-imagem", "is_open")
)
def exibir_imagem(active_cell, table_data, fechar, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, ""
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "tabela-dados" and active_cell:
        if active_cell.get("column_id") == "thumbnail_link":
            cell_value = table_data[active_cell.get("row")].get("thumbnail_link", "")
            if cell_value:
                start = cell_value.find('src="')
                if start != -1:
                    start += len('src="')
                    end = cell_value.find('"', start)
                    url = cell_value[start:end]
                    return True, url
    elif trigger == "fechar-modal":
        return False, ""
    return is_open, ""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run_server(debug=False, host='0.0.0.0', port=port)
