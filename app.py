import dash
from dash import dcc, html, dash_table, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import os
import base64
from datetime import datetime

# =====================================================
# CONFIGURATION INITIALE
# =====================================================

FICHIER_DONNEES = "mon_suivi_general.csv"
DOSSIER_FICHIERS = "fichiers_chantier"
LISTE_VILLAS = [f"Villa {i}" for i in range(1, 109)]
LISTE_TACHES = [
    "1. Réception des axes",
    "2. Réception fond de fouille",
    "3. Réception coffrage et ferraillage semelles",
    "4. Réception béton des semelles (Labo)"
]

# Créer le dossier de fichiers s'il n'existe pas
if not os.path.exists(DOSSIER_FICHIERS):
    os.makedirs(DOSSIER_FICHIERS)

# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

def charger_donnees():
    if os.path.exists(FICHIER_DONNEES):
        df = pd.read_csv(FICHIER_DONNEES, index_col=0)
    else:
        df = pd.DataFrame(index=LISTE_TACHES, columns=LISTE_VILLAS)
        df = df.fillna("À faire")
        df.to_csv(FICHIER_DONNEES)
    return df

def sauvegarder_donnees(df):
    df.to_csv(FICHIER_DONNEES)

def get_color_for_status(status):
    colors = {
        'OK': '#d4edda',
        'Non Conforme': '#f8d7da',
        'En cours': '#fff3cd',
        'À faire': '#ffffff'
    }
    return colors.get(status, '#ffffff')

def sauvegarder_fichier(content, filename, tache, villa, type_doc):
    """Sauvegarde un fichier uploadé"""
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    
    # Nettoyer le nom
    extension = filename.split('.')[-1]
    nom_propre = f"{tache}_{villa}_{type_doc}".replace(" ", "_").replace(".", "")
    nom_final = f"{nom_propre}.{extension}"
    
    chemin_complet = os.path.join(DOSSIER_FICHIERS, nom_final)
    
    with open(chemin_complet, 'wb') as f:
        f.write(decoded)
    
    return nom_final

def fichier_existe(tache, villa, type_doc):
    """Vérifie si un fichier existe pour cette tâche/villa"""
    nom_base = f"{tache}_{villa}_{type_doc}".replace(" ", "_").replace(".", "")
    for ext in ['pdf', 'png', 'jpg', 'jpeg']:
        chemin = os.path.join(DOSSIER_FICHIERS, f"{nom_base}.{ext}")
        if os.path.exists(chemin):
            return chemin
    return None

# =====================================================
# INITIALISATION DE L'APP DASH
# =====================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Suivi Chantier Noria"
server = app.server  # Pour déploiement avec gunicorn

# =====================================================
# LAYOUT PRINCIPAL
# =====================================================

app.layout = dbc.Container([
    
    # Store pour garder les sélections
    dcc.Store(id='selected-cell', data={'row': 0, 'column': 0}),
    dcc.Store(id='is-admin', data=False),
    dcc.Store(id='current-page', data='tableau'),
    
    # Titre et Navigation
    dbc.Row([
        dbc.Col([
            html.H1("🏗️ Suivi Chantier Noria - 108 Villas", className="text-center mb-4 mt-3")
        ])
    ]),
    
    # Sidebar Navigation
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🗂️ Navigation", className="mb-3"),
                    html.Hr(),
                    html.H6("🔒 Espace Ingénieur"),
                    dbc.Input(id="password-input", type="password", placeholder="Mot de passe Admin", className="mb-2"),
                    html.Div(id="admin-status", className="mb-3"),
                    html.Hr(),
                    dbc.RadioItems(
                        id="menu-choice",
                        options=[
                            {"label": "📊 Tableau de Suivi Général", "value": "tableau"},
                            {"label": "📁 Dossier de démarrage", "value": "dossier"},
                            {"label": "📂 Suivi de chaque tâche", "value": "suivi"}
                        ],
                        value="tableau"
                    )
                ])
            ], className="sticky-top")
        ], width=2),
        
        # Contenu Principal
        dbc.Col([
            html.Div(id="main-content")
        ], width=10)
    ])
    
], fluid=True, style={'backgroundColor': '#f8f9fa'})

# =====================================================
# CALLBACKS
# =====================================================

