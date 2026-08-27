import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { AppShell } from "@/components/app-shell";
import { AccessRoleProvider } from "@/components/access-role-provider";
import { DemoMutationGuard } from "@/components/demo-mutation-guard";

it("shows the demo badge only for demo access", () => {
  const { rerender } = render(
    <AccessRoleProvider role="admin">
      <AppShell><p>内容</p></AppShell>
    </AccessRoleProvider>,
  );
  expect(screen.queryByText("演示模式")).not.toBeInTheDocument();

  rerender(
    <AccessRoleProvider role="demo">
      <AppShell><p>内容</p></AppShell>
    </AccessRoleProvider>,
  );
  expect(screen.getAllByText("演示模式").length).toBeGreaterThan(0);
});

it("blocks marked clicks and submits in demo mode with an announced explanation", () => {
  const action = vi.fn();
  render(
    <AccessRoleProvider role="demo">
      <DemoMutationGuard>
        <form onSubmit={action}>
          <button data-requires-admin="true" type="submit">保存资料</button>
        </form>
        <a href="/queries">查看问题</a>
      </DemoMutationGuard>
    </AccessRoleProvider>,
  );

  const button = screen.getByRole("button", { name: "保存资料" });
  fireEvent.click(button);
  expect(action).not.toHaveBeenCalled();
  expect(screen.getByRole("status")).toHaveTextContent("当前为演示权限，实际操作请联系管理员。");
  expect(button).toHaveFocus();

  fireEvent.submit(button.closest("form")!);
  expect(action).not.toHaveBeenCalled();
});

it("does not intercept unmarked read-only navigation", () => {
  render(
    <AccessRoleProvider role="demo">
      <DemoMutationGuard>
        <a href="/queries">查看问题</a>
      </DemoMutationGuard>
    </AccessRoleProvider>,
  );

  const link = screen.getByRole("link", { name: "查看问题" });
  const event = new MouseEvent("click", { bubbles: true, cancelable: true });
  link.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(false);
});
