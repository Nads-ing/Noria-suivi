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

def get_types_docs_pour_tache(tache):
    """Retourne les types de documents possibles pour une tâche"""
    if "Réception des axes" in tache:
        return {
            "Autocontrole_Archi": "📂 Autocontrôle Archi",
            "PV_Archi": "📄 PV Archi", 
            "Scan_Topo": "📐 Scan Topo"
        }
    elif "fond de fouille" in tache:
        return {"Document_Unique": "📄 Document Unique"}
    elif "semelles" in tache:
        return {
            "Autocontrole": "📂 Autocontrôle",
            "PV_Reception": "📄 PV Réception"
        }
    elif "béton" in tache:
        return {
            "Rapport_Labo": "🔬 Rapport Labo",
            "PV_Reception": "📄 PV Réception"
        }
    else:
        return {"Document": "📄 Document"}

def sauvegarder_fichier(content, filename, tache, villa, type_doc):
    """Sauvegarde un fichier uploadé"""
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    
    # Nettoyer le nom
    extension = filename.split('.')[-1]
    nom_propre = f"{tache}_{villa}_{type_doc}".replace(" ", "_").replace(".", "").replace(",", "")
    nom_final = f"{nom_propre}.{extension}"
    
    chemin_complet = os.path.join(DOSSIER_FICHIERS, nom_final)
    
    with open(chemin_complet, 'wb') as f:
        f.write(decoded)
    
    return nom_final

def fichier_existe(tache, villa, type_doc):
    """Vérifie si un fichier existe pour cette tâche/villa/type"""
    nom_base = f"{tache}_{villa}_{type_doc}".replace(" ", "_").replace(".", "").replace(",", "")
    for ext in ['pdf', 'png', 'jpg', 'jpeg']:
        chemin = os.path.join(DOSSIER_FICHIERS, f"{nom_base}.{ext}")
        if os.path.exists(chemin):
            return chemin
    return None

def supprimer_fichier(tache, villa, type_doc):
    """Supprime un fichier"""
    chemin = fichier_existe(tache, villa, type_doc)
    if chemin and os.path.exists(chemin):
        os.remove(chemin)
        return True
    return False

