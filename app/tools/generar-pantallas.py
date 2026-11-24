"""Genera src/Src/App.fx.yaml y las 6 pantallas de Reembolsa.

Uso (desde la carpeta app/):  python -I tools/generar-pantallas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yamlgen import (Ctl, screen_text, label, rect, button, icon, textinput, dropdown, datepicker,  # noqa: E402
                     gallery, card, row_sep, badge)

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(APP, 'src', 'Src')

W, H = 1366, 768
SB = 220          # ancho de la barra lateral
CX = 244          # x de inicio del contenido
CW = 1098         # ancho del contenido (244 -> 1342)

MONEY = '"$" & Text({v}, "#,##0")'


def money(v):
    return MONEY.replace('{v}', v)


# ------------------------------------------------------------------ App.fx.yaml

APP_FORMULAS = r'''
ColorPrimario = ColorValue("#0F766E");
ColorPrimarioClaro = ColorValue("#CCFBF1");
ColorOscuro = ColorValue("#1E293B");
ColorFondo = ColorValue("#F1F5F9");
ColorTarjeta = Color.White;
ColorTexto = ColorValue("#334155");
ColorTextoSuave = ColorValue("#64748B");
ColorBorde = ColorValue("#E2E8F0");
ColorAcento = ColorValue("#F59E0B");
ColorExito = ColorValue("#16A34A");
ColorError = ColorValue("#DC2626");
ColorInfo = ColorValue("#0284C7");
ColorSidebarTexto = ColorValue("#CBD5E1");
ColorSidebarSuave = ColorValue("#94A3B8");
ColorSidebarHover = ColorValue("#334155");
UsuarioActual = {
    '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser",
    Claims: "i:0#.f|membership|" & Lower(User().Email),
    DisplayName: User().FullName,
    Email: User().Email,
    Department: "",
    JobTitle: "",
    Picture: ""
};
EstadosMeta = Table(
    {Raw: "Borrador", Texto: "Borrador", Fondo: ColorValue("#E2E8F0"), Letra: ColorValue("#475569")},
    {Raw: "PendienteJefe", Texto: "Pendiente jefe", Fondo: ColorValue("#FEF3C7"), Letra: ColorValue("#92400E")},
    {Raw: "PendienteFinanzas", Texto: "Pendiente Finanzas", Fondo: ColorValue("#FEF3C7"), Letra: ColorValue("#92400E")},
    {Raw: "Aprobada", Texto: "Aprobada", Fondo: ColorValue("#DCFCE7"), Letra: ColorValue("#166534")},
    {Raw: "Devuelta", Texto: "Devuelta", Fondo: ColorValue("#FFEDD5"), Letra: ColorValue("#9A3412")},
    {Raw: "Rechazada", Texto: "Rechazada", Fondo: ColorValue("#FEE2E2"), Letra: ColorValue("#991B1B")},
    {Raw: "Pagada", Texto: "Pagada", Fondo: ColorValue("#CCFBF1"), Letra: ColorValue("#115E59")}
);
EstadosFiltro = Table(
    {Value: "Todos", Raw: "Todos"},
    {Value: "Borrador", Raw: "Borrador"},
    {Value: "Pendiente jefe", Raw: "PendienteJefe"},
    {Value: "Pendiente Finanzas", Raw: "PendienteFinanzas"},
    {Value: "Aprobada", Raw: "Aprobada"},
    {Value: "Devuelta", Raw: "Devuelta"},
    {Value: "Rechazada", Raw: "Rechazada"},
    {Value: "Pagada", Raw: "Pagada"}
);
'''

APP_ONSTART = r'''
Set(gblUserEmail, Lower(User().Email));
Set(gblUser, LookUp(UsuariosRolLST, UsuarioEmail = gblUserEmail));
Set(gblRol, Coalesce(gblUser.Rol.Value, "Solicitante"));
Set(gblNombre, Coalesce(gblUser.Title, User().FullName));
Set(gblEsAprobador, gblRol in ["Aprobador", "Finanzas", "Administrador"]);
Set(gblEsFinanzas, gblRol in ["Finanzas", "Administrador"]);
Set(gblEditId, 0);
Set(gblEditNo, "");
Concurrent(
    ClearCollect(
        colCentros,
        ForAll(
            Filter(CentrosCostoLST, Activo = true),
            {Value: Title & " - " & Nombre, Cod: Title, Id: ID}
        )
    ),
    ClearCollect(
        colCategorias,
        ForAll(
            Filter(CategoriasGastoLST, Activo = true),
            {Value: Title, Id: ID, Limite: LimiteMonto, Recibo: RequiereRecibo}
        )
    ),
    ClearCollect(colParametros, ParametrosLST)
);
Set(gblUmbral, Coalesce(Value(LookUp(colParametros, Title = "UmbralFinanzas").Valor), 1000000));
Set(gblDiasMax, Coalesce(Value(LookUp(colParametros, Title = "DiasMaxAntiguedad").Valor), 60));
Set(gblDiasAlerta, Coalesce(Value(LookUp(colParametros, Title = "DiasAlertaPendiente").Valor), 3));
If(!IsBlank(Param("ID")), Set(gblSelId, Value(Param("ID"))))
'''


def write(name, text):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def app_yaml():
    from yamlgen import _prop
    out = ['App As appinfo:', '    BackEnabled: =true']
    out += _prop('Formulas', APP_FORMULAS, '    ')
    out += _prop('OnStart', APP_ONSTART, '    ')
    out += _prop('StartScreen', 'If(!IsBlank(Param("ID")), DetalleSolicitudScreen, InicioScreen)', '    ')
    out += ['    Theme: =PowerAppsTheme', '',
            '    Host As hostControl.DefaultHostControlVariant:',
            '        OnCancel: =false', '        OnEdit: =false', '        OnNew: =false',
            '        OnSave: =false', '        OnView: =false', '']
    return '\n'.join(out) + '\n'


# ------------------------------------------------------------------ chrome comun

NAV = [
    ('Inicio', 'InicioScreen', 'true', 'Navigate(InicioScreen, ScreenTransition.None)'),
    ('Mis solicitudes', 'MisSolicitudesScreen', 'true', 'Navigate(MisSolicitudesScreen, ScreenTransition.None)'),
    ('Nueva solicitud', 'NuevaSolicitudScreen', 'true',
     'Set(gblEditId, 0);\nSet(gblEditNo, "");\nNavigate(NuevaSolicitudScreen, ScreenTransition.None)'),
    ('Bandeja de aprobación', 'BandejaScreen', 'gblEsAprobador', 'Navigate(BandejaScreen, ScreenTransition.None)'),
    ('Reportes', 'ReportesScreen', 'gblEsFinanzas', 'Navigate(ReportesScreen, ScreenTransition.None)'),
]


def chrome(p, active, title):
    """Barra lateral + encabezado. p = prefijo unico de la pantalla."""
    ctl = [
        rect(f'{p}SidebarBg', 0, 0, SB, H, fill='ColorOscuro', radius=0),
        label(f'{p}AppNombre', '"Reembolsa"', 24, 22, 172, 32, size=22, color='Color.White', bold=True),
        label(f'{p}AppLema', '"Gestión de gastos"', 24, 54, 172, 20, size=11, color='ColorSidebarSuave'),
    ]
    for i, (txt, scr, vis, nav) in enumerate(NAV):
        on = scr == active
        ctl.append(button(
            f'{p}Nav{i}', f'"{txt}"', 10, 110 + i * 52, 200, 44, nav,
            fill='ColorPrimario' if on else 'Color.Transparent',
            color='Color.White' if on else 'ColorSidebarTexto', align='Left', bold=on,
            hover='ColorPrimario' if on else 'ColorSidebarHover', visible=vis,
            extra={'PaddingLeft': '16'}))
    ctl += [
        rect(f'{p}SidebarLinea', 16, 680, 188, 1, fill='ColorSidebarHover', radius=0),
        label(f'{p}UsuarioNombre', 'gblNombre', 24, 690, 180, 22, size=12, color='Color.White', bold=True, wrap=False),
        label(f'{p}UsuarioRol', 'gblRol', 24, 712, 180, 20, size=11, color='ColorSidebarSuave', wrap=False),
        rect(f'{p}HeaderBg', SB, 0, W - SB, 64, fill='Color.White', radius=0),
        rect(f'{p}HeaderLinea', SB, 63, W - SB, 1, fill='ColorBorde', radius=0),
        label(f'{p}Titulo', f'"{title}"', CX, 0, 700, 64, size=22, color='ColorOscuro', bold=True),
        label(f'{p}Fecha', 'Text(Today(), "dd/mm/yyyy")', 1042, 0, 300, 64, size=12, color='ColorTextoSuave', align='Right'),
    ]
    return ctl


def kpi(p, i, x, y, w, h, valor, texto, color='ColorPrimario', onselect=None):
    ctl = [
        card(f'{p}Kpi{i}Card', x, y, w, h),
        rect(f'{p}Kpi{i}Barra', x, y + 14, 4, h - 28, fill=color, radius=2),
        label(f'{p}Kpi{i}Valor', valor, x + 20, y + 10, w - 36, 52, size=30, color='ColorOscuro', bold=True, wrap=False),
        label(f'{p}Kpi{i}Texto', texto, x + 20, y + h - 40, w - 36, 28, size=12, color='ColorTextoSuave', wrap=False),
    ]
    if onselect:
        ctl.append(button(f'{p}Kpi{i}Click', '""', x, y, w, h, onselect, fill='Color.Transparent',
                          hover='Color.Transparent', radius=10))
    return ctl


BANDEJA_LOAD = r'''
If(
    gblEsAprobador,
    If(
        gblRol = "Administrador",
        ClearCollect(colBandeja, Filter(SolicitudesLST, Estado.Value = "PendienteJefe")),
        ClearCollect(colBandeja, Filter(SolicitudesLST, Estado.Value = "PendienteJefe", AprobadorEmail = gblUserEmail))
    );
    If(gblEsFinanzas, Collect(colBandeja, Filter(SolicitudesLST, Estado.Value = "PendienteFinanzas"))),
    Clear(colBandeja)
)
'''

def abrir_detalle(galeria):
    """OnSelect de la galeria: usa Selected (ThisItem solo existe dentro de la plantilla)."""
    return 'Set(gblSelId, ' + galeria + '.Selected.ID);\nNavigate(DetalleSolicitudScreen, ScreenTransition.None)'


# ------------------------------------------------------------------ 1. Inicio

def inicio():
    p = 'ini'
    c = chrome(p, 'InicioScreen', 'Inicio')
    kw, kg = 258, 22
    kx = [CX + i * (kw + kg) for i in range(4)]
    c += kpi(p, 1, kx[0], 88, kw, 110, 'CountRows(Filter(colMisSol, Estado.Value = "Borrador"))', '"Borradores"',
             'ColorTextoSuave', 'Navigate(MisSolicitudesScreen, ScreenTransition.None)')
    c += kpi(p, 2, kx[1], 88, kw, 110,
             'CountRows(Filter(colMisSol, Estado.Value in ["PendienteJefe", "PendienteFinanzas"]))', '"En trámite"',
             'ColorAcento', 'Navigate(MisSolicitudesScreen, ScreenTransition.None)')
    c += kpi(p, 3, kx[2], 88, kw, 110, 'CountRows(Filter(colMisSol, Estado.Value = "Devuelta"))', '"Devueltas para corregir"',
             'ColorError', 'Navigate(MisSolicitudesScreen, ScreenTransition.None)')
    c += kpi(p, 4, kx[3], 88, kw, 110, 'If(gblEsAprobador, Text(CountRows(colBandeja)), "-")', '"Por aprobar"',
             'ColorPrimario', 'If(gblEsAprobador, Navigate(BandejaScreen, ScreenTransition.None))')

    c += [card(f'{p}ListaCard', CX, 222, 718, 522),
          label(f'{p}ListaTitulo', '"Mis últimas solicitudes"', CX + 20, 234, 400, 32, size=15, color='ColorOscuro', bold=True)]
    rows = [
        label(f'{p}RowNo', 'ThisItem.Title', 20, 8, 200, 24, size=13, color='ColorOscuro', bold=True, wrap=False),
        label(f'{p}RowMotivo', 'ThisItem.Motivo', 20, 32, 330, 22, size=11, color='ColorTextoSuave', wrap=False),
        label(f'{p}RowMonto', money('ThisItem.MontoTotal'), 370, 8, 140, 46, size=13, color='ColorOscuro', bold=True, align='Right', wrap=False),
        *badge(f'{p}RowEst', 530, 17, 150, 24, 'ThisItem.Estado.Value'),
        row_sep(f'{p}RowSep', 678, 58),
    ]
    c.append(gallery(f'{p}GalUltimas', 'FirstN(Sort(colMisSol, ID, SortOrder.Descending), 8)', CX + 20, 272, 678, 460, 58,
                     rows, onselect=abrir_detalle(f'{p}GalUltimas')))
    c += [card(f'{p}AccCard', 986, 222, 356, 522),
          label(f'{p}AccTitulo', '"Acciones rápidas"', 1006, 234, 300, 32, size=15, color='ColorOscuro', bold=True),
          button(f'{p}AccNueva', '"Nueva solicitud"', 1006, 284, 316, 48,
                 'Set(gblEditId, 0);\nSet(gblEditNo, "");\nNavigate(NuevaSolicitudScreen, ScreenTransition.None)'),
          button(f'{p}AccMis', '"Ver mis solicitudes"', 1006, 344, 316, 48,
                 'Navigate(MisSolicitudesScreen, ScreenTransition.None)', fill='Color.White', color='ColorPrimario',
                 border='ColorPrimario', hover='ColorPrimarioClaro'),
          button(f'{p}AccBandeja', '"Ir a la bandeja de aprobación"', 1006, 404, 316, 48,
                 'Navigate(BandejaScreen, ScreenTransition.None)', fill='Color.White', color='ColorPrimario',
                 border='ColorPrimario', hover='ColorPrimarioClaro', visible='gblEsAprobador'),
          label(f'{p}AccNota', '"Rol actual: " & gblRol & Char(10) & "Las solicitudes desde " & Text(gblUmbral, "#,##0") '
                '& " pasan también por Finanzas."', 1006, 480, 316, 80, size=11, color='ColorTextoSuave', valign='Top')]
    props = {'Fill': 'ColorFondo',
             'OnVisible': 'Refresh(SolicitudesLST);\nClearCollect(colMisSol, Filter(SolicitudesLST, SolicitanteEmail = gblUserEmail));\n'
                          + BANDEJA_LOAD}
    return screen_text('InicioScreen', props, c)


# ------------------------------------------------------------------ 2. Mis solicitudes

def mis_solicitudes():
    p = 'mis'
    c = chrome(p, 'MisSolicitudesScreen', 'Mis solicitudes')
    c += [card(f'{p}FiltroCard', CX, 88, CW, 64),
          textinput(f'{p}Buscar', CX + 20, 100, 320, 40, hint='"Buscar por número (REM-2026-...)"'),
          dropdown(f'{p}Estado', 'EstadosFiltro', CX + 360, 100, 240, 40, default='"Todos"'),
          button(f'{p}Nueva', '"+ Nueva solicitud"', CX + CW - 220, 100, 200, 40,
                 'Set(gblEditId, 0);\nSet(gblEditNo, "");\nNavigate(NuevaSolicitudScreen, ScreenTransition.None)')]
    hdr_y = 168
    cols = [('Número', 20, 150), ('Motivo', 190, 330), ('Centro', 530, 80), ('Monto', 620, 130),
            ('Fecha', 770, 100), ('Estado', 890, 150)]
    c.append(card(f'{p}TablaCard', CX, hdr_y, CW, 576))
    for i, (t, x, w) in enumerate(cols):
        c.append(label(f'{p}Th{i}', f'"{t}"', CX + x, hdr_y + 8, w, 28, size=11, color='ColorTextoSuave', bold=True,
                       align='Right' if t == 'Monto' else 'Left', wrap=False))
    c.append(rect(f'{p}ThLinea', CX, hdr_y + 40, CW, 1, fill='ColorBorde', radius=0))
    c.append(button(f'{p}Ver', 'If(ctxTodas, "Viendo: todas", "Viendo: mis solicitudes")', CX + 620, 100, 240, 40,
                    'UpdateContext({ctxTodas: !ctxTodas})', fill='Color.White', color='ColorPrimario', border='ColorPrimario',
                    hover='ColorPrimarioClaro', visible='gblEsFinanzas'))

    def consulta(propias):
        base = 'Filter(SolicitudesLST, ' + ('SolicitanteEmail = gblUserEmail, ' if propias else '') \
               + 'StartsWith(Title, ' + p + 'Buscar.Text){extra})'
        return ('If(\n        ' + p + 'Estado.Selected.Raw = "Todos",\n        Sort(' + base.replace('{extra}', '')
                + ', ID, SortOrder.Descending),\n        Sort(' + base.replace('{extra}', ', Estado.Value = ' + p + 'Estado.Selected.Raw')
                + ', ID, SortOrder.Descending)\n    )')
    # Finanzas/Administrador pueden alternar entre sus solicitudes y todas
    items = 'If(\n    ctxTodas && gblEsFinanzas,\n    ' + consulta(False) + ',\n    ' + consulta(True) + '\n)'
    rows = [
        label(f'{p}RowNo', 'ThisItem.Title', 20, 0, 160, 56, size=12, color='ColorOscuro', bold=True, wrap=False),
        label(f'{p}RowMotivo', 'ThisItem.Motivo', 190, 0, 330, 56, size=12, wrap=False),
        label(f'{p}RowCC', 'ThisItem.CentroCostoCod', 530, 0, 80, 56, size=12, wrap=False),
        label(f'{p}RowMonto', money('ThisItem.MontoTotal'), 620, 0, 130, 56, size=12, color='ColorOscuro', bold=True, align='Right', wrap=False),
        label(f'{p}RowFecha', 'Text(ThisItem.FechaSolicitud, "dd/mm/yyyy")', 770, 0, 100, 56, size=12, wrap=False),
        *badge(f'{p}RowEst', 890, 16, 150, 24, 'ThisItem.Estado.Value'),
        row_sep(f'{p}RowSep', CW, 56),
    ]
    c.append(gallery(f'{p}Gal', items, CX, hdr_y + 42, CW, 532, 56, rows, onselect=abrir_detalle(f'{p}Gal')))
    props = {'Fill': 'ColorFondo',
             'OnVisible': 'Refresh(SolicitudesLST);\nUpdateContext({ctxTodas: false});\nReset(' + p + 'Buscar)'}
    return screen_text('MisSolicitudesScreen', props, c)


# ------------------------------------------------------------------ 3. Nueva solicitud

def bitacora(accion, nivel, ant, nue, comentario, no_expr, id_expr):
    return ('IfError(\n'
            '    Patch(\n        BitacoraLST,\n        Defaults(BitacoraLST),\n        {\n'
            f'            Title: {no_expr},\n'
            f'            Solicitud: {{Id: {id_expr}, Value: {no_expr}}},\n'
            f'            Accion: {{Value: "{accion}"}},\n'
            f'            Nivel: {nivel},\n'
            '            Actor: UsuarioActual,\n'
            '            ActorEmail: gblUserEmail,\n'
            f'            EstadoAnterior: {ant},\n'
            f'            EstadoNuevo: {nue},\n'
            f'            Comentario: {comentario},\n'
            '            FechaAccion: Now()\n        }\n    );\n    true,\n'
            '    Notify("El cambio se guardó, pero no se pudo escribir en la bitácora.", NotificationType.Warning)\n)')


def guardar_formula(enviar):
    msg_incompleto = ('"Completa el centro de costo, el motivo y agrega al menos un gasto."' if enviar
                      else '"Selecciona el centro de costo y agrega al menos un gasto."')
    cond = 'IsBlank(nuevaCentro.Selected) || CountRows(colGastosNuevo) = 0' + (
        ' || IsBlank(Trim(nuevaMotivo.Text))' if enviar else '')
    estado = ('If(IsBlank(gblUser.JefeEmail) || Lower(gblUser.JefeEmail) = gblUserEmail, "PendienteFinanzas", "PendienteJefe")'
              if enviar else 'If(gblEditId > 0, gblEdit.Estado.Value, "Borrador")')
    fecha_envio_new = 'Now()' if enviar else 'Blank()'
    fecha_envio_edit = 'Now()' if enviar else 'gblEdit.FechaEnvio'
    bit_creada = bitacora('Creada', 0, '""', '"Borrador"', '""', 'gblNoGuardar', 'gblHdr.ID')
    bit_enviada = bitacora('Enviada', 1, 'If(gblEditId > 0, gblEdit.Estado.Value, "Borrador")', 'gblEstadoNuevo', '""',
                           'gblNoGuardar', 'gblHdr.ID') if enviar else ''
    exito = ('ForAll(colOld As O, Remove(GastosLST, O));\n'
             'If(gblEditId = 0, ' + bit_creada + ');\n'
             + (bit_enviada + ';\n' if enviar else '')
             + 'Set(gblSelId, gblHdr.ID);\n'
             'UpdateContext({ctxGuardando: false});\n'
             'Notify("' + ('Solicitud enviada a aprobación.' if enviar else 'Borrador guardado.') + '", NotificationType.Success);\n'
             'Navigate(DetalleSolicitudScreen, ScreenTransition.None)')
    nuevo = '''Set(gblTipoConsec, "REM-" & Text(Year(Today()), "0"));
Refresh(ConsecutivoLST);
Set(gblContador, LookUp(ConsecutivoLST, Tipo = gblTipoConsec));
Set(gblN, Coalesce(Value(gblContador.Valor), 0) + 1);
Set(
    gblReservaOK,
    !IsBlank(
        IfError(
            If(
                IsBlank(gblContador),
                Patch(ConsecutivoLST, Defaults(ConsecutivoLST), {Title: gblTipoConsec, Tipo: gblTipoConsec, Valor: Text(gblN)}),
                Patch(ConsecutivoLST, gblContador, {Valor: Text(gblN)})
            ),
            Blank()
        )
    )
);
If(
    !gblReservaOK,
    Notify("Otra persona está creando una solicitud en este momento. No se creó nada. Intenta de nuevo.", NotificationType.Warning);
    UpdateContext({ctxFallo: true}),
    Set(gblNoGuardar, gblTipoConsec & "-" & Text(gblN, "00000"));
    Set(
        gblHdr,
        IfError(
            Patch(
                SolicitudesLST,
                Defaults(SolicitudesLST),
                {
                    Title: gblNoGuardar,
                    Solicitante: UsuarioActual,
                    SolicitanteEmail: gblUserEmail,
                    CentroCosto: {Id: nuevaCentro.Selected.Id, Value: nuevaCentro.Selected.Cod},
                    CentroCostoCod: nuevaCentro.Selected.Cod,
                    Motivo: Trim(nuevaMotivo.Text),
                    FechaSolicitud: Today(),
                    MontoTotal: gblTotal,
                    Estado: {Value: gblEstadoNuevo},
                    NivelActual: gblNivelNuevo,
                    AprobadorEmail: gblAprobNuevo,
                    RequiereFinanzas: gblTotal >= gblUmbral,
                    FechaEnvio: ''' + fecha_envio_new + '''
                }
            ),
            Blank()
        )
    );
    If(
        IsBlank(gblHdr),
        Notify("No se pudo crear la solicitud. Intenta de nuevo.", NotificationType.Error);
        UpdateContext({ctxFallo: true})
    )
)'''
    editar = '''Set(gblNoGuardar, gblEditNo);
Set(gblHdr, gblEdit)'''
    hijos = '''ClearCollect(colOld, Filter(GastosLST, Title = gblNoGuardar));
Clear(colCreados);
IfError(
    ForAll(
        colGastosNuevo As G,
        Collect(
            colCreados,
            Patch(
                GastosLST,
                Defaults(GastosLST),
                {
                    Title: gblNoGuardar,
                    Solicitud: {Id: gblHdr.ID, Value: gblNoGuardar},
                    Categoria: {Id: G.CatId, Value: G.Cat},
                    CategoriaNombre: G.Cat,
                    FechaGasto: G.Fecha,
                    Proveedor: G.Prov,
                    Descripcion: G.Desc,
                    Monto: G.Monto,
                    NumeroRecibo: G.Recibo
                }
            )
        )
    );
    true,
    UpdateContext({ctxFallo: true})
);
If(
    !ctxFallo && gblEditId > 0,
    Set(
        gblHdr2,
        IfError(
            Patch(
                SolicitudesLST,
                gblEdit,
                {
                    CentroCosto: {Id: nuevaCentro.Selected.Id, Value: nuevaCentro.Selected.Cod},
                    CentroCostoCod: nuevaCentro.Selected.Cod,
                    Motivo: Trim(nuevaMotivo.Text),
                    MontoTotal: gblTotal,
                    Estado: {Value: gblEstadoNuevo},
                    NivelActual: gblNivelNuevo,
                    AprobadorEmail: gblAprobNuevo,
                    RequiereFinanzas: gblTotal >= gblUmbral,
                    FechaEnvio: ''' + fecha_envio_edit + '''
                }
            ),
            Blank()
        )
    );
    If(IsBlank(gblHdr2), UpdateContext({ctxFallo: true}))
);
If(
    ctxFallo,
    ForAll(colCreados As C, Remove(GastosLST, C));
    If(gblEditId = 0, Remove(SolicitudesLST, gblHdr));
    Notify("No se pudo guardar la solicitud. No se aplicó ningún cambio. Intenta de nuevo.", NotificationType.Error),
    ''' + exito.replace('\n', '\n    ') + '''
)'''
    return ('UpdateContext({ctxMsg: ""});\nIf(\n    ' + cond + ',\n    UpdateContext({ctxMsg: ' + msg_incompleto + '}),\n'
            '    UpdateContext({ctxGuardando: true, ctxFallo: false});\n'
            '    Set(gblTotal, Sum(colGastosNuevo, Monto));\n'
            '    Set(gblEstadoNuevo, ' + estado + ');\n'
            '    Set(gblNivelNuevo, Switch(gblEstadoNuevo, "PendienteJefe", 1, "PendienteFinanzas", 2, 0));\n'
            '    Set(gblAprobNuevo, If(gblEstadoNuevo = "PendienteJefe", Lower(gblUser.JefeEmail), ""));\n'
            '    If(\n        gblEditId = 0,\n        ' + nuevo.replace('\n', '\n        ') + ',\n        '
            + editar.replace('\n', '\n        ') + '\n    );\n'
            '    If(\n        !ctxFallo,\n        ' + hijos.replace('\n', '\n        ') + '\n    );\n'
            '    If(ctxFallo, UpdateContext({ctxGuardando: false}))\n)')


AGREGAR_GASTO = r'''
UpdateContext({ctxMsg: ""});
With(
    {
        _monto: IfError(Value(nuevaMonto.Text), 0),
        _cat: nuevaCategoria.Selected,
        _fecha: nuevaFechaGasto.SelectedDate
    },
    If(
        IsBlank(_cat),
        UpdateContext({ctxMsg: "Selecciona una categoría."}),
        _monto <= 0,
        UpdateContext({ctxMsg: "Ingresa un monto mayor que cero."}),
        _fecha > Today(),
        UpdateContext({ctxMsg: "La fecha del gasto no puede ser futura."}),
        _fecha < DateAdd(Today(), -gblDiasMax, TimeUnit.Days),
        UpdateContext({ctxMsg: "El gasto supera la antigüedad máxima de " & gblDiasMax & " días."}),
        !IsBlank(_cat.Limite) && _monto > _cat.Limite,
        UpdateContext({ctxMsg: "El monto supera el límite de la categoría (" & Text(_cat.Limite, "#,##0") & ")."}),
        _cat.Recibo && IsBlank(Trim(nuevaRecibo.Text)),
        UpdateContext({ctxMsg: "Esta categoría requiere número de recibo."}),
        Collect(
            colGastosNuevo,
            {
                Cat: _cat.Value,
                CatId: _cat.Id,
                Prov: Trim(nuevaProveedor.Text),
                Desc: Trim(nuevaDescripcion.Text),
                Recibo: Trim(nuevaRecibo.Text),
                Fecha: _fecha,
                Monto: _monto
            }
        );
        Reset(nuevaProveedor);
        Reset(nuevaDescripcion);
        Reset(nuevaRecibo);
        Reset(nuevaMonto)
    )
)
'''

NUEVA_ONVISIBLE = r'''
Clear(colGastosNuevo);
UpdateContext({ctxMsg: "", ctxGuardando: false});
If(
    gblEditId > 0,
    Set(gblEdit, LookUp(SolicitudesLST, ID = gblEditId));
    ClearCollect(
        colGastosNuevo,
        ForAll(
            Filter(GastosLST, Title = gblEditNo),
            {
                Cat: CategoriaNombre,
                CatId: Categoria.Id,
                Prov: Proveedor,
                Desc: Descripcion,
                Recibo: NumeroRecibo,
                Fecha: FechaGasto,
                Monto: Monto
            }
        )
    ),
    Set(gblEdit, Blank())
);
Reset(nuevaCentro);
Reset(nuevaMotivo);
Reset(nuevaFechaGasto);
Reset(nuevaProveedor);
Reset(nuevaDescripcion);
Reset(nuevaRecibo);
Reset(nuevaMonto)
'''


def nueva():
    p = 'nueva'
    c = chrome(p, 'NuevaSolicitudScreen', 'Solicitud de reembolso')
    LX = CX + 20
    c += [card('nuevaFormCard', CX, 88, 520, 656),
          label('nuevaFormTitulo', 'If(gblEditId > 0, "Editar " & gblEditNo, "Datos de la solicitud")', LX, 100, 480, 30, size=15, color='ColorOscuro', bold=True),
          label('nuevaLblCentro', '"Centro de costo"', LX, 140, 480, 20, size=11, color='ColorTextoSuave', bold=True),
          dropdown('nuevaCentro', 'colCentros', LX, 162, 480, 38,
                   default='LookUp(colCentros, Cod = If(gblEditId > 0, gblEdit.CentroCosto.Value, gblUser.CentroCosto.Value)).Value'),
          label('nuevaLblMotivo', '"Motivo"', LX, 208, 480, 20, size=11, color='ColorTextoSuave', bold=True),
          textinput('nuevaMotivo', LX, 230, 480, 76, hint='"Describe el motivo del gasto"',
                    default='If(gblEditId > 0, gblEdit.Motivo, "")', multiline=True),
          rect('nuevaSep1', LX, 322, 480, 1, fill='ColorBorde', radius=0),
          label('nuevaLblAgregar', '"Agregar gasto"', LX, 332, 480, 28, size=14, color='ColorOscuro', bold=True),
          label('nuevaLblCat', '"Categoría"', LX, 364, 230, 20, size=11, color='ColorTextoSuave', bold=True),
          dropdown('nuevaCategoria', 'colCategorias', LX, 386, 230, 36),
          label('nuevaLblFecha', '"Fecha del gasto"', LX + 250, 364, 230, 20, size=11, color='ColorTextoSuave', bold=True),
          datepicker('nuevaFechaGasto', LX + 250, 386, 230, 36),
          label('nuevaLblProv', '"Proveedor"', LX, 430, 230, 20, size=11, color='ColorTextoSuave', bold=True),
          textinput('nuevaProveedor', LX, 452, 230, 36),
          label('nuevaLblRecibo', '"Nº de recibo"', LX + 250, 430, 230, 20, size=11, color='ColorTextoSuave', bold=True),
          textinput('nuevaRecibo', LX + 250, 452, 230, 36),
          label('nuevaLblDesc', '"Descripción"', LX, 496, 480, 20, size=11, color='ColorTextoSuave', bold=True),
          textinput('nuevaDescripcion', LX, 518, 480, 36),
          label('nuevaLblMonto', '"Monto (COP)"', LX, 562, 230, 20, size=11, color='ColorTextoSuave', bold=True),
          textinput('nuevaMonto', LX, 584, 230, 36, number=True),
          button('nuevaAgregar', '"+ Agregar gasto"', LX + 250, 584, 230, 36, AGREGAR_GASTO),
          label('nuevaMsg', 'ctxMsg', LX, 632, 480, 96, size=12, color='ColorError', bold=True, valign='Top',
                visible='!IsBlank(ctxMsg)')]
    RX = 786
    c += [card('nuevaListaCard', RX, 88, 556, 656),
          label('nuevaListaTitulo', '"Gastos de la solicitud (" & CountRows(colGastosNuevo) & ")"', RX + 20, 100, 400, 30, size=15, color='ColorOscuro', bold=True),
          rect('nuevaListaLinea', RX, 140, 556, 1, fill='ColorBorde', radius=0)]
    rows = [
        label('nuevaRowCat', 'ThisItem.Cat', 20, 6, 220, 22, size=12, color='ColorOscuro', bold=True, wrap=False),
        label('nuevaRowProv', 'ThisItem.Prov & If(!IsBlank(ThisItem.Recibo), " - " & ThisItem.Recibo, "")', 20, 28, 280, 20, size=11, color='ColorTextoSuave', wrap=False),
        label('nuevaRowFecha', 'Text(ThisItem.Fecha, "dd/mm/yyyy")', 310, 0, 90, 56, size=11, wrap=False),
        label('nuevaRowMonto', money('ThisItem.Monto'), 400, 0, 100, 56, size=12, color='ColorOscuro', bold=True, align='Right', wrap=False),
        icon('nuevaRowQuitar', 'Cancel', 508, 16, 24, 24, onselect='Remove(colGastosNuevo, ThisItem)', color='ColorError'),
        row_sep('nuevaRowSep', 556, 56),
    ]
    c.append(gallery('nuevaGal', 'colGastosNuevo', RX, 142, 556, 340, 56, rows))
    c += [rect('nuevaTotalLinea', RX, 486, 556, 1, fill='ColorBorde', radius=0),
          label('nuevaTotalLbl', '"Total"', RX + 20, 494, 200, 32, size=14, color='ColorTextoSuave', bold=True),
          label('nuevaTotal', money('Sum(colGastosNuevo, Monto)'), RX + 236, 494, 300, 32, size=20, color='ColorOscuro', bold=True, align='Right'),
          label('nuevaNota', 'If(Sum(colGastosNuevo, Monto) >= gblUmbral, "Este monto requiere también la aprobación de Finanzas.", '
                '"Desde " & Text(gblUmbral, "#,##0") & " la solicitud pasa también por Finanzas.")',
                RX + 20, 532, 516, 40, size=11, color='ColorTextoSuave', valign='Top'),
          button('nuevaBorrador', '"Guardar borrador"', RX + 20, 596, 240, 44, guardar_formula(False),
                 fill='Color.White', color='ColorPrimario', border='ColorPrimario', hover='ColorPrimarioClaro',
                 display='If(ctxGuardando, DisplayMode.Disabled, DisplayMode.Edit)'),
          button('nuevaEnviar', '"Enviar a aprobación"', RX + 276, 596, 260, 44, guardar_formula(True),
                 display='If(ctxGuardando, DisplayMode.Disabled, DisplayMode.Edit)'),
          button('nuevaCancelar', '"Cancelar"', RX + 20, 656, 516, 40,
                 'Set(gblEditId, 0);\nNavigate(If(gblEditId > 0, DetalleSolicitudScreen, MisSolicitudesScreen), ScreenTransition.None)',
                 fill='Color.Transparent', color='ColorTextoSuave', hover='ColorFondo', bold=False)]
    props = {'Fill': 'ColorFondo', 'OnVisible': NUEVA_ONVISIBLE}
    return screen_text('NuevaSolicitudScreen', props, c)


# ------------------------------------------------------------------ 4. Detalle

def accion_formula(accion, estado_nuevo, nivel, aprobador, guard, req_comentario=False, req_ref=False, extra_campos='',
                   etiqueta_ok='"Listo."', nivel_bit='gblSel.NivelActual'):
    """Transicion de estado: refresca, valida estado actual, Patch con IfError, luego bitacora."""
    pre = ''
    if req_comentario:
        pre = ('If(\n    IsBlank(Trim(detComentario.Text)),\n    Notify("Escribe un comentario para continuar.", NotificationType.Warning),\n    ')
    if req_ref:
        pre = ('If(\n    IsBlank(Trim(detReferencia.Text)),\n    Notify("Escribe la referencia del pago.", NotificationType.Warning),\n    ')
    cierre = ('\n)' if pre else '')
    body = f'''Refresh(SolicitudesLST);
Set(gblSel, LookUp(SolicitudesLST, ID = gblSelId));
If(
    !({guard}),
    Notify("La solicitud cambió de estado. Se actualizó la pantalla.", NotificationType.Warning),
    Set(gblEstadoAnt, gblSel.Estado.Value);
    Set(
        gblRes,
        IfError(
            Patch(
                SolicitudesLST,
                gblSel,
                {{
                    Estado: {{Value: {estado_nuevo}}},
                    NivelActual: {nivel},
                    AprobadorEmail: {aprobador}{extra_campos}
                }}
            ),
            Blank()
        )
    );
    If(
        IsBlank(gblRes),
        Notify("No se pudo guardar el cambio. Intenta de nuevo.", NotificationType.Error),
        {bitacora_detalle(accion, nivel_bit, estado_nuevo)};
        Set(gblSel, gblRes);
        Reset(detComentario);
        Reset(detReferencia);
        Notify({etiqueta_ok}, NotificationType.Success)
    )
)'''
    if pre:
        body = pre + body.replace('\n', '\n    ') + cierre
    return body


def bitacora_detalle(accion, nivel, nue):
    return ('IfError(\n'
            '            Patch(\n                BitacoraLST,\n                Defaults(BitacoraLST),\n                {\n'
            '                    Title: gblSel.Title,\n'
            '                    Solicitud: {Id: gblSel.ID, Value: gblSel.Title},\n'
            f'                    Accion: {{Value: "{accion}"}},\n'
            f'                    Nivel: {nivel},\n'
            '                    Actor: UsuarioActual,\n'
            '                    ActorEmail: gblUserEmail,\n'
            '                    EstadoAnterior: gblEstadoAnt,\n'
            f'                    EstadoNuevo: {nue},\n'
            '                    Comentario: Trim(detComentario.Text),\n'
            '                    FechaAccion: Now()\n                }\n            );\n            true,\n'
            '            Notify("El cambio se guardó, pero no se pudo escribir en la bitácora.", NotificationType.Warning)\n        )')


ES_DUENO = 'Lower(gblSel.SolicitanteEmail) = gblUserEmail'
GUARD_N1 = ('gblSel.Estado.Value = "PendienteJefe" && !(' + ES_DUENO + ') && (Lower(gblSel.AprobadorEmail) = gblUserEmail || gblRol = "Administrador")')
GUARD_N2 = 'gblSel.Estado.Value = "PendienteFinanzas" && !(' + ES_DUENO + ') && gblEsFinanzas'
PUEDE_APROBAR = '(' + GUARD_N1 + ') || (' + GUARD_N2 + ')'
GUARD_APROBAR = PUEDE_APROBAR
PUEDE_EDITAR = ES_DUENO + ' && gblSel.Estado.Value in ["Borrador", "Devuelta"]'
PUEDE_PAGAR = 'gblEsFinanzas && gblSel.Estado.Value = "Aprobada"'

DET_ONVISIBLE = r'''
Refresh(SolicitudesLST);
Set(gblSel, LookUp(SolicitudesLST, ID = gblSelId));
Set(gblSelNo, gblSel.Title);
Reset(detComentario);
Reset(detReferencia)
'''


def detalle():
    p = 'det'
    c = chrome(p, '', 'Detalle de la solicitud')
    c += [card('detInfoCard', CX, 88, 560, 296),
          label('detNo', 'gblSel.Title', CX + 20, 100, 300, 34, size=20, color='ColorOscuro', bold=True, wrap=False),
          *badge('detEst', CX + 340, 105, 200, 26, 'gblSel.Estado.Value'),
          rect('detInfoLinea', CX, 142, 560, 1, fill='ColorBorde', radius=0)]
    campos = [
        ('Solicitante', 'Coalesce(LookUp(UsuariosRolLST, UsuarioEmail = gblSel.SolicitanteEmail).Title, gblSel.SolicitanteEmail)'),
        ('Centro de costo', 'gblSel.CentroCostoCod'),
        ('Fecha', 'Text(gblSel.FechaSolicitud, "dd/mm/yyyy")'),
        ('Monto total', money('gblSel.MontoTotal')),
        ('Pendiente con', 'Switch(gblSel.Estado.Value, "PendienteJefe", Coalesce(LookUp(UsuariosRolLST, UsuarioEmail = gblSel.AprobadorEmail).Title, gblSel.AprobadorEmail), '
                          '"PendienteFinanzas", "Equipo de Finanzas", "-")'),
    ]
    for i, (t, v) in enumerate(campos):
        y = 152 + i * 30
        c += [label(f'detLbl{i}', f'"{t}"', CX + 20, y, 150, 28, size=11, color='ColorTextoSuave', bold=True),
              label(f'detVal{i}', v, CX + 170, y, 370, 28, size=12, color='ColorOscuro', wrap=False)]
    c += [label('detMotivoLbl', '"Motivo"', CX + 20, 306, 150, 22, size=11, color='ColorTextoSuave', bold=True),
          label('detMotivo', 'gblSel.Motivo', CX + 20, 328, 520, 48, size=12, color='ColorOscuro', valign='Top')]

    AX = 826
    c += [card('detAccCard', AX, 88, 516, 296),
          label('detAccTitulo', '"Acciones"', AX + 20, 100, 300, 30, size=15, color='ColorOscuro', bold=True),
          label('detSinAcc', '"No tienes acciones disponibles para esta solicitud."', AX + 20, 140, 476, 40, size=12, color='ColorTextoSuave',
                valign='Top', visible='!(' + PUEDE_APROBAR + ') && !(' + PUEDE_EDITAR + ') && !(' + PUEDE_PAGAR + ')'),
          # edicion
          button('detEditar', '"Editar solicitud"', AX + 20, 140, 220, 44,
                 'Set(gblEditId, gblSel.ID);\nSet(gblEditNo, gblSel.Title);\nNavigate(NuevaSolicitudScreen, ScreenTransition.None)',
                 fill='Color.White', color='ColorPrimario', border='ColorPrimario', hover='ColorPrimarioClaro',
                 visible=PUEDE_EDITAR),
          button('detEnviar', 'If(gblSel.Estado.Value = "Devuelta", "Reenviar a aprobación", "Enviar a aprobación")', AX + 256, 140, 240, 44,
                 accion_formula('Enviada', 'If(IsBlank(gblUser.JefeEmail) || Lower(gblUser.JefeEmail) = gblUserEmail, "PendienteFinanzas", "PendienteJefe")',
                                'If(IsBlank(gblUser.JefeEmail) || Lower(gblUser.JefeEmail) = gblUserEmail, 2, 1)',
                                'If(IsBlank(gblUser.JefeEmail) || Lower(gblUser.JefeEmail) = gblUserEmail, "", Lower(gblUser.JefeEmail))',
                                PUEDE_EDITAR, extra_campos=',\n                    RequiereFinanzas: gblSel.MontoTotal >= gblUmbral,\n                    FechaEnvio: Now()',
                                etiqueta_ok='"Solicitud enviada a aprobación."', nivel_bit='1'),
                 visible=PUEDE_EDITAR),
          # aprobacion
          label('detComLbl', '"Comentario (obligatorio al devolver o rechazar)"', AX + 20, 140, 476, 20, size=11, color='ColorTextoSuave', bold=True,
                visible=PUEDE_APROBAR),
          textinput('detComentario', AX + 20, 162, 476, 70, hint='"Escribe un comentario"', multiline=True, visible=PUEDE_APROBAR),
          button('detAprobar', '"Aprobar"', AX + 20, 246, 150, 44,
                 accion_formula('AprobadaJefe',
                                'If(gblSel.Estado.Value = "PendienteJefe", If(gblSel.MontoTotal >= gblUmbral, "PendienteFinanzas", "Aprobada"), "Aprobada")',
                                'If(gblSel.Estado.Value = "PendienteJefe" && gblSel.MontoTotal >= gblUmbral, 2, 0)',
                                '""', GUARD_APROBAR, nivel_bit='gblSel.NivelActual',
                                etiqueta_ok='"Solicitud aprobada."').replace('Accion: {Value: "AprobadaJefe"}',
                                                                              'Accion: {Value: If(gblEstadoAnt = "PendienteJefe", "AprobadaJefe", "AprobadaFinanzas")}'),
                 fill='ColorExito', visible=PUEDE_APROBAR),
          button('detDevolver', '"Devolver"', AX + 186, 246, 150, 44,
                 accion_formula('Devuelta', '"Devuelta"', '0', '""', GUARD_APROBAR, req_comentario=True,
                                etiqueta_ok='"Solicitud devuelta al solicitante."'),
                 fill='ColorAcento', visible=PUEDE_APROBAR),
          button('detRechazar', '"Rechazar"', AX + 352, 246, 144, 44,
                 accion_formula('Rechazada', '"Rechazada"', '0', '""', GUARD_APROBAR, req_comentario=True,
                                extra_campos=',\n                    FechaCierre: Now()',
                                etiqueta_ok='"Solicitud rechazada."'),
                 fill='ColorError', visible=PUEDE_APROBAR),
          # pago
          label('detRefLbl', '"Referencia del pago"', AX + 20, 140, 476, 20, size=11, color='ColorTextoSuave', bold=True, visible=PUEDE_PAGAR),
          textinput('detReferencia', AX + 20, 162, 476, 38, hint='"Ej. TRF-2026-1234"', visible=PUEDE_PAGAR),
          button('detPagar', '"Registrar pago"', AX + 20, 214, 476, 44,
                 accion_formula('Pagada', '"Pagada"', '0', '""', PUEDE_PAGAR, req_ref=True,
                                extra_campos=',\n                    ReferenciaPago: Trim(detReferencia.Text),\n                    FechaPago: Today(),\n                    FechaCierre: Now()',
                                etiqueta_ok='"Pago registrado."'),
                 visible=PUEDE_PAGAR)]

    # gastos
    c += [card('detGastosCard', CX, 400, 560, 344),
          label('detGastosTitulo', '"Gastos (" & CountRows(detGastosGal.AllItems) & ")"', CX + 20, 410, 300, 30, size=14, color='ColorOscuro', bold=True),
          rect('detGastosLinea', CX, 446, 560, 1, fill='ColorBorde', radius=0)]
    rows = [
        label('detGRowCat', 'ThisItem.CategoriaNombre', 20, 6, 230, 22, size=12, color='ColorOscuro', bold=True, wrap=False),
        label('detGRowProv', 'ThisItem.Proveedor & If(!IsBlank(ThisItem.NumeroRecibo), " - " & ThisItem.NumeroRecibo, "")', 20, 28, 300, 20, size=11, color='ColorTextoSuave', wrap=False),
        label('detGRowFecha', 'Text(ThisItem.FechaGasto, "dd/mm/yyyy")', 330, 0, 90, 56, size=11, wrap=False),
        label('detGRowMonto', money('ThisItem.Monto'), 420, 0, 120, 56, size=12, color='ColorOscuro', bold=True, align='Right', wrap=False),
        row_sep('detGRowSep', 560, 56),
    ]
    c.append(gallery('detGastosGal', 'Filter(GastosLST, Title = gblSelNo)', CX, 448, 560, 294, 56, rows))

    # bitacora
    c += [card('detBitCard', AX, 400, 516, 344),
          label('detBitTitulo', '"Historial"', AX + 20, 410, 300, 30, size=14, color='ColorOscuro', bold=True),
          rect('detBitLinea', AX, 446, 516, 1, fill='ColorBorde', radius=0)]
    brows = [
        rect('detBRowPunto', 22, 20, 10, 10, fill='ColorPrimario', radius=5),
        label('detBRowAccion', 'Switch(ThisItem.Accion.Value, "AprobadaJefe", "Aprobada por el jefe", "AprobadaFinanzas", "Aprobada por Finanzas", ThisItem.Accion.Value)', 44, 8, 250, 22, size=12, color='ColorOscuro', bold=True, wrap=False),
        label('detBRowFecha', 'Text(ThisItem.FechaAccion, "dd/mm/yyyy hh:mm")', 300, 8, 196, 22, size=11, color='ColorTextoSuave', align='Right', wrap=False),
        label('detBRowActor', 'Coalesce(LookUp(UsuariosRolLST, UsuarioEmail = ThisItem.ActorEmail).Title, ThisItem.ActorEmail) & If(!IsBlank(ThisItem.Comentario), ": " & ThisItem.Comentario, "")',
              44, 30, 452, 40, size=11, color='ColorTextoSuave', valign='Top'),
        row_sep('detBRowSep', 516, 72),
    ]
    c.append(gallery('detBitGal', 'Sort(Filter(BitacoraLST, Title = gblSelNo), ID, SortOrder.Descending)', AX, 448, 516, 294, 72, brows))
    c.append(button('detVolver', '"< Volver"', CX + 460, 14, 100, 36, 'Navigate(MisSolicitudesScreen, ScreenTransition.None)',
                    fill='Color.White', color='ColorPrimario', border='ColorPrimario', hover='ColorPrimarioClaro'))
    props = {'Fill': 'ColorFondo', 'OnVisible': DET_ONVISIBLE}
    return screen_text('DetalleSolicitudScreen', props, c)


# ------------------------------------------------------------------ 5. Bandeja

def bandeja():
    p = 'ban'
    c = chrome(p, 'BandejaScreen', 'Bandeja de aprobación')
    hdr_y = 88
    c.append(card('banCard', CX, hdr_y, CW, 656))
    cols = [('Número', 20, 150), ('Solicitante', 180, 220), ('Centro', 410, 80), ('Monto', 500, 130),
            ('Enviada', 650, 100), ('Espera', 770, 100), ('Nivel', 890, 150)]
    for i, (t, x, w) in enumerate(cols):
        c.append(label(f'banTh{i}', f'"{t}"', CX + x, hdr_y + 8, w, 28, size=11, color='ColorTextoSuave', bold=True,
                       align='Right' if t == 'Monto' else 'Left', wrap=False))
    c.append(rect('banThLinea', CX, hdr_y + 40, CW, 1, fill='ColorBorde', radius=0))
    dias = 'DateDiff(ThisItem.FechaEnvio, Now(), TimeUnit.Days)'
    rows = [
        label('banRowNo', 'ThisItem.Title', 20, 0, 160, 56, size=12, color='ColorOscuro', bold=True, wrap=False),
        label('banRowSol', 'Coalesce(LookUp(UsuariosRolLST, UsuarioEmail = ThisItem.SolicitanteEmail).Title, ThisItem.SolicitanteEmail)', 180, 0, 220, 56, size=12, wrap=False),
        label('banRowCC', 'ThisItem.CentroCostoCod', 410, 0, 80, 56, size=12, wrap=False),
        label('banRowMonto', money('ThisItem.MontoTotal'), 500, 0, 130, 56, size=12, color='ColorOscuro', bold=True, align='Right', wrap=False),
        label('banRowFecha', 'Text(ThisItem.FechaEnvio, "dd/mm/yyyy")', 650, 0, 100, 56, size=12, wrap=False),
        rect('banRowAlertaBg', 770, 16, 90, 24, fill='If(' + dias + ' >= gblDiasAlerta, ColorValue("#FEF3C7"), ColorFondo)', radius=12),
        label('banRowDias', dias + ' & If(' + dias + ' = 1, " día", " días")', 770, 16, 90, 24, size=11,
              color='If(' + dias + ' >= gblDiasAlerta, ColorValue("#92400E"), ColorTextoSuave)', bold=True, align='Center', wrap=False),
        *badge('banRowNivel', 890, 16, 150, 24, 'ThisItem.Estado.Value'),
        row_sep('banRowSep', CW, 56),
    ]
    c.append(gallery('banGal', 'Sort(colBandeja, FechaEnvio, SortOrder.Ascending)', CX, hdr_y + 42, CW, 612, 56, rows, onselect=abrir_detalle('banGal')))
    c.append(label('banVacio', '"No tienes solicitudes pendientes. Buen trabajo."', CX, hdr_y + 200, CW, 40, size=14,
                   color='ColorTextoSuave', align='Center', visible='CountRows(colBandeja) = 0'))
    props = {'Fill': 'ColorFondo',
             'OnVisible': 'Refresh(SolicitudesLST);\n' + BANDEJA_LOAD}
    return screen_text('BandejaScreen', props, c)


# ------------------------------------------------------------------ 6. Reportes

PERIODOS = 'Table({Value: "Últimos 30 días", Dias: 30}, {Value: "Últimos 90 días", Dias: 90}, {Value: "Últimos 180 días", Dias: 180}, {Value: "Últimos 365 días", Dias: 365})'

REP_CARGA = r'''
Set(gblDesde, DateAdd(Today(), -repPeriodo.Selected.Dias, TimeUnit.Days));
ClearCollect(colRepSol, Filter(SolicitudesLST, FechaSolicitud >= gblDesde));
ClearCollect(colRepGas, Filter(GastosLST, FechaGasto >= gblDesde));
ClearCollect(
    colRepEstado,
    Sort(
        DropColumns(AddColumns(GroupBy(AddColumns(colRepSol, Grupo, Estado.Value), Grupo, g), Total, Sum(g, MontoTotal)), g),
        Total,
        SortOrder.Descending
    )
);
ClearCollect(
    colRepCentro,
    Sort(
        DropColumns(AddColumns(GroupBy(colRepSol, CentroCostoCod, g), Total, Sum(g, MontoTotal)), g),
        Total,
        SortOrder.Descending
    )
);
ClearCollect(
    colRepCategoria,
    Sort(
        DropColumns(AddColumns(GroupBy(colRepGas, CategoriaNombre, g), Total, Sum(g, Monto)), g),
        Total,
        SortOrder.Descending
    )
)
'''


def reportes():
    p = 'rep'
    c = chrome(p, 'ReportesScreen', 'Reportes')
    c += [label('repPeriodoLbl', '"Período"', CX, 88, 80, 36, size=12, color='ColorTextoSuave', bold=True),
          dropdown('repPeriodo', PERIODOS, CX + 80, 88, 220, 36, default='"Últimos 180 días"',
                   extra={'OnChange': REP_CARGA})]
    kw, kg = 258, 22
    kx = [CX + i * (kw + kg) for i in range(4)]
    c += kpi(p, 1, kx[0], 140, kw, 100, money('Sum(colRepSol, MontoTotal)'), '"Total solicitado"', 'ColorPrimario')
    c += kpi(p, 2, kx[1], 140, kw, 100, money('Sum(Filter(colRepSol, Estado.Value = "Pagada"), MontoTotal)'), '"Total pagado"', 'ColorExito')
    c += kpi(p, 3, kx[2], 140, kw, 100,
             money('Sum(Filter(colRepSol, Estado.Value in ["PendienteJefe", "PendienteFinanzas", "Aprobada"]), MontoTotal)'),
             '"Por aprobar o pagar"', 'ColorAcento')
    c += kpi(p, 4, kx[3], 140, kw, 100,
             # Average sobre una tabla vacia da error: se valida antes con CountRows
             'With({_p: Filter(colRepSol, Estado.Value = "Pagada")}, If(CountRows(_p) = 0, "-", Text(Average(_p, DateDiff(FechaEnvio, FechaCierre, TimeUnit.Days)), "0.0") & " días"))',
             '"Tiempo medio hasta el pago"', 'ColorInfo')
    secciones = [
        ('Estado', 'Por estado', 'colRepEstado', 'ThisItem.Grupo'),
        ('Centro', 'Por centro de costo', 'colRepCentro', 'ThisItem.CentroCostoCod'),
        ('Categoria', 'Por categoría de gasto', 'colRepCategoria', 'ThisItem.CategoriaNombre'),
    ]
    sx = [CX, CX + 374, CX + 748]
    for (key, titulo, items, nombre), x in zip(secciones, sx):
        gal = f'rep{key}Gal'
        c += [card(f'rep{key}Card', x, 264, 350, 480),
              label(f'rep{key}Titulo', f'"{titulo}"', x + 20, 276, 310, 30, size=14, color='ColorOscuro', bold=True),
              rect(f'rep{key}Linea', x, 312, 350, 1, fill='ColorBorde', radius=0)]
        # El maximo se calcula sobre la coleccion: una galeria no puede leer su propio AllItems desde la plantilla.
        ancho = 'Max(6, ThisItem.Total / Max(1, Max(' + items + ', Total)) * 306)'
        rows = [
            label(f'rep{key}RowNombre', nombre if key != 'Estado' else 'Coalesce(LookUp(EstadosMeta, Raw = ThisItem.Grupo).Texto, ThisItem.Grupo)',
                  20, 6, 200, 22, size=11, color='ColorTexto', bold=True, wrap=False),
            label(f'rep{key}RowValor', money('ThisItem.Total'), 150, 6, 176, 22, size=11, color='ColorOscuro', align='Right', wrap=False),
            rect(f'rep{key}RowBase', 20, 34, 310, 10, fill='ColorFondo', radius=5),
            rect(f'rep{key}RowBarra', 22, 34, 0, 10, fill='ColorPrimario', radius=5, extra={}),
        ]
        rows[-1].props['Width'] = ancho
        rows[-1].props['X'] = '20'
        c.append(gallery(gal, items, x, 316, 350, 424, 56, rows))
    props = {'Fill': 'ColorFondo',
             'OnVisible': 'If(!gblEsFinanzas, Navigate(InicioScreen, ScreenTransition.None));\nReset(repPeriodo);\n' + REP_CARGA.strip()}
    return screen_text('ReportesScreen', props, c)


# ------------------------------------------------------------------ main

if __name__ == '__main__':
    write('App.fx.yaml', app_yaml())
    for fn, name in [(inicio, 'InicioScreen'), (mis_solicitudes, 'MisSolicitudesScreen'), (nueva, 'NuevaSolicitudScreen'),
                     (detalle, 'DetalleSolicitudScreen'), (bandeja, 'BandejaScreen'), (reportes, 'ReportesScreen')]:
        write(name + '.fx.yaml', fn())
        print('OK', name)
