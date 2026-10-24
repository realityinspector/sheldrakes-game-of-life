import { Link } from "@tanstack/react-router";

const tab = "inline-flex h-11 items-center rounded-full px-3 text-sm";

export function LabBrand({ titleAsHeading = true }: { titleAsHeading?: boolean }) {
  const Title = titleAsHeading ? "h1" : "p";
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span
        aria-hidden="true"
        className="grid size-11 shrink-0 place-items-center rounded-full border border-line bg-panel"
      >
        <span className="size-3 rotate-45 rounded-sm bg-life" />
      </span>
      <div className="min-w-0">
        <p className="text-xs tracking-widest text-mist uppercase">Morphic laboratory</p>
        <Title className="font-display text-3xl leading-none font-medium text-bone italic">
          Sheldrake
        </Title>
        <nav
          aria-label="Sections"
          className="mt-2 flex w-fit max-w-full flex-wrap gap-1 rounded-full border border-line bg-ink p-1"
        >
          <Link
            to="/"
            activeOptions={{ exact: true }}
            className={tab}
            activeProps={{ className: "bg-panel-2 text-bone" }}
            inactiveProps={{ className: "text-mist" }}
          >
            Laboratory
          </Link>
          <Link
            to="/sweep"
            activeOptions={{ exact: true }}
            className={tab}
            activeProps={{ className: "bg-panel-2 text-bone" }}
            inactiveProps={{ className: "text-mist" }}
          >
            Sweep
          </Link>
          <Link
            to="/method"
            activeOptions={{ exact: true }}
            className={tab}
            activeProps={{ className: "bg-panel-2 text-bone" }}
            inactiveProps={{ className: "text-mist" }}
          >
            Method
          </Link>
        </nav>
      </div>
    </div>
  );
}
