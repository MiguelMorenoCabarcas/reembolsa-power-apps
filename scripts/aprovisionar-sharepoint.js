/*
 * Reembolsa - aprovisionamiento del sitio de SharePoint desde la consola del navegador.
 *
 * Crea las 8 listas (columnas, indices, claves unicas) y, opcionalmente, carga datos de demostracion
 * ficticios. No necesita registrar ninguna aplicacion: usa la sesion del navegador y la API REST del sitio.
 *
 * USO
 *   1. Abre el sitio de SharePoint (por ejemplo https://TU-TENANT.sharepoint.com/sites/Reembolsa)
 *      con una cuenta que sea propietaria del sitio.
 *   2. Abre las herramientas de desarrollo (F12) -> Consola y pega TODO este archivo. Enter.
 *   3. Ejecuta, en este orden (cada paso puede tardar un minuto):
 *        await reembolsa.crearListas();
 *        await reembolsa.cargarDatosDemo();            // opcional
 *
 *   Las dos funciones son idempotentes en lo que se puede: crearListas() no duplica listas ni columnas.
 *   cargarDatosDemo() agrega datos cada vez que se ejecuta; correla una sola vez.
 *
 * NOTA: el sitio debe ser nuevo y de uso exclusivo para la demo. El codigo se ejecuto por partes contra un
 * sitio de comunicacion en espanol; si tu sitio tiene otro idioma, revisa los nombres internos de las columnas.
 */
