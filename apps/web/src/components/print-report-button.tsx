"use client";

export function PrintReportButton() {
  return (
    <button className="button primary" onClick={() => window.print()} type="button">
      打印 / 另存为 PDF
    </button>
  );
}
