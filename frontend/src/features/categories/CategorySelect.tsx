import CategoryBanner from "../../shared/components/CategoryBanner";
import { categories } from "../../data/categories";

interface Props {
  city: string;
  onBack: () => void;
}

export default function CategorySelect({
  city,
  onBack,
}: Props) {
  return (
    <main
      style={{
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <button onClick={onBack}>
        ← Back
      </button>

      <h1>{city}</h1>

      {categories.map(category => (
        <CategoryBanner
          key={category.id}
          title={category.title}
          image={category.image}
          description="Explore places"
        />
      ))}
    </main>
  );
}