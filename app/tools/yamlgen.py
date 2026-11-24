"""Mini-DSL para emitir pantallas de Power Apps (layout Experimental: src/Src/*.fx.yaml).

Cada control se describe con (tipo, nombre, propiedades). Las propiedades son formulas Power Fx
(se antepone '=' si falta). Las formulas de varias lineas o con ': ' van como bloque '|-'.
"""
import re
import textwrap


class Ctl:
    def __init__(self, kind, name, props=None, children=None):
        self.kind = kind
        self.name = name
        self.props = dict(props or {})
        self.children = list(children or [])


def _fx(expr):
    expr = textwrap.dedent(expr).strip('\n')
    # sin lineas en blanco dentro del bloque (PA3003) y sin espacios finales
    lines = [ln.rstrip() for ln in expr.split('\n') if ln.strip() != '']
    expr = '\n'.join(lines)
    if not expr.startswith('='):
        expr = '=' + expr
    return expr


def _prop(key, expr, pad):
    expr = _fx(expr)
    needs_block = ('\n' in expr) or (': ' in expr) or ('#' in expr) or expr.rstrip().endswith(':')
    if needs_block:
        out = [f'{pad}{key}: |-']
        out += [f'{pad}    {ln}' for ln in expr.split('\n')]
        return out
    return [f'{pad}{key}: {expr}']


def render(ctl, level=1):
    pad = '    ' * level
    out = [f'{pad}{ctl.name} As {ctl.kind}:']
    props = dict(ctl.props)
    z = 1
    for ch in ctl.children:
        ch.props.setdefault('ZIndex', str(z))
        z += 1
    for k in sorted(props):
        out += _prop(k, props[k], pad + '    ')
    for ch in ctl.children:
        out.append('')
        out += render(ch, level + 1)
    return out


def screen_text(name, props, children):
    """Devuelve el contenido de <name>.fx.yaml"""
    out = [f'{name} As screen:']
    for k in sorted(props):
        out += _prop(k, props[k], '    ')
    z = 1
    for ch in children:
        ch.props.setdefault('ZIndex', str(z))
        z += 1
        out.append('')
        out += render(ch, 1)
    return '\n'.join(out) + '\n'


# ------------------------------------------------------------------ helpers de controles

def _geo(x, y, w, h):
    return {'X': str(x), 'Y': str(y), 'Width': str(w), 'Height': str(h)}


FONT = "Font.'Open Sans'"


def label(name, text, x, y, w, h, size=12, color='ColorTexto', bold=False, align='Left',
          visible=None, wrap=True, valign='Middle', fill=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'Text': text, 'Size': str(size), 'Color': color, 'Font': FONT,
              'FontWeight': 'FontWeight.Bold' if bold else 'FontWeight.Normal',
              'Align': f'Align.{align}', 'VerticalAlign': f'VerticalAlign.{valign}',
              'Wrap': 'true' if wrap else 'false', 'PaddingLeft': '0', 'PaddingRight': '0',
              'PaddingTop': '0', 'PaddingBottom': '0'})
    if visible is not None:
        p['Visible'] = visible
    if fill:
        p['Fill'] = fill
    if extra:
        p.update(extra)
    return Ctl('label', name, p)


def rect(name, x, y, w, h, fill='ColorTarjeta', radius=8, border=None, visible=None, extra=None):
    p = _geo(x, y, w, h)
    p['Fill'] = fill
    r = str(radius)
    p.update({'RadiusTopLeft': r, 'RadiusTopRight': r, 'RadiusBottomLeft': r, 'RadiusBottomRight': r})
    if border:
        p.update({'BorderColor': border, 'BorderThickness': '1', 'BorderStyle': 'BorderStyle.Solid'})
    else:
        p.update({'BorderThickness': '0'})
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl('rectangle', name, p)


def button(name, text, x, y, w, h, onselect, fill='ColorPrimario', color='Color.White', size=12,
           visible=None, display=None, hover=None, border=None, radius=8, bold=True, align='Center',
           extra=None):
    p = _geo(x, y, w, h)
    p.update({'Text': text, 'OnSelect': onselect, 'Fill': fill, 'Color': color, 'Size': str(size),
              'Font': FONT, 'FontWeight': 'FontWeight.Semibold' if bold else 'FontWeight.Normal',
              'Align': f'Align.{align}',
              'HoverFill': hover or fill,
              'PressedFill': hover or fill,
              'HoverColor': color, 'PressedColor': color,
              'BorderThickness': '1' if border else '0', 'BorderColor': border or fill,
              'DisabledFill': 'ColorBorde', 'DisabledColor': 'ColorTextoSuave',
              'RadiusTopLeft': str(radius), 'RadiusTopRight': str(radius),
              'RadiusBottomLeft': str(radius), 'RadiusBottomRight': str(radius)})
    if visible is not None:
        p['Visible'] = visible
    if display is not None:
        p['DisplayMode'] = display
    if extra:
        p.update(extra)
    return Ctl('button', name, p)


