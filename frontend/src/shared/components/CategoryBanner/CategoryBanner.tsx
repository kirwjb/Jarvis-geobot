import styles from "./CategoryBanner.module.css";
import type { CategoryBannerProps } from "./types";

export default function CategoryBanner({
  title,
  image,
  description,
}: CategoryBannerProps) {
  return (
    <div className={styles.banner}>
      <img
        src={image}
        alt={title}
        className={styles.background}
      />

      <div className={styles.overlay}>
        <h3>{title}</h3>

        <span>{description}</span>
        </div>
      </div>
  );
}