(() => {
  const S = location.origin + location.pathname.split('/').slice(0, 3).join('/'); // https://tenant/sites/NombreSitio

  // ---------------------------------------------------------------- utilidades REST
  let _dg = null, _dgT = 0;
  const dig = async () => {
    if (_dg && Date.now() - _dgT < 15 * 60e3) return _dg;
    const d = await (await fetch(S + '/_api/contextinfo', { method: 'POST', credentials: 'same-origin', headers: { Accept: 'application/json;odata=nometadata' } })).json();
    _dg = d.FormDigestValue; _dgT = Date.now();
    return _dg;
  };
  const sp = async (path, { method = 'GET', body, merge = false } = {}) => {
    const headers = { Accept: 'application/json;odata=verbose' };
    if (method !== 'GET') {
      headers['Content-Type'] = 'application/json;odata=verbose';
      headers['X-RequestDigest'] = await dig();
      if (merge) { headers['X-HTTP-Method'] = 'MERGE'; headers['IF-MATCH'] = '*'; }
    }
    const r = await fetch(S + path, { method: merge ? 'POST' : method, credentials: 'same-origin', headers, body: body ? JSON.stringify(body) : undefined });
    const t = await r.text();
    if (!r.ok) throw new Error(r.status + ' ' + path + ' ' + t.slice(0, 300));
    return t ? JSON.parse(t) : null;
  };
  const lt = (t) => `/_api/web/lists/getbytitle('${t}')`;

  // ---------------------------------------------------------------- esquema
  const estados = ['Borrador', 'PendienteJefe', 'PendienteFinanzas', 'Aprobada', 'Devuelta', 'Rechazada', 'Pagada'];
  const acciones = ['Creada', 'Enviada', 'AprobadaJefe', 'AprobadaFinanzas', 'Devuelta', 'Rechazada', 'Pagada', 'Comentario'];
  const roles = ['Solicitante', 'Aprobador', 'Finanzas', 'Administrador'];

  // [nombre, tipo, opciones]  tipos: Text, Note, Number, Boolean, Date, DateTime, User, Choice, Lookup
  const SCHEMA = {
    CentrosCostoLST: { titleUnique: true, fields: [['Nombre', 'Text', { req: 1 }], ['Responsable', 'User'], ['Activo', 'Boolean', { def: '1' }]], view: ['Nombre', 'Responsable', 'Activo'] },
    CategoriasGastoLST: { titleUnique: true, fields: [['LimiteMonto', 'Number'], ['RequiereRecibo', 'Boolean', { def: '1' }], ['Activo', 'Boolean', { def: '1' }]], view: ['LimiteMonto', 'RequiereRecibo', 'Activo'] },
    UsuariosRolLST: { fields: [['Usuario', 'User'], ['UsuarioEmail', 'Text', { req: 1, idx: 1, uniq: 1 }], ['Rol', 'Choice', { req: 1, choices: roles, def: 'Solicitante' }], ['CentroCosto', 'Lookup', { target: 'CentrosCostoLST' }], ['JefeEmail', 'Text'], ['Activo', 'Boolean', { def: '1' }]], view: ['UsuarioEmail', 'Rol', 'CentroCosto', 'JefeEmail', 'Activo'] },
    ParametrosLST: { titleUnique: true, fields: [['Valor', 'Text', { req: 1 }]], view: ['Valor'] },
    ConsecutivoLST: { titleUnique: true, fields: [['Tipo', 'Text', { req: 1, idx: 1 }], ['Valor', 'Text', { req: 1, def: '0' }]], view: ['Tipo', 'Valor'] },
    SolicitudesLST: { titleUnique: true, fields: [['Solicitante', 'User'], ['SolicitanteEmail', 'Text', { req: 1, idx: 1 }], ['CentroCosto', 'Lookup', { target: 'CentrosCostoLST' }], ['CentroCostoCod', 'Text'], ['Motivo', 'Note'], ['FechaSolicitud', 'Date'], ['MontoTotal', 'Number', { def: '0' }], ['Estado', 'Choice', { req: 1, choices: estados, def: 'Borrador', idx: 1 }], ['NivelActual', 'Number', { def: '0', idx: 1 }], ['AprobadorEmail', 'Text', { idx: 1 }], ['RequiereFinanzas', 'Boolean', { def: '0' }], ['FechaEnvio', 'DateTime'], ['FechaCierre', 'DateTime'], ['ReferenciaPago', 'Text'], ['FechaPago', 'Date']], view: ['SolicitanteEmail', 'CentroCostoCod', 'MontoTotal', 'Estado', 'NivelActual', 'AprobadorEmail', 'FechaSolicitud'] },
    GastosLST: { titleIdx: true, fields: [['Solicitud', 'Lookup', { target: 'SolicitudesLST' }], ['Categoria', 'Lookup', { target: 'CategoriasGastoLST' }], ['CategoriaNombre', 'Text'], ['FechaGasto', 'Date', { req: 1 }], ['Proveedor', 'Text'], ['Descripcion', 'Text'], ['Monto', 'Number', { req: 1 }], ['NumeroRecibo', 'Text']], view: ['CategoriaNombre', 'FechaGasto', 'Proveedor', 'Monto'] },
    BitacoraLST: { titleIdx: true, fields: [['Solicitud', 'Lookup', { target: 'SolicitudesLST' }], ['Accion', 'Choice', { req: 1, choices: acciones }], ['Nivel', 'Number', { def: '0' }], ['Actor', 'User'], ['ActorEmail', 'Text'], ['EstadoAnterior', 'Text'], ['EstadoNuevo', 'Text'], ['Comentario', 'Note'], ['FechaAccion', 'DateTime']], view: ['Accion', 'Nivel', 'ActorEmail', 'EstadoNuevo', 'FechaAccion'] },
  };

  const fieldXml = async (n, t, o = {}) => {
    const req = o.req ? 'TRUE' : 'FALSE';
    const ix = (o.idx || o.uniq) ? " Indexed='TRUE'" : '';
    const un = o.uniq ? " EnforceUniqueValues='TRUE'" : '';
    // DisplayName = Name (sin espacios ni tildes) para que Power Apps use el mismo nombre en las formulas
    const c = `DisplayName='${n}' Name='${n}' StaticName='${n}' Required='${req}'${ix}${un}`;
    const d = (o.def !== undefined) ? `<Default>${o.def}</Default>` : '';
    switch (t) {
      case 'Text': return `<Field Type='Text' ${c} MaxLength='255'>${d}</Field>`;
      case 'Note': return `<Field Type='Note' ${c} NumLines='6' RichText='FALSE' />`;
      case 'Number': return `<Field Type='Number' ${c} Decimals='0'>${d}</Field>`;
      case 'Boolean': return `<Field Type='Boolean' ${c}>${d}</Field>`;
      case 'Date': return `<Field Type='DateTime' ${c} Format='DateOnly' />`;
      case 'DateTime': return `<Field Type='DateTime' ${c} Format='DateTime' />`;
      case 'User': return `<Field Type='User' ${c} UserSelectionMode='PeopleOnly' UserSelectionScope='0' />`;
      case 'Choice': return `<Field Type='Choice' ${c} Format='Dropdown'><CHOICES>${o.choices.map((x) => `<CHOICE>${x}</CHOICE>`).join('')}</CHOICES>${d}</Field>`;
      case 'Lookup': { const L = await sp(lt(o.target) + '?$select=Id'); return `<Field Type='Lookup' ${c} List='{${L.d.Id}}' ShowField='Title' />`; }
    }
  };

  // IMPORTANTE: buscar por nombre interno. En un sitio en espanol 'Nombre' y 'Tipo' coinciden con columnas
  // del sistema si se busca por titulo (getbyinternalnameortitle) y la columna se daria por existente.
  const hasField = async (list, n) => (await sp(lt(list) + `/fields?$select=InternalName&$filter=InternalName eq '${n}'`)).d.results.length > 0;

  const buildList = async (name) => {
    const sc = SCHEMA[name]; const log = [];
    const titleF = lt(name) + "/fields/getbyinternalnameortitle('Title')";
    await sp(titleF, { method: 'POST', merge: true, body: { __metadata: { type: 'SP.Field' }, Title: 'Title' } });
    if (sc.titleUnique || sc.titleIdx) {
      await sp(titleF, { method: 'POST', merge: true, body: { __metadata: { type: 'SP.Field' }, Indexed: true } });
      if (sc.titleUnique) await sp(titleF, { method: 'POST', merge: true, body: { __metadata: { type: 'SP.Field' }, EnforceUniqueValues: true } });
    }
    for (const [n, t, o] of sc.fields) {
      if (await hasField(name, n)) { log.push(n + ' (existe)'); continue; }
      try {
        const xml = await fieldXml(n, t, o || {});
        await sp(lt(name) + '/fields/createfieldasxml', { method: 'POST', body: { parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: xml, Options: 8 } } });
        log.push(n);
      } catch (e) { log.push('ERROR ' + n + ': ' + e.message.slice(0, 200)); }
    }
    for (const v of sc.view) {
      try { await sp(lt(name) + `/defaultview/viewfields/addviewfield('${v}')`, { method: 'POST' }); } catch (e) { /* ya estaba */ }
    }
    return name + ': ' + log.join(', ');
  };

  const crearListas = async () => {
    const out = [];
    for (const n of Object.keys(SCHEMA)) {
      const ex = await fetch(S + lt(n) + '?$select=Id', { credentials: 'same-origin', headers: { Accept: 'application/json;odata=verbose' } });
      if (ex.ok) { out.push(n + ': ya existe'); continue; }
      await sp('/_api/web/lists', { method: 'POST', body: { __metadata: { type: 'SP.List' }, Title: n, BaseTemplate: 100, Description: 'Reembolsa - demo', OnQuickLaunch: true } });
      out.push(n + ': creada');
    }
    // los lookups necesitan que todas las listas existan
    for (const n of Object.keys(SCHEMA)) out.push(await buildList(n));
    console.log(out.join('\n'));
    return out;
  };

  // ---------------------------------------------------------------- datos de demostracion (ficticios)
  const rng = (seed) => () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };

  const cargarDatosDemo = async ({ asignarAlPropietario = true } = {}) => {
    const R = rng(2026);
    const ri = (a, b) => Math.floor(R() * (b - a + 1)) + a;
    const pick = (a) => a[Math.floor(R() * a.length)];
    const r1000 = (x) => Math.round(x / 1000) * 1000;
    const D = 'reembolsa.example'; // dominio reservado: no existe, son correos ficticios
    const U = {
      camila: { n: 'Camila Ríos', e: `camila.rios@${D}`, rol: 'Administrador', cc: 'CC-100', jefe: '' },
      andres: { n: 'Andrés Pardo', e: `andres.pardo@${D}`, rol: 'Finanzas', cc: 'CC-500', jefe: `camila.rios@${D}` },
      valentina: { n: 'Valentina Mora', e: `valentina.mora@${D}`, rol: 'Finanzas', cc: 'CC-500', jefe: `camila.rios@${D}` },
      sergio: { n: 'Sergio Beltrán', e: `sergio.beltran@${D}`, rol: 'Aprobador', cc: 'CC-200', jefe: `camila.rios@${D}` },
      luisa: { n: 'Luisa Herrera', e: `luisa.herrera@${D}`, rol: 'Aprobador', cc: 'CC-300', jefe: `camila.rios@${D}` },
      daniel: { n: 'Daniel Cortés', e: `daniel.cortes@${D}`, rol: 'Solicitante', cc: 'CC-200', jefe: `sergio.beltran@${D}` },
      mariana: { n: 'Mariana Duarte', e: `mariana.duarte@${D}`, rol: 'Solicitante', cc: 'CC-300', jefe: `luisa.herrera@${D}` },
      julian: { n: 'Julián Ospina', e: `julian.ospina@${D}`, rol: 'Solicitante', cc: 'CC-400', jefe: `camila.rios@${D}` },
    };
    const centros = [['CC-100', 'Dirección General'], ['CC-200', 'Comercial'], ['CC-300', 'Operaciones'], ['CC-400', 'Tecnología'], ['CC-500', 'Finanzas y Administración']];
    const cats = {
      'Transporte': { lim: 500000, rec: true, min: 15000, max: 280000, prov: ['Taxis Urbanos S.A.S.', 'Movilidad Express', 'Aerolínea Andina', 'Peajes Autopista Norte'] },
      'Alimentación': { lim: 120000, rec: true, min: 18000, max: 95000, prov: ['Restaurante La Esquina', 'Café Central', 'Panadería El Trigal'] },
      'Hospedaje': { lim: 600000, rec: true, min: 180000, max: 520000, prov: ['Hotel Plaza Real', 'Hostal Del Parque', 'Hotel Mirador'] },
      'Material de oficina': { lim: 250000, rec: true, min: 25000, max: 200000, prov: ['Suministros Oficina Ltda.', 'Papelería Mundo'] },
      'Capacitación': { lim: 2000000, rec: true, min: 350000, max: 1400000, prov: ['Instituto Formación Digital', 'Academia Profesional', 'Escuela de Negocios del Sur'] },
      'Otros': { lim: 200000, rec: false, min: 20000, max: 150000, prov: ['Servicios Varios S.A.S.', 'Mensajería Rápida'] },
    };
    const motivos = ['Visita a cliente en Medellín', 'Taller de capacitación técnica', 'Compra de papelería para la oficina', 'Reunión comercial en Bogotá', 'Viaje a feria sectorial', 'Capacitación en herramientas de gestión', 'Desplazamientos de campo', 'Atención de proyecto en sitio', 'Curso de actualización profesional', 'Reposición de insumos de oficina'];
    const comDev = ['Falta el soporte del segundo gasto.', 'El monto no coincide con el recibo adjunto.', 'Indica el centro de costo correcto.', 'Adjunta la factura legible.'];
    const comRech = ['El gasto no corresponde a la política vigente.', 'Gasto duplicado con otra solicitud.', 'Fuera del plazo permitido.'];
    const UMB = 1000000;

    // --- generar las 40 solicitudes en memoria
    const states = [];
    [['Borrador', 3], ['PendienteJefe', 6], ['PendienteFinanzas', 5], ['Aprobada', 5], ['Devuelta', 3], ['Rechazada', 3], ['Pagada', 15]].forEach(([s, c]) => { for (let i = 0; i < c; i++) states.push(s); });
    for (let i = states.length - 1; i > 0; i--) { const j = ri(0, i);[states[i], states[j]] = [states[j], states[i]]; }
    const now = new Date(); const solicitantes = [U.daniel, U.mariana, U.julian]; const fin = [U.andres, U.valentina];
    const day = 86400000; const isoD = (d) => d.toISOString().slice(0, 10) + 'T12:00:00Z';
    const sols = [];
    for (const est of states) {
      const u = pick(solicitantes); const back = est === 'Borrador' ? ri(1, 6) : ri(4, 120); const fecha = new Date(now.getTime() - back * day);
      const ng = ri(1, 4); const gs = [];
      for (let i = 0; i < ng; i++) { const cn = pick(Object.keys(cats)); const c = cats[cn]; const m = r1000(Math.min(c.lim, c.min + R() * (c.max - c.min))); gs.push({ cat: cn, prov: pick(c.prov), monto: m, fecha: new Date(fecha.getTime() - ri(0, 12) * day) }); }
      let total = gs.reduce((a, g) => a + g.monto, 0);
      if (est === 'PendienteFinanzas' && total < UMB) { const m = r1000(900000 + R() * 500000); gs.push({ cat: 'Capacitación', prov: pick(cats['Capacitación'].prov), monto: m, fecha: new Date(fecha.getTime() - ri(0, 10) * day) }); total += m; }
      const req = total >= UMB;
      gs.forEach((g) => { g.desc = g.cat + ' - ' + pick(['servicio', 'compra', 'pago', 'gestión']); g.recibo = 'R-' + ri(10000, 99999); });
      sols.push({ est, u, fecha, gs, total, req, motivo: pick(motivos) });
    }
    sols.sort((a, b) => a.fecha - b.fecha);
    const cnt = {};
    for (const s of sols) {
      const y = s.fecha.getUTCFullYear(); cnt[y] = (cnt[y] || 0) + 1; s.year = y; s.no = `REM-${y}-${String(cnt[y]).padStart(5, '0')}`;
      s.jefe = Object.values(U).find((x) => x.e === s.u.jefe);
      const ev = []; let t = new Date(s.fecha.getTime() + ri(9, 11) * 3600000);
      const step = () => { t = new Date(Math.min(now.getTime() - 3600000, t.getTime() + ri(1, 3) * day + ri(0, 5) * 3600000)); return new Date(t); };
      ev.push({ a: 'Creada', n: 0, actor: s.u, ant: '', nue: 'Borrador', t: new Date(t), c: '' });
      if (s.est !== 'Borrador') {
        s.envio = step(); ev.push({ a: 'Enviada', n: 1, actor: s.u, ant: 'Borrador', nue: 'PendienteJefe', t: s.envio, c: '' });
        const lvl2dev = s.req && R() < 0.5;
        if (s.est === 'Devuelta' || s.est === 'Rechazada') {
          const a = s.est; const com = pick(s.est === 'Devuelta' ? comDev : comRech);
          if (lvl2dev) { ev.push({ a: 'AprobadaJefe', n: 1, actor: s.jefe, ant: 'PendienteJefe', nue: 'PendienteFinanzas', t: step(), c: '' }); ev.push({ a, n: 2, actor: pick(fin), ant: 'PendienteFinanzas', nue: s.est, t: step(), c: com }); }
          else ev.push({ a, n: 1, actor: s.jefe, ant: 'PendienteJefe', nue: s.est, t: step(), c: com });
          s.cierre = s.est === 'Rechazada' ? t : null;
        } else if (s.est !== 'PendienteJefe') {
          ev.push({ a: 'AprobadaJefe', n: 1, actor: s.jefe, ant: 'PendienteJefe', nue: s.req ? 'PendienteFinanzas' : 'Aprobada', t: step(), c: '' });
          if (s.est !== 'PendienteFinanzas') {
            if (s.req) ev.push({ a: 'AprobadaFinanzas', n: 2, actor: pick(fin), ant: 'PendienteFinanzas', nue: 'Aprobada', t: step(), c: '' });
            if (s.est === 'Pagada') { const p = pick(fin); const tp = step(); ev.push({ a: 'Pagada', n: 2, actor: p, ant: 'Aprobada', nue: 'Pagada', t: tp, c: '' }); s.pago = tp; s.cierre = tp; s.ref = 'TRF-' + s.year + '-' + ri(1000, 9999); }
          }
        }
      }
      s.ev = ev;
      s.nivel = s.est === 'PendienteJefe' ? 1 : (s.est === 'PendienteFinanzas' ? 2 : 0);
      s.aprob = s.est === 'PendienteJefe' ? s.u.jefe : '';
    }

    // --- subir a SharePoint
    const ET = {};
    for (const n of Object.keys(SCHEMA)) ET[n] = (await sp(lt(n) + '?$select=ListItemEntityTypeFullName')).d.ListItemEntityTypeFullName;
    const add = async (list, obj) => (await sp(lt(list) + '/items', { method: 'POST', body: { __metadata: { type: ET[list] }, ...obj } })).d.Id;

    const ccId = {};
    for (const [c, n] of centros) ccId[c] = await add('CentrosCostoLST', { Title: c, Nombre: n, Activo: true });
    for (const [n, c] of Object.entries(cats)) await add('CategoriasGastoLST', { Title: n, LimiteMonto: c.lim, RequiereRecibo: c.rec, Activo: true });
    for (const u of Object.values(U)) await add('UsuariosRolLST', { Title: u.n, UsuarioEmail: u.e, Rol: u.rol, CentroCostoId: ccId[u.cc], JefeEmail: u.jefe, Activo: true });
    // la cuenta que ejecuta el script queda como Administrador para poder probar la app
    const me = (await sp('/_api/web/currentuser?$select=Id,Email')).d;
    await add('UsuariosRolLST', { Title: 'Administrador Demo (propietario)', UsuarioId: me.Id, UsuarioEmail: me.Email, Rol: 'Administrador', CentroCostoId: ccId['CC-100'], JefeEmail: '', Activo: true });
    for (const [k, v] of [['UmbralFinanzas', '1000000'], ['DiasMaxAntiguedad', '60'], ['Moneda', 'COP'], ['DiasAlertaPendiente', '3']]) await add('ParametrosLST', { Title: k, Valor: v });
    for (const [y, v] of Object.entries(cnt)) await add('ConsecutivoLST', { Title: 'REM-' + y, Tipo: 'REM-' + y, Valor: String(v) });
    const catId = {};
    (await sp(lt('CategoriasGastoLST') + '/items?$select=Id,Title&$top=100')).d.results.forEach((x) => { catId[x.Title] = x.Id; });

    const owner = (me.Email || '').toLowerCase();
    // opcional: unas solicitudes de ejemplo quedan a nombre de quien ejecuta el script, para ver datos en "Mis solicitudes"
    const cupo = { Borrador: 2, Devuelta: 2, Pagada: 3, Rechazada: 1, Aprobada: 1, PendienteJefe: 1 };
    for (const s of sols) {
      let solicitanteEmail = s.u.e;
      if (asignarAlPropietario && cupo[s.est] > 0) { cupo[s.est]--; solicitanteEmail = owner; }
      const body = { Title: s.no, SolicitanteEmail: solicitanteEmail, CentroCostoId: ccId[s.u.cc], CentroCostoCod: s.u.cc, Motivo: s.motivo, FechaSolicitud: isoD(s.fecha), MontoTotal: s.total, Estado: s.est, NivelActual: s.nivel, AprobadorEmail: s.aprob, RequiereFinanzas: s.req && s.est !== 'Borrador' };
      if (s.envio) body.FechaEnvio = s.envio.toISOString();
      if (s.cierre) body.FechaCierre = new Date(s.cierre).toISOString();
      if (s.ref) { body.ReferenciaPago = s.ref; body.FechaPago = isoD(s.pago); }
      const id = await add('SolicitudesLST', body);
      await Promise.all(s.gs.map((g) => add('GastosLST', { Title: s.no, SolicitudId: id, CategoriaId: catId[g.cat], CategoriaNombre: g.cat, FechaGasto: isoD(g.fecha), Proveedor: g.prov, Descripcion: g.desc, Monto: g.monto, NumeroRecibo: g.recibo })));
      await Promise.all(s.ev.map((e) => add('BitacoraLST', { Title: s.no, SolicitudId: id, Accion: e.a, Nivel: e.n, ActorEmail: e.actor.e, EstadoAnterior: e.ant, EstadoNuevo: e.nue, Comentario: e.c, FechaAccion: e.t.toISOString() })));
    }
    console.log('Datos de demostración cargados:', sols.length, 'solicitudes');
  };

  window.reembolsa = { crearListas, cargarDatosDemo };
  console.log('Listo. Ejecuta: await reembolsa.crearListas();  y luego (opcional): await reembolsa.cargarDatosDemo();');
})();
