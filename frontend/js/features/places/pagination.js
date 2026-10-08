import { state } from '../../core/state.js?v=1791475344';
import { request } from '../../core/api.js?v=1791475344';
import { toast } from '../../ui/helpers.js?v=1791475344';
import { t } from '../../ui/language.js?v=1791475344';
import { placesState, buildPlacesQueryKey } from './state.js?v=1791475344';
import { renderPlaces } from './view.js?v=1791475344';
import { loadMissingPhotos } from './photos.js?v=1791475344';

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
    const payload = {
      limit: placesState.pageSize + 1,
      offset: nextPage * placesState.pageSize,
    };
    if (placesState.search) {
      payload.search = placesState.search;
    } else {
      payload.region = state.region;
      payload.city = state.city;
      payload.tags = [...state.tags];
    }
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
