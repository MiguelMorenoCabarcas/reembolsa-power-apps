"""Genera las partes de src/ que dependen de las listas de SharePoint:
DataSources/*.json, pkgs/TableDefinitions/*.json, Connections/Connections.json y CanvasManifest.json.

Uso (desde la carpeta app/):  python -I tools/generar-datos.py
"""
import json
import os
import uuid
import hashlib
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
SRC = os.path.join(APP, 'src')
# listas.local.json (no se publica) tiene el sitio y los IDs reales; listas.json trae valores de ejemplo
_cfg_path = os.path.join(HERE, 'listas.local.json')
if not os.path.exists(_cfg_path):
    _cfg_path = os.path.join(HERE, 'listas.json')
cfg = json.load(open(_cfg_path, encoding='utf-8'))
SITE = cfg['site']


def stable_guid(seed):
    """GUID estable entre corridas, para no cambiar ids al regenerar."""
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))


COMMON = {
    "Author": "Creado por", "Author#Claims": "Creado por Claims",
    "ComplianceAssetId": "Id. de activo de cumplimiento normativo",
    "Created": "Creado", "Editor": "Modificado por", "Editor#Claims": "Modificado por Claims",
    "ID": "ID", "Modified": "Modificado", "OData__ColorTag": "Etiqueta de color", "Title": "Title",
}


def mapping(fields):
    m = dict(COMMON)
    for n, t in fields:
        m[n] = n
        if t in ('Choice', 'Lookup'):
            m[n + '#Id'] = n + ' Id'
        if t == 'User':
            m[n + '#Claims'] = n + ' Claims'
    return dict(sorted(m.items()))


PLANTILLA = open(os.path.join(HERE, 'plantilla-tabla.json'), encoding='utf-8').read()
_u = urlparse(SITE)


def _plantilla(table_id):
    txt = (PLANTILLA.replace('{SITE_PATH}', _u.path).replace('{SITE_HOST}', f'{_u.scheme}://{_u.netloc}')
           .replace('{TABLE_ID}', table_id))
    return json.loads(txt)


def _prop(nombre, tipo, perm='read-write'):
    """Esquema de una columna personalizada, con la forma que devuelve el conector de SharePoint."""
    base = {"title": nombre, "x-ms-permission": perm}
    if tipo == 'Text':
        return {**base, "type": "string", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq", "startswith"]}, "maxLength": 255}
    if tipo == 'Note':
        return {**base, "type": "string", "x-ms-sort": "none"}
    if tipo == 'Number':
        return {**base, "type": "number", "format": "double", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq", "gt", "ge", "lt", "le", "ne"]},
                "maximum": 1.7976931348623157e+308, "minimum": -1.7976931348623157e+308}
    if tipo == 'Boolean':
        return {**base, "type": "boolean", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq"]}, "default": False}
    if tipo in ('Date', 'DateTime'):
        return {**base, "type": "string", "format": "date" if tipo == 'Date' else "date-time", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq", "gt", "ge", "lt", "le", "ne"]}}
    inner_odata = {"title": "@odata.type", "x-ms-visibility": "internal", "type": "string", "x-ms-permission": "read-write"}
    if tipo == 'Choice':
        return {**base, "type": "object", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"x-ms-sp": {"IsChoice": True}, "filterFunctions": ["eq"]},
                "properties": {"@odata.type": inner_odata, "Value": {"title": "Value", "type": "string"},
                               "Id": {"title": "Id", "type": "integer", "format": "int64",
                                      "x-ms-visibility": "internal", "x-ms-permission": "read-only"}},
                "x-ms-displayFormat": {"titleProperty": "Value"}}
    if tipo == 'Lookup':
        return {**base, "type": "object", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq"]},
                "properties": {"@odata.type": inner_odata,
                               "Id": {"title": "Id", "type": "integer", "format": "int64"},
                               "Value": {"title": "Value", "type": "string", "x-ms-permission": "read-only",
                                         "x-ms-capabilities": {"x-ms-sp": {"OdataQueryName": f"{nombre}/Title"},
                                                               "filterFunctions": ["eq"]}}},
                "x-ms-displayFormat": {"titleProperty": "Value"}}
    if tipo == 'User':
        return {**base, "type": "object", "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq"]},
                "properties": {"@odata.type": inner_odata,
                               "Claims": {"title": "Claims", "type": "string"},
                               "DisplayName": {"title": "DisplayName", "type": "string", "x-ms-permission": "read-only",
                                               "x-ms-capabilities": {"x-ms-sp": {"OdataQueryName": "Title"},
                                                                     "filterFunctions": ["eq", "startswith"]}},
                               "Email": {"title": "Email", "type": "string", "format": "email", "x-ms-permission": "read-only",
                                         "x-ms-capabilities": {"x-ms-sp": {"OdataQueryName": "EMail"},
                                                               "filterFunctions": ["eq", "startswith"]}},
                               "Picture": {"title": "Picture", "type": "string", "format": "uri", "x-ms-media-kind": "image",
                                           "x-ms-media-default-folder-path": _u.path,
                                           "x-ms-media-base-url": f'{_u.scheme}://{_u.netloc}{_u.path}',
                                           "x-ms-permission": "read-only"},
                               "Department": {"title": "Department", "type": "string", "x-ms-permission": "read-only"},
                               "JobTitle": {"title": "JobTitle", "type": "string", "x-ms-permission": "read-only"}},
                "x-ms-displayFormat": {"titleProperty": "DisplayName", "subtitleProperty": "Email",
                                       "thumbnailProperty": "Picture"}}
    raise ValueError(tipo)


