import { state, TAGS, persist } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast, haptic } from '../ui/helpers.js';
import { go } from '../core/router.js';
import { loadPlaces } from './places.js';
import { t } from '../ui/language.js';

/** Render region choices from application state or a filtered subset. */
export function renderRegions(list = state.regions) {
  const grid = $('#regions-grid');
  if (!grid) return;
  grid.innerHTML = list.length ? list.map((region) => `<button class="card" type="button" data-action="region" data-id="${esc(region.id)}"><span>${esc(region.name)}</span></button>`).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
}

/** Render city choices using the city name as the stable event payload. */
export function renderCities(list = state.cities) {
  const grid = $('#cities-grid');
  if (!grid) return;
  grid.innerHTML = list.length ? list.map((city) => `<button class="card ${state.city === city.name ? 'active' : ''}" type="button" data-action="city" data-city="${esc(city.name)}"><span>${esc(city.name)}</span></button>`).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
}

/** Render translated place categories and enable the continue action when needed. */
export function renderTags() {
  const list = $('#tags-list');
  if (!list) return;
  list.innerHTML = TAGS.map((tag) => `<button class="tag ${state.tags.has(tag.id) ? 'active' : ''}" type="button" data-action="tag" data-id="${esc(tag.id)}">${esc(t(tag.id))}</button>`).join('');
  const button = $('#btn-tags');
  if (button) button.disabled = !state.tags.size;
}

/** Load available regions from the backend and render them. */
export async function loadRegions() {
  try {
    state.regions = await request('/regions') || [];
    renderRegions();
  } catch (error) {
    console.error(error);
    toast(`${t('regions_failed')}: ${error.message}`);
  }
}

/** Select a region, load its cities, and transition to the city screen. */
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

/** Select a city by its stable name instead of a fragile rendered-array index. */
export function pickCity(name) {
  const wanted = String(name || '').trim();
  const city = state.cities.find((item) => item.name === wanted);
  if (!city) return;
  state.city = city.name;
  if (state.mode === 'weather') {
    go('weather');
    window.dispatchEvent(new CustomEvent('jarvis:weather'));
    return;
  }
  renderTags();
  go('tags');
  persist();
  haptic();
}

/** Toggle one category in the current POI query. */
export function toggleTag(id) {
  state.tags.has(id) ? state.tags.delete(id) : state.tags.add(id);
  renderTags();
  persist();
  haptic();
}

/** Filter regions locally without issuing a backend request for every keystroke. */
export function filterRegions(query) {
  const value = String(query || '').toLowerCase().trim();
  renderRegions(state.regions.filter((region) => region.name.toLowerCase().includes(value)));
}

/** Filter cities locally while preserving stable city names for click handling. */
export function filterCities(query) {
  const value = String(query || '').toLowerCase().trim();
  renderCities(state.cities.filter((city) => city.name.toLowerCase().includes(value)));
}

/** Validate the travel selection and start a fresh places feed. */
export async function startPlaces() {
  if (!state.region || !state.city) return toast(t('select_city'));
  if (!state.tags.size) return toast(t('select_category'));
  await loadPlaces();
}
