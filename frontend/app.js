const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}



const S = {


  mode: 'travel',

  region: null,
  city: null,

  tags: new Set(),
  favs: new Set(),

  route: [],

  filtered: []
};




const API = '/api';




const REGIONS = [

  {
    id: 'minsk',
    name: 'Минская'
  },

  {
    id: 'brest',
    name: 'Брестская'
  },

  {
    id: 'grodno',
    name: 'Гродненская'
  },

  {
    id: 'gomel',
    name: 'Гомельская'
  },

  {
    id: 'mogilev',
    name: 'Могилёвская'
  },

  {
    id: 'vitebsk',
    name: 'Витебская'
  }

];




const CITIES = {

  minsk: [

    {
      name: 'Минск',
      w: {
        t: 22,
        d: 'Переменная облачность',
        h: 58,
        wind: 3.2,
        p: 1012
      }
    },

    {
      name: 'Несвиж',
      w: {
        t: 21,
        d: 'Ясно',
        h: 55,
        wind: 2.8,
        p: 1013
      }
    },

    {
      name: 'Мир',
      w: {
        t: 20,
        d: 'Облачно',
        h: 62,
        wind: 3.5,
        p: 1011
      }
    },

    {
      name: 'Борисов',
      w: {
        t: 19,
        d: 'Пасмурно',
        h: 65,
        wind: 4.1,
        p: 1010
      }
    }

  ],


  brest: [

    {
      name: 'Брест',
      w: {
        t: 24,
        d: 'Солнечно',
        h: 50,
        wind: 2.5,
        p: 1014
      }
    },

    {
      name: 'Пинск',
      w: {
        t: 23,
        d: 'Ясно',
        h: 52,
        wind: 2.2,
        p: 1013
      }
    },

    {
      name: 'Кобрин',
      w: {
        t: 22,
        d: 'Переменная облачность',
        h: 56,
        wind: 3.0,
        p: 1012
      }
    }

  ],


  grodno: [

    {
      name: 'Гродно',
      w: {
        t: 21,
        d: 'Облачно',
        h: 60,
        wind: 3.3,
        p: 1011
      }
    },

    {
      name: 'Лида',
      w: {
        t: 20,
        d: 'Пасмурно',
        h: 64,
        wind: 3.8,
        p: 1010
      }
    },

    {
      name: 'Слоним',
      w: {
        t: 19,
        d: 'Дождь',
        h: 78,
        wind: 4.5,
        p: 1008
      }
    }

  ],


  gomel: [

    {
      name: 'Гомель',
      w: {
        t: 23,
        d: 'Солнечно',
        h: 48,
        wind: 2.4,
        p: 1014
      }
    },

    {
      name: 'Мозырь',
      w: {
        t: 22,
        d: 'Ясно',
        h: 50,
        wind: 2.6,
        p: 1013
      }
    },

    {
      name: 'Речица',
      w: {
        t: 21,
        d: 'Переменная облачность',
        h: 55,
        wind: 3.1,
        p: 1012
      }
    }

  ],


  mogilev: [

    {
      name: 'Могилёв',
      w: {
        t: 20,
        d: 'Пасмурно',
        h: 66,
        wind: 3.9,
        p: 1009
      }
    },

    {
      name: 'Бобруйск',
      w: {
        t: 19,
        d: 'Облачно',
        h: 63,
        wind: 3.5,
        p: 1010
      }
    },

    {
      name: 'Осиповичи',
      w: {
        t: 18,
        d: 'Дождь',
        h: 80,
        wind: 4.8,
        p: 1007
      }
    }

  ],


  vitebsk: [

    {
      name: 'Витебск',
      w: {
        t: 19,
        d: 'Переменная облачность',
        h: 61,
        wind: 3.4,
        p: 1011
      }
    },

    {
      name: 'Полоцк',
      w: {
        t: 18,
        d: 'Пасмурно',
        h: 67,
        wind: 4.0,
        p: 1009
      }
    },

    {
      name: 'Новополоцк',
      w: {
        t: 18,
        d: 'Облачно',
        h: 65,
        wind: 3.7,
        p: 1010
      }
    }

  ]

};



const TAGS = [

  {
    id: 'architecture',
    name: 'Архитектура'
  },

  {
    id: 'nature',
    name: 'Природа'
  },

  {
    id: 'museum',
    name: 'Музеи'
  },

  {
    id: 'church',
    name: 'Храмы'
  },

  {
    id: 'castle',
    name: 'Замки'
  },

  {
    id: 'monument',
    name: 'Памятники'
  },

  {
    id: 'park',
    name: 'Парки'
  }

];




