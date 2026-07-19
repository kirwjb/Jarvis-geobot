interface Props {
  title: string;
  onClick: () => void;
}

export default function CityCard({
  title,
  onClick,
}: Props) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "18px",
        borderRadius: "16px",
        background: "#2b3038",
        color: "white",
        cursor: "pointer",
      }}
    >
      📍 {title}
    </div>
  );
}
