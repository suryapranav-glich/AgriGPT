import type { ReactNode } from "react";
import { Sidebar, OpenSidebarButton } from "./Sidebar";
import { Header } from "./Header";
import { useSidebar } from "../../contexts/SidebarContext";

export function PageWrapper({
  title,
  children,
  fullBleed = false,
}: {
  title: string;
  children: ReactNode;
  fullBleed?: boolean;
}) {
  const { open } = useSidebar();
  return (
    <div className="min-h-screen" style={{ background: "var(--c-bg)", color: "var(--c-ink)" }}>
      <Sidebar />
      <div
        className={`transition-[margin] duration-200 ease-out ${open ? "md:ml-[240px]" : "md:ml-[64px]"}`}
      >
        <Header title={title} />
        <div className="px-6 pt-3">
          <OpenSidebarButton />
        </div>
        <main className={fullBleed ? "page-fade" : "px-6 pb-6 pt-3 page-fade"}>{children}</main>
      </div>
    </div>
  );
}
