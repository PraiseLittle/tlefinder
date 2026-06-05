export interface Toast {
  id: number;
  msg: string;
  kind: "info" | "success" | "error";
}

export function ToastStack({ toasts }: { toasts: Toast[] }) {
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={"toast " + t.kind}>{t.msg}</div>
      ))}
    </div>
  );
}
