import CityCard from "./components/CityCard";

interface Props {
  regionTitle: string;
  cities: string[];
  onBack: () => void;
  onCitySelect: (city: string) => void;
}

export default function CitySelect({
  regionTitle,
  cities,
  onBack,
  onCitySelect,
}: Props) {
  return (
    <main
      style={{
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <button onClick={onBack}>
        ← Back
      </button>

      <h1>{regionTitle}</h1>

      {cities.map(city => (
        <CityCard
          key={city}
          title={city}
          onClick={() => onCitySelect(city)}
        />
      ))}
    </main>
  );
}