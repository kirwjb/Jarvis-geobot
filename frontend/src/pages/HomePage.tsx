import { useState } from "react";

import CitySelect from "../features/cities/CitySelect";
import CategorySelect from "../features/categories/CategorySelect";

import RegionCard from "../features/regions/components/RegionCard";

import { regions } from "../data/regions";
import { cities } from "../data/cities";

export default function HomePage() {
  const [selectedRegion, setSelectedRegion] =
    useState<string | null>(null);

  const [selectedCity, setSelectedCity] =
    useState<string | null>(null);

  if (selectedCity) {
    return (
      <CategorySelect
        city={selectedCity}
        onBack={() => setSelectedCity(null)}
      />
    );
  }

  if (selectedRegion) {
    return (
      <CitySelect
        regionTitle={
          regions.find(
            r => r.id === selectedRegion
          )?.title || ""
        }
        cities={
          cities[
            selectedRegion as keyof typeof cities
          ]
        }
        onBack={() => setSelectedRegion(null)}
        onCitySelect={setSelectedCity}
      />
    );
  }

  return (
    <main
      style={{
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <h1>🇧🇾 Explore Belarus</h1>

      {regions.map(region => (
        <RegionCard
          key={region.id}
          title={region.title}
          onClick={() => {
            setSelectedRegion(region.id);
          }}
        />
      ))}
    </main>
  );
}