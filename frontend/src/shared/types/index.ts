export interface Attraction {
    id: string;
    title: string;
    location: string;
    address: string;
    category: 'Architecture' | 'Nature' | 'Museum' | 'Religion' | 'Default' | string;
    rating: string;
    hours: string;
    description: string;
    lat: number;
    lon: number;
}

export type TabType = 'explore' | 'route' | 'favorites';