def build_table(name, info):
    """TableDefinition completa (esquema de columnas) para que Studio no tenga que descargarlo."""
    t = _plantilla(info['id'])
    props = {"ID": t['id'], "Title": {**t['title'], "title": "Title"}}
    ref = {}
    rel = {}
    orden = ['Title']
    for n, tipo in info['fields']:
        orden.append(n)
        if tipo in ('Choice', 'Lookup'):
            props[n + '#Id'] = {"title": n + " Id", "type": "integer", "format": "int64",
                                "x-ms-permission": "read-only", "x-ms-visibility": "internal"}
            ref[n] = {"lookupEndpoint": {"path": f"/tables/{info['id']}/entities/{n}",
                                         "capabilities": {"searchable": True, "requiresSearch": False}}}
            rel[n] = {"targetEntity": n, "referentialConstraints": {n + "#Id": {"referencedProperty": "Id"}}}
        if tipo == 'User':
            props[n + '#Claims'] = {"title": n + " Claims", "type": "string", "x-ms-permission": "read-only",
                                    "x-ms-visibility": "internal"}
            ref[n] = {"lookupEndpoint": {"path": f"/tables/{info['id']}/entities/{n}",
                                         "capabilities": {"searchable": True, "requiresSearch": False}}}
            rel[n] = {"targetEntity": n, "referentialConstraints": {n + "#Claims": {"referencedProperty": "Claims"}}}
        props[n] = _prop(n, tipo)
    props.update(t['sistema'])
    ref.update(t['refSistema'])
    rel.update(t['relSistema'])
    return {
        "name": info['id'], "title": name, "x-ms-permission": "read-write",
        "x-ms-capabilities": t['cap'], "referencedEntities": ref,
        "schema": {"type": "array", "items": {
            "type": "object", "required": [], "properties": props, "x-ms-relationships": rel,
            "x-ms-displayFormat": {"propertiesDisplayOrder": orden, "propertiesCompactDisplayOrder": orden,
                                   "propertiesTabularDisplayOrder": orden}}},
        "webUrl": f"{SITE}/Lists/{name}/AllItems.aspx",
    }


for d in (('DataSources',), ('pkgs', 'TableDefinitions'), ('Connections',)):
    os.makedirs(os.path.join(SRC, *d), exist_ok=True)

for name, info in cfg['listas'].items():
    ds = [{
        "ApiId": "/providers/microsoft.powerapps/apis/shared_sharepointonline",
        "CdpRevision": {"BaseUrl": "/", "LastChangedTimeString": "2026-11-23T00:00:00.0000000Z", "RevisionNumber": 1},
        "ConnectedDataSourceInfoNameMapping": mapping(info['fields']),
        "DatasetName": SITE, "EncodeDataset": True, "IsSampleData": False, "IsWritable": True,
        "Name": name, "Type": "ConnectedDataSourceInfo",
    }]
    with open(os.path.join(SRC, 'DataSources', name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(ds, f, indent=2, ensure_ascii=False)
    gid = info['id']
    meta = build_table(name, info)
    td = {"DataEntityMetadataJson": {gid: json.dumps(meta, separators=(',', ':'), ensure_ascii=False)},
          "EntityName": name, "TableName": gid}
    with open(os.path.join(SRC, 'pkgs', 'TableDefinitions', name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(td, f, indent=2, ensure_ascii=False)

conn_id = stable_guid('reembolsa-sharepoint-connection')
conn = {conn_id: {
    "appActions": ["providers/PowerPlatform.Governance/Operations/Read",
                   "providers/PowerPlatform.Governance/Operations/Write",
                   "providers/PowerPlatform.Governance/Operations/Delete"],
    "connectionRef": {
        "apiTier": "Standard", "displayName": "SharePoint",
        "iconUri": "https://static.powerapps.com/resource/ppcr/releases/v1.0.1809/1.0.1809.4723/sharepointonline/icon.png",
        "id": "/providers/microsoft.powerapps/apis/shared_sharepointonline",
        "parameterHints": {}, "parameterHintsV2": {}},
    "datasets": {SITE: {"dataSources": {n: {"tableName": i['id']} for n, i in sorted(cfg['listas'].items())}}},
    "dataSources": list(cfg['listas'].keys()),
    "dependencies": {}, "dependents": [], "id": conn_id}}
with open(os.path.join(SRC, 'Connections', 'Connections.json'), 'w', encoding='utf-8') as f:
    json.dump(conn, f, indent=2)

manifest = json.load(open(os.path.join(HERE, 'manifest-base.json'), encoding='utf-8-sig'))
manifest['Properties']['AppCreationSource'] = 'AppFromScratch'
manifest['Properties']['Id'] = stable_guid('reembolsa-app-id')
manifest['Properties']['FileID'] = stable_guid('reembolsa-file-id')
manifest['Properties']['Name'] = 'UmVlbWJvbHNh.msapp'  # base64("Reembolsa")
manifest['PublishInfo']['AppName'] = 'Reembolsa'
manifest['PublishInfo']['BackgroundColor'] = 'RGBA(15,118,110,1)'
manifest['PublishInfo']['UserLocale'] = 'es-ES'
manifest['ScreenOrder'] = cfg['screens']
with open(os.path.join(SRC, 'CanvasManifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print('OK:', len(cfg['listas']), 'listas;', len(cfg['screens']), 'pantallas')
