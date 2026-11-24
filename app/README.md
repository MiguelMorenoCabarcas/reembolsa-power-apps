# Reembolsa — app Power Apps

App Canvas (tablet 1366x768) sobre las 8 listas de SharePoint descritas en
[../docs/01-Diseno-y-Modelo-de-Datos.md](../docs/01-Diseno-y-Modelo-de-Datos.md).

## Pantallas

| Pantalla | Para qué | Quién la ve |
|---|---|---|
| `InicioScreen` | Tarjetas (borradores, en trámite, devueltas, por aprobar), últimas solicitudes y accesos rápidos | Todos |
| `MisSolicitudesScreen` | Lista con búsqueda por número y filtro por estado. Finanzas y Administrador pueden alternar a "todas" | Todos |
| `NuevaSolicitudScreen` | Crear o editar: encabezado, líneas de gasto con validaciones, guardar borrador o enviar | Todos |
| `DetalleSolicitudScreen` | Datos, gastos, historial y acciones según rol y estado (editar, enviar, aprobar, devolver, rechazar, pagar) | Todos |
| `BandejaScreen` | Pendientes del usuario (jefe asignado) o de Finanzas, con días de espera | Aprobador, Finanzas, Administrador |
| `ReportesScreen` | Totales por estado, centro de costo y categoría, y tiempo medio hasta el pago | Finanzas, Administrador |

## Estructura

| Ruta | Contenido |
|---|---|
| `tools/listas.json` | Plantilla con la URL del sitio, los IDs de las listas y sus columnas. Copiar a `listas.local.json` con valores reales (ese archivo no se versiona) |
| `tools/generar-datos.py` | Genera `DataSources`, esquemas de tabla (`pkgs/TableDefinitions`), conexión y manifiesto |
| `tools/yamlgen.py` | Mini-DSL que emite controles Power Apps (label, button, gallery…) en el formato `.fx.yaml` |
| `tools/generar-pantallas.py` | `App.fx.yaml` y las 6 pantallas con sus fórmulas |
| `src/` | Fuentes en el layout `Experimental` de `pac canvas` (plantillas de controles de Microsoft incluidas) |

```powershell
python tools\generar-datos.py
python tools\generar-pantallas.py
pac canvas pack --sources src --msapp dist\Reembolsa.msapp --overwrite
```

## Cómo importar

1. En Power Apps crea una app de lienzo en blanco (tableta).
2. En Studio: **Archivo → Abrir → Examinar** y elige `dist/Reembolsa.msapp`.
3. Si alguna lista no carga, ve a **Datos**, quita la fuente que falle y vuelve a agregarla (mismo nombre de lista).
4. Revisa el **Comprobador de aplicaciones**.
5. Ejecuta la app (F5). En modo diseño las colecciones están vacías hasta que corre `OnStart` y el `OnVisible` de cada pantalla.

> Si cambias el idioma de Studio, cambia también el separador de argumentos: las fórmulas de los `.fx.yaml` usan coma;
> en un Studio en español se muestran con `;`.

## Prueba por rol

La cuenta que ejecutó el script de aprovisionamiento queda como **Administrador Demo**. Los usuarios de ejemplo son
ficticios (`@reembolsa.example`); para probar otros roles, cambia el `Rol` de esa fila en `UsuariosRolLST`.

| Rol | Qué debe poder hacer |
|---|---|
| Solicitante | Crear solicitud, agregar gastos, guardar borrador, enviar; ver devueltas y editarlas. No ve Bandeja ni Reportes |
| Aprobador | Lo anterior + Bandeja con las solicitudes donde es el jefe asignado |
| Finanzas / Administrador | Bandeja de nivel Finanzas, registrar pago, Reportes |

Casos a probar:
- Gasto con fecha futura o de más de 60 días → mensaje de error.
- Gasto sobre el límite de la categoría → mensaje.
- Categoría con recibo obligatorio sin número de recibo → mensaje.
- Solicitud ≥ 1.000.000 → pasa a Finanzas tras el jefe; menor → queda Aprobada tras el jefe.
- Nadie aprueba su propia solicitud (los botones no aparecen).
- Devolver o rechazar sin comentario → aviso; con comentario → queda en el historial.
- Dos personas creando solicitudes a la vez → una recibe un aviso y no se crea nada.

## Problemas conocidos

- **Adjuntos de recibos:** v0.x exige el número de recibo pero no sube el archivo.
- **Reportes y KPIs** se calculan en la app sobre hasta 500 filas del período.
- **Columnas de persona** (`Solicitante`, `Actor`) quedan vacías en los datos de prueba porque los usuarios ficticios no existen en el tenant; la app filtra por las columnas de correo.