const POIS = [

  {
    id: 1,
    name: 'Red Church',
    city: 'Минск',
    region: 'minsk',
    addr: 'Красный костёл',
    cat: 'church',
    rating: 4.8
  },

  {
    id: 2,
    name: 'National Library',
    city: 'Минск',
    region: 'minsk',
    addr: 'Независимости 116',
    cat: 'architecture',
    rating: 4.7
  },

  {
    id: 3,
    name: 'Mir Castle',
    city: 'Мир',
    region: 'minsk',
    addr: 'Мирский сельсовет',
    cat: 'castle',
    rating: 4.9
  },

  {
    id: 4,
    name: 'Nesvizh Castle',
    city: 'Несвиж',
    region: 'minsk',
    addr: 'Замковая 2',
    cat: 'castle',
    rating: 4.8
  },

  {
    id: 5,
    name: 'Brest Fortress',
    city: 'Брест',
    region: 'brest',
    addr: 'Территория крепости',
    cat: 'monument',
    rating: 4.9
  },

  {
    id: 6,
    name: 'Belovezhskaya Pushcha',
    city: 'Брест',
    region: 'brest',
    addr: 'Каменюкский с/с',
    cat: 'nature',
    rating: 4.8
  },

  {
    id: 7,
    name: 'Grodno Castle',
    city: 'Гродно',
    region: 'grodno',
    addr: 'Замковая 20',
    cat: 'castle',
    rating: 4.6
  },

  {
    id: 8,
    name: 'Park Gorkogo',
    city: 'Минск',
    region: 'minsk',
    addr: 'Проспект Независимости',
    cat: 'park',
    rating: 4.5
  },

  {
    id: 9,
    name: 'Museum of Great War',
    city: 'Минск',
    region: 'minsk',
    addr: 'Проспект Победителей 8',
    cat: 'museum',
    rating: 4.7
  },

  {
    id: 10,
    name: 'Kolozhskaya Church',
    city: 'Гродно',
    region: 'grodno',
    addr: 'Коложский пер. 6',
    cat: 'church',
    rating: 4.6
  },

  {
    id: 11,
    name: 'Rumyantsev Palace',
    city: 'Гомель',
    region: 'gomel',
    addr: 'Площадь Ленина 1',
    cat: 'architecture',
    rating: 4.5
  },

  {
    id: 12,
    name: 'Bobruisk Fortress',
    city: 'Бобруйск',
    region: 'mogilev',
    addr: 'ул. Крепостная',
    cat: 'monument',
    rating: 4.4
  }

];




function go(id) {

  const target = document.getElementById(id);

  if (!target) {
    console.error('Screen not found:', id);
    return;
  }

  document
    .querySelectorAll('.screen')
    .forEach(screen => {
      screen.classList.remove('active');
    });

  target.classList.add('active');




  const nav = document.getElementById('bottom-nav');

  if (nav) {

    nav.style.display =
      id === 'splash'
        ? 'none'
        : 'flex';

  }




  if (tg) {

    if (id === 'splash') {
      tg.BackButton.hide();
    } else {
      tg.BackButton.show();
    }

  }




  if (id === 'route') {
    renderRoute();
  }

}




if (tg) {

  tg.BackButton.onClick(() => {

    const active =
      document.querySelector('.screen.active');

    if (!active) {
      return;
    }

    const id = active.id;


    if (id === 'regions') {

      go('splash');

    }

    else if (id === 'cities') {

      go('regions');

    }

    else if (id === 'weather') {

   

      go('cities');

    }

    else if (id === 'tags') {

      go('cities');

    }

    else if (id === 'cards') {

      go('tags');

    }

    else if (id === 'route') {

      goBackFromRoute();

    }

  });

}




function toast(message) {

  const element =
    document.getElementById('toast');

  if (!element) {
    return;
  }

  element.textContent = message;

  element.classList.add('show');

  setTimeout(() => {

    element.classList.remove('show');

  }, 2000);

}




function updateFab() {

  const fab =
    document.getElementById('fab');

  const count =
    document.getElementById('fab-count');


  if (!fab || !count) {
    return;
  }


  count.textContent =
    S.route.length;


  if (S.route.length > 0) {

    fab.classList.remove('hidden');

  } else {

    fab.classList.add('hidden');

  }

}




function setActiveTab(tab) {

  document
    .querySelectorAll('.bottom-nav-item')
    .forEach(item => {

      item.classList.toggle(
        'active',
        item.dataset.tab === tab
      );

    });

}



function openTravel() {

  S.mode = 'travel';

  setActiveTab('travel');

  go('regions');

}




function openWeather() {

  S.mode = 'weather';

  setActiveTab('weather');


  if (S.city) {

    renderWeatherScreen();

    return;

  }


  go('regions');

}




function bottomNavigate(tab) {

  if (tab === 'travel') {

    openTravel();

    return;

  }


  if (tab === 'weather') {

    openWeather();

    return;

  }

}