# Vérification du mot de passe admin
@app.callback(
    [Output('is-admin', 'data'),
     Output('admin-status', 'children')],
    Input('password-input', 'value')
)
def check_password(password):
    if password == "Noria2026":
        return True, dbc.Alert("Mode Édition Activé ✅", color="success", className="p-2")
    else:
        return False, dbc.Alert("Mode Lecture Seule 👀", color="info", className="p-2")

# Gestion du contenu principal selon le menu
@app.callback(
    Output('main-content', 'children'),
    [Input('menu-choice', 'value'),
     Input('is-admin', 'data'),
     Input('selected-cell', 'data')]
)
def update_main_content(page, is_admin, selected_cell):
    if page == "tableau":
        return create_tableau_page(is_admin, selected_cell)
    elif page == "dossier":
        return create_dossier_page()
    else:
        return create_suivi_page()

def create_tableau_page(is_admin, selected_cell):
    """Crée la page du tableau principal"""
    df = charger_donnees()
    
    # Préparer les données pour le tableau Dash
    table_data = []
    for idx, tache in enumerate(LISTE_TACHES):
        row = {'Tâche': tache}
        for villa in LISTE_VILLAS:
            row[villa] = df.at[tache, villa]
        table_data.append(row)
    
    # Créer les colonnes avec style conditionnel
    columns = [{'name': 'Tâche', 'id': 'Tâche', 'editable': False}]
    for villa in LISTE_VILLAS:
        columns.append({'name': villa, 'id': villa, 'editable': False})
    
    # Style conditionnel pour les cellules
    style_data_conditional = []
    for villa in LISTE_VILLAS:
        for status, color in [('OK', '#d4edda'), ('Non Conforme', '#f8d7da'), 
                              ('En cours', '#fff3cd'), ('À faire', '#ffffff')]:
            style_data_conditional.append({
                'if': {
                    'filter_query': f'{{{villa}}} = "{status}"',
                    'column_id': villa
                },
                'backgroundColor': color,
                'fontWeight': 'bold' if status in ['OK', 'Non Conforme'] else 'normal'
            })
    
    # Récupérer la tâche et villa sélectionnées
    tache_idx = selected_cell.get('row', 0)
    villa_idx = selected_cell.get('column', 0)
    tache_select = LISTE_TACHES[tache_idx]
    villa_select = LISTE_VILLAS[villa_idx]
    
    return html.Div([
        # Le tableau
        html.Div([
            dbc.Alert("👇 Cliquez sur une case pour voir les détails en bas (scroll automatique).", color="info"),
            dash_table.DataTable(
                id='datatable-interactivity',
                columns=columns,
                data=table_data,
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'center',
                    'padding': '10px',
                    'fontSize': '14px'
                },
                style_header={
                    'backgroundColor': '#f0f2f6',
                    'fontWeight': 'bold',
                    'fontSize': '15px',
                    'color': '#1f77b4'
                },
                style_data_conditional=style_data_conditional,
                cell_selectable=True,
                page_size=10
            )
        ], id='table-container'),
        
        # Ancre pour le scroll
        html.Div(id='inspecteur-ancre', style={'marginTop': '30px'}),
        
        # Zone de détails (Inspecteur)
        html.Div([
            create_inspecteur_box(tache_select, villa_select, is_admin)
        ], id='inspecteur-box')
    ])