def get_tous_les_fichiers(tache, villa):
    """Récupère tous les fichiers existants pour une tâche/villa"""
    fichiers = {}
    types_possibles = get_types_docs_pour_tache(tache)
    for type_doc, label in types_possibles.items():
        chemin = fichier_existe(tache, villa, type_doc)
        if chemin:
            fichiers[type_doc] = {
                'chemin': chemin,
                'nom': os.path.basename(chemin),
                'extension': chemin.split('.')[-1],
                'label': label
            }
    return fichiers

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
    dcc.Store(id='refresh-trigger', data=0),
    
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
     Input('selected-cell', 'data'),
     Input('refresh-trigger', 'data')]
)
def update_main_content(page, is_admin, selected_cell, refresh):
    if page == "tableau":
        return create_tableau_page(is_admin, selected_cell)
    elif page == "dossier":
        return create_dossier_page()
    else:
        return create_suivi_page(is_admin)

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
    
    # Récupérer tous les fichiers existants
    fichiers_existants = get_tous_les_fichiers(tache, villa)
    types_docs = get_types_docs_pour_tache(tache)
    
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
            dbc.Button("💾 Sauvegarder Statut", id="btn-save-status", color="success", className="mt-2 w-100", size="sm")
        ])
    else:
        color_text = "green" if statut_actuel == "OK" else "red" if statut_actuel == "Non Conforme" else "grey"
        validation_content = html.H3(statut_actuel, style={'color': color_text})
    
    # Section gestion des documents
    docs_cards = []
    for type_doc, label in types_docs.items():
        fichier_info = fichiers_existants.get(type_doc)
        
        if fichier_info:
            # Fichier existe - Afficher avec options
            card_content = [
                html.H6(label, className="mb-2"),
                dbc.Badge(f"✓ {fichier_info['nom']}", color="success", className="mb-2"),
                html.Br(),
                dbc.ButtonGroup([
                    dbc.Button(
                        "👁️ Voir", 
                        id={'type': 'btn-view-doc', 'index': f"{tache}_{villa}_{type_doc}"},
                        color="info", 
                        size="sm",
                        href=f"/{fichier_info['chemin']}",
                        target="_blank",
                        external_link=True
                    ),
                    dbc.Button(
                        "📥 Télécharger", 
                        id={'type': 'btn-download-doc', 'index': f"{tache}_{villa}_{type_doc}"},
                        color="primary", 
                        size="sm",
                        href=f"/{fichier_info['chemin']}",
                        download=fichier_info['nom'],
                        external_link=True
                    )
                ], className="w-100 mb-2")
            ]
            
            if is_admin:
                card_content.append(
                    dbc.ButtonGroup([
                        dbc.Button(
                            "🔄 Remplacer", 
                            id={'type': 'btn-replace-doc', 'index': f"{tache}_{villa}_{type_doc}"},
                            color="warning", 
                            size="sm",
                            className="me-1"
                        ),
                        dbc.Button(
                            "🗑️ Supprimer", 
                            id={'type': 'btn-delete-doc', 'index': f"{tache}_{villa}_{type_doc}"},
                            color="danger", 
                            size="sm"
                        )
                    ], className="w-100")
                )
        else:
            # Pas de fichier - Afficher upload (admin only)
            if is_admin:
                card_content = [
                    html.H6(label, className="mb-2"),
                    dbc.Badge("⚠️ Manquant", color="warning", className="mb-2"),
                    html.Br(),
                    dcc.Upload(
                        id={'type': 'upload-doc', 'index': f"{tache}_{villa}_{type_doc}"},
                        children=dbc.Button("📤 Uploader", color="success", size="sm", className="w-100"),
                        multiple=False
                    )
                ]
            else:
                card_content = [
                    html.H6(label, className="mb-2"),
                    dbc.Badge("⚠️ Aucun document", color="secondary", className="mb-2")
                ]
        
        docs_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(card_content)
                ], className="mb-2", style={'minHeight': '180px'})
            ], width=12 if len(types_docs) == 1 else 6 if len(types_docs) <= 2 else 4)
        )
    
    # Zone de message pour les actions
    action_messages = html.Div(id='action-messages', className="mt-2")
    
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
                    html.H5(f"📂 Documents pour : {tache}", className="mb-3"),
                    dbc.Row(docs_cards),
                    action_messages
                ], width=9),
                dbc.Col([
                    validation_content
                ], width=3)
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

def create_suivi_page(is_admin):
    """Page suivi de chaque tâche"""
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
        col_id = active_cell['column_id']
        if col_id != 'Tâche':
            row_idx = active_cell['row']
            col_idx = LISTE_VILLAS.index(col_id)
            
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
    Output('refresh-trigger', 'data'),
    [Input('btn-save-status', 'n_clicks')],
    [State('statut-radio', 'value'),
     State('selected-cell', 'data'),
     State('is-admin', 'data'),
     State('refresh-trigger', 'data')],
    prevent_initial_call=True
)
def save_status(n_clicks, new_status, selected_cell, is_admin, current_refresh):
    if n_clicks and is_admin:
        df = charger_donnees()
        tache = LISTE_TACHES[selected_cell['row']]
        villa = LISTE_VILLAS[selected_cell['column']]
        df.at[tache, villa] = new_status
        sauvegarder_donnees(df)
        return current_refresh + 1
    return dash.no_update

