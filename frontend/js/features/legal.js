import { esc } from '../ui/helpers.js?v=20261017-010';
import { ICONS } from '../ui/icons.js?v=20261017-010';
import { currentLanguage } from '../ui/language.js?v=20261017-010';

export const LEGAL_CONTENT = {
  version: '1.0.0',
  locale: 'be-BY',
  lastUpdated: '2026-10-12',
  title: 'Прававая інфармацыя і ліцэнзіі',
  subtitle: 'Адкрыты зыходны код, картаграфічныя крыніцы і прыватнасць даных',
  sections: [
    {
      id: 'license',
      icon: ICONS.scroll,
      title: 'Аўтарскія правы і ліцэнзія праекта',
      badge: 'MIT License',
      body: 'Зыходны код кліенцкай і сервернай частак праграмнага комплексу «Jarvis GeoBot» распаўсюджваецца на ўмовах свабоднай ліцэнзіі MIT. Праект з\'яўляецца некамерцыйнай распрацоўкай, створанай у адукацыйных мэтах і для грамадскага карыстання супольнасцю. Вы маеце права свабодна вывучаць, выкарыстоўваць, мадыфікаваць і распаўсюджваць гэты прадукт у адпаведнасці з умовамі ліцэнзійнага пагаднення MIT.',
      links: [
        {
          label: 'Рэпазіторый праекта на GitHub',
          url: 'https://github.com/kirwjb/Jarvis-geobot'
        }
      ]
    },
    {
      id: 'osm',
      icon: ICONS.map,
      title: 'Картаграфічныя даныя і пошук аб\'ектаў',
      badge: 'ODbL 1.0',
      body: 'Даныя карт і геаграфічных аб\'ектаў прадастаўлены ўдзельнікамі OpenStreetMap. База геаграфічных звестак і каардынатаў распаўсюджваецца на ўмовах ліцэнзіі Open Database License (ODbL) фонду OpenStreetMap Foundation (OSMF). Пошук славутасцяў і адлюстраванне кропак цікавасці (POI) ажыццяўляюцца праз адкрытыя геаінфармацыйныя крыніцы з поўным прызнаннем аўтарскіх правоў супольнасці картографаў.',
      copyright: '© Удзельнікі OpenStreetMap (ODbL)',
      links: [
        {
          label: 'Ліцэнзія і аўтарскія правы OpenStreetMap',
          url: 'https://www.openstreetmap.org/copyright'
        }
      ]
    },
    {
      id: 'weather',
      icon: ICONS.weatherCloudSun,
      title: 'Метэаралагічная інфармацыя',
      badge: 'wttr.in API',
      body: 'Звесткі аб надвор\'і, тэмпературы, вільготнасці, ветры і астранамічных цыклах фарміруюцца шляхам агрэгацыі з адкрытых крыніц праз сэрвіс wttr.in. Прадстаўленая метэаралагічная інфармацыя носіць выключна даведачны і арыенціровачны характар. Бот «Jarvis GeoBot» не з\'яўляецца дзяржаўнай гідраметэаралагічнай службай, не фарміруе афіцыйных штармавых папярэджанняў або надзвычайных абвестак і не нясе адказнасці за магчымыя нязручнасці або рашэнні, прынятыя на падставе прагнозу.',
      links: [
        {
          label: 'Апісанне сэрвісу wttr.in',
          url: 'https://wttr.in/:help'
        }
      ]
    },
    {
      id: 'privacy',
      icon: ICONS.shield,
      title: 'Палітыка прыватнасці і апрацоўка даных',
      badge: 'Закон РБ № 99-З',
      body: 'Апрацоўка звестак выконваецца ў адпаведнасці з базавымі прынцыпамі абароны інфармацыі і палажэннямі Закона Рэспублікі Беларусь ад 7 мая 2021 г. № 99-З «Аб абароне персанальных даных».\n\n• Апрацоўваемыя звесткі: Telegram User ID, імя карыстальніка (username) і часавыя геаграфічныя каардынаты, якія перадаюцца выключна па ініцыятыве і са згоды карыстальніка.\n• Мэта апрацоўкі: пошук найбліжэйшых славутасцяў, разлік аптымальных турыстычных маршрутаў і атрыманне мясцовага прагнозу надвор\'я для бягучай сесіі.\n• Захаванне і канфідэнцыйнасць: геалакацыйныя каардынаты захоўваюцца выключна часова ў аператыўнай памяці (кэш Redis) і аўтаматычна выдаляюцца пасля завяршэння сесіі. Геаданыя не фіксуюцца на пастаяннай аснове, не выкарыстоўваюцца для прафілявання перамяшчэння і ніколі не перадаюцца трэцім асобам.\n• Кіраванне доступам: карыстальнік мае права ў любы момант забараніць доступ да геалакацыі ў наладах прылады або спыніць сесію ў боце, што цалкам анулюе часовы стан сесіі.',
      links: [
        {
          label: 'Закон РБ «Аб абароне персанальных даных» (№ 99-З)',
          url: 'https://pravo.by/document/?guid=12551&p0=H12100099'
        }
      ]
    }
  ]
};

