(() => {
  'use strict';

  const REPO = 'MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io';
  const API = `https://api.github.com/repos/${REPO}/issues?state=all&sort=updated&direction=desc&per_page=100`;
  const MARKER = '<!-- bheard-board:v1 -->';
  const CATEGORY_FALLBACK = 'GENERAL';

  const list = document.getElementById('thread-list');
  const status = document.getElementById('board-status');
  const refresh = document.getElementById('board-refresh');
  const threadCount = document.getElementById('thread-count');
  const replyCount = document.getElementById('reply-count');
  const updated = document.getElementById('board-updated');
  const filters = document.getElementById('category-filters');

  if (!list || !status) return;

  let threads = [];
  let activeCategory = 'ALL';

  const pushEvent = (payload) => {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ surface: 'bheard-board-alpha', ...payload });
  };

  document.querySelectorAll('[data-board-action]').forEach((node) => {
    node.addEventListener('click', () => {
      pushEvent({ event: 'board_action', action: node.dataset.boardAction || 'unknown' });
    });
  });

  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    return node;
  };

  const normalizeCategory = (body = '') => {
    const match = body.match(/###\s+Category\s*\n+\s*([^\n]+)/i);
    if (!match) return CATEGORY_FALLBACK;
    return match[1].replace(/\r/g, '').trim().toUpperCase() || CATEGORY_FALLBACK;
  };

  const displayName = (body = '', fallback = '') => {
    const match = body.match(/###\s+(?:Display name|Artist \/ creator name)\s*\n+\s*([^\n]+)/i);
    const value = match ? match[1].replace(/\r/g, '').trim() : '';
    return value && value !== '_No response_' ? value : fallback;
  };

  const cleanTitle = (title = '') => title.replace(/^\[BOARD\]\s*/i, '').trim();

  const isBoardThread = (item) => {
    if (item.pull_request) return false;
    return /^\[BOARD\]/i.test(item.title || '') || (item.body || '').includes(MARKER);
  };

  const isPinned = (item) => /📌|\bSTART HERE\b/i.test(item.title || '');

  const relativeTime = (iso) => {
    const stamp = Date.parse(iso);
    if (!Number.isFinite(stamp)) return 'unknown';
    const seconds = Math.max(0, Math.floor((Date.now() - stamp) / 1000));
    if (seconds < 60) return 'now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months}mo ago`;
    return `${Math.floor(months / 12)}y ago`;
  };

  const sortThreads = (items) => [...items].sort((a, b) => {
    const pinned = Number(isPinned(b)) - Number(isPinned(a));
    if (pinned) return pinned;
    return Date.parse(b.updated_at) - Date.parse(a.updated_at);
  });

  const renderStats = () => {
    threadCount.textContent = String(threads.length);
    replyCount.textContent = String(threads.reduce((sum, item) => sum + Number(item.comments || 0), 0));
    updated.textContent = threads.length ? relativeTime(sortThreads(threads)[0].updated_at) : '—';
  };

  const renderThreads = () => {
    list.replaceChildren();
    const visible = sortThreads(threads).filter((item) => {
      if (activeCategory === 'ALL') return true;
      return normalizeCategory(item.body || '') === activeCategory;
    });

    if (!visible.length) {
      const empty = text('div', activeCategory === 'ALL'
        ? 'No public B Heard Board threads exist yet. Start the first one.'
        : 'No threads are currently filed in this category.', 'board-empty');
      list.appendChild(empty);
      return;
    }

    visible.forEach((item) => {
      const row = document.createElement('a');
      row.className = 'thread-row';
      row.href = item.html_url;
      row.target = '_blank';
      row.rel = 'noopener noreferrer';
      row.dataset.issueNumber = String(item.number);
      row.addEventListener('click', () => {
        pushEvent({ event: 'board_thread_open', issue_number: item.number, category: normalizeCategory(item.body || '') });
      });

      row.appendChild(text('span', normalizeCategory(item.body || ''), 'thread-category'));

      const main = document.createElement('div');
      main.className = 'thread-main';
      const title = text('span', cleanTitle(item.title || 'Untitled thread'), 'thread-title');
      if (isPinned(item)) {
        const pin = text('span', 'PINNED', 'thread-pin');
        title.prepend(pin);
      }
      main.appendChild(title);
      main.appendChild(text('div', `${item.state === 'closed' ? 'Archived' : 'Open'} · updated ${relativeTime(item.updated_at)}`, 'thread-meta'));
      row.appendChild(main);

      const author = document.createElement('div');
      author.className = 'thread-author';
      if (item.user && item.user.avatar_url) {
        const avatar = document.createElement('img');
        avatar.src = item.user.avatar_url;
        avatar.alt = '';
        avatar.loading = 'lazy';
        author.appendChild(avatar);
      }
      author.appendChild(text('span', displayName(item.body || '', item.user?.login || 'unknown')));
      row.appendChild(author);

      const replies = document.createElement('div');
      replies.className = 'thread-replies';
      replies.appendChild(text('b', String(item.comments || 0)));
      replies.appendChild(document.createTextNode(item.comments === 1 ? 'reply' : 'replies'));
      row.appendChild(replies);

      list.appendChild(row);
    });
  };

  const load = async () => {
    refresh?.setAttribute('disabled', 'disabled');
    status.className = 'board-status';
    status.textContent = 'Loading public threads…';
    try {
      const response = await fetch(API, {
        headers: {
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        cache: 'no-store'
      });
      if (!response.ok) throw new Error(`GitHub API returned ${response.status}`);
      const data = await response.json();
      threads = Array.isArray(data) ? data.filter(isBoardThread) : [];
      renderStats();
      renderThreads();
      const remaining = response.headers.get('x-ratelimit-remaining');
      status.textContent = threads.length
        ? `Live public index loaded${remaining ? ` · GitHub API reads remaining for this client: ${remaining}` : ''}. Open any thread to read or reply.`
        : 'The live board is connected and currently has no public threads.';
      pushEvent({ event: 'board_loaded', thread_count: threads.length });
    } catch (error) {
      status.className = 'board-status error';
      status.textContent = `Live thread index could not load right now (${error.message}). The board itself is still available on GitHub.`;
      list.replaceChildren();
      const fallback = document.createElement('a');
      fallback.className = 'button button-ghost';
      fallback.href = `https://github.com/${REPO}/issues?q=is%3Aissue+%5BBOARD%5D`;
      fallback.target = '_blank';
      fallback.rel = 'noopener noreferrer';
      fallback.textContent = 'Open board directly on GitHub ↗';
      list.appendChild(fallback);
      pushEvent({ event: 'board_load_error', message: String(error.message || error) });
    } finally {
      refresh?.removeAttribute('disabled');
    }
  };

  filters?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-category]');
    if (!button) return;
    activeCategory = button.dataset.category || 'ALL';
    filters.querySelectorAll('[data-category]').forEach((node) => node.classList.toggle('active', node === button));
    renderThreads();
    pushEvent({ event: 'board_filter', category: activeCategory });
  });

  refresh?.addEventListener('click', load);
  load();
})();