# Callback pour uploader un document
@app.callback(
    Output('action-messages', 'children'),
    [Input({'type': 'upload-doc', 'index': ALL}, 'contents')],
    [State({'type': 'upload-doc', 'index': ALL}, 'filename'),
     State({'type': 'upload-doc', 'index': ALL}, 'id'),
     State('is-admin', 'data')],
    prevent_initial_call=True
)
def upload_file(contents_list, filenames_list, ids_list, is_admin):
    if not is_admin:
        return dbc.Alert("⛔ Accès refusé", color="danger")
    
    for i, content in enumerate(contents_list):
        if content:
            filename = filenames_list[i]
            index = ids_list[i]['index']
            parts = index.split('_')
            
            # Reconstituer tache et villa
            tache = None
            villa = None
            type_doc = None
            
            for j, tache_possible in enumerate(LISTE_TACHES):
                if index.startswith(tache_possible):
                    tache = tache_possible
                    reste = index[len(tache)+1:]
                    for villa_possible in LISTE_VILLAS:
                        if reste.startswith(villa_possible):
                            villa = villa_possible
                            type_doc = reste[len(villa)+1:]
                            break
                    break
            
            if tache and villa and type_doc:
                nom_final = sauvegarder_fichier(content, filename, tache, villa, type_doc)
                return dbc.Alert(f"✅ Fichier uploadé : {nom_final}", color="success", dismissable=True, duration=4000)
    
    return dash.no_update

# Callback pour supprimer un document
@app.callback(
    Output('refresh-trigger', 'data', allow_duplicate=True),
    [Input({'type': 'btn-delete-doc', 'index': ALL}, 'n_clicks')],
    [State({'type': 'btn-delete-doc', 'index': ALL}, 'id'),
     State('is-admin', 'data'),
     State('refresh-trigger', 'data')],
    prevent_initial_call=True
)
def delete_file(n_clicks_list, ids_list, is_admin, current_refresh):
    if not is_admin:
        return dash.no_update
    
    for i, n_clicks in enumerate(n_clicks_list):
        if n_clicks:
            index = ids_list[i]['index']
            parts = index.split('_')
            
            for tache in LISTE_TACHES:
                if index.startswith(tache):
                    reste = index[len(tache)+1:]
                    for villa in LISTE_VILLAS:
                        if reste.startswith(villa):
                            type_doc = reste[len(villa)+1:]
                            if supprimer_fichier(tache, villa, type_doc):
                                return current_refresh + 1
    
    return dash.no_update

# Callback pour la page de suivi
@app.callback(
    Output('folder-content', 'children'),
    [Input('folder-tache', 'value'),
     Input('folder-villa', 'value'),
     Input('refresh-trigger', 'data')],
    [State('is-admin', 'data')]
)
def update_folder_content(tache, villa, refresh, is_admin):
    df = charger_donnees()
    statut = df.at[tache, villa]
    
    # Même système de gestion de documents que dans l'inspecteur
    fichiers_existants = get_tous_les_fichiers(tache, villa)
    types_docs = get_types_docs_pour_tache(tache)
    
    docs_list = []
    for type_doc, label in types_docs.items():
        fichier_info = fichiers_existants.get(type_doc)
        if fichier_info:
            docs_list.append(
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([
                            html.Strong(label),
                            html.Br(),
                            html.Small(fichier_info['nom'], className="text-muted")
                        ], width=6),
                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button("👁️ Voir", href=f"/{fichier_info['chemin']}", target="_blank", color="info", size="sm", external_link=True),
                                dbc.Button("📥 Télécharger", href=f"/{fichier_info['chemin']}", download=fichier_info['nom'], color="primary", size="sm", external_link=True),
                            ], className="float-end")
                        ], width=6)
                    ])
                ])
            )
        else:
            docs_list.append(
                dbc.ListGroupItem([
                    html.Strong(label),
                    dbc.Badge("⚠️ Manquant", color="warning", className="ms-2")
                ])
            )
    
    return html.Div([
        html.H3(f"📂 {tache} > {villa}", className="mb-3"),
        dbc.Card([
            dbc.CardBody([
                html.H5("📄 Documents disponibles", className="mb-3"),
                dbc.ListGroup(docs_list) if docs_list else dbc.Alert("Aucun document configuré", color="info")
            ])
        ], className="mb-3"),
        html.Hr(),
        html.Small(f"Statut actuel dans le tableau : ", className="text-muted"),
        dbc.Badge(statut, color="success" if statut == "OK" else "danger" if statut == "Non Conforme" else "warning")
    ])

# =====================================================
# LANCEMENT DU SERVEUR
# =====================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)