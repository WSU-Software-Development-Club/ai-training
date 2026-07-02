import styles from "../styles/components/LoadingSpinner.module.css";

export default function LoadingSpinner({ inline = false }) {
  return (
    <div className={inline ? styles.spinnerWrapperInline : styles.spinnerWrapper}>
      <div className={styles.spinner} />
    </div>
  );
}