function renderRegions(list) {

  const grid =
    document.getElementById('regions-grid');

  if (!grid) {
    return;
  }


  grid.innerHTML = list.map(region => `

    <div
      class="card"
      onclick="pickRegion('${region.id}')"
    >

      <span>
        ${region.name}
      </span>

    </div>

  `).join('');

}


function filterRegions(query) {

  const q =
    query.toLowerCase().trim();


  renderRegions(

    REGIONS.filter(region =>
      region.name
        .toLowerCase()
        .includes(q)
    )

  );

}



function pickRegion(id) {

  S.region = id;


  const region =
    REGIONS.find(
      item => item.id === id
    );


  if (!region) {
    return;
  }


  document
    .getElementById('region-title')
    .textContent =
      `${region.name} область`;


  renderCities(
    CITIES[id] || []
  );




  go('cities');

}



function renderCities(list) {

  const grid =
    document.getElementById('cities-grid');

  if (!grid) {
    return;
  }


  grid.innerHTML = list.map(
    (city, index) => `

      <div
        class="card ${
          S.city === city.name
            ? 'active'
            : ''
        }"
        onclick="pickCity('${city.name}', ${index})"
      >

        <span>
          ${city.name}
        </span>

      </div>

    `
  ).join('');

}


function filterCities(query) {

  const q =
    query.toLowerCase().trim();


  const cities =
    CITIES[S.region] || [];


  renderCities(

    cities.filter(city =>
      city.name
        .toLowerCase()
        .includes(q)
    )

  );

}




function pickCity(name, index) {

  const cities =
    CITIES[S.region] || [];


  const city =
    cities[index];


  if (!city) {
    return;
  }


  S.city = city.name;


 

  if (S.mode === 'weather') {

    renderWeatherScreen();

    return;

  }




  if (S.mode === 'travel') {

    renderTags();

    go('tags');

    return;

  }

}




function renderWeatherScreen() {

  const empty =
    document.getElementById('weather-empty');

  const box =
    document.getElementById('weather-box');


  if (!empty || !box) {
    return;
  }



  if (!S.city) {

    empty.style.display = 'flex';

    box.style.display = 'none';

    go('weather');

    return;

  }


  const cities =
    CITIES[S.region] || [];


  const city =
    cities.find(
      item => item.name === S.city
    );


  if (!city) {

    empty.style.display = 'flex';

    box.style.display = 'none';

    go('weather');

    return;

  }

  empty.style.display = 'none';

  box.style.display = 'block';


  renderWeather(city);


  go('weather');

}


function renderWeather(city) {

  const box =
    document.getElementById('weather-box');


  if (!box || !city || !city.w) {
    return;
  }


  const w = city.w;


  box.innerHTML = `

    <div class="w-top">

      <div>

        <div class="w-temp">
          ${w.t}°C
        </div>

        <div class="w-desc">
          ${w.d}
        </div>

        <div
          style="
            margin-top:6px;
            font-size:13px;
            color:#777786;
          "
        >
          ${city.name}
        </div>

      </div>

    </div>


    <div class="w-grid">

      <div class="w-item">

        <label>
          Влажность
        </label>

        <val>
          ${w.h}%
        </val>

      </div>


      <div class="w-item">

        <label>
          Ветер
        </label>

        <val>
          ${w.wind} м/с
        </val>

      </div>


      <div class="w-item">

        <label>
          Давление
        </label>

        <val>
          ${w.p} hPa
        </val>

      </div>

    </div>

  `;

}




function renderTags() {

  const list =
    document.getElementById('tags-list');

  const button =
    document.getElementById('btn-tags');


  if (!list || !button) {
    return;
  }


  list.innerHTML = TAGS.map(tag => `

    <div
      class="tag ${
        S.tags.has(tag.id)
          ? 'active'
          : ''
      }"
      onclick="toggleTag('${tag.id}')"
    >

      ${tag.name}

    </div>

  `).join('');


  button.disabled =
    S.tags.size === 0;

}


function toggleTag(id) {

  if (S.tags.has(id)) {

    S.tags.delete(id);

  } else {

    S.tags.add(id);

  }


  renderTags();

}



function loadCards() {

  S.filtered = POIS.filter(place => {

    const sameRegion =
      place.region === S.region;


    const sameCity =
      !S.city ||
      place.city === S.city;


    const sameCategory =
      S.tags.has(place.cat);


    return (
      sameRegion &&
      sameCity &&
      sameCategory
    );

  });


  document
    .getElementById('cards-title')
    .textContent =
      S.city || 'Места';


  renderFeed();

  go('cards');

}