export function openExternalLink(url) {
  if (!url) return;
  const fullUrl = url.startsWith('http') ? url : new URL(url, window.location.origin).href;
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink && fullUrl.startsWith('https://')) {
    tg.openLink(fullUrl);
  } else {
    window.open(fullUrl, '_blank', 'noopener,noreferrer');
  }
}

export async function openFullLegalViewer() {
  try {
    const res = await fetch('/LEGAL.MD', {
      headers: { Accept: 'text/markdown, text/plain, */*' },
    });
    if (res.ok) {
      const text = await res.text();
      showLegalTextModal(text);
      return;
    }
  } catch (_) {}
  openExternalLink('/LEGAL.MD');
}

export function renderMarkdown(md) {
  if (!md) return '';
  const lines = md.split(/\r?\n/);
  const out = [];
  let inList = false;
  let inQuote = false;
  let quoteBuf = [];

  function flushList() {
    if (inList) {
      out.push('</ul>');
      inList = false;
    }
  }

  function flushQuote() {
    if (inQuote) {
      const qHtml = quoteBuf.map(l => formatInline(l)).join('<br>');
      out.push(`<blockquote class="legal-blockquote">${qHtml}</blockquote>`);
      inQuote = false;
      quoteBuf = [];
    }
  }

  function formatInline(str) {
    let s = esc(str);
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="legal-link">$1</a>');
    s = s.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    return s;
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (trimmed.startsWith('> ') || trimmed === '>') {
      flushList();
      inQuote = true;
      quoteBuf.push(trimmed.replace(/^>\s?/, ''));
      continue;
    } else {
      flushQuote();
    }

    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushList();
      out.push('<hr class="legal-divider">');
      continue;
    }

    if (trimmed.startsWith('# ')) {
      flushList();
      out.push(`<h1 class="legal-h1">${formatInline(trimmed.slice(2))}</h1>`);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      out.push(`<h2 class="legal-h2">${formatInline(trimmed.slice(3))}</h2>`);
      continue;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      out.push(`<h3 class="legal-h3">${formatInline(trimmed.slice(4))}</h3>`);
      continue;
    }
    if (trimmed.startsWith('#### ')) {
      flushList();
      out.push(`<h4 class="legal-h4">${formatInline(trimmed.slice(5))}</h4>`);
      continue;
    }

    const listMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    if (listMatch) {
      if (!inList) {
        out.push('<ul class="legal-list">');
        inList = true;
      }
      out.push(`<li>${formatInline(listMatch[1])}</li>`);
      continue;
    } else {
      flushList();
    }

    if (!trimmed) {
      continue;
    }

    out.push(`<p class="legal-p">${formatInline(trimmed)}</p>`);
  }

  flushList();
  flushQuote();
  return out.join('\n');
}