def create_inspecteur_box(tache, villa, is_admin):
    """Crée la boîte de détails avec documents"""
    df = charger_donnees()
    statut_actuel = df.at[tache, villa]
    
    # Partie documents selon la tâche
    if "Réception des axes" in tache:
        docs_content = html.Div([
            dbc.RadioItems(
                id='doc-type-radio',
                options=[
                    {"label": "Archi", "value": "Archi"},
                    {"label": "Topo", "value": "Topo"}
                ],
                value="Archi",
                inline=True,
                className="mb-2"
            ),
            html.Div(id='docs-buttons-axes')
        ])
    elif "fond de fouille" in tache:
        docs_content = html.Div([
            dbc.Button(f"📄 Document Unique ({villa})", color="primary", className="w-100")
        ])
    elif "semelles" in tache:
        docs_content = dbc.Row([
            dbc.Col([dbc.Button(f"📂 Autocontrôle ({villa})", color="primary", className="w-100")]),
            dbc.Col([dbc.Button(f"📄 PV Réception ({villa})", color="primary", className="w-100")])
        ])
    else:
        docs_content = dbc.Alert("Pas de configuration pour cette tâche.", color="info")
    
    # Section validation
    if is_admin:
        validation_content = html.Div([
            html.H6("Validation", className="mb-2"),
            dbc.RadioItems(
                id='statut-radio',
                options=[
                    {"label": "À faire", "value": "À faire"},
                    {"label": "En cours", "value": "En cours"},
                    {"label": "OK", "value": "OK"},
                    {"label": "Non Conforme", "value": "Non Conforme"}
                ],
                value=statut_actuel
            ),
            dbc.Button("💾 Sauvegarder", id="btn-save-status", color="success", className="mt-2 w-100")
        ])
    else:
        color_text = "green" if statut_actuel == "OK" else "red" if statut_actuel == "Non Conforme" else "grey"
        validation_content = html.H3(statut_actuel, style={'color': color_text})
    
    # Section upload/download documents
    if is_admin:
        upload_section = html.Div([
            html.Hr(),
            html.H6(f"📂 Gestion des documents : {villa}", className="mb-2"),
            dcc.Upload(
                id='upload-document',
                children=dbc.Button("📁 Uploader un document (PDF, PNG, JPG)", color="info", className="w-100"),
                multiple=False
            ),
            html.Div(id='upload-status', className="mt-2")
        ])
    else:
        upload_section = html.Div()
    
    # Vérifier si un fichier existe
    chemin_fichier = fichier_existe(tache, villa, "Preuve")
    if chemin_fichier:
        download_section = html.Div([
            html.Hr(),
            dbc.Button(
                f"📥 Télécharger la preuve ({villa})",
                id="btn-download-doc",
                color="success",
                className="w-100",
                href=f"/download/{os.path.basename(chemin_fichier)}",
                external_link=True
            )
        ])
    else:
        download_section = dbc.Alert("⚠️ Aucun document disponible pour le moment.", color="warning")
    
    return dbc.Card([
        dbc.CardBody([
            html.H3("🔎 Détails & Documents", className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Tâche sélectionnée :"),
                    dbc.Select(
                        id='select-tache',
                        options=[{"label": t, "value": i} for i, t in enumerate(LISTE_TACHES)],
                        value=LISTE_TACHES.index(tache)
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Choisir la Villa concernée :"),
                    dbc.Select(
                        id='select-villa',
                        options=[{"label": v, "value": i} for i, v in enumerate(LISTE_VILLAS)],
                        value=LISTE_VILLAS.index(villa)
                    )
                ], width=8)
            ], className="mb-3"),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H6(f"📂 Preuves pour : {tache}", className="mb-2"),
                    docs_content,
                    html.Div([
                        upload_section,
                        download_section
                    ])
                ], width=8),
                dbc.Col([
                    validation_content
                ], width=4)
            ])
        ])
    ], style={
        'backgroundColor': '#e3f2fd',
        'borderLeft': '5px solid #1f77b4',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
        'marginBottom': '50px'
    })

def create_dossier_page():
    """Page dossier de démarrage"""
    return html.Div([
        html.H2("📁 Dossier de Démarrage"),
        dbc.Alert("Plans généraux, Permis, etc.", color="info")
    ])

def create_suivi_page():
    """Page suivi de chaque tâche"""
    df = charger_donnees()
    
    return html.Div([
        html.H2("📂 Explorateur de Dossiers (Vue Arborescence)"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Ouvrir le dossier de la tâche :"),
                dbc.Select(
                    id='folder-tache',
                    options=[{"label": t, "value": t} for t in LISTE_TACHES],
                    value=LISTE_TACHES[0]
                )
            ], width=6),
            dbc.Col([
                html.Label("Ouvrir la villa :"),
                dbc.Select(
                    id='folder-villa',
                    options=[{"label": v, "value": v} for v in LISTE_VILLAS],
                    value=LISTE_VILLAS[0]
                )
            ], width=6)
        ], className="mb-3"),
        
        html.Div(id='folder-content')
    ])

