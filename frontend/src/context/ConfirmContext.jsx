import { createContext, useCallback, useContext, useRef, useState } from "react";
import "../styles/confirm-dialog.css";

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const [dialog, setDialog] = useState(null);
  const resolverRef = useRef(null);

  const close = useCallback((result) => {
    resolverRef.current?.(result);
    resolverRef.current = null;
    setDialog(null);
  }, []);

  const confirm = useCallback((message, options = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setDialog({
        message,
        mode: "confirm",
        title: options.title || (options.danger ? "Confirm Removal" : "Confirm Action"),
        confirmLabel: options.confirmLabel || "OK",
        cancelLabel: options.cancelLabel || "Cancel",
        danger: options.danger || false,
      });
    });
  }, []);

  const alertModal = useCallback((message, options = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = () => resolve();
      setDialog({
        message,
        mode: "alert",
        title: options.title || "Notice",
        confirmLabel: options.confirmLabel || "OK",
        danger: options.danger || false,
      });
    });
  }, []);

  return (
    <ConfirmContext.Provider value={{ confirm, alert: alertModal }}>
      {children}
      {dialog && (
        <div className="cf-overlay" onClick={() => close(dialog.mode === "confirm" ? false : undefined)}>
          <div className={`cf-dialog${dialog.danger ? " cf-dialog--danger" : ""}`} onClick={(e) => e.stopPropagation()}>
            <div className="cf-icon">
              {dialog.mode === "alert" ? (dialog.danger ? "!" : "✓") : (dialog.danger ? "!" : "?")}
            </div>
            <p className="cf-eyebrow">{dialog.title}</p>
            <p className="cf-message">{dialog.message}</p>
            <div className="cf-divider" />
            <div className="cf-actions">
              {dialog.mode === "confirm" && (
                <button type="button" className="cf-btn cf-btn--cancel" onClick={() => close(false)}>
                  {dialog.cancelLabel}
                </button>
              )}
              <button
                type="button"
                className={`cf-btn cf-btn--confirm${dialog.danger ? " cf-btn--danger" : ""}`}
                onClick={() => close(dialog.mode === "confirm" ? true : undefined)}
                autoFocus
              >
                {dialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a ConfirmProvider");
  return ctx.confirm;
}

export function useAlert() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useAlert must be used within a ConfirmProvider");
  return ctx.alert;
}