function showLegalTextModal(markdownText) {
  const viewer = document.createElement('div');
  viewer.className = 'jarvis-modal jarvis-legal-modal';
  const title = currentLanguage === 'RU' ? 'Полная юридическая информация' : 'Поўная юрыдычная інфармацыя';
  const closeText = currentLanguage === 'RU' ? 'Закрыть' : 'Закрыць';

  viewer.innerHTML = `
    <div class="jarvis-modal-card legal-modal-sheet legal-full-viewer">
      <div class="legal-sheet-head">
        <div>
          <h2 class="legal-sheet-title">${ICONS.legal} <span>${esc(title)}</span></h2>
          <p class="legal-sheet-subtitle">LEGAL.MD · Jarvis GeoBot Compliance Core</p>
        </div>
        <button class="jarvis-close" type="button" data-action="close-viewer" aria-label="${esc(closeText)}">${ICONS.close}</button>
      </div>
      <div class="legal-sheet-content legal-full-content">
        <div class="legal-markdown-view">${renderMarkdown(markdownText)}</div>
      </div>
      <div class="legal-sheet-footer">
        <button class="btn-main legal-sheet-close-btn" type="button" data-action="close-viewer">${esc(closeText)}</button>
      </div>
    </div>
  `;

  viewer.addEventListener('click', (event) => {
    if (event.target === viewer) viewer.remove();
  });
  viewer.querySelectorAll('[data-action="close-viewer"]').forEach(btn => {
    btn.addEventListener('click', () => viewer.remove());
  });

  document.body.appendChild(viewer);
}

export function openLegalModal() {
  document.querySelectorAll('.jarvis-legal-modal').forEach(el => el.remove());
  const modal = document.createElement('div');
  modal.className = 'jarvis-modal jarvis-legal-modal';

  const sectionsHtml = LEGAL_CONTENT.sections.map(s => `
    <article class="legal-card" id="legal-${esc(s.id)}">
      <div class="legal-card-header">
        <span class="legal-card-icon">${s.icon}</span>
        <div class="legal-card-titles">
          <h3 class="legal-card-title">${esc(s.title)}</h3>
          ${s.badge ? `<span class="legal-badge">${esc(s.badge)}</span>` : ''}
        </div>
      </div>
      <p class="legal-card-body">${esc(s.body).replaceAll('\n', '<br>')}</p>
      ${s.copyright ? `<div class="legal-copyright-box"><strong>${esc(s.copyright)}</strong></div>` : ''}
      ${s.links && s.links.length ? `
        <div class="legal-card-links">
          ${s.links.map(l => `
            <button class="legal-link-btn" type="button" data-action="open-legal-link" data-url="${esc(l.url)}">
              <span>${esc(l.label)}</span>
              <span class="legal-link-arrow">${ICONS.externalLink}</span>
            </button>
          `).join('')}
        </div>
      ` : ''}
    </article>
  `).join('');

  const fullLegalLabel = currentLanguage === 'RU' ? 'Полная юридическая информация' : 'Поўная юрыдычная інфармацыя';

  modal.innerHTML = `
    <div class="jarvis-modal-card legal-modal-sheet">
      <div class="legal-sheet-head">
        <div>
          <h2 class="legal-sheet-title">${ICONS.legal} <span>${esc(LEGAL_CONTENT.title)}</span></h2>
          <p class="legal-sheet-subtitle">${esc(LEGAL_CONTENT.subtitle)}</p>
        </div>
        <button class="jarvis-close" type="button" data-action="close-modal" aria-label="Закрыць">${ICONS.close}</button>
      </div>
      <div class="legal-sheet-content">
        ${sectionsHtml}
        <div class="legal-subtle-box">
          <button class="legal-subtle-link" type="button" data-action="open-full-legal" data-url="/LEGAL.MD">
            ${esc(fullLegalLabel)}
          </button>
        </div>
      </div>
      <div class="legal-sheet-footer">
        <button class="btn-main legal-sheet-close-btn" type="button" data-action="close-modal">Зразумела</button>
      </div>
    </div>
  `;

  modal.addEventListener('click', (event) => {
    if (event.target === modal) modal.remove();
  });

  modal.querySelectorAll('[data-action="open-legal-link"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const url = btn.dataset.url;
      if (url) openExternalLink(url);
    });
  });

  modal.querySelectorAll('[data-action="open-full-legal"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      await openFullLegalViewer();
    });
  });

  document.body.appendChild(modal);
}
