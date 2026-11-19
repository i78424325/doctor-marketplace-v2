/* Голосовой ввод: Web Speech API (ru-RU). Если браузер не умеет — подсказка про микрофон клавиатуры. */
window.DMVoice = (function () {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var active = null;
  var ERR = {
    'not-allowed': 'Нет доступа к микрофону. Разрешите его в настройках браузера.',
    'service-not-allowed': 'Браузер не дал включить распознавание. Нажмите микрофон на клавиатуре телефона.',
    'no-speech': 'Ничего не услышали. Нажмите ещё раз и говорите.',
    'audio-capture': 'Не нашли микрофон. Проверьте, что он подключён.',
    'network': 'Нет связи с сервисом распознавания. Нажмите микрофон на клавиатуре телефона.'
  };
  function setStatus(el, text, state) { if (!el) return; el.textContent = text || ''; el.setAttribute('data-state', state || ''); }
  function join(a, b) { a = (a || '').replace(/\s+$/, ''); b = (b || '').trim(); return a && b ? a + ' ' + b : (a || b); }
  function stop() { if (active) { try { active.rec.stop(); } catch (e) { active = null; } } }
  // onChange(value) — запасной путь: если поле уже убрано со страницы (перешли на другой шаг), надиктованное не теряется
  function attach(btn, field, statusEl, onChange) {
    btn.setAttribute('aria-pressed', 'false');
    if (!SR) {
      btn.addEventListener('click', function () { setStatus(statusEl, 'В этом браузере нет голосового ввода. Нажмите микрофон на клавиатуре телефона — речь сама станет текстом.', 'warn'); field.focus(); });
      return;
    }
    btn.addEventListener('click', function () {
      if (active && active.btn === btn) { stop(); return; }
      stop();
      var rec = new SR(), base = field.value, fin = '', edited = false;
      var put = function (val) {
        if (field.isConnected) { field.value = val; field.dispatchEvent(new Event('input', { bubbles: true })); }
        else if (onChange) onChange(val);
      };
      var ui = function (on) { btn.classList.toggle('rec', on); btn.setAttribute('aria-pressed', String(on)); btn.setAttribute('aria-label', on ? 'Остановить запись' : 'Надиктовать голосом'); };
      // начали печатать руками во время записи — запись останавливаем, набранное не трогаем
      var onType = function (e) { if (e.isTrusted && !edited) { edited = true; try { rec.stop(); } catch (x) {} } };
      rec.lang = 'ru-RU'; rec.interimResults = true; rec.continuous = true;
      rec.onstart = function () { ui(true); setStatus(statusEl, 'Слушаю. Говорите — текст появится в поле.', 'live'); };
      rec.onresult = function (e) {
        if (edited) return;
        var interim = '';
        for (var i = e.resultIndex; i < e.results.length; i++) { var r = e.results[i]; if (r.isFinal) fin += r[0].transcript + ' '; else interim += r[0].transcript; }
        put(join(base, fin + interim));
      };
      rec.onerror = function (e) { setStatus(statusEl, ERR[e.error] || 'Не получилось распознать. Попробуйте ещё раз.', 'warn'); };
      rec.onend = function () {
        // текст уже в поле после последнего onresult — здесь его не трогаем, чтобы не потерять недоговорённое
        ui(false); field.removeEventListener('input', onType);
        if (active && active.rec === rec) active = null;
        if (statusEl && statusEl.getAttribute('data-state') === 'live') setStatus(statusEl, '', '');
      };
      field.addEventListener('input', onType);
      active = { rec: rec, btn: btn };
      try { rec.start(); } catch (err) { active = null; field.removeEventListener('input', onType); ui(false); setStatus(statusEl, 'Не получилось включить микрофон. Попробуйте ещё раз.', 'warn'); }
    });
  }
  return { attach: attach, stop: stop, supported: !!SR };
})();
