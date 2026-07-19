interface Props {
  title: string;
  rating: number;
}

export default function PlaceCard({
  title,
  rating,
}: Props) {
  return (
    <div>
      <h3>{title}</h3>
      <span>⭐ {rating}</span>
    </div>
  );
}
