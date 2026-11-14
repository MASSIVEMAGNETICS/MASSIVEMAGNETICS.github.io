import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, '../beheardnetwork/analytics.js'), 'utf8');

function clickEventFor(hostname) {
  const listeners = {};
  const makeStorage = () => {
    const data = new Map();
    return {
      getItem: (key) => (data.has(key) ? data.get(key) : null),
      setItem: (key, value) => data.set(key, value),
    };
  };
  const window = {
    dataLayer: [],
    crypto: { randomUUID: () => 'test-session' },
    dispatchEvent: () => {},
  };
  const document = {
    referrer: '',
    querySelector: () => null,
    addEventListener: (name, callback) => { listeners[name] = callback; },
  };
  const context = {
    window,
    document,
    location: { search: '', pathname: '/test', href: 'https://bheardnetwork.com/test' },
    localStorage: makeStorage(),
    sessionStorage: makeStorage(),
    navigator: {},
    URL,
    URLSearchParams,
    Date,
    Math,
    CustomEvent: class {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
  };

  vm.runInNewContext(source, context, { filename: 'analytics.js' });
  const link = {
    href: `https://${hostname}/artist`,
    dataset: {},
    textContent: 'Listen',
    querySelector: () => null,
  };
  listeners.click({ target: { closest: () => link } });
  return window.dataLayer.at(-1).event;
}

test('recognized music domains and their subdomains are classified as music', () => {
  for (const hostname of ['youtube.com', 'www.youtube.com', 'music.youtube.com', 'music.apple.com', 'spotify.com']) {
    assert.equal(clickEventFor(hostname), 'track_button_click', hostname);
  }
});

test('lookalike domains are not classified as music', () => {
  for (const hostname of ['notyoutube.com', 'evil-youtube.com', 'youtube.com.attacker.example', 'spotify.com.evil.test', 'evil-unitedmasters.com']) {
    assert.equal(clickEventFor(hostname), 'link_click', hostname);
  }
});

test('a trailing DNS dot does not change an exact music-domain match', () => {
  assert.equal(clickEventFor('youtube.com.'), 'track_button_click');
});
