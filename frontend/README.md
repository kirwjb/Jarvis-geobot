# Frontend architecture

The Mini App frontend is intentionally split by responsibility.

```text
frontend/
├── index.html              # semantic UI shell; no application logic
├── style.css               # legacy visual base styles kept stable
├── css/
│   ├── interactions.css    # hit-testing / cursor contract
│   └── components.css      # reusable component states
├── js/
│   ├── main.js             # single application entrypoint + event boundary
│   ├── core/
│   │   ├── state.js        # application state + persistence
│   │   ├── api.js          # authenticated API client
│   │   └── router.js       # screen navigation + Telegram back button
│   ├── features/
│   │   ├── travel.js       # regions, cities, interests
│   │   ├── places.js       # POI feed, pagination, favorites, details
│   │   ├── weather.js       # weather screen/data
│   │   ├── route.js         # route building/editing
│   │   └── navigation-extra.js # favorites/groups navigation
│   └── ui/
│       ├── helpers.js       # DOM helpers, toast, haptics
│       ├── theme.js         # local theme state
│       └── language.js      # language selector state
├── logo.svg
└── favicon.svg
```

## Rules

1. `index.html` contains markup only. No inline `onclick`, `oninput` or navigation logic.
2. `main.js` is the only application entrypoint and owns the document-level event boundary.
3. Features do not install global click handlers.
4. API calls go through `core/api.js`.
5. Persistent state lives in `core/state.js`.
6. Screen changes go through `core/router.js`.
7. Interactive hit-testing is defined once in `css/interactions.css`.
8. Temporary override files are not used. A feature must have one owner.

The previous `app.js`, `ux_fixes.js`, `enhancements.js`, `navigation.js`, `startup_fix.js`, `feed_pagination.js`, `photo_loader.js` and global `i18n.js` layers were removed because they were competing for ownership of the same DOM and functions.
