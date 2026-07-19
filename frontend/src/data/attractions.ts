import { Landmark, TreePine, Palette, Church, Map } from 'lucide-react';
import { Attraction } from '../types';

export const ATTRACTIONS: Attraction[] = [
    {
        id: "1",
        title: "National Library of Belarus",
        location: "Minsk",
        address: "Nezavisimosti Ave 116",
        category: "Architecture",
        rating: "4.8",
        hours: "10:00 - 21:00",
        description: "An architectural icon in the shape of a rhombicuboctahedron. Features a spectacular rooftop viewing deck at 73 meters offering panoramic views over Minsk.",
        lat: 53.9314,
        lon: 27.6461
    },
    {
        id: "2",
        title: "Chelyuskintsev Park & Botanical Garden",
        location: "Minsk",
        address: "Surganova St 2v",
        category: "Nature",
        rating: "4.7",
        hours: "09:00 - 21:00",
        description: "A gorgeous green escape featuring a colossal collection of temperate flora, scenic pine alleys, and serene walking routes near the heart of the city.",
        lat: 53.9221,
        lon: 27.6148
    },
    {
        id: "3",
        title: "National Art Museum of Belarus",
        location: "Minsk",
        address: "Lenina St 20",
        category: "Museum",
        rating: "4.9",
        hours: "11:00 - 19:00",
        description: "The crown jewel of Belarusian culture. Boasts over thirty thousand masterworks of national, Russian, and international art behind classic colonnades.",
        lat: 53.8989,
        lon: 27.5612
    },
    {
        id: "4",
        title: "Church of Saints Simon and Helena",
        location: "Minsk",
        address: "Sovetskaya St 15",
        category: "Religion",
        rating: "4.9",
        hours: "07:00 - 20:00",
        description: "The 'Red Church'. A neo-Gothic brick marvel displaying gorgeous stain-glass windows, bronze castings, and deep historical resonance.",
        lat: 53.8964,
        lon: 27.5476
    },
    {
        id: "5",
        title: "Trinity Hill & Island of Tears",
        location: "Minsk",
        address: "Starovilenskaya St 16",
        category: "Architecture",
        rating: "4.8",
        hours: "Open 24/7",
        description: "The oldest surviving historic suburb of Minsk, rebuilt with nineteenth-century pastel-colored merchant houses on the bank of Svislach River.",
        lat: 53.9083,
        lon: 27.5564
    },
    {
        id: "6",
        title: "Minsk Botanical Garden Conservatory",
        location: "Minsk",
        address: "Akademičeskaja St 31",
        category: "Nature",
        rating: "4.6",
        hours: "10:00 - 19:00",
        description: "A modern glass dome housing lush tropical species, citrus orchards, and exquisite exotic plant exhibits that feel like an absolute rainforest.",
        lat: 53.9185,
        lon: 27.6192
    }
];

export const CATEGORIES = ["All", "Architecture", "Nature", "Museum", "Religion"];

export const CATEGORY_CONFIG: Record<string, any> = {
    Architecture: { color: "bg-blue-950/40 border-blue-500/20", textColor: "text-blue-400", icon: Landmark },
    Nature: { color: "bg-emerald-950/40 border-emerald-500/20", textColor: "text-emerald-400", icon: TreePine },
    Museum: { color: "bg-purple-950/40 border-purple-500/20", textColor: "text-purple-400", icon: Palette },
    Religion: { color: "bg-amber-950/40 border-amber-500/20", textColor: "text-amber-400", icon: Church },
    Default: { color: "bg-gray-800/40 border-gray-500/20", textColor: "text-gray-400", icon: Map }
};