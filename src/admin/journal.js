/* Журнал правок админки и откат сайта.
   Кто, когда, с какого IP и что изменил — дописывается к каждой правке строкой «journal:v1:…».
   Репозиторий публичный, поэтому запись зашифрована открытым ключом владельца (ECDH P-256 + AES-GCM):
   прочитать её может только владелец, у которого в браузере есть закрытый ключ журнала.
   Откат: новая правка, которая возвращает папку content/ (тексты, цены, кейсы, новости, документы) к выбранной версии. */
(function (w) {
  'use strict';
  var REPO = 'i78424325/doctor-marketplace-v2', BRANCH = 'main', KEY_PATH = 'src/admin/journal-key.json';
  var API = 'https://api.github.com', PRIV = 'dm-journal-private', WHO = 'dm-admin-who';
  var store = function (s) {
    return {
      get: function (k) { try { return w[s].getItem(k); } catch (e) { return null; } },
      set: function (k, v) { try { w[s].setItem(k, v); } catch (e) { /* приватный режим */ } },
      del: function (k) { try { w[s].removeItem(k); } catch (e) { /* приватный режим */ } }
    };
  };
  var LS = store('localStorage'), SS = store('sessionStorage');
  var F = function () { return w.__dmFetch || w.fetch.bind(w); }; // наши запросы идут мимо перехвата
  var subtle = w.crypto && w.crypto.subtle;
  var ECDH = { name: 'ECDH', namedCurve: 'P-256' };

  /* ---------- вход и имя ---------- */
  function token() {
    try { var u = JSON.parse(LS.get('sveltia-cms.user') || 'null'); return u && typeof u.token === 'string' ? u.token : ''; } catch (e) { return ''; }
  }
  function who() { return LS.get(WHO) || ''; }
  function setWho(n) { n = String(n || '').replace(/\s+/g, ' ').trim().slice(0, 40); if (n) LS.set(WHO, n); return n; }
  function whoFromLink() { // ссылка входа со страницы ssylka.html несёт имя получателя
    var m = (w.location.hash || '').match(/^#\/signin\/([A-Za-z0-9_\-+\/=]+)/);
    if (!m) return;
    try { var j = JSON.parse(utf8(b64u.dec(m[1]))); if (j && j.who) setWho(j.who); } catch (e) { /* не наша ссылка */ }
  }

  /* ---------- base64url и текст ---------- */
  var b64u = {
    enc: function (buf) { var b = new Uint8Array(buf), s = ''; for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); },
    dec: function (str) { var s = String(str).replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; var bin = atob(s), b = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i); return b; }
  };
  function utf8(bytes) { return new TextDecoder().decode(bytes); }
  function b64text(text) { var b = new TextEncoder().encode(text), s = ''; for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]); return btoa(s); } // обычный base64 — для GitHub

  /* ---------- GitHub API ---------- */
  function gh(path, opts) {
    opts = opts || {};
    var h = { Accept: 'application/vnd.github+json' }, t = token();
    if (t) h.Authorization = 'Bearer ' + t;
    if (opts.body) h['Content-Type'] = 'application/json';
    return F()(API + path, { method: opts.method || 'GET', headers: h, body: opts.body ? JSON.stringify(opts.body) : undefined, cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) { var e = new Error('GitHub ответил ' + r.status); e.status = r.status; throw e; }
        return r.status === 204 ? null : r.json();
      });
  }

  /* ---------- IP и браузер ---------- */
  function timeout(p, ms, fallback) { return Promise.race([p, new Promise(function (res) { setTimeout(function () { res(fallback); }, ms); })]); }
  function ipInfo() {
    var c = SS.get('dm-ip');
    if (c) { try { var o = JSON.parse(c); if (Date.now() - o.t < 600000) return Promise.resolve(o.d); } catch (e) { /* заново */ } }
    var save = function (d) { SS.set('dm-ip', JSON.stringify({ t: Date.now(), d: d })); return d; };
    var none = { ip: 'не определён', city: '', country: '', org: '' };
    return F()('https://ipapi.co/json/').then(function (r) { return r.json(); })
      .then(function (j) { if (!j || !j.ip) throw new Error('нет ip'); return save({ ip: j.ip, city: j.city || '', country: j.country_name || '', org: j.org || '' }); })
      .catch(function () { return F()('https://api.ipify.org?format=json').then(function (r) { return r.json(); }).then(function (j) { return save({ ip: j.ip || none.ip, city: '', country: '', org: '' }); }); })
      .catch(function () { return none; });
  }
  function browser() {
    var u = navigator.userAgent || '', os = /iPhone|iPad/.test(u) ? 'iOS' : /Android/.test(u) ? 'Android' : /Mac OS X/.test(u) ? 'macOS' : /Windows/.test(u) ? 'Windows' : /Linux/.test(u) ? 'Linux' : '';
    var m = u.match(/(YaBrowser|Edg|OPR|Firefox|Chrome|Version)\/(\d+)/), name = m ? ({ YaBrowser: 'Яндекс Браузер', Edg: 'Edge', OPR: 'Opera', Version: 'Safari' }[m[1]] || m[1]) + ' ' + m[2] : 'браузер';
    return name + (os ? ', ' + os : '');
  }

  /* ---------- шифрование записей ---------- */
  function genOwnerKeys() {
    return subtle.generateKey(ECDH, true, ['deriveKey'])
      .then(function (kp) { return Promise.all([subtle.exportKey('jwk', kp.publicKey), subtle.exportKey('jwk', kp.privateKey)]); })
      .then(function (a) { return { pub: a[0], priv: a[1] }; });
  }
  function encryptFor(pubJwk, obj) {
    var eph;
    return Promise.all([subtle.importKey('jwk', pubJwk, ECDH, false, []), subtle.generateKey(ECDH, true, ['deriveKey'])])
      .then(function (a) { eph = a[1]; return subtle.deriveKey({ name: 'ECDH', public: a[0] }, eph.privateKey, { name: 'AES-GCM', length: 256 }, false, ['encrypt']); })
      .then(function (key) {
        var iv = w.crypto.getRandomValues(new Uint8Array(12));
        return Promise.all([subtle.exportKey('raw', eph.publicKey), iv, subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(JSON.stringify(obj)))]);
      })
      .then(function (a) { return 'journal:v1:' + b64u.enc(a[0]) + '.' + b64u.enc(a[1]) + '.' + b64u.enc(a[2]); });
  }
  function decryptLine(privJwk, text) {
    var m = String(text || '').match(/journal:v1:([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)/);
    if (!m || !privJwk) return Promise.resolve(null);
    return Promise.all([subtle.importKey('jwk', privJwk, ECDH, false, ['deriveKey']), subtle.importKey('raw', b64u.dec(m[1]), ECDH, false, [])])
      .then(function (a) { return subtle.deriveKey({ name: 'ECDH', public: a[1] }, a[0], { name: 'AES-GCM', length: 256 }, false, ['decrypt']); })
      .then(function (key) { return subtle.decrypt({ name: 'AES-GCM', iv: b64u.dec(m[2]) }, key, b64u.dec(m[3])); })
      .then(function (pt) { return JSON.parse(utf8(new Uint8Array(pt))); })
      .catch(function () { return null; });
  }
  var keyCache = null;
  function ownerKey() { // открытый ключ владельца лежит в репозитории; нет файла — журнал ещё не включён
    if (keyCache) return keyCache;
    keyCache = gh('/repos/' + REPO + '/contents/' + KEY_PATH + '?ref=' + BRANCH)
      .then(function (f) { var j = JSON.parse(utf8(b64u.dec(String(f.content || '').replace(/\s+/g, '')))); return j && j.pub ? j.pub : null; })
      .catch(function (e) { keyCache = null; return e && e.status === 404 ? null : Promise.reject(e); });
    return keyCache;
  }
  function privateKey() { try { return JSON.parse(LS.get(PRIV) || 'null'); } catch (e) { return null; } }
  function journalLine(action, files) {
    return Promise.all([ownerKey(), timeout(ipInfo(), 3000, { ip: 'не определён', city: '', country: '', org: '' })])
      .then(function (a) {
        if (!a[0]) return '';
        var ip = a[1] || {};
        return encryptFor(a[0], { v: 1, who: who() || 'не указано', ip: ip.ip, city: ip.city, country: ip.country, org: ip.org, ua: browser(), ts: new Date().toISOString(), files: files || [], action: action || '' });
      })
      .catch(function () { return ''; });
  }

  /* ---------- перехват сохранений Sveltia: к сообщению правки дописываем строку журнала ---------- */
  function addJournal(body) {
    var j = JSON.parse(body), inp = j && j.variables && j.variables.input;
    if (!inp || !inp.message || !inp.message.headline) return Promise.resolve(body);
    var fc = inp.fileChanges || {};
    var files = (fc.additions || []).map(function (x) { return x.path; }).concat((fc.deletions || []).map(function (x) { return '− ' + x.path; }));
    return journalLine(inp.message.headline, files).then(function (line) {
      if (!line) return body;
      inp.message.body = (inp.message.body ? inp.message.body + '\n\n' : '') + line;
      return JSON.stringify(j);
    }, function () { return body; });
  }
  function installInterceptor() {
    if (w.__dmFetch || !w.fetch) return;
    var orig = w.__dmFetch = w.fetch.bind(w);
    w.fetch = function (input, init) {
      try {
        var url = typeof input === 'string' ? input : (input && input.url) || '';
        if (url.indexOf('api.github.com/graphql') !== -1 && init && typeof init.body === 'string' && init.body.indexOf('createCommitOnBranch') !== -1) {
          return addJournal(init.body).then(function (b) { return orig(input, Object.assign({}, init, { body: b })); }, function () { return orig(input, init); });
        }
      } catch (e) { /* не мешаем сохранению */ }
      return orig(input, init);
    };
  }

  /* ---------- история и откат ---------- */
  function history(page) { return gh('/repos/' + REPO + '/commits?sha=' + BRANCH + '&per_page=30&page=' + (page || 1)); }
  function rollbackTo(sha, label) {
    var headSha, headTree;
    return gh('/repos/' + REPO + '/git/ref/heads/' + BRANCH)
      .then(function (ref) { headSha = ref.object.sha; return Promise.all([gh('/repos/' + REPO + '/git/commits/' + headSha), gh('/repos/' + REPO + '/git/commits/' + sha)]); })
      .then(function (c) { headTree = c[0].tree.sha; return gh('/repos/' + REPO + '/git/trees/' + c[1].tree.sha); })
      .then(function (t) {
        var e = (t.tree || []).filter(function (x) { return x.path === 'content' && x.type === 'tree'; })[0];
        if (!e) throw new Error('В этой версии ещё не было текстов сайта — к ней откатить нельзя.');
        return gh('/repos/' + REPO + '/git/trees', { method: 'POST', body: { base_tree: headTree, tree: [{ path: 'content', mode: '040000', type: 'tree', sha: e.sha }] } });
      })
      .then(function (nt) {
        if (nt.sha === headTree) throw new Error('Сайт уже в этой версии — менять нечего.');
        return journalLine('Откат сайта к версии от ' + label, ['content/']).then(function (line) { return [nt, line]; });
      })
      .then(function (a) {
        var msg = 'Откат сайта к версии от ' + label + '\n\nВерсия ' + sha.slice(0, 7) + (a[1] ? '\n\n' + a[1] : '');
        return gh('/repos/' + REPO + '/git/commits', { method: 'POST', body: { message: msg, tree: a[0].sha, parents: [headSha] } });
      })
      .then(function (nc) { return gh('/repos/' + REPO + '/git/refs/heads/' + BRANCH, { method: 'PATCH', body: { sha: nc.sha, force: false } }).then(function () { return nc; }); });
  }
  function enableJournal() { // один раз, на устройстве владельца
    return genOwnerKeys().then(function (k) {
      return gh('/repos/' + REPO + '/contents/' + KEY_PATH, { method: 'PUT', body: {
        message: 'Журнал правок: включён (открытый ключ владельца)', branch: BRANCH,
        content: b64text(JSON.stringify({ v: 1, pub: k.pub }, null, 2) + '\n') } })
        .then(function () { LS.set(PRIV, JSON.stringify(k.priv)); keyCache = Promise.resolve(k.pub); return k; });
    });
  }
  function importPrivate(text) {
    var j = JSON.parse(String(text || '').trim());
    var priv = j && j.priv ? j.priv : j;
    if (!priv || priv.kty !== 'EC' || !priv.d) throw new Error('Это не ключ журнала.');
    LS.set(PRIV, JSON.stringify(priv));
    return priv;
  }

  /* ---------- админка: кнопка журнала и вопрос «как вас подписывать» ---------- */
  function injectAdminUI() {
    var css = '#dmj{position:fixed;left:16px;bottom:16px;z-index:2147483000;display:grid;gap:8px;font:14px/20px system-ui,-apple-system,"Segoe UI",sans-serif}' +
      '#dmj a,#dmj button{font:inherit}#dmj .b{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:#0F3B2A;color:#fff;text-decoration:none;box-shadow:0 8px 24px -10px rgba(0,0,0,.5);opacity:.92}' +
      '#dmj .b:hover{opacity:1}#dmj .c{max-width:300px;padding:14px;border-radius:16px;background:#fff;color:#121C16;box-shadow:0 0 0 1px rgba(16,32,24,.12),0 18px 44px -18px rgba(16,32,24,.35)}' +
      '#dmj .c p{margin:0 0 8px}#dmj .c small{display:block;margin-top:8px;color:#56625C;font-size:12px;line-height:16px}#dmj input{width:100%;padding:8px 10px;border:1px solid rgba(16,32,24,.2);border-radius:10px;font:inherit}' +
      '#dmj .ok{margin-top:8px;padding:8px 12px;border:0;border-radius:999px;background:#4EB679;color:#0B1A12;font-weight:700;cursor:pointer}';
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    var box = document.createElement('div'); box.id = 'dmj';
    box.innerHTML = '<a class="b" href="zhurnal.html" target="_blank" rel="noopener">Журнал правок и откат</a>';
    document.body.appendChild(box);
    var ask = function () {
      if (who() || !token() || box.querySelector('.c')) return;
      var c = document.createElement('form'); c.className = 'c';
      c.innerHTML = '<p><b>Как вас подписывать в журнале правок?</b></p><input name="n" placeholder="Например: Артём" maxlength="40" autocomplete="name">' +
        '<button class="ok" type="submit">Сохранить</button><small>В журнал записываются имя, время, IP-адрес и что изменено. Видит только владелец сайта.</small>';
      c.addEventListener('submit', function (e) { e.preventDefault(); if (setWho(c.n.value)) c.remove(); });
      box.insertBefore(c, box.firstChild);
    };
    setInterval(ask, 2000); ask();
  }
  function boot() {
    whoFromLink();
    installInterceptor();
    var go = function () { injectAdminUI(); if (token()) { ownerKey().catch(function () {}); ipInfo(); } };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
  }

  w.DMJournal = { boot: boot, token: token, who: who, setWho: setWho, history: history, rollbackTo: rollbackTo, enableJournal: enableJournal,
                  importPrivate: importPrivate, privateKey: privateKey, ownerKey: ownerKey, decryptLine: decryptLine, encryptFor: encryptFor,
                  genOwnerKeys: genOwnerKeys, addJournal: addJournal, browser: browser, REPO: REPO };
})(window);
