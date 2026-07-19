interface Props {
  title: string;
  onClick: () => void;
}

export default function RegionCard({
  title,
  onClick,
}: Props) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "20px",
        borderRadius: "20px",
        background: "#1f232b",
        color: "white",
        cursor: "pointer",
      }}
    >
      <h3>{title}</h3>
    </div>
  );
}