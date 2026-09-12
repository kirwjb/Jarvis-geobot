from __future__ import annotations
from typing import Any
import aiohttp
API_URL='https://commons.wikimedia.org/w/api.php'
USER_AGENT='JARVIS-GEO-APP/2.0 (Wikimedia Commons geosearch)'
MIN_RADIUS_M=5
MAX_RADIUS_M=30

def _image_info(page:dict[str,Any])->dict[str,Any]|None:
    info=(page.get('imageinfo') or [None])[0]
    if not info or not info.get('url'): return None
    meta=info.get('extmetadata') or {}
    return {'source':'wikimedia','original_url':info['url'],'thumbnail_url':info.get('thumburl') or info['url'],'author':(meta.get('Artist') or {}).get('value'),'license':(meta.get('LicenseShortName') or {}).get('value'),'title':page.get('title','')}

async def find_photo_by_coordinates(lat:float,lon:float,*,radius_m:int=30)->dict[str,Any]|None:
    radius=max(MIN_RADIUS_M,min(int(radius_m),MAX_RADIUS_M))
    params={'action':'query','format':'json','generator':'geosearch','ggsprimary':'all','ggsnamespace':6,'ggscoord':f'{float(lat)},{float(lon)}','ggsradius':radius,'ggslimit':20,'prop':'imageinfo|coordinates','iiprop':'url|mime|extmetadata','iiurlwidth':1200,'colimit':1}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8),headers={'User-Agent':USER_AGENT,'Accept':'application/json'}) as session:
        async with session.get(API_URL,params=params) as response:
            response.raise_for_status();data=await response.json()
    for page in (data.get('query',{}).get('pages',{}) or {}).values():
        coords=page.get('coordinates') or []
        try: dist=float(coords[0].get('dist'))
        except (IndexError,TypeError,ValueError): continue
        if not MIN_RADIUS_M<=dist<=MAX_RADIUS_M: continue
        image=_image_info(page)
        if not image: continue
        mime=str((page.get('imageinfo') or [{}])[0].get('mime') or '')
        if not mime.startswith('image/'): continue
        image['distance_m']=dist
        return image
    return None
