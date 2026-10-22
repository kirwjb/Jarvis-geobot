import { state, TAGS, persist } from '../core/state.js?v=20261017-010';
import { request } from '../core/api.js?v=20261017-010';
import { $, esc, toast, haptic } from '../ui/helpers.js?v=20261017-010';
import { go } from '../core/router.js?v=20261017-010';
import { loadPlaces } from './places.js?v=20261017-010';
import { t } from '../ui/language.js?v=20261017-010';

export function renderRegions(list = state.regions) {
  const grid = $('#regions-grid');
  if (!grid) return;
  grid.innerHTML = list.length ? list.map((region) => `<button class="card" type="button" data-action="region" data-id="${esc(region.id)}"><span>${esc(region.name)}</span></button>`).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
}

export function renderCities(list = state.cities) {
  const grid = $('#cities-grid');
  if (!grid) return;
  grid.innerHTML = list.length ? list.map((city) => `<button class="card ${state.city === city.name ? 'active' : ''}" type="button" data-action="city" data-city="${esc(city.name)}"><span>${esc(city.name)}</span></button>`).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
}

export function renderTags() {
  const list = $('#tags-list');
  if (!list) return;
  list.innerHTML = TAGS.map((tag) => {
    const active = state.tags.has(tag.id);
    return `<button class="tag ${active ? 'active' : ''}" type="button" data-action="tag" data-id="${esc(tag.id)}" aria-pressed="${active ? 'true' : 'false'}">${esc(t(tag.id))}</button>`;
  }).join('');
  const button = $('#btn-tags');
  if (button) button.disabled = !state.tags.size;
}

export async function loadRegions() {
  try {
    state.regions = await request('/regions') || [];
    renderRegions();
  } catch (error) {
    toast(`${t('regions_failed')}: ${error.message}`);
  }
}

export async function pickRegion(id) {
  const region = state.regions.find((item) => item.id === id);
  if (!region) return;
  state.region = region.id;
  state.city = null;
  state.cities = [];
  $('#region-title').textContent = region.name;
  $('#cities-grid').innerHTML = `<div class="loading">${esc(t('loading'))}</div>`;
  go('cities');
  try {
    state.cities = await request(`/cities/${encodeURIComponent(id)}`) || [];
    renderCities();
  } catch (error) {
    $('#cities-grid').innerHTML = `<div class="empty">${esc(error.message)}</div>`;
    toast(`${t('cities_failed')}: ${error.message}`);
  }
  persist();
}

export function pickCity(name) {
  const wanted = String(name || '').trim();
  const city = state.cities.find((item) => item.name === wanted);
  if (!city) return;
  state.city = city.name;
  state.weatherCity = city.name;
  if (state.mode === 'weather') {
    state.mode = 'travel';
    go('weather');
    persist();
    haptic();
    window.dispatchEvent(new CustomEvent('jarvis:weather', { detail: { city: city.name } }));
    return;
  }
  renderTags();
  go('tags');
  persist();
  haptic();
}

export function toggleTag(id) {
  state.tags.has(id) ? state.tags.delete(id) : state.tags.add(id);
  renderTags();
  persist();
  haptic();
}

export function filterRegions(query) {
  const value = String(query || '').toLowerCase().trim();
  renderRegions(state.regions.filter((region) => region.name.toLowerCase().includes(value)));
}

export function filterCities(query) {
  const value = String(query || '').toLowerCase().trim();
  renderCities(state.cities.filter((city) => city.name.toLowerCase().includes(value)));
}

export async function startPlaces() {
  if (!state.region || !state.city) return toast(t('select_city'));
  if (!state.tags.size) return toast(t('select_category'));
  await loadPlaces();
}
