import { createFileRoute } from "@tanstack/react-router";
import { SweepPage } from "@/components/sweep-page";

export const Route = createFileRoute("/sweep")({
  head: () => ({
    meta: [{ title: "Sweep — Sheldrake" }],
  }),
  component: SweepPage,
});
