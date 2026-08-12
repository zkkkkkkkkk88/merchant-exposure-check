import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ScanAutoRefresh } from "@/components/scan-auto-refresh";

const { refreshMock } = vi.hoisted(() => ({ refreshMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}));

beforeEach(() => {
  vi.useFakeTimers();
  refreshMock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

it("refreshes active scans every two seconds and stops at a terminal state", () => {
  const { rerender } = render(<ScanAutoRefresh active />);

  act(() => vi.advanceTimersByTime(4000));
  expect(refreshMock).toHaveBeenCalledTimes(2);

  rerender(<ScanAutoRefresh active={false} />);
  act(() => vi.advanceTimersByTime(4000));
  expect(refreshMock).toHaveBeenCalledTimes(2);
});