def icon(name, icon_name, x, y, w, h, onselect='false', color='ColorTextoSuave', visible=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'Icon': f'Icon.{icon_name}', 'Color': color, 'OnSelect': onselect,
              'PaddingTop': '4', 'PaddingBottom': '4', 'PaddingLeft': '4', 'PaddingRight': '4'})
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl(f'icon.{icon_name}', name, p)


def textinput(name, x, y, w, h, hint='""', default='""', multiline=False, number=False, size=12,
              visible=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'Default': default, 'HintText': hint, 'Size': str(size), 'Font': FONT,
              'Color': 'ColorTexto', 'Fill': 'Color.White', 'BorderColor': 'ColorBorde',
              'HoverBorderColor': 'ColorPrimario', 'PressedBorderColor': 'ColorPrimario',
              'FocusedBorderColor': 'ColorPrimario', 'BorderThickness': '1',
              'RadiusTopLeft': '6', 'RadiusTopRight': '6', 'RadiusBottomLeft': '6', 'RadiusBottomRight': '6'})
    if multiline:
        p['Mode'] = 'TextMode.MultiLine'
    if number:
        p['Format'] = 'TextFormat.Number'
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl('text', name, p)


def dropdown(name, items, x, y, w, h, default=None, size=12, visible=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'Items': items, 'Size': str(size), 'Font': FONT, 'Color': 'ColorTexto', 'Fill': 'Color.White',
              'BorderColor': 'ColorBorde', 'BorderThickness': '1',
              'ChevronBackground': 'ColorPrimario', 'ChevronFill': 'Color.White',
              'SelectionFill': 'ColorPrimario', 'SelectionColor': 'Color.White',
              'HoverColor': 'ColorTexto', 'HoverFill': 'ColorFondo'})
    if default is not None:
        p['Default'] = default
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl('dropdown', name, p)


def datepicker(name, x, y, w, h, default='Today()', size=12, visible=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'DefaultDate': default, 'Size': str(size), 'Font': FONT, 'Color': 'ColorTexto',
              'Fill': 'Color.White', 'BorderColor': 'ColorBorde', 'BorderThickness': '1',
              'IconBackground': 'ColorPrimario', 'IconFill': 'Color.White',
              'StartYear': 'Year(Today()) - 2', 'EndYear': 'Year(Today())'})
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl('datepicker', name, p)


def gallery(name, items, x, y, w, h, row_h, children, visible=None, onselect=None, extra=None):
    p = _geo(x, y, w, h)
    p.update({'Items': items, 'TemplateSize': str(row_h), 'TemplatePadding': '0',
              'Layout': 'Layout.Vertical', 'ShowScrollbar': 'true', 'WrapCount': '1',
              'TemplateFill': 'Color.Transparent', 'Fill': 'Color.Transparent',
              'BorderThickness': '0', 'LoadingSpinner': 'LoadingSpinner.Data'})
    if onselect:
        p['OnSelect'] = onselect
    if visible is not None:
        p['Visible'] = visible
    if extra:
        p.update(extra)
    return Ctl('gallery.galleryVertical', name, p, children)


def card(name, x, y, w, h):
    return rect(name, x, y, w, h, fill='ColorTarjeta', radius=10, border='ColorBorde')


def row_sep(name, w, row_h):
    return rect(name, 0, row_h - 1, w, 1, fill='ColorBorde', radius=0)


def badge(prefix, x, y, w, h, estado_expr):
    """Insignia de estado: rectangulo redondeado + etiqueta, segun EstadosMeta (App.Formulas)."""
    meta = f'LookUp(EstadosMeta, Raw = {estado_expr})'
    return [
        rect(f'{prefix}Fondo', x, y, w, h, fill=f'{meta}.Fondo', radius=h // 2),
        label(f'{prefix}Texto', f'{meta}.Texto', x, y, w, h, size=11, color=f'{meta}.Letra',
              bold=True, align='Center', wrap=False),
    ]
