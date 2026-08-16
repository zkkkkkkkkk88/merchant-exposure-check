"use client";

export function PrintReportButton({
  disabled = false,
  disabledReason,
}: {
  disabled?: boolean;
  disabledReason?: string;
}) {
  return (
    <div className="report-print-control">
      <button
        className="button primary"
        disabled={disabled}
        onClick={() => {
          if (!disabled) window.print();
        }}
        type="button"
      >
        打印 / 另存为 PDF
      </button>
      {disabled && disabledReason && <small>{disabledReason}</small>}
    </div>
  );
}
