# Frontend architecture

The frontend is organized by responsibility rather than by screen count.

```text
frontend/
├── index.html                 # Semantic UI shell and screen containers
├── favicon.svg                # Favicon
├── logo.svg                   # Brand mark
├── style.css                  # Backward-compatibility alias (@import css/style.css)
├── css/                       # Modular stylesheets
│   ├── style.css              # Core tokens, light/dark themes, resets & layout
│   ├── components.css         # UI components, modals, toasts, cards, tools & pagination
│   ├── interactions.css       # Hit-testing, touch feedback, active states
│   └── weather.css            # Weather metrics & display styles
└── js/
    ├── main.js                # Application entrypoint & composition root
    ├── app/
    │   └── events.js          # Centralized event delegation graph
    ├── core/                  # Core infrastructure
    │   ├── api.js             # Authenticated HTTP transport
    │   ├── router.js          # Screen transitions & Telegram BackButton integration
    │   └── state.js           # Global state, persistence & user identity
    ├── ui/                    # Presentation primitives
    │   ├── helpers.js         # DOM helpers, string escaping, toasts, haptics
    │   ├── language.js        # Internationalization (RU/BY) & language switching
    │   └── theme.js           # Theme state (dark/light) & Telegram styling sync
    └── features/              # User-facing domain modules
        ├── travel.js          # Regions, cities & tags selection
        ├── places.js          # POI feed coordinator, search & shuffle
        ├── places/            # POI sub-modules
        │   ├── pagination.js  # Page-based POI fetching & caching
        │   ├── photos.js      # Resilient photo rendering & proxying
        │   ├── state.js       # Runtime feed, search & shuffle seed state
        │   └── view.js        # POI card markup & feed rendering
        ├── favorites.js       # Favorites domain (toggle, load, paginated screen)
        ├── route.js           # Route domain (points, build route, FAB updater)
        └── weather.js         # City weather view & caching
```

## Architectural Guidelines

1. `index.html` contains markup only. No inline `onclick`, `oninput`, or hardcoded navigation logic.
2. `app/events.js` installs the single application-wide event delegation layer. Feature modules never attach ad-hoc document listeners.
3. Feature domains own their data and mutations:
   - `features/favorites.js` owns loading, toggling, and rendering favorites.
   - `features/route.js` owns route points, route building, and the floating route FAB.
   - `features/places.js` coordinates the POI feed, free search, and server-driven shuffling.
   - `features/travel.js` coordinates region, city, and interest category selection.
4. HTTP requests are made via `core/api.js`.
5. Global persisted state lives in `core/state.js`; transient feed state stays inside feature modules.
6. User-provided strings inserted with `innerHTML` must be escaped via `esc()`.