# Callback pour la sélection de cellule dans le tableau
@app.callback(
    [Output('selected-cell', 'data'),
     Output('inspecteur-ancre', 'children')],
    Input('datatable-interactivity', 'active_cell'),
    prevent_initial_call=True
)
def update_selected_cell(active_cell):
    if active_cell:
        # Récupérer la colonne cliquée (ignorer la colonne "Tâche")
        col_id = active_cell['column_id']
        if col_id != 'Tâche':
            row_idx = active_cell['row']
            col_idx = LISTE_VILLAS.index(col_id)
            
            # Script JavaScript pour faire le scroll
            scroll_script = html.Script(
                "setTimeout(function() { document.getElementById('inspecteur-ancre').scrollIntoView({behavior: 'smooth', block: 'start'}); }, 100);"
            )
            
            return {'row': row_idx, 'column': col_idx}, scroll_script
    
    return dash.no_update, dash.no_update

# Callback pour mettre à jour l'inspecteur quand on change les selectbox
@app.callback(
    Output('selected-cell', 'data', allow_duplicate=True),
    [Input('select-tache', 'value'),
     Input('select-villa', 'value')],
    prevent_initial_call=True
)
def update_from_selects(tache_idx, villa_idx):
    if tache_idx is not None and villa_idx is not None:
        return {'row': int(tache_idx), 'column': int(villa_idx)}
    return dash.no_update

# Callback pour sauvegarder le changement de statut
@app.callback(
    Output('main-content', 'children', allow_duplicate=True),
    [Input('btn-save-status', 'n_clicks')],
    [State('statut-radio', 'value'),
     State('selected-cell', 'data'),
     State('is-admin', 'data')],
    prevent_initial_call=True
)
def save_status(n_clicks, new_status, selected_cell, is_admin):
    if n_clicks and is_admin:
        df = charger_donnees()
        tache = LISTE_TACHES[selected_cell['row']]
        villa = LISTE_VILLAS[selected_cell['column']]
        df.at[tache, villa] = new_status
        sauvegarder_donnees(df)
    return create_tableau_page(is_admin, selected_cell)

# Callback pour uploader un document
@app.callback(
    Output('upload-status', 'children'),
    [Input('upload-document', 'contents')],
    [State('upload-document', 'filename'),
     State('selected-cell', 'data'),
     State('is-admin', 'data')],
    prevent_initial_call=True
)
def upload_file(content, filename, selected_cell, is_admin):
    if content and is_admin:
        tache = LISTE_TACHES[selected_cell['row']]
        villa = LISTE_VILLAS[selected_cell['column']]
        nom_final = sauvegarder_fichier(content, filename, tache, villa, "Preuve")
        return dbc.Alert(f"✅ Fichier enregistré : {nom_final}", color="success")
    return dash.no_update

# Callback pour afficher les docs selon le type (Archi/Topo)
@app.callback(
    Output('docs-buttons-axes', 'children'),
    [Input('doc-type-radio', 'value'),
     Input('selected-cell', 'data')]
)
def update_docs_axes(doc_type, selected_cell):
    villa = LISTE_VILLAS[selected_cell['column']]
    if doc_type == "Archi":
        return dbc.Row([
            dbc.Col([dbc.Button(f"📂 Autocontrôle ({villa})", color="primary", className="w-100")]),
            dbc.Col([dbc.Button(f"📄 PV Archi ({villa})", color="primary", className="w-100")])
        ])
    else:
        return dbc.Button(f"📐 Scan Topo ({villa})", color="primary", className="w-100")

# Callback pour la page de suivi
@app.callback(
    Output('folder-content', 'children'),
    [Input('folder-tache', 'value'),
     Input('folder-villa', 'value')]
)
def update_folder_content(tache, villa):
    df = charger_donnees()
    statut = df.at[tache, villa]
    
    if "Réception des axes" in tache:
        content = html.Div([
            html.P("📄 Sous-dossier Archi : [Autocontrôle.pdf] | [PV.pdf]"),
            html.P("📐 Sous-dossier Topo : [Scan_Topo.pdf]")
        ])
    elif "semelles" in tache:
        content = html.P("📄 Documents : [Autocontrôle.pdf] | [PV.pdf]")
    else:
        content = html.P("📄 Document : [Doc_Unique.pdf]")
    
    return html.Div([
        html.H3(f"📂 {tache} > {villa}"),
        content,
        html.Hr(),
        html.Small(f"Statut actuel dans le tableau : {statut}")
    ])

# =====================================================
# LANCEMENT DU SERVEUR
# =====================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)