function renderFeed() {

  const feed =
    document.getElementById('feed');


  if (!feed) {
    return;
  }


  if (S.filtered.length === 0) {

    feed.innerHTML = `

      <div
        style="
          text-align:center;
          padding:50px;
          color:#4a4a5a;
        "
      >

        Ничего не найдено

      </div>

    `;

    return;

  }


  feed.innerHTML = S.filtered.map(
    place => {

      const isFavorite =
        S.favs.has(place.id);


      const inRoute =
        S.route.some(
          item => item.id === place.id
        );


      return `

        <div class="poi-card">

          <div class="poi-img">

            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1"
            >

              <path
                d="
                  M3 21h18
                  M5 21V7l8-4
                  8 4v14
                  M9 21v-6h6v6
                "
              />

            </svg>

          </div>


          <div class="poi-body">

            <div class="poi-name">
              ${place.name}
            </div>


            <div class="poi-rating">

              <span class="star">
                ★
              </span>

              <span class="val">
                ${place.rating}
              </span>

            </div>


            <div class="poi-loc">

              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >

                <path
                  d="
                    M12 2
                    C8 2 5 5 5 9
                    c0 5 7 13 7 13
                    s7-8 7-13
                    c0-4-3-7-7-7z
                  "
                />

                <circle
                  cx="12"
                  cy="9"
                  r="2.5"
                />

              </svg>

              ${place.city}

            </div>
            <div class="poi-actions">
              <button
                class="
                  poi-act
                  ${isFavorite ? 'active' : ''}
                "
                onclick="
                  toggleFav(${place.id})
                "
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="${
                    isFavorite
                      ? 'currentColor'
                      : 'none'
                  }"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="
                      M20.84 4.61
                      a5.5 5.5 0 0 0-7.78 0
                      L12 5.67
                      l-1.06-1.06
                      a5.5 5.5 0 0 0-7.78 7.78
                      l1.06 1.06
                      L12 21.23
                      l7.78-7.78
                      1.06-1.06
                      a5.5 5.5 0 0 0 0-7.78z
                    "
                  />
                </svg>
                Favorite
              </button>
              <button
                class="
                  poi-act
                  ${inRoute ? 'active' : ''}
                "
                onclick="
                  toggleRoute(${place.id})
                "
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="
                      M12 2L2 7l10 5
                      10-5-10-5z
                    "
                  />
                  <path
                    d="
                      M2 17l10 5
                      10-5
                    "
                  />
                  <path
                    d="
                      M2 12l10 5
                      10-5
                    "
                  />
                </svg>
                Route
              </button>
            </div>
          </div>
        </div>
      `;
    }
  ).join('');
}
function toggleFav(id) {
  if (S.favs.has(id)) {
    S.favs.delete(id);
    toast('Удалено из избранного');
  } else {
    S.favs.add(id);
    toast('В избранном');
  }
  renderFeed();
}
function toggleRoute(id) {
  const existing =
    S.route.find(
      item => item.id === id
    );
  if (existing) {
    S.route =
      S.route.filter(
        item => item.id !== id
      );
    toast('Удалено из маршрута');
  }
  else {
    const place =
      POIS.find(
        item => item.id === id
      );
    if (place) {
      S.route.push(place);
      toast('Добавлено в маршрут');
    }
  }
  updateFab();
  renderFeed();
}
function goBackFromRoute() {
  if (S.filtered.length > 0) {
    go('cards');
  } else {
    go('tags');
  }
}

function renderRoute() {
  const list =
    document.getElementById('route-list');
  const button =
    document.getElementById('btn-build');
  if (!list || !button) {
    return;
  }
  if (S.route.length === 0) {
    list.innerHTML = `
      <div class="route-empty">
        Маршрут пуст.
        <br>
        Добавьте точки из карточек.
      </div>
    `;
    button.disabled = true;
    return;
  }
  button.disabled =
    S.route.length < 2;
  list.innerHTML =
    S.route.map(
      (place, index) => `
        <div class="route-item">
          <div class="route-num">
            ${index + 1}
          </div>
          <div class="route-info">
            <div class="route-name">
              ${place.name}
            </div>
            <div class="route-city">
              ${place.city}
            </div>
          </div>
          <button
            class="route-del"
            onclick="
              removeRoute(${place.id})
            "
          >
            ✕
          </button>
        </div>
      `
    ).join('');
}

function removeRoute(id) {
  S.route =
    S.route.filter(
      item => item.id !== id
    );
  updateFab();
  renderRoute();
}

function buildRoute() {
  toast('Маршрут построен!');
  if (
    tg &&
    tg.HapticFeedback
  ) {
    tg.HapticFeedback
      .notificationOccurred(
        'success'
      );

  }

}
function init() {
  S.mode = 'travel';
  setActiveTab('travel');
  renderRegions(REGIONS);
  renderTags();
  updateFab();
  const nav =
    document.getElementById('bottom-nav');

  if (nav) {
    nav.style.display = 'none';
  }

}
init();