import { state } from '../../core/state.js';
import { request } from '../../core/api.js';
import { toast } from '../../ui/helpers.js';
import { t } from '../../ui/language.js';
import { placesState, buildPlacesQueryKey } from './state.js';
import { renderPlaces } from './view.js';
import { loadMissingPhotos } from './photos.js';

/** Fetch and display one POI page; cached pages avoid repeat backend calls. */
export async function loadPage(nextPage) {
  if (nextPage < 0 || placesState.loading) return;
  const key = buildPlacesQueryKey(state);
  if (key !== placesState.queryKey) {
    placesState.cache.clear();
    placesState.queryKey = key;
    placesState.page = 0;
    placesState.hasNext = false;
    if (nextPage !== 0) nextPage = 0;
  }
  const cached = placesState.cache.get(nextPage);
  if (cached) {
    placesState.page = nextPage;
    state.pois = cached.places;
    placesState.hasNext = cached.hasNext;
    renderPlaces();
    void loadMissingPhotos(state.pois);
    return;
  }
  placesState.loading = true;
  renderPlaces();
  try {
    const data = await request('/pois/query', { method: 'POST', body: JSON.stringify({ region: state.region, city: state.city, tags: [...state.tags], limit: placesState.pageSize + 1, offset: nextPage * placesState.pageSize }) });
    const pois = Array.isArray(data?.pois) ? data.pois : [];
    const page = { places: pois.slice(0, placesState.pageSize), hasNext: pois.length > placesState.pageSize };
    placesState.cache.set(nextPage, page);
    placesState.page = nextPage;
    state.pois = page.places;
    placesState.hasNext = page.hasNext;
    renderPlaces();
    void loadMissingPhotos(state.pois);
  } catch (error) {
    toast(`${t('places_failed')}: ${error.message}`);
  } finally {
    placesState.loading = false;
    renderPlaces();
  }
}
