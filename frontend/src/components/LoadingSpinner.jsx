import styles from "../styles/components/LoadingSpinner.module.css";

export default function LoadingSpinner() {
  return (
    <div className={styles.spinnerWrapper}>
      <div className={styles.spinner} />
    </div>
  );
}
