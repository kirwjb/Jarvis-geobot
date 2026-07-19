interface Props {
  title: string;
  image: string;
}

export default function CategoryCard({
  title,
  image,
}: Props) {
  return (
    <div>
      <img src={image} alt={title} />
      <h3>{title}</h3>
    </div>
  );
}
