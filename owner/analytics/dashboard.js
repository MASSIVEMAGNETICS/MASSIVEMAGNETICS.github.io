(() => {
  'use strict';

  const EVENT_KEY = 'iambandobandz_click_events';
  let importedEvents = [];

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  function readLocal() {
    try {
      const value = JSON.parse(localStorage.getItem(EVENT_KEY) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (_) {
      return [];
    }
  }

  function normalized(events) {
    return events.filter((item) => item && typeof item === 'object' && item.event && item.timestamp).map((item) => ({
      event: String(item.event || 'unknown'),
      timestamp: String(item.timestamp || ''),
      page_path: String(item.page_path || item.path || '/'),
      path: String(item.path || ''),
      stage: String(item.stage || ''),
      destination: String(item.destination || ''),
      session_id: String(item.session_id || ''),
      referrer: String(item.referrer || ''),
      utm_source: String(item.utm_source || ''),
      utm_medium: String(item.utm_medium || ''),
      utm_campaign: String(item.utm_campaign || ''),
      label: String(item.label || ''),
      sku: String(item.sku || ''),
      format: String(item.format || '')
    }));
  }

  function allEvents() {
    return normalized([...readLocal(), ...importedEvents]);
  }

  function dateCutoff(days) {
    if (!days) return null;
    return Date.now() - days * 24 * 60 * 60 * 1000;
  }

  function filteredEvents() {
    const days = Number($('windowSelect').value || '0');
    const page = $('pageSelect').value;
    const cutoff = dateCutoff(days);
    return allEvents().filter((event) => {
      const time = Date.parse(event.timestamp);
      if (cutoff && (!Number.isFinite(time) || time < cutoff)) return false;
      if (page !== 'ALL' && event.page_path !== page) return false;
      return true;
    });
  }

  function count(events, name) {
    return events.reduce((total, event) => total + (event.event === name ? 1 : 0), 0);
  }

  function uniqueSessions(events) {
    const ids = new Set(events.map((event) => event.session_id).filter(Boolean));
    return ids.size;
  }

  function sourceName(event) {
    if (event.utm_source) return `utm:${event.utm_source}`;
    if (event.referrer) {
      try { return new URL(event.referrer).hostname.replace(/^www\./, '') || 'referrer'; } catch (_) {}
    }
    return 'direct / unknown';
  }

  function tally(items) {
    const map = new Map();
    for (const item of items) map.set(item, (map.get(item) || 0) + 1);
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }

  function renderBars(target, entries, emptyLabel) {
    const el = $(target);
    if (!entries.length) {
      el.innerHTML = `<div class="empty">${esc(emptyLabel)}</div>`;
      return;
    }
    const max = entries[0][1] || 1;
    el.innerHTML = entries.slice(0, 12).map(([label, value]) => `
      <div class="bar-row">
        <div class="bar-label" title="${esc(label)}">${esc(label)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.max(3, Math.round((value / max) * 100))}%"></div></div>
        <div class="bar-value">${value}</div>
      </div>`).join('');
  }

  function renderPageOptions(events) {
    const select = $('pageSelect');
    const current = select.value;
    const pages = [...new Set(events.map((event) => event.page_path).filter(Boolean))].sort();
    select.innerHTML = '<option value="ALL">All pages</option>' + pages.map((page) => `<option value="${esc(page)}">${esc(page)}</option>`).join('');
    if (pages.includes(current)) select.value = current;
  }

  function renderFunnel(events) {
    const steps = [
      ['DISCOVER', count(events, 'page_view'), 'page views'],
      ['CHOOSE', count(events, 'revenue_path_click'), 'revenue path clicks'],
      ['LISTEN', count(events, 'track_button_click'), 'music clicks'],
      ['PAY', count(events, 'checkout_start'), 'checkout starts'],
      ['CAPTURE', count(events, 'signal_capture_complete'), 'lead captures']
    ];
    $('funnel').innerHTML = steps.map(([name, value, label], index) => {
      const prior = index ? steps[index - 1][1] : value;
      const rate = prior ? `${Math.round((value / prior) * 100)}% of prior` : 'no prior events';
      return `<div class="step"><b>${name}</b><strong>${value}</strong><span>${label}<br>${rate}</span></div>`;
    }).join('');
  }

  function renderRows(events) {
    const rows = [...events].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp)).slice(0, 200);
    $('eventCount').textContent = `${events.length} events`;
    if (!rows.length) {
      $('eventRows').innerHTML = '<tr><td colspan="7" class="empty">No recorded events in this window.</td></tr>';
      return;
    }
    $('eventRows').innerHTML = rows.map((event) => {
      const when = Number.isFinite(Date.parse(event.timestamp)) ? new Date(event.timestamp).toLocaleString() : event.timestamp;
      const pathStage = [event.path, event.stage].filter(Boolean).join(' / ');
      return `<tr>
        <td>${esc(when)}</td>
        <td><code>${esc(event.event)}</code></td>
        <td>${esc(event.page_path)}</td>
        <td>${esc(pathStage)}</td>
        <td>${esc(event.destination || event.label)}</td>
        <td>${esc(sourceName(event))}</td>
        <td><code>${esc(event.session_id ? event.session_id.slice(0, 12) : 'legacy')}</code></td>
      </tr>`;
    }).join('');
  }

  function render() {
    const all = allEvents();
    renderPageOptions(all);
    const events = filteredEvents();
    $('kpiViews').textContent = count(events, 'page_view');
    $('kpiSessions').textContent = uniqueSessions(events);
    $('kpiRevenue').textContent = count(events, 'revenue_path_click');
    $('kpiCheckout').textContent = count(events, 'checkout_start');
    $('kpiMusic').textContent = count(events, 'track_button_click');
    $('kpiLeads').textContent = count(events, 'signal_capture_complete');
    renderFunnel(events);
    renderBars('sourceBars', tally(events.filter((e) => e.event === 'page_view').map(sourceName)), 'No acquisition events yet.');
    renderBars('pageBars', tally(events.filter((e) => e.event === 'page_view').map((e) => e.page_path || '/')), 'No page views yet.');
    renderRows(events);
    const localCount = readLocal().length;
    const importedCount = importedEvents.length;
    $('coverageText').textContent = `${localCount} local events${importedCount ? ` + ${importedCount} imported events` : ''}.`;
    $('collectorText').textContent = 'Site-wide collector: not connected.';
  }

  function exportBlob(text, type, filename) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function csvValue(value) {
    const text = String(value ?? '');
    return `"${text.replace(/"/g, '""')}"`;
  }

  function exportJson() {
    const payload = {
      schema_version: '1.0.0',
      exported_at: new Date().toISOString(),
      coverage: 'browser-local-plus-imported',
      events: allEvents()
    };
    exportBlob(JSON.stringify(payload, null, 2), 'application/json', `iambandobandz-analytics-${Date.now()}.json`);
  }

  function exportCsv() {
    const events = allEvents();
    const columns = ['timestamp','event','page_path','path','stage','destination','session_id','referrer','utm_source','utm_medium','utm_campaign','label','sku','format'];
    const rows = [columns.join(','), ...events.map((event) => columns.map((key) => csvValue(event[key])).join(','))];
    exportBlob(rows.join('\n'), 'text/csv', `iambandobandz-analytics-${Date.now()}.csv`);
  }

  async function importFile(file) {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const events = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.events) ? parsed.events : [];
    if (!events.length) throw new Error('No events array found');
    importedEvents = normalized(events);
    render();
  }

  $('refreshBtn').addEventListener('click', render);
  $('windowSelect').addEventListener('change', render);
  $('pageSelect').addEventListener('change', render);
  $('exportJsonBtn').addEventListener('click', exportJson);
  $('exportCsvBtn').addEventListener('click', exportCsv);
  $('importBtn').addEventListener('click', () => $('importFile').click());
  $('importFile').addEventListener('change', async () => {
    const file = $('importFile').files?.[0];
    if (!file) return;
    try { await importFile(file); }
    catch (error) { alert(`Import failed: ${error.message}`); }
    finally { $('importFile').value = ''; }
  });
  $('clearBtn').addEventListener('click', () => {
    if (!confirm('Clear analytics events stored in THIS browser only? Imported events will also be discarded.')) return;
    localStorage.removeItem(EVENT_KEY);
    importedEvents = [];
    render();
  });

  window.addEventListener('storage', (event) => {
    if (event.key === EVENT_KEY) render();
  });

  render();
})();
