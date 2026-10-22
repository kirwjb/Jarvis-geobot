import { state } from '../../core/state.js?v=20261017-010';
import { request } from '../../core/api.js?v=20261017-010';
import { toast } from '../../ui/helpers.js?v=20261017-010';
import { t } from '../../ui/language.js?v=20261017-010';
import { placesState, buildPlacesQueryKey } from './state.js?v=20261017-010';
import { renderPlaces } from './view.js?v=20261017-010';
import { loadMissingPhotos } from './photos.js?v=20261017-010';

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
    const payload = {
      limit: placesState.pageSize + 1,
      offset: nextPage * placesState.pageSize,
    };
    if (state.region) payload.region = state.region;
    if (state.city) payload.city = state.city;
    if (state.tags && state.tags.size) payload.tags = [...state.tags];
    if (placesState.search) payload.search = placesState.search;
    if (placesState.shuffleSeed) payload.shuffle = placesState.shuffleSeed;
    const data = await request('/pois/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const pois = Array.isArray(data?.pois) ? data.pois : [];
    const page = { places: pois.slice(0, placesState.pageSize), hasNext: pois.length > placesState.pageSize };
    placesState.cache.set(nextPage, page);
    placesState.page = nextPage;
    state.pois = page.places;
    placesState.hasNext = page.hasNext;
  } catch (error) {
    toast(`${t('places_failed')}: ${error.message}`);
  } finally {
    placesState.loading = false;
    renderPlaces();
    void loadMissingPhotos(state.pois);
  }
}
