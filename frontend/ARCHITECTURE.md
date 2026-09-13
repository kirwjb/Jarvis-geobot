# Frontend architecture

The frontend is organized by responsibility rather than by screen count.

```text
frontend/
├── index.html                 # Static shell and screen containers
├── style.css                  # Global layout and tokens
├── css/                       # Feature/component stylesheets
│   ├── components.css
│   ├── interactions.css
│   ├── weather.css
│   └── groups.css
└── js/
    ├── main.js                # Small application composition root
    ├── core/                  # State, API transport, routing
    ├── ui/                    # Theme, language, DOM helpers
    └── features/              # User-facing domains
        ├── travel.js
        ├── places.js
        ├── weather.js
        ├── route.js
        ├── groups.js          # Groups controller
        ├── groups/
        │   ├── api.js         # Groups HTTP contract
        │   └── view.js        # Groups rendering
        └── ...
```

## Rules for new features

1. A new button belongs to the feature that owns its behavior.
2. `main.js` only dispatches events; business logic should not accumulate there.
3. HTTP requests belong in a feature `api.js` module when a feature has more than a few endpoints.
4. DOM rendering belongs in a feature view module once a feature becomes non-trivial.
5. Global state belongs in `core/state.js`; temporary feature state stays inside the feature.
6. CSS that is specific to a feature belongs in `css/<feature>.css`.
7. User-provided strings inserted with `innerHTML` must be escaped.
8. External media should be represented by URLs. The frontend must not assume that the backend stores image bytes.
9. Each feature should expose a small public API from its controller instead of exporting internal helpers.

This structure is deliberately incremental: existing features can be split into
`api.js` and `view.js` when they grow, without forcing a large rewrite of the app.
