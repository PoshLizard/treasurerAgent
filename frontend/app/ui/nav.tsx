"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArchiveIcon, ChatIcon, ReceiptIcon } from "./icons";

const LINKS = [
  { href: "/", label: "Process receipt", Icon: ReceiptIcon },
  { href: "/ask", label: "Ask a question", Icon: ChatIcon },
  { href: "/receipts", label: "Saved receipts", Icon: ArchiveIcon },
];

function isActive(href: string, pathname: string | null) {
  return href === "/" ? pathname === "/" : Boolean(pathname?.startsWith(href));
}

// Takes the pathname as a prop so the layout can render it without one while the real pathname loads
export function NavLinks({ pathname }: { pathname: string | null }) {
  return (
    <ul className="grid grid-cols-3 gap-1 md:flex md:flex-col">
      {LINKS.map(({ href, label, Icon }) => {
        const active = isActive(href, pathname);
        return (
          <li key={href}>
            <Link
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center gap-1 border px-2 py-2 text-center text-xs font-medium sm:flex-row sm:justify-center sm:gap-2.5 sm:text-sm md:justify-start md:px-3 md:text-left ${
                active ? "border-ink bg-ink text-panel" : "border-transparent hover:border-ink"
              }`}
            >
              <Icon />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function CurrentNavLinks() {
  return <NavLinks pathname={usePathname()} />;
